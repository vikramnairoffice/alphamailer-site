"""Browser OAuth broker. No Google password or Android AccountManager access.

The web client secret stays on the server. Temporary handoff credentials are
encrypted, worker-bound, and erased on acknowledgement or expiry. Refresh tokens
live on the phone after handoff; an encrypted receipt binds refresh to that worker.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import time
import uuid
from urllib.parse import urlencode, urlsplit

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import httpx
from sqlalchemy import Integer, String, Text, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base, get_db
from .fleet_models import Worker
from .fleet_routes import require_worker
from .fleet_schemas import GoogleOAuthRefresh, GoogleOAuthSession, GoogleOAuthStart

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USER_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = ["https://www.googleapis.com/auth/userinfo.email",
          "https://www.googleapis.com/auth/gmail.compose"]
TTL = 600
HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache",
           "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"}
class SecretRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def guarded(request):
            try:
                return await handler(request)
            except RequestValidationError:
                # FastAPI's default error echoes invalid input, including tokens.
                return JSONResponse({"detail": "Invalid authorization request"}, 422, headers=HEADERS)
        return guarded


router = APIRouter(tags=["Google authorization"], route_class=SecretRoute)


class GoogleAuthorization(Base):
    __tablename__ = "google_authorization_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(64), unique=True)
    worker_token_hash: Mapped[str] = mapped_column(String(64))
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    handoff_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    expires: Mapped[int] = mapped_column(Integer)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def configuration():
    """Read an operator-controlled web-client JSON; never accept remote endpoints."""
    try:
        path = Path(os.environ["GOOGLE_OAUTH_CLIENT_FILE"])
        if path.stat().st_size > 32_768:
            raise ValueError()
        client = json.loads(path.read_text(encoding="utf-8"))["web"]
        redirect = os.environ["GOOGLE_OAUTH_REDIRECT_URI"]
        uri = urlsplit(redirect)
        if (uri.scheme != "https" or not uri.hostname or uri.username or uri.password
                or uri.query or uri.fragment or uri.path != "/oauth/google/callback"
                or redirect not in client["redirect_uris"]):
            raise ValueError()
        if not isinstance(client["client_id"], str) or not client["client_id"].endswith(".apps.googleusercontent.com"):
            raise ValueError()
        if not isinstance(client["client_secret"], str) or not client["client_secret"]:
            raise ValueError()
        cipher = Fernet(os.environ["GOOGLE_OAUTH_ENCRYPTION_KEY"].encode())
        return client, redirect, cipher
    except (KeyError, ValueError, TypeError, OSError):
        raise HTTPException(503, "Google browser authorization is not configured") from None


def seal(cipher, value):
    return cipher.encrypt(json.dumps(value).encode()).decode()


def unseal(cipher, value):
    try:
        return json.loads(cipher.decrypt(value.encode()))
    except (InvalidToken, ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Authorization expired; connect again") from None


def cleanup(db):
    db.execute(delete(GoogleAuthorization).where(GoogleAuthorization.expires <= int(time.time())))
    db.commit()


def android_worker(db, identity, email=None):
    worker = db.get(Worker, identity)
    if not worker or worker.platform != "android" or (email and email not in worker.accounts):
        raise HTTPException(403, "Pair this Android worker with the requested email first")
    return worker


def session_for(db, identity, body):
    cleanup(db)
    worker = android_worker(db, identity)
    row = db.get(GoogleAuthorization, body.session_id)
    if (not row or row.worker_id != identity or row.worker_token_hash != worker.token_hash
            or not secrets.compare_digest(row.handoff_hash, digest(body.handoff_key))):
        raise HTTPException(404, "Authorization session unavailable")
    return row


async def google_request(method, url, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as transport:
            response = await transport.request(method, url, **kwargs)
        if response.status_code != 200 or len(response.content) > 65_536:
            raise ValueError()
        value = response.json()
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (httpx.HTTPError, ValueError):
        # Provider bodies can contain credentials. Never include them in errors.
        raise HTTPException(502, "Google authorization failed; connect again") from None


@router.post("/api/v1/worker/google/start")
def start(body: GoogleOAuthStart, identity=Depends(require_worker), db: Session = Depends(get_db)):
    client, redirect, cipher = configuration()
    worker = android_worker(db, identity, body.email)
    cleanup(db)
    # At most one live attempt per worker. Restart explicitly replaces its attempt.
    db.execute(delete(GoogleAuthorization).where(GoogleAuthorization.worker_id == identity))
    state, handoff, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    row = GoogleAuthorization(id=str(uuid.uuid4()), worker_id=identity,
        worker_token_hash=worker.token_hash, state_hash=digest(state), handoff_hash=digest(handoff),
        status="pending", expires=int(time.time()) + TTL,
        context=seal(cipher, {"email": body.email, "verifier": verifier, "client_id": client["client_id"]}),
        result=None)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Another authorization started; try again") from None
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    url = AUTH_URL + "?" + urlencode({"client_id": client["client_id"], "redirect_uri": redirect,
        "response_type": "code", "scope": " ".join(SCOPES), "access_type": "offline",
        "prompt": "consent select_account", "login_hint": body.email, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    return JSONResponse({"protocol_version": 1, "session_id": row.id, "handoff_key": handoff,
                         "authorization_url": url, "expires_in": TTL}, headers=HEADERS)


@router.get("/oauth/google/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    params = request.query_params
    # Uvicorn must not record Google's code/state in its access log. Reverse
    # proxies must also suppress query logging for this endpoint (see setup guide).
    request.scope["query_string"] = b""
    cleanup(db)
    state = params.get("state", "")
    if len(state) > 128 or len(params.getlist("state")) != 1:
        return HTMLResponse("Authorization session unavailable. Return to Alphamailer.", 400, headers=HEADERS)
    row = db.scalar(select(GoogleAuthorization).where(GoogleAuthorization.state_hash == digest(state)))
    if not row or row.status != "pending":
        return HTMLResponse("Authorization session unavailable. Return to Alphamailer.", 400, headers=HEADERS)
    row_id, worker_id, worker_hash, context_text = row.id, row.worker_id, row.worker_token_hash, row.context
    # Database compare-and-set prevents callback replay across processes.
    claimed = db.execute(update(GoogleAuthorization).where(GoogleAuthorization.id == row_id,
        GoogleAuthorization.status == "pending").values(status="exchanging"))
    db.commit()
    if claimed.rowcount != 1:
        return HTMLResponse("Authorization already handled. Return to Alphamailer.", 400, headers=HEADERS)
    try:
        client, redirect, cipher = configuration()
        context = unseal(cipher, context_text)
        worker = android_worker(db, worker_id, context["email"])
        if worker.token_hash != worker_hash or context["client_id"] != client["client_id"]:
            raise HTTPException(400, "Authorization changed")
        code = params.get("code", "")
        if params.get("error") or not code or len(code) > 8192 or len(params.getlist("code")) != 1:
            raise HTTPException(400, "Authorization declined")
        token = await google_request("POST", TOKEN_URL, data={"code": code,
            "client_id": client["client_id"], "client_secret": client["client_secret"],
            "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": context["verifier"]})
        scopes = token.get("scope", "").split()
        if not set(SCOPES).issubset(scopes) or not token.get("refresh_token") or not token.get("access_token"):
            raise HTTPException(400, "Required permission or offline access not granted")
        user = await google_request("GET", USER_URL, headers={"Authorization": "Bearer " + token["access_token"]})
        if user.get("email_verified") is not True or str(user.get("email", "")).lower() != context["email"]:
            raise HTTPException(400, "The Google account does not match the requested email")
        import datetime as dt
        expires = int(token.get("expires_in", 3600))
        if not 0 < expires <= 86400:
            raise HTTPException(400, "Invalid token lifetime")
        receipt = seal(cipher, {"purpose": "google-refresh-v1", "worker_id": worker_id,
            "worker_token_hash": worker_hash, "refresh_hash": digest(token["refresh_token"]),
            "client_id": client["client_id"], "email": context["email"], "scopes": scopes})
        result = {"id": "google-" + digest(client["client_id"] + ":" + context["email"])[:32],
            "email": context["email"], "auth_type": "oauth", "oauth": {
                "type": "authorized_user", "token": token["access_token"],
                "refresh_token": token["refresh_token"], "client_id": client["client_id"],
                "scopes": scopes, "expiry": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=expires)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "alphamailer_broker": {"origin": redirect.removesuffix("/oauth/google/callback"), "receipt": receipt}}}
        # Cancellation/replacement during the provider exchange must win.
        db.execute(update(GoogleAuthorization).where(GoogleAuthorization.id == row_id,
            GoogleAuthorization.status == "exchanging", GoogleAuthorization.expires > int(time.time()))
            .values(status="ready", context=None, result=seal(cipher, result)))
        db.commit()
    except (HTTPException, ValueError, TypeError, KeyError):
        db.execute(update(GoogleAuthorization).where(GoogleAuthorization.id == row_id,
            GoogleAuthorization.status == "exchanging").values(status="failed", context=None, result=None))
        db.commit()
    return RedirectResponse("/oauth/google/complete", status_code=303, headers=HEADERS)


@router.get("/oauth/google/complete")
def complete():
    # The app link carries no tokens, codes, identity or session secrets. Opening
    # it merely wakes the app, which retrieves its own result over authenticated HTTPS.
    return HTMLResponse('''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width">
<title>Return to Alphamailer</title><body><h1>Return to Alphamailer</h1>
<p>The app will check the result and save the connected account securely.</p>
<p><a href="alphamailer://oauth/return">Open Alphamailer</a></p>
<script>window.location.replace('alphamailer://oauth/return');</script></body></html>''', headers={
        **HEADERS, "Content-Security-Policy": "default-src 'none'; script-src 'sha256-" +
        base64.b64encode(hashlib.sha256(b"window.location.replace('alphamailer://oauth/return');").digest()).decode() +
        "'; base-uri 'none'; frame-ancestors 'none'"})


@router.post("/api/v1/worker/google/poll")
def poll(body: GoogleOAuthSession, identity=Depends(require_worker), db: Session = Depends(get_db)):
    row = session_for(db, identity, body)
    response = {"protocol_version": 1, "status": row.status}
    if row.status == "ready":
        _, _, cipher = configuration()
        account = unseal(cipher, row.result)
        android_worker(db, identity, account["email"])
        response["account"] = account
    return JSONResponse(response, headers=HEADERS)


@router.post("/api/v1/worker/google/ack")
def acknowledge(body: GoogleOAuthSession, identity=Depends(require_worker), db: Session = Depends(get_db)):
    row = session_for(db, identity, body)
    if row.status not in ("ready", "consumed"):
        raise HTTPException(409, "No credential handoff to acknowledge")
    row.status, row.context, row.result = "consumed", None, None
    db.commit()
    return JSONResponse({"protocol_version": 1, "status": "consumed"}, headers=HEADERS)


@router.post("/api/v1/worker/google/cancel")
def cancel(body: GoogleOAuthSession, identity=Depends(require_worker), db: Session = Depends(get_db)):
    row = session_for(db, identity, body)
    row.status, row.context, row.result = "cancelled", None, None
    db.commit()
    return JSONResponse({"protocol_version": 1, "status": "cancelled"}, headers=HEADERS)


@router.post("/api/v1/worker/google/refresh")
async def refresh(body: GoogleOAuthRefresh, identity=Depends(require_worker), db: Session = Depends(get_db)):
    client, _, cipher = configuration()
    receipt = unseal(cipher, body.receipt)
    worker = android_worker(db, identity, receipt.get("email"))
    if (receipt.get("purpose") != "google-refresh-v1" or receipt.get("worker_id") != identity
            or receipt.get("worker_token_hash") != worker.token_hash
            or receipt.get("client_id") != client["client_id"]
            or not secrets.compare_digest(receipt.get("refresh_hash", ""), digest(body.refresh_token))):
        raise HTTPException(403, "Connect the Google account again")
    value = await google_request("POST", TOKEN_URL, data={"grant_type": "refresh_token",
        "refresh_token": body.refresh_token, "client_id": client["client_id"], "client_secret": client["client_secret"]})
    if not isinstance(value.get("access_token"), str) or not value["access_token"]:
        raise HTTPException(502, "Google token refresh failed")
    # Google normally retains the original refresh token, but preserve rotation.
    refresh_token = value.get("refresh_token", body.refresh_token)
    receipt["refresh_hash"] = digest(refresh_token)
    scopes = value.get("scope", " ".join(receipt["scopes"])).split()
    receipt["scopes"] = scopes
    return JSONResponse({"access_token": value["access_token"], "expires_in": value.get("expires_in", 3600),
        "refresh_token": refresh_token, "scope": " ".join(scopes), "receipt": seal(cipher, receipt)}, headers=HEADERS)
