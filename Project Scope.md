# Project Scope

This repository contains two related parts that work together:

1) Alpha Mailer (Python + Gradio)
- Purpose: run outreach campaigns using Gmail/OAuth tokens with a local/web UI.
- Key features: content templating, invoice generation, single/multi‑account send, Gradio UI.
- Where it runs: Colab, Deepnote, local machines, or Hugging Face.

2) URL Registry Website (FastAPI)
- Purpose: capture and display the public Gradio URL each time the mailer starts, so a user can quickly open the live session from a central place.
- What it stores: a small record with id, public_url, local_url, session_name, host, started_at, last_seen.
- Views: admin login, dashboard of currently running instances (only “active” sessions are shown).
- API: POST /api/instances (Bearer token) to upsert; GET /api/instances to read (for diagnostics/automation).
- Hosting target: Render (free) with Postgres; can place Cloudflare in front later.

Out of scope (for now)
- Triggering/running mailer sessions from the site (Deepnote/HF automation).
- Real‑time presence (we show active within a time window, heartbeat will come later).
- Complex RBAC/user management; we only have an admin login to view the dashboard and create additional users.

Why this split works
- Mailer can run anywhere (not tied to one host). It posts the URL to a small web registry.
- The registry is minimal, cheap to host, and easy to replace or scale.

Success criteria
- When the mailer runs and shares a Gradio link, the registry site shows that link as active within seconds.
- Admin login allows viewing only the currently running sessions.
- The site is deployable to a free tier (onrender.com) with a simple POST secret (API_TOKEN).
