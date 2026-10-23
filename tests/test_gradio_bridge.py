import datetime as dt
from types import SimpleNamespace
from unittest.mock import Mock

from app import auth
from app.gradio_bridge import Bridge, Invocation
from app.models import Instance, User


def register(database):
    with database() as db:
        db.add(Instance(id="colab-fixture", public_url="https://fixture.gradio.live", local_url="http://127.0.0.1:7860",
                        started_at=dt.datetime.now(dt.timezone.utc), last_seen=dt.datetime.now(dt.timezone.utc)))
        db.commit()


def fake_bridge(client, monkeypatch):
    remote = Mock()
    remote.view_api.return_value = {"named_endpoints": {"/echo": {"parameters": [{"parameter_name": "value"}]}}}
    job = Mock()
    job.done.return_value = False
    job.outputs.return_value = ["prepared"]
    job.status.return_value = SimpleNamespace(code=SimpleNamespace(name="PROCESSING"))
    remote.submit.return_value = job
    factory = Mock(return_value=remote)
    client.app.state.gradio_bridge = Bridge(factory)
    monkeypatch.setenv("GRADIO_TRUSTED_ORIGINS", "https://fixture.gradio.live")
    monkeypatch.setenv("ENABLE_GRADIO_EXECUTION", "true")
    return remote, job, factory


def test_gradio_discovery_execution_same_session_and_no_replay(client, operator, database, monkeypatch):
    register(database)
    remote, job, factory = fake_bridge(client, monkeypatch)
    spec = client.get("/api/v1/gradio/instances/colab-fixture/schema", headers=operator).json()
    assert remote.submit.call_count == 0
    body = {"idempotency_key": "gradio-unique-1", "api_name": "/echo", "schema_hash": spec["schema_hash"],
            "arguments": ["value"], "confirmation": "EXECUTE"}
    call = client.post("/api/v1/gradio/instances/colab-fixture/calls", headers=operator, json=body)
    assert call.status_code == 201, call.text
    identity = call.json()["id"]
    assert client.post("/api/v1/gradio/instances/colab-fixture/calls", headers=operator, json=body).json()["id"] == identity
    assert factory.call_count == 1
    remote.submit.assert_called_once_with("value", api_name="/echo")
    job.done.return_value = True
    assert client.get("/api/v1/gradio/calls/" + identity, headers=operator).json()["state"] == "succeeded"
    client.app.state.gradio_bridge = Bridge(factory)
    assert client.post("/api/v1/gradio/instances/colab-fixture/calls", headers=operator, json=body).json()["state"] == "succeeded"
    assert remote.submit.call_count == 1


def test_gradio_restart_ambiguity_and_schema_fences(client, operator, database, monkeypatch):
    register(database)
    remote, job, factory = fake_bridge(client, monkeypatch)
    spec = client.get("/api/v1/gradio/instances/colab-fixture/schema", headers=operator).json()
    body = {"idempotency_key": "gradio-unique-2", "api_name": "/echo", "schema_hash": "0"*64,
            "arguments": ["value"], "confirmation": "EXECUTE"}
    assert client.post("/api/v1/gradio/instances/colab-fixture/calls", headers=operator, json=body).status_code == 409
    body["schema_hash"] = spec["schema_hash"]
    call = client.post("/api/v1/gradio/instances/colab-fixture/calls", headers=operator, json=body).json()
    client.app.state.gradio_bridge = Bridge(factory)
    result = client.get("/api/v1/gradio/calls/" + call["id"], headers=operator).json()
    assert result["state"] == "uncertain"
    assert client.post("/api/v1/gradio/instances/colab-fixture/calls", headers=operator, json=body).json()["state"] == "uncertain"
    assert remote.submit.call_count == 1


def test_gradio_requires_trust_and_explicit_execution(client, operator, database, monkeypatch):
    register(database)
    fake_bridge(client, monkeypatch)
    monkeypatch.setenv("GRADIO_TRUSTED_ORIGINS", "")
    assert client.get("/api/v1/gradio/instances/colab-fixture/schema", headers=operator).status_code == 403
    assert client.get("/api/v1/gradio/instances").status_code == 401


def test_cookie_api_requires_csrf_and_expired_sessions_fail(client, database):
    with database() as db:
        user = User(email="operator@example.test", hashed_password="unused", is_admin=True)
        db.add(user)
        db.commit()
        token = auth.create_session_token(user.id)
        expired = auth._get_serializer().dumps({"user_id": user.id, "issued_at": 1})
    client.cookies.set("url_registry_session", expired)
    assert client.get("/api/v1/workers").status_code == 401
    client.cookies.set("url_registry_session", token)
    response = client.get("/api/v1/session")
    assert response.status_code == 200
    data = {"name": "cookie worker", "platform": "android", "capabilities": ["runtime.probe"]}
    assert client.post("/api/v1/workers", json=data).status_code == 403
    assert client.post("/api/v1/workers", json=data, headers={"X-CSRF-Token": response.json()["csrf_token"]}).status_code == 201


def test_rotation_revokes_old_credential_and_cancels_queue(client, operator, paired):
    job = client.post("/api/v1/jobs", headers=operator, json={
        "idempotency_key": "rotation-queued", "worker_id": paired["id"], "operation": "runtime.probe"}).json()
    response = client.post("/api/v1/workers/" + paired["id"] + "/rotate", headers=operator)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/worker", headers=paired["headers"]).status_code == 401
    new_headers = {"Authorization": "Bearer " + response.json()["worker_token"]}
    assert client.get("/api/v1/worker", headers=new_headers).status_code == 200
    assert client.get("/api/v1/jobs", headers=operator).json()[0]["state"] == "cancelled"

