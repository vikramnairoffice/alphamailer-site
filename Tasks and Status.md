# Tasks and Status (Website)

Scope: URL registry website only (separate from the mailer).

## Done
- Admin + login + user management.
- `/api/instances` webhook with Bearer token; upserts and marks `last_seen`.
- Dashboard shows only currently running sessions, improved readability.
- Render blueprint and Postgres driver/URL normalization.

## In Progress
- Deploy to Render and seed the first admin user.
- Verify a live post from the mailer running on Colab/Deepnote/HF.

## Next (post‑deploy)
- Update the mailer to point at the final Render endpoint:
  - `URL_PUBLISH_WEBHOOK=https://<your-service>.onrender.com/api/instances`
  - `URL_PUBLISH_AUTH="Bearer <API_TOKEN>"`
- Add optional heartbeat endpoint + client (every 60–120s) for true liveness.

## Backlog
- Auto‑refresh dashboard.
- De‑duplication by session/machine.
- Mirror to Slack/Discord.
- Link health checks; show reachable/unreachable.
- Auto cleanup of old rows.
