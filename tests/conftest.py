import os
import tempfile

# Set before importing the application: startup must never touch a real app.db.
_startup = tempfile.TemporaryDirectory(prefix="alphamailer-fleet-test-")
os.environ["DATABASE_URL"] = "sqlite:///" + _startup.name.replace("\\", "/") + "/startup.db"
os.environ["API_TOKEN"] = "test-operator-only"
os.environ["SESSION_SECRET"] = "test-session-secret-not-for-deployment"
os.environ["ENABLE_BROWSER_SEND"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import create_app
from app.database import Base, get_db


def pytest_sessionfinish(session, exitstatus):
    from app.database import engine
    engine.dispose()
    _startup.cleanup()


@pytest.fixture
def database(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "fleet.db"), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def client(database):
    def db():
        with database() as session:
            yield session
    app = create_app()
    app.dependency_overrides[get_db] = db
    with TestClient(app) as client:
        yield client


@pytest.fixture
def operator():
    return {"Authorization": "Bearer test-operator-only"}


@pytest.fixture
def paired(client, operator):
    response = client.post("/api/v1/workers", headers=operator, json={
        "name": "Fixture browser", "platform": "test", "capabilities": ["runtime.probe", "gmail.compose", "gmail.draft"],
        "accounts": [f"account{i}@example.com" for i in range(5)], "max_parallel": 5})
    assert response.status_code == 201, response.text
    worker = response.json()
    worker["headers"] = {"Authorization": "Bearer " + worker["worker_token"]}
    response = client.post("/api/v1/worker/heartbeat", headers=worker["headers"], json={"session_id": "fixture-session"})
    assert response.status_code == 200, response.text
    return worker
