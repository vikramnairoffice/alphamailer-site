import datetime as dt
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import select

from app import google_oauth as oauth
from app.fleet_models import Worker


@pytest.fixture
def configured(tmp_path, monkeypatch):
    path = tmp_path / "web-client.json"
    client = {"client_id": "fixture.apps.googleusercontent.com", "client_secret": "fixture-client-secret",
              "redirect_uris": ["https://auth.example.test/oauth/google/callback"]}
    path.write_text(json.dumps({"web": client}))
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_FILE", str(path))
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", client["redirect_uris"][0])
    monkeypatch.setenv("GOOGLE_OAUTH_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return client


@pytest.fixture
def phone(client, operator):
    data = client.post("/api/v1/workers", headers=operator, json={
        "name": "Test phone", "platform": "android", "capabilities": ["runtime.probe", "engine.command"],
        "accounts": ["sender@example.test"], "max_parallel": 1}).json()
    return data | {"headers": {"Authorization": "Bearer " + data["worker_token"]}}


@pytest.fixture
def provider(monkeypatch):
    calls = []
    async def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url == oauth.TOKEN_URL:
            if kwargs["data"]["grant_type"] == "refresh_token":
                return {"access_token": "rotated-access", "refresh_token": "rotated-refresh", "expires_in": 3600}
            return {"access_token": "fixture-access", "refresh_token": "fixture-refresh", "expires_in": 3600,
                    "scope": " ".join(oauth.SCOPES)}
        assert url == oauth.USER_URL
        return {"email": "sender@example.test", "email_verified": True}
    monkeypatch.setattr(oauth, "google_request", request)
    return calls


def start(client, phone):
    response = client.post("/api/v1/worker/google/start", headers=phone["headers"],
                           json={"protocol_version": 1, "email": "sender@example.test"})
    assert response.status_code == 200, response.text
    return response.json()


def session(attempt):
    return {key: attempt[key] for key in ("protocol_version", "session_id", "handoff_key")}


def callback(client, attempt):
    state = parse_qs(urlsplit(attempt["authorization_url"]).query)["state"][0]
    return client.get("/oauth/google/callback", params={"state": state, "code": "fixture-code"}, follow_redirects=False)


def poll(client, phone, attempt):
    return client.post("/api/v1/worker/google/poll", headers=phone["headers"], json=session(attempt))


def test_browser_handoff_refresh_and_ack(client, phone, configured, provider, database):
    attempt = start(client, phone)
    params = parse_qs(urlsplit(attempt["authorization_url"]).query)
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent select_account"]
    assert params["code_challenge_method"] == ["S256"]
    assert phone["worker_token"] not in attempt["authorization_url"]
    assert configured["client_secret"] not in json.dumps(attempt)
    assert poll(client, phone, attempt).json()["status"] == "pending"
    response = callback(client, attempt)
    assert response.status_code == 303
    assert response.headers["location"] == "/oauth/google/complete"
    assert callback(client, attempt).status_code == 400
    assert len(provider) == 2
    import base64
    verifier = provider[0][2]["data"]["code_verifier"]
    assert base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode() == params["code_challenge"][0]
    result = poll(client, phone, attempt)
    assert result.headers["cache-control"] == "no-store"
    account = result.json()["account"]
    assert account["email"] == "sender@example.test"
    assert "client_secret" not in account["oauth"]
    # Retry before acknowledgement returns the same account, even from a new DB session.
    assert poll(client, phone, attempt).json()["account"] == account
    with database() as db:
        row = db.get(oauth.GoogleAuthorization, attempt["session_id"])
        assert row.context is None
        assert "fixture-refresh" not in row.result
        assert "fixture-access" not in row.result
    refreshed = client.post("/api/v1/worker/google/refresh", headers=phone["headers"], json={
        "refresh_token": account["oauth"]["refresh_token"],
        "receipt": account["oauth"]["alphamailer_broker"]["receipt"]})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["access_token"] == "rotated-access"
    assert "client_secret" not in refreshed.text
    for _ in range(2):
        assert client.post("/api/v1/worker/google/ack", headers=phone["headers"], json=session(attempt)).status_code == 200
    assert poll(client, phone, attempt).json()["status"] == "consumed"
    with database() as db:
        row = db.get(oauth.GoogleAuthorization, attempt["session_id"])
        assert row.result is None and row.context is None


def test_unauthorized_scope_and_expiry(client, phone, configured, paired, database):
    assert client.post("/api/v1/worker/google/start", json={"email": "sender@example.test"}).status_code == 401
    assert client.post("/api/v1/worker/google/start", headers=paired["headers"],
                       json={"email": "account0@example.com"}).status_code == 403
    assert client.post("/api/v1/worker/google/start", headers=phone["headers"],
                       json={"email": "stranger@example.test"}).status_code == 403
    attempt = start(client, phone)
    bad = session(attempt) | {"handoff_key": "x" * 43}
    assert client.post("/api/v1/worker/google/poll", headers=phone["headers"], json=bad).status_code == 404
    with database() as db:
        db.get(oauth.GoogleAuthorization, attempt["session_id"]).expires = int(time.time()) - 1
        db.commit()
    assert poll(client, phone, attempt).status_code == 404
    with database() as db:
        assert db.get(oauth.GoogleAuthorization, attempt["session_id"]) is None


@pytest.mark.parametrize("fault", ["wrong_email", "unverified", "no_refresh", "missing_scope", "denied"])
def test_no_handoff_for_failed_consent(client, phone, configured, monkeypatch, fault):
    async def provider(method, url, **kwargs):
        if url == oauth.TOKEN_URL:
            return {"access_token": "access", "refresh_token": "" if fault == "no_refresh" else "refresh",
                    "scope": "" if fault == "missing_scope" else " ".join(oauth.SCOPES)}
        return {"email": "other@example.test" if fault == "wrong_email" else "sender@example.test",
                "email_verified": fault != "unverified"}
    monkeypatch.setattr(oauth, "google_request", provider)
    attempt = start(client, phone)
    if fault == "denied":
        state = parse_qs(urlsplit(attempt["authorization_url"]).query)["state"][0]
        response = client.get("/oauth/google/callback", params={"state": state, "error": "access_denied"}, follow_redirects=False)
    else:
        response = callback(client, attempt)
    assert response.status_code == 303
    assert poll(client, phone, attempt).json() == {"protocol_version": 1, "status": "failed"}


def test_cancel_replace_and_worker_rotation(client, phone, configured, provider, operator):
    first = start(client, phone)
    second = start(client, phone)
    assert poll(client, phone, first).status_code == 404
    assert callback(client, first).status_code == 400
    assert client.post("/api/v1/worker/google/cancel", headers=phone["headers"], json=session(second)).status_code == 200
    assert callback(client, second).status_code == 400
    assert not provider
    third = start(client, phone)
    client.post(f"/api/v1/workers/{phone['id']}/rotate", headers=operator)
    assert callback(client, third).status_code == 303
    assert not provider
    assert poll(client, phone, third).status_code == 401


def test_other_worker_cannot_poll_or_refresh(client, phone, configured, provider, operator):
    attempt = start(client, phone)
    callback(client, attempt)
    account = poll(client, phone, attempt).json()["account"]
    second = client.post("/api/v1/workers", headers=operator, json={
        "name": "Other phone", "platform": "android", "capabilities": ["runtime.probe"],
        "accounts": ["sender@example.test"]}).json()
    headers = {"Authorization": "Bearer " + second["worker_token"]}
    assert client.post("/api/v1/worker/google/poll", headers=headers, json=session(attempt)).status_code == 404
    refresh = {"refresh_token": "fixture-refresh", "receipt": account["oauth"]["alphamailer_broker"]["receipt"]}
    assert client.post("/api/v1/worker/google/refresh", headers=headers, json=refresh).status_code == 403
    assert client.post("/api/v1/worker/google/refresh", headers=phone["headers"],
                       json=refresh | {"refresh_token": "wrong-refresh"}).status_code == 403


def test_configuration_and_validation_never_echo_secrets(client, phone, configured, monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost/oauth/google/callback")
    response = client.post("/api/v1/worker/google/start", headers=phone["headers"], json={"email": "sender@example.test"})
    assert response.status_code == 503
    assert configured["client_secret"] not in response.text
    response = client.post("/api/v1/worker/google/refresh", headers=phone["headers"],
                           json={"refresh_token": "sensitive-fixture", "receipt": "too-short"})
    assert response.status_code == 422
    assert "sensitive-fixture" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_callback_is_claimed_once_under_concurrency(client, phone, configured, provider):
    attempt = start(client, phone)
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: callback(client, attempt).status_code, range(2)))
    assert sorted(statuses) == [303, 400]
    assert len(provider) == 2


def test_exported_oauth_contracts_and_fixture():
    from pathlib import Path
    from app import fleet_schemas
    fixture = json.loads(Path("contracts/v1/fixtures/google-oauth.json").read_text())
    for name, key in [("GoogleOAuthStart", "start"), ("GoogleOAuthSession", "session"), ("GoogleOAuthRefresh", "refresh")]:
        model = getattr(fleet_schemas, name)
        assert json.loads(Path(f"contracts/v1/{name}.schema.json").read_text()) == model.model_json_schema()
        assert model.model_validate(fixture[key]).protocol_version == 1
