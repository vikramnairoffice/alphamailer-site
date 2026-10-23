"""Authenticated access to registered, explicitly trusted Gradio sessions.

Run one coordinator process for this bridge: Gradio client session state and live
job handles are process-owned. The durable call ledger prevents restart replay.
"""
from __future__ import annotations
import hashlib
import base64
import json
import os
import secrets
import threading
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import String, JSON, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, Session

from .database import Base, get_db
from .fleet_routes import require_operator
from .fleet_schemas import StrictModel
from .models import Instance

router = APIRouter(prefix="/api/v1/gradio", tags=["Gradio"], dependencies=[Depends(require_operator)])


class Invocation(Base):
    __tablename__ = "gradio_invocations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    instance_id: Mapped[str] = mapped_column(String(64), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    endpoint: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSON, default=dict)


class Invoke(StrictModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    api_name: str = Field(min_length=1, max_length=120)
    schema_hash: str = Field(min_length=64, max_length=64)
    arguments: list = Field(default_factory=list, max_length=200)
    confirmation: str


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Bridge:
    def __init__(self, client_factory=None):
        self.factory = client_factory
        self.clients = {}
        self.handles = {}
        self.pending = set()
        self.staging = {}
        self.lock = threading.RLock()

    def connect(self, instance):
        url = instance.public_url or instance.local_url
        parsed = urlparse(url)
        trusted = {value.strip() for value in os.getenv("GRADIO_TRUSTED_ORIGINS", "").split(",") if value.strip()}
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in trusted or parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            raise HTTPException(403, "Add this runner's exact origin to GRADIO_TRUSTED_ORIGINS")
        key = (instance.id, url)
        with self.lock:
            if key not in self.clients:
                factory = self.factory
                if factory is None:
                    from gradio_client import Client
                    factory = Client
                auth_by_id = json.loads(os.getenv("GRADIO_AUTH_JSON", "{}"))
                credentials = auth_by_id.get(instance.id)
                self.clients[key] = factory(url, verbose=False,
                    auth=tuple(credentials) if credentials else None,
                    httpx_kwargs={"timeout": 30})
            return self.clients[key]

    def stage_arguments(self, arguments, identity):
        """Accept bounded uploaded bytes, never operator-supplied server paths."""
        directory = tempfile.TemporaryDirectory(prefix="alphamailer-gradio-upload-")
        count = 0
        def convert(value):
            nonlocal count
            if isinstance(value, list):
                return [convert(item) for item in value]
            if not isinstance(value, dict):
                return value
            if "__alphamailer_upload__" in value:
                if set(value) != {"__alphamailer_upload__"}:
                    raise HTTPException(422, "Invalid uploaded file marker")
                file = value["__alphamailer_upload__"]
                if not isinstance(file, dict) or set(file) != {"name", "data_base64"}:
                    raise HTTPException(422, "Upload requires a name and base64 bytes")
                name = file["name"]
                if not isinstance(name, str) or not 1 <= len(name) <= 180 or name in (".", "..") or any(c in name for c in "/\\\x00\r\n"):
                    raise HTTPException(422, "Invalid uploaded filename")
                try:
                    data = base64.b64decode(file["data_base64"], validate=True)
                except Exception:
                    raise HTTPException(422, "Invalid upload encoding")
                count += 1
                if len(data) > 500_000 or count > 8:
                    raise HTTPException(422, "Upload exceeds the connector limit")
                path = Path(directory.name) / str(count) / name
                path.parent.mkdir()
                path.write_bytes(data)
                from gradio_client import handle_file
                return handle_file(str(path))
            if isinstance(value.get("meta"), dict) and value["meta"].get("_type") == "gradio.FileData":
                raise HTTPException(422, "Upload file bytes instead of supplying server filesystem paths")
            return {key: convert(item) for key, item in value.items()}
        try:
            result = convert(arguments)
            if count:
                self.staging[identity] = directory
            else:
                directory.cleanup()
            return result
        except BaseException:
            directory.cleanup()
            raise

    def discover(self, instance):
        client = self.connect(instance)
        spec = client.view_api(return_format="dict", print_info=False)
        named = spec.get("named_endpoints", {})
        return {"named_endpoints": named, "schema_hash": fingerprint(named),
                "execution_enabled": os.getenv("ENABLE_GRADIO_EXECUTION", "false").lower() == "true"}

    def view(self, db, invocation):
        if invocation.state in ("running", "cancel_requested"):
            with self.lock:
                handle = self.handles.get(invocation.id)
                if invocation.id in self.pending:
                    return {"id": invocation.id, "instance_id": invocation.instance_id,
                            "api_name": invocation.endpoint, "state": "running", "result": {}}
            if handle is None:
                invocation.state = "uncertain"
                invocation.result = {"reason": "Client session was lost; remote execution was not replayed."}
            else:
                try:
                    status = handle.status()
                    outputs = handle.outputs()
                    # Outputs are authenticated operator data, never printed to server logs.
                    last = outputs[-1] if outputs else None
                    if len(json.dumps(last, default=str)) > 64000:
                        last = {"note": "Output exceeds dashboard limit; inspect the original instance."}
                    invocation.result = {"remote_status": status.code.name, "latest_output": last}
                    if handle.done():
                        handle.result()
                        invocation.state = "succeeded"
                except Exception:
                    invocation.state = "uncertain"
                    invocation.result = {"reason": "Remote acceptance or completion could not be confirmed."}
                if invocation.state not in ("running", "cancel_requested"):
                    with self.lock:
                        self.handles.pop(invocation.id, None)
                        staged = self.staging.pop(invocation.id, None)
                        if staged is not None:
                            staged.cleanup()
            db.commit()
        return {"id": invocation.id, "instance_id": invocation.instance_id,
                "api_name": invocation.endpoint, "state": invocation.state, "result": invocation.result}

    def invoke(self, db, instance, body):
        digest = fingerprint([instance.id, instance.public_url or instance.local_url,
                              body.api_name, body.schema_hash, body.arguments])
        # Serialize submissions per instance with a database write lock.
        db.execute(update(Instance).where(Instance.id == instance.id).values(host=Instance.host))
        previous = db.scalar(select(Invocation).where(Invocation.idempotency_key == body.idempotency_key))
        if previous:
            if previous.fingerprint != digest:
                raise HTTPException(409, "Idempotency key already used for another command")
            db.commit()
            return self.view(db, previous)
        if body.confirmation != "EXECUTE" or os.getenv("ENABLE_GRADIO_EXECUTION", "false").lower() != "true":
            raise HTTPException(403, "Remote execution requires enablement and EXECUTE confirmation")
        if len(json.dumps(body.arguments)) > 1_000_000:
            raise HTTPException(422, "Arguments exceed the connector limit")
        spec = self.discover(instance)
        if spec["schema_hash"] != body.schema_hash or body.api_name not in spec["named_endpoints"]:
            raise HTTPException(409, "Runner API changed; inspect its current schema")
        endpoint = spec["named_endpoints"][body.api_name]
        parameters = endpoint.get("parameters", [])
        if len(body.arguments) != len(parameters):
            raise HTTPException(422, "Provide one value for every exposed parameter, including defaults")
        active = db.scalar(select(Invocation).where(Invocation.instance_id == instance.id,
                                                    Invocation.state.in_(("running", "cancel_requested"))))
        # Explicit pause/stop callbacks may need the same session while a campaign runs.
        controls = {"/pause_campaign", "/stop_campaign", "/pause_multi_campaign", "/stop_multi_campaign"}
        if active and body.api_name not in controls:
            raise HTTPException(409, "A command is already running in this instance session")
        invocation = Invocation(id=secrets.token_hex(16), idempotency_key=body.idempotency_key,
                                instance_id=instance.id, fingerprint=digest, endpoint=body.api_name,
                                state="running", result={})
        arguments = self.stage_arguments(body.arguments, invocation.id)
        db.add(invocation)
        with self.lock:
            self.pending.add(invocation.id)
        try:
            db.commit()  # Durable effect fence. Never reissue on restart.
        except IntegrityError:
            db.rollback()
            with self.lock:
                self.pending.discard(invocation.id)
                staged = self.staging.pop(invocation.id, None)
                if staged is not None:
                    staged.cleanup()
            raise HTTPException(409, "Concurrent duplicate submission; retrieve the existing call")
        try:
            handle = self.connect(instance).submit(*arguments, api_name=body.api_name)
            with self.lock:
                self.handles[invocation.id] = handle
                self.pending.discard(invocation.id)
        except Exception:
            invocation.state = "uncertain"
            invocation.result = {"reason": "Submission acceptance was not confirmed; do not automatically resubmit."}
            db.commit()
            with self.lock:
                self.pending.discard(invocation.id)
                staged = self.staging.pop(invocation.id, None)
                if staged is not None:
                    staged.cleanup()
        return self.view(db, invocation)


def bridge(request: Request):
    return request.app.state.gradio_bridge


def instance(db, instance_id):
    row = db.get(Instance, instance_id)
    if row is None:
        raise HTTPException(404, "Instance not found")
    return row


@router.get("/instances")
def instances(db: Session = Depends(get_db)):
    return [{"id": row.id, "name": row.session_name or row.id,
             "url": row.public_url or row.local_url}
            for row in db.scalars(select(Instance).order_by(Instance.last_seen.desc()))]


@router.get("/instances/{identity}/schema")
def schema(identity: str, adapter=Depends(bridge), db: Session = Depends(get_db)):
    return adapter.discover(instance(db, identity))


@router.post("/instances/{identity}/calls", status_code=201)
def invoke(identity: str, body: Invoke, adapter=Depends(bridge), db: Session = Depends(get_db)):
    return adapter.invoke(db, instance(db, identity), body)


@router.get("/calls")
def calls(adapter=Depends(bridge), db: Session = Depends(get_db)):
    rows = db.scalars(select(Invocation).order_by(Invocation.id.desc()).limit(100)).all()
    return [adapter.view(db, row) for row in rows]


@router.get("/calls/{identity}")
def call(identity: str, adapter=Depends(bridge), db: Session = Depends(get_db)):
    row = db.get(Invocation, identity)
    if row is None:
        raise HTTPException(404, "Call not found")
    return adapter.view(db, row)


@router.post("/calls/{identity}/cancel")
def cancel(identity: str, adapter=Depends(bridge), db: Session = Depends(get_db)):
    row = db.get(Invocation, identity)
    if row is None:
        raise HTTPException(404, "Call not found")
    with adapter.lock:
        handle = adapter.handles.get(identity)
    if handle is None:
        return adapter.view(db, row)
    handle.cancel()
    row.state = "cancel_requested"
    row.result = {"note": "Cancellation requested; use the runner's stop callback for campaign control."}
    db.commit()
    return {"id": row.id, "state": row.state, "result": row.result}
