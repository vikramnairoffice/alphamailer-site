import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select
from pydantic import ValidationError

from app import fleet_service as service
from app.fleet_schemas import Claim, JobCreate, PreparedMessage
from app.fleet_models import Job, Worker, JobEvent
from app.models import User
from app.auth import create_session_token


def queue(client, operator, worker, key="fixture-job-0001", account=None, **kw):
    body = {"worker_id": worker["id"], "idempotency_key": key, "operation": "runtime.probe"} | kw
    if account:
        body |= {"account_email": account, "operation": "gmail.compose", "message": {
            "to": ["recipient@example.com"], "subject": "Fixture", "body": "Hello"}}
    return client.post("/api/v1/jobs", headers=operator, json=body)


def claim(client, paired, account=None, slot="slot-one"):
    return client.post("/api/v1/worker/claim", headers=paired["headers"], json={
        "session_id": "fixture-session", "slot_id": slot, "account_email": account})


def report(client, paired, lease, state, **kw):
    return client.post("/api/v1/worker/report", headers=paired["headers"], json={
        "session_id": "fixture-session", "job_id": lease["job"]["id"],
        "lease_token": lease["lease_token"], "state": state, **kw})


def test_auth_and_protocol(client, operator, paired):
    assert client.get("/api/v1/workers").status_code == 401
    assert client.get("/api/v1/workers", headers=paired["headers"]).status_code == 401
    assert client.get("/api/v1/worker", headers=operator).status_code == 401
    assert "worker_token" not in client.get("/api/v1/workers", headers=operator).text
    assert client.post("/api/v1/worker/heartbeat", headers=paired["headers"], json={
        "session_id": "fixture-session", "protocol_version": 2}).status_code == 422


def test_idempotency_and_durable_result(client, operator, paired, database):
    first = queue(client, operator, paired).json()
    assert queue(client, operator, paired).json()["id"] == first["id"]
    assert queue(client, operator, paired, account="account0@example.com").status_code == 409
    lease = claim(client, paired).json()
    assert report(client, paired, lease, "running").status_code == 200
    result = {"python_available": True, "engine_available": False}
    assert report(client, paired, lease, "succeeded", result=result).status_code == 200
    assert report(client, paired, lease, "succeeded", result=result).status_code == 200
    with database() as restarted:
        assert restarted.get(Job, first["id"]).result == result
        assert len(restarted.scalars(select(JobEvent).where(JobEvent.job_id == first["id"])).all()) == 4
    assert report(client, paired, lease, "running").status_code == 409


def test_account_scope_and_send_gate(client, operator, paired):
    assert queue(client, operator, paired, account="other@example.com").status_code == 422
    assert queue(client, operator, paired, account="account0@example.com", execution="send", confirmation="SEND").status_code == 403
    queue(client, operator, paired, account="account0@example.com")
    lease = claim(client, paired, "account0@example.com").json()
    report(client, paired, lease, "running")
    assert report(client, paired, lease, "sending").status_code == 409
    assert claim(client, paired, "other@example.com").status_code == 403


def test_worker_lease_and_session_fences(client, operator, paired, database):
    queue(client, operator, paired)
    lease = claim(client, paired).json()
    bad = dict(lease, lease_token="x" * 32)
    assert report(client, paired, bad, "running").status_code == 403
    assert client.post("/api/v1/worker/heartbeat", headers=paired["headers"], json={"session_id": "other-session"}).status_code == 409
    other = client.post("/api/v1/workers", headers=operator, json={
        "name": "Other", "platform": "test", "capabilities": ["runtime.probe"]}).json()
    other["headers"] = {"Authorization": "Bearer " + other["worker_token"]}
    client.post("/api/v1/worker/heartbeat", headers=other["headers"], json={"session_id": "fixture-session"})
    assert report(client, other, lease, "running").status_code == 404
    assert client.get("/api/v1/worker/jobs", headers=other["headers"]).json() == []


