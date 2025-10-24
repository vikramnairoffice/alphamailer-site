# URL Registry Admin (FastAPI)

Small FastAPI app that accepts public URLs from the Alpha Mailer runners and exposes a lightweight admin panel.

## Features
- Bearer-protected `POST /api/instances` endpoint to capture Gradio public URLs
- Simple dashboard to view active/recent instances
- Admin login with cookie session
- Manage additional users from the admin panel
- SQLite storage by default (one file, no setup)

## Quick start

```bash
cd web_admin
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# set secrets for dev
export API_TOKEN="dev-api-token"
export SESSION_SECRET="dev-session-secret"
python seed_admin.py --email admin@example.com --password mypass
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/admin/login` and sign in with the seeded admin user.

## Environment variables
- `API_TOKEN` (required): Bearer token expected by `/api/instances`
- `SESSION_SECRET` (required): secret key used to sign admin session cookies
- `DATABASE_URL` (optional): SQLAlchemy URL, defaults to `sqlite:///./app.db`

## API contract

`POST /api/instances`

Headers:
- `Authorization: Bearer <API_TOKEN>`

Request JSON:

```json
{
  "id": "uuid",
  "public_url": "https://xxxxx.gradio.live",
  "local_url": "http://127.0.0.1:7860",
  "session_name": "QA run",
  "host": "machine-01",
  "started_at": "2025-01-01T00:00:00Z"
}
```

Response:

```json
{"status": "ok"}
```

`GET /api/instances?status=active`

- Optional `status` query, use `active` to filter by last_seen (<=15 minutes old).

## Admin panel
- `/admin/login` – form login
- `/admin/` – dashboard (requires login)
- `/admin/users` – create/list users (admin only)
- `/admin/logout` – clear session

## Next steps
- Deploy wherever you like (Railway, Render, Fly.io, etc.)
- Add heartbeats or deletion endpoints if needed
- Keep the project separate by copying or cloning this folder
