"""Opt-in integration test against an actual local Gradio server, never Gmail."""
import datetime as dt
import base64
import os
from pathlib import Path
import socket
import subprocess
import time

import httpx
import pytest
from app.gradio_bridge import Bridge, Invoke
from app.models import Instance

@pytest.mark.skipif(not os.getenv("GRADIO_FIXTURE_PYTHON"), reason="Specify a Python with Gradio installed")
def test_real_gradio_stream_and_shared_session(database, monkeypatch, tmp_path):
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    monkeypatch.setenv("GRADIO_TRUSTED_ORIGINS", url)
    monkeypatch.setenv("ENABLE_GRADIO_EXECUTION", "true")
    tool = Path(__file__).resolve().parents[1] / "tools/gradio_fixture.py"
    with (tmp_path / "fixture.log").open("w") as log:
        process = subprocess.Popen([os.environ["GRADIO_FIXTURE_PYTHON"], "-B", str(tool), "--port", str(port)],
                                   cwd=tmp_path, stdout=log, stderr=log)
        try:
            for attempt in range(180):
                if process.poll() is not None:
                    pytest.fail("Gradio fixture exited; inspect fixture.log")
                try:
                    if httpx.get(url + "/config", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                pytest.fail("Gradio fixture did not become ready")
            bridge = Bridge()
            with database() as db:
                runner = Instance(id="real-gradio", public_url=url, local_url=url,
                    started_at=dt.datetime.now(dt.timezone.utc), last_seen=dt.datetime.now(dt.timezone.utc))
                db.add(runner); db.commit()
                schema = bridge.discover(runner)
                def call(endpoint, arguments, key):
                    result = bridge.invoke(db, runner, Invoke(idempotency_key=key, api_name=endpoint,
                        schema_hash=schema["schema_hash"], arguments=arguments, confirmation="EXECUTE"))
                    for _ in range(150):
                        if result["state"] != "running":
                            return result
                        time.sleep(0.1)
                        from app.gradio_bridge import Invocation
                        result = bridge.view(db, db.get(Invocation, result["id"]))
                    pytest.fail("Remote job did not complete")
                result = call("/echo", ["fixture"], "real-echo-1")
                assert result["state"] == "succeeded", result
                assert result["result"]["latest_output"] == "complete:fixture"
                result = call("/count", [], "real-count-1")
                assert result["result"]["latest_output"] == "1"
                result = call("/read_upload", [{"__alphamailer_upload__": {
                    "name": "fixture.txt", "data_base64": base64.b64encode(b"file-upload-through-gradio").decode()
                }}], "real-file-1")
                assert result["state"] == "succeeded", result
                assert result["result"]["latest_output"] == "file-upload-through-gradio"
                assert not bridge.staging
        finally:
            process.terminate()
            process.wait(timeout=15)
