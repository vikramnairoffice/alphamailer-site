# Orchestrator implementation status — 2026-09-27

The coordinator now connects legacy Gradio sessions, Android engine workers and
Chrome/Firefox browser workers. The user-authored Project Scope.md, Tasks and
Status.md and Technical Specs.md remain unchanged.

| Area | Implementation and evidence |
| --- | --- |
| Legacy registry | Existing startup URL publication payload preserved |
| Fleet | Scoped hashed tokens, pair/rotate/revoke, heartbeat/session, account slots, leases, idempotency, cancellation and uncertainty |
| Engine jobs | Account-bound prepare/execute and campaign start/status/pause/resume/stop |
| Browser jobs | Compose and exact draft, explicit preview/send, maximum five distinct account slots |
| Dashboard | Existing Jinja /admin/fleet plus shared Flutter /dashboard/ |
| Gradio | Trusted origins, per-instance authentication/client session, live API schema and hash, generated endpoint execution, asynchronous output/cancellation |
| Uploads | Bounded inline file marker staged through gradio_client.handle_file; raw server paths rejected |
| Persistence | Additive SQLAlchemy/SQLite tables; jobs paginate; durable invocation ledger |
| Verification | 26 tests pass including a real local Gradio server with streaming, persistent State and file upload |

The actual Chromium extension/coordinator fixture also loaded the shared Flutter
dashboard, selected a worker and queued a preview which the worker completed.

Gradio call identity is persisted before submission. A repeated payload/key does
not start another command. Lost in-memory handles become uncertain after restart.
Cancellation requests are not proof that the remote campaign stopped.

Run ONE coordinator process (--workers 1). Gradio client sessions and active Job
handles currently live in that process. PostgreSQL configuration exists, but it
does not make this Gradio bridge safe for several coordinator processes.

## Local start

Install requirements-dev.txt and requirements-gradio.txt into an isolated venv.
Set DATABASE_URL to a fresh development database and set API_TOKEN and
SESSION_SECRET privately. Use the existing administrator setup instructions.

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1

Build ../Alphamailer-Android for web with --base-href /dashboard/ before starting
the coordinator; it mounts that build automatically. Sign in at /admin/login,
then open /dashboard/ or /admin/fleet. Do not deploy fixture credentials.

Set GRADIO_TRUSTED_ORIGINS to the exact accepted runner origins, and configure
GRADIO_AUTH_JSON as an object keyed by instance ID with username/password arrays.
ENABLE_GRADIO_EXECUTION enables confirmed legacy calls. ENABLE_WORKER_DELIVERY
enables explicitly confirmed worker delivery; ENABLE_BROWSER_SEND is a legacy
fallback. Public deployments require HTTPS.

## Tests

    .venv/Scripts/python -B -m pytest -q

For the real Gradio fixture set GRADIO_FIXTURE_PYTHON to an interpreter containing
Gradio. The fixture is local and does not load original mailer accounts or send mail.

## Remaining acceptance and deployment work

Real Colab endpoint compatibility, hidden/stateful legacy callbacks and frontend
feature mapping require validation against the final original UI. PostgreSQL
concurrency, multiple-process operation, retention, backups and deployment are
not production-certified. No live Gmail or physical-device pass is implied by
coordinator tests. See sibling status documents for their evidence.

## Fleet campaign update — 2026-09-27

The coordinator now accepts an authenticated, bounded `CampaignCreate` manifest
at `POST /api/v1/campaigns`. It stores campaign, lead assignments, account pacing
and existing jobs atomically in additive tables. Lead IDs are reserved across
campaign history, including cancelled campaigns; the legacy assignment journal
is checked when the new identity table did not exist. Repeated identical submission
returns the same campaign; changed input with the same key conflicts. One account
maps to one worker within a campaign. A second active campaign cannot claim the
same account. Claims observe per-account intervals across consecutive campaigns and
continue to use the existing worker/session/slot lease guards. Expired effects
remain uncertain and are not automatically rescheduled.

`GET /api/v1/campaigns/{id}` derives counts and lead/job drill-down from durable
job states. Campaign cancellation stops queued leads and reports `cancelling`
while in-flight work remains; it does not claim a send was undone. The admin
page and shared Flutter dashboard show aggregate progress. `CampaignCreate`
JSON Schema is exported under `contracts/v1/`.

Local coordinator suite: **33 passed, 1 skipped** (the optional real Gradio
fixture), including eight fleet campaign tests. SQLite restart reads and
existing independent-session claim/capacity tests passed. PostgreSQL, multiple
coordinator processes, mixed browser/Android end-to-end jobs, in-flight stop
acknowledgements and production storage operations remain open.

One fleet test checks Android-engine and Firefox-browser assignment shapes
in one campaign and aggregate completion through the same job contract. Its
workers report fixture outcomes; actual mixed clients have not been run together.

`python -B -m tools.bench_fleet` on this Windows host inserted 500 synthetic
preview leads across five accounts into disposable SQLite in 1.3120 seconds;
five claims took 0.2687 seconds. `tracemalloc` observed 5,589,893 peak Python
bytes during submission and the SQLite file was 987,136 bytes. This is one local
measurement without rendering, network, provider calls or email, not a throughput
or production capacity claim.

## Google browser authorization — 2026-10-08

Added a worker-scoped Google Web OAuth broker with PKCE/state, verified account
matching, offline consent, encrypted temporary handoff, acknowledgement, and
worker-bound refresh receipts. The Google client secret stays on the coordinator;
Android receives and stores the refresh token through its encrypted credential
vault. Three request schemas and a fixture extend contract version 1.

Coordinator suite: **45 passed, 1 skipped** (the existing optional Gradio fixture).
Google responses were mocked; no provider account was contacted and no mail was
sent. Deployment/configuration and live consent remain pending. See
`Google-Browser-Auth.md` for the Web client JSON, HTTPS callback, encryption key,
reverse-proxy logging requirements, and scope/renewal boundaries. The protected
Alphamailer source directory was not edited by this change.