def test_expired_browser_work_is_uncertain_and_not_retried(client, operator, paired, database):
    queue(client, operator, paired, account="account0@example.com")
    lease = claim(client, paired, "account0@example.com").json()
    with database() as db:
        job = db.get(Job, lease["job"]["id"])
        job.lease_expires_at = service.now() - dt.timedelta(seconds=1)
        db.commit()
    assert report(client, paired, lease, "succeeded").status_code == 409
    assert client.get("/api/v1/jobs", headers=operator).json()[0]["state"] == "uncertain"
    assert claim(client, paired, "account0@example.com").json()["job"] is None


def test_heartbeat_renews_only_valid_owned_leases(client, operator, paired):
    queue(client, operator, paired)
    lease = claim(client, paired).json()
    body = {"session_id": "fixture-session", "leases": [{"job_id": lease["job"]["id"], "lease_token": "x" * 32}]}
    assert client.post("/api/v1/worker/heartbeat", headers=paired["headers"], json=body).json()["renewed_job_ids"] == []
    body["leases"][0]["lease_token"] = lease["lease_token"]
    assert client.post("/api/v1/worker/heartbeat", headers=paired["headers"], json=body).json()["renewed_job_ids"] == [lease["job"]["id"]]


def test_concurrent_claims_enforce_account_slot_and_capacity(client, operator, paired, database):
    for i in range(20):
        assert queue(client, operator, paired, key=f"concurrent-job-{i}", account=f"account{i % 5}@example.com").status_code == 201
    def concurrent(i):
        with database() as db:
            return service.claim(db, paired["id"], Claim(session_id="fixture-session", slot_id=f"slot-{i % 5}", account_email=f"account{i % 5}@example.com"))
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(concurrent, range(30)))
    leased = [r["job"] for r in results if r["job"]]
    assert len(leased) == 5
    assert len({j["id"] for j in leased}) == len({j["account_email"] for j in leased}) == len({j["slot_id"] for j in leased}) == 5
    with database() as db:
        assert len(db.scalars(select(Job).where(Job.state == "leased")).all()) == 5


def test_cancel_and_events(client, operator, paired):
    job = queue(client, operator, paired).json()
    assert client.post(f"/api/v1/jobs/{job['id']}/cancel", headers=operator).json()["state"] == "cancelled"
    assert claim(client, paired).json()["job"] is None
    assert [e["state"] for e in client.get(f"/api/v1/jobs/{job['id']}/events", headers=operator).json()] == ["queued", "cancelled"]


def test_csrf_and_dashboard(client, operator, paired, database):
    with database() as db:
        user = User(email="operator@example.com", hashed_password="unused", is_admin=True)
        db.add(user)
        db.commit()
        token = create_session_token(user.id)
    client.cookies.set("url_registry_session", token)
    page = client.get("/admin/fleet")
    assert page.status_code == 200
    assert "Fixture browser" in page.text
    assert "worker_token" not in page.text
    assert page.headers["cache-control"] == "no-store"
    assert client.post("/admin/fleet/pair", data={"name": "bad", "platform": "android", "csrf": "bad"}).status_code == 403
    import re
    csrf = re.search('name="csrf" value="([^"]+)"', page.text).group(1)
    response = client.post("/admin/fleet/pair", data={"name": "Phone", "platform": "android", "csrf": csrf})
    assert response.status_code == 200 and "Worker paired: Phone" in response.text
    submission = re.search('name="submission_id" value="([^"]+)"', page.text).group(1)
    form = {"worker_id": paired["id"], "operation": "runtime.probe", "csrf": csrf, "submission_id": submission}
    assert client.post("/admin/fleet/jobs", data=form, follow_redirects=False).status_code == 303
    assert client.post("/admin/fleet/jobs", data=form, follow_redirects=False).status_code == 303
    with database() as db:
        assert len(db.scalars(select(Job)).all()) == 1


