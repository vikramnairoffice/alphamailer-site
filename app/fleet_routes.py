from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, fleet_service as service, campaign_service
from .admin_routes import templates
from .config import get_settings
from .database import get_db
from .fleet_models import Worker, Job, JobEvent, Campaign
from .fleet_schemas import WorkerCreate, JobCreate, PreparedMessage, Heartbeat, Claim, Report, CampaignCreate

router = APIRouter(prefix="/api/v1", tags=["fleet"])
ui_router = APIRouter(prefix="/admin/fleet", tags=["fleet dashboard"])
async def require_operator(request: Request,
                           credentials=Depends(auth.http_bearer),
                           user=Depends(auth.get_current_user)):
    if credentials is not None:
        await auth.require_api_token(credentials)
        return
    if user is None or not user.is_admin:
        raise HTTPException(401, "Administrator login required")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        check_csrf(request, request.headers.get("X-CSRF-Token", ""))


operator = [Depends(require_operator)]


def require_worker(credentials: HTTPAuthorizationCredentials | None = Depends(auth.http_bearer),
                   db: Session = Depends(get_db)):
    worker = None
    if credentials and credentials.scheme.lower() == "bearer":
        worker = db.scalar(select(Worker).where(Worker.token_hash == service.digest(credentials.credentials)))
    if not worker:
        raise HTTPException(401, "Invalid worker token")
    return worker.id


@router.get("/protocol")
def protocol():
    return {"protocol_version": 1, "lease_seconds": service.LEASE_SECONDS,
            "operations": ["runtime.probe", "gmail.compose", "gmail.draft", "engine.command"]}


@router.post("/workers", dependencies=operator, status_code=201)
def pair(body: WorkerCreate, db: Session = Depends(get_db)):
    return service.pair(db, body)


@router.get("/workers", dependencies=operator)
def workers(db: Session = Depends(get_db)):
    return [service.worker_view(row) for row in db.scalars(select(Worker).order_by(Worker.created_at))]


