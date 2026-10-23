# Technical Specs

## Components
- Mailer (Gradio UI, Python): `ui.py`, `url_publisher.py`, others.
- Registry site (FastAPI): lives under `web_admin/` (separate repo when hosted). Uses SQLAlchemy + Postgres.

## Data model (registry)
- instances
  - id: string (UUID from mailer run)
  - public_url: string (nullable)
  - local_url: string
  - session_name: string (nullable)
  - host: string (nullable)
  - started_at: datetime (tz‑aware)
  - last_seen: datetime (tz‑aware)
  - created_at: datetime (server default)
- users
  - email: unique
  - hashed_password: bcrypt
  - is_admin: bool
  - created_at

## API (registry)
- POST `/api/instances` (Bearer token)
  - Body:
    - id, public_url, local_url, session_name, host, started_at (ISO8601)
  - Upserts record and sets `last_seen=now()`.
  - 200 {"status":"ok"} on success.
- GET `/api/instances?status=active`
  - Returns `{ items: [...] }` with computed `status` and formatted timestamps.
  - UI only shows “active” (last_seen within ACTIVE_MINUTES).

## Auth
- Webhook: `Authorization: Bearer <API_TOKEN>`
- Admin UI: cookie session with `SESSION_SECRET`.

## Mailer → Registry payload
```
{
  "id": "<uuid>",
  "public_url": "https://....gradio.live",
  "local_url": "http://127.0.0.1:<port>/",
  "session_name": "<optional>",
  "host": "<hostname>",
  "started_at": "<ISO8601>"
}
```

## Env vars
- Mailer side
  - `GRADIO_SHARE` (1/0): share a public link (default: ON in code today)
  - `URL_PUBLISH_ENABLED` (1/0): publish URL over webhook (default: ON in code today)
  - `URL_PUBLISH_WEBHOOK`: registry endpoint, e.g., `https://<service>.onrender.com/api/instances`
  - `URL_PUBLISH_AUTH`: `Bearer <API_TOKEN>`
  - Optional: `URL_PUBLISH_SLACK_WEBHOOK`, `URL_PUBLISH_FILE_PATH`, `URL_PUBLISH_STDOUT=1`
- Registry site
  - `DATABASE_URL`: Postgres URL (accepts postgres://, normalized to postgresql://)
  - `API_TOKEN`: required for webhook auth
  - `SESSION_SECRET`: required for admin sessions
  - `ACTIVE_MINUTES`: status window (default 15)

## Deployment (registry)
- Target: Render free web service + free Postgres.
- Blueprint: `render.yaml` in the website repo (web_admin when split out).
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Post‑deploy: `python seed_admin.py --email ... --password ...`

## Styling (registry)
- Minimal CSS in `app/static/site.css` with better contrast, sticky header, badges, zebra rows.

## Known tradeoffs / TODOs
- Live presence uses a time window; heartbeat optional for true real‑time.
- No rate limiting on the webhook (could add basic throttling by IP/token).
- No audit log yet; can be a simple table (`events`) if needed.
- Mailer defaults to share/publish ON in code; can be toggled with envs.
