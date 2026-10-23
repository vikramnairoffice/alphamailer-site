from app import fleet_service as service
from test_fleet import claim, report


def test_android_commands_retain_payload_and_enforce_account_and_send_fences(client, operator, monkeypatch):
    worker = client.post("/api/v1/workers", headers=operator, json={
        "name":"Device", "platform":"android", "capabilities":["runtime.probe","engine.command"],
        "accounts":["device@example.test"]}).json()
    worker["headers"] = {"Authorization":"Bearer " + worker["worker_token"]}
    client.post("/api/v1/worker/heartbeat", headers=worker["headers"], json={"session_id":"fixture-session"})
    body = {"worker_id":worker["id"],"idempotency_key":"engine-fixture-job","operation":"engine.command",
        "account_email":"device@example.test","engine":{"command":"message.prepare",
            "parameters":{"lead":"recipient@example.test","config":{"subject_override":"Fixture"}}}}
    assert client.post("/api/v1/jobs", headers=operator, json=body).status_code == 201
    lease = claim(client, worker, "device@example.test").json()
    assert lease["job"]["engine"] == body["engine"]
    assert report(client, worker, lease, "running").status_code == 200
    assert report(client, worker, lease, "sending").status_code == 409
    assert report(client, worker, lease, "succeeded", result={"id":"prepared-fixture"}).status_code == 200
    body["idempotency_key"] = "engine-delivery-fixture"
    body["engine"] = {"command":"message.execute","parameters":{"prepared_id":"prepared-fixture"}}
    assert client.post("/api/v1/jobs", headers=operator, json=body).status_code == 422
    body.update(execution="send", confirmation="SEND")
    assert client.post("/api/v1/jobs", headers=operator, json=body).status_code == 403
    body["engine"] = {"command":"account.put","parameters":{}}
    assert client.post("/api/v1/jobs", headers=operator, json=body).status_code == 422


def test_gradio_inline_upload_is_staged_and_server_paths_are_rejected(tmp_path):
    import base64
    from pathlib import Path
    import pytest
    from fastapi import HTTPException
    from app.gradio_bridge import Bridge
    bridge = Bridge()
    result = bridge.stage_arguments([{"__alphamailer_upload__":{
        "name":"leads.txt","data_base64":base64.b64encode(b"fixture@example.test").decode()}}], "fixture")
    assert Path(result[0]["path"]).read_bytes() == b"fixture@example.test"
    bridge.staging.pop("fixture").cleanup()
    with pytest.raises(HTTPException):
        bridge.stage_arguments([{"path":str(tmp_path / "secret"),"meta":{"_type":"gradio.FileData"}}], "other")