@router.get("/session", dependencies=operator)
def session_info(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": csrf_token(request)}


@router.post("/workers/{worker_id}/rotate", dependencies=operator)
def rotate(worker_id: str, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return service.rotate_token(db, worker_id)


@router.post("/workers/{worker_id}/revoke", dependencies=operator)
def revoke(worker_id: str, db: Session = Depends(get_db)):
    return service.rotate_token(db, worker_id, revoke=True)


@router.get("/worker")
def worker(identity: str = Depends(require_worker), db: Session = Depends(get_db)):
    return service.worker_view(db.get(Worker, identity))


@router.post("/worker/heartbeat")
def heartbeat(body: Heartbeat, identity: str = Depends(require_worker), db: Session = Depends(get_db)):
    return service.heartbeat(db, identity, body)


@router.post("/worker/claim")
def claim(body: Claim, identity: str = Depends(require_worker), db: Session = Depends(get_db)):
    return service.claim(db, identity, body)


@router.post("/worker/report")
def report(body: Report, identity: str = Depends(require_worker), db: Session = Depends(get_db)):
    return service.report(db, identity, body, get_settings().enable_browser_send)


@router.get("/worker/jobs")
def worker_jobs(identity: str = Depends(require_worker), db: Session = Depends(get_db)):
    return service.jobs(db, identity)


@router.post("/jobs", dependencies=operator, status_code=201)
def submit(body: JobCreate, db: Session = Depends(get_db)):
    return service.submit(db, body, get_settings().enable_browser_send)


@router.post("/campaigns", dependencies=operator, status_code=201)
def submit_campaign(body: CampaignCreate, db: Session = Depends(get_db)):
    return campaign_service.submit(db, body, get_settings().enable_browser_send)


@router.get("/campaigns", dependencies=operator)
def campaigns(db: Session = Depends(get_db)):
    return [campaign_service.view(db, row.id) for row in db.scalars(
        select(Campaign).order_by(Campaign.created_at.desc()).limit(100))]


@router.get("/campaigns/{campaign_id}", dependencies=operator)
def campaign(campaign_id: str, db: Session = Depends(get_db)):
    return campaign_service.view(db, campaign_id, include_assignments=True)


@router.post("/campaigns/{campaign_id}/cancel", dependencies=operator)
def cancel_campaign(campaign_id: str, db: Session = Depends(get_db)):
    return campaign_service.cancel(db, campaign_id)


@router.get("/jobs", dependencies=operator)
def jobs(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return service.jobs(db, limit=limit, offset=offset)


@router.get("/jobs/{job_id}/events", dependencies=operator)
def events(job_id: str, db: Session = Depends(get_db)):
    if db.get(Job, job_id) is None:
        raise HTTPException(404, "Job not found")
    return [{"state": row.state, "detail": row.detail, "at": row.created_at}
            for row in db.scalars(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id))]


@router.post("/jobs/{job_id}/cancel", dependencies=operator)
def cancel(job_id: str, db: Session = Depends(get_db)):
    return service.cancel(db, job_id)


def csrf_token(request):
    settings = get_settings()
    cookie = request.cookies.get(settings.session_cookie_name, "")
    if not cookie or not settings.session_secret:
        raise HTTPException(403, "A signed login session is required")
    return hmac.new(settings.session_secret.encode(), ("fleet:" + cookie).encode(), hashlib.sha256).hexdigest()


def check_csrf(request, token):
    if not secrets.compare_digest(csrf_token(request), token):
        raise HTTPException(403, "Invalid form token; reload the fleet page")


def render(request, user, db, paired=None, error=None, code=200):
    response = templates.TemplateResponse("fleet.html", {
        "request": request, "user": user, "csrf": csrf_token(request), "paired": paired,
        "error": error, "workers": workers(db), "jobs": service.jobs(db),
        "campaigns": [campaign_service.view(db, row.id) for row in db.scalars(
            select(Campaign).order_by(Campaign.created_at.desc()).limit(100))],
        "submission_id": secrets.token_hex(16),
    }, status_code=code)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@ui_router.get("")
def fleet_page(request: Request, user=Depends(auth.require_admin), db: Session = Depends(get_db)):
    return render(request, user, db)


@ui_router.post("/pair")
def pair_form(request: Request, name: str = Form(...), platform: str = Form(...),
              accounts: str = Form(""), csrf: str = Form(...), max_parallel: int = Form(10),
              user=Depends(auth.require_admin), db: Session = Depends(get_db)):
    check_csrf(request, csrf)
    try:
        body = WorkerCreate(name=name, platform=platform,
            accounts=[value.strip() for value in accounts.split(",") if value.strip()],
            capabilities=["runtime.probe", "engine.command"] if platform == "android" else ["runtime.probe", "gmail.compose", "gmail.draft"],
            max_parallel=1 if platform == "android" else max_parallel)
        return render(request, user, db, paired=service.pair(db, body))
    except ValidationError:
        return render(request, user, db,
            error="Check worker platform, up to ten plain email addresses, and 1-10 parallel browser tabs.", code=422)


@ui_router.post("/jobs")
def job_form(request: Request, worker_id: str = Form(...), operation: str = Form(...),
             account: str = Form(""), to: str = Form(""), subject: str = Form(""), body: str = Form(""),
             draft_id: str = Form(""), csrf: str = Form(...), submission_id: str = Form(...),
             user=Depends(auth.require_admin), db: Session = Depends(get_db)):
    check_csrf(request, csrf)
    try:
        message = None if operation == "runtime.probe" else PreparedMessage(
            to=[value.strip() for value in to.split(",")], subject=subject, body=body,
            rfc822_message_id=draft_id or None)
        job = JobCreate(idempotency_key=submission_id, worker_id=worker_id, operation=operation,
                        account_email=account or None, message=message)
        service.submit(db, job)
    except ValidationError:
        return render(request, user, db, error="Check the operation, account, recipients and exact draft ID.", code=422)
    except HTTPException as exc:
        db.rollback()
        return render(request, user, db, error=exc.detail, code=exc.status_code)
    return RedirectResponse("/admin/fleet", status_code=303)


@ui_router.post("/cancel/{job_id}")
def cancel_form(request: Request, job_id: str, csrf: str = Form(...),
                user=Depends(auth.require_admin), db: Session = Depends(get_db)):
    check_csrf(request, csrf)
    service.cancel(db, job_id)
    return RedirectResponse("/admin/fleet", status_code=303)


@ui_router.post("/campaigns/{campaign_id}/cancel")
def cancel_campaign_form(request: Request, campaign_id: str, csrf: str = Form(...),
                         user=Depends(auth.require_admin), db: Session = Depends(get_db)):
    check_csrf(request, csrf)
    campaign_service.cancel(db, campaign_id)
    return RedirectResponse("/admin/fleet", status_code=303)