def test_legacy_registry_unchanged(client, operator):
    body = {"id": "legacy-instance", "local_url": "http://127.0.0.1:7860", "public_url": "https://fixture.gradio.live",
            "session_name": "Colab", "host": "fixture", "started_at": service.now().isoformat()}
    assert client.post("/api/instances", headers=operator, json=body).status_code == 200
    assert "legacy-instance" in client.get("/api/instances", headers=operator).text


@pytest.mark.parametrize("message_id", ["<broken@example.com", "broken@example.com>", "id@example.com in:sent"])
def test_draft_identity_rejects_ambiguous_values(message_id):
    with pytest.raises(ValidationError):
        PreparedMessage(to=["a@example.com"], subject="s", body="b", rfc822_message_id=message_id)


def test_gradio_discovery_never_invokes_a_campaign():
    from app.gradio_adapter import inspect_runner
    class Fake:
        def __init__(self, *args, **kwargs):
            pass
        def view_api(self, **kwargs):
            return {"named_endpoints": {"/start_campaign": {"parameters": []}}}
    result = inspect_runner("https://fixture.gradio.live", client_factory=Fake)
    assert not result["execution_enabled"]
    assert "/start_campaign" in result["named_endpoints"]


def test_sending_fence_and_disable_switch(client, operator, paired, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "enable_browser_send", True)
    queued = queue(client, operator, paired, account="account0@example.com", execution="send", confirmation="SEND")
    assert queued.status_code == 201
    lease = claim(client, paired, "account0@example.com").json()
    assert report(client, paired, lease, "succeeded").status_code == 409
    assert report(client, paired, lease, "running").status_code == 200
    monkeypatch.setattr(get_settings(), "enable_browser_send", False)
    assert report(client, paired, lease, "sending").status_code == 403
    monkeypatch.setattr(get_settings(), "enable_browser_send", True)
    assert report(client, paired, lease, "sending").status_code == 200
    assert report(client, paired, lease, "failed").status_code == 409
    assert report(client, paired, lease, "uncertain").status_code == 200
    assert claim(client, paired, "account0@example.com").json()["job"] is None


def test_contract_fixtures_and_export_are_current():
    import json
    from pathlib import Path
    from app import fleet_schemas as schemas
    root = Path(__file__).resolve().parents[1] / "contracts/v1"
    fixtures = json.loads((root / "fixtures.json").read_text())
    for name, model in (("android_claim", schemas.Claim), ("browser_claim", schemas.Claim),
                        ("compose_preview", schemas.JobCreate), ("probe_result", schemas.Report)):
        model.model_validate(fixtures[name])
    for name in ("WorkerCreate", "JobCreate", "Heartbeat", "Claim", "Report"):
        assert json.loads((root / f"{name}.schema.json").read_text()) == getattr(schemas, name).model_json_schema()


def test_additive_tables_preserve_old_rows(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.database import Base
    from app.models import Instance
    engine = create_engine("sqlite:///" + str(tmp_path / "old-registry.db"))
    User.__table__.create(engine)
    Instance.__table__.create(engine)
    with Session(engine) as db:
        db.add(User(email="old@example.com", hashed_password="existing-hash", is_admin=True))
        db.add(Instance(id="old-runner", local_url="http://localhost:7860", started_at=service.now(), last_seen=service.now()))
        db.commit()
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        assert db.scalar(select(User)).hashed_password == "existing-hash"
        assert db.get(Instance, "old-runner").local_url == "http://localhost:7860"
        assert db.scalars(select(Worker)).all() == []
    engine.dispose()


def test_offline_session_takeover_fences_old_claim(client, operator, paired, database):
    queue(client, operator, paired)
    lease = claim(client, paired).json()
    with database() as db:
        db.get(Worker, paired["id"]).last_seen = service.now() - dt.timedelta(seconds=121)
        db.commit()
    response = client.post("/api/v1/worker/heartbeat", headers=paired["headers"], json={"session_id": "replacement-session"})
    assert response.status_code == 200
    assert report(client, paired, lease, "succeeded").status_code == 409
    assert client.get("/api/v1/jobs", headers=operator).json()[0]["state"] == "failed"
