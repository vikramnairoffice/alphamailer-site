# AlphaMailer Orchestrator (FastAPI)

Documentation/source review: 2026-11-07, HEAD `eee837a`. The current fleet, Google OAuth and registry routes were compared with `app/` and the v1 schemas. [Review findings](Tasks.md#source-review-2026-11-07) distinguish server defaults from Automation's owned local coordinator and retain the historical Render setup as deployment reference.


## Consolidated sections

- [Render deployment reference](#render-deployment)

These sections now live in this document. Task IDs, unresolved requirements and dated evidence retain their original meaning. This documents-only consolidation on 2026-11-06 ran no application, provider or device tests.

Consolidated 2026-11-06. This is the single repository README.md.
Component material is merged below; dated results keep their original scope.
Update the relevant section here rather than creating directory copies.
This consolidation reviewed documents only and ran no application/provider tests.

## Component sections

- [app: Coordinator application map](#component-app)
- [contracts/v1: Fleet protocol version 1](#component-contracts-v1)

Execution: [Plan.md](Plan.md) · [Tasks.md](Tasks.md).

The original URL registry is retained. The application also implements scoped
workers, fleet jobs/campaigns, a Gradio bridge, a shared Flutter dashboard and the
Android Google browser OAuth broker. See the [application source map](#component-app).

## Navigation

[Suite index](../README.md) · [Contributor rules](AGENTS.md) · [Architecture](Architecture.md)

| Need | Start here |
| --- | --- |
| Current fleet startup, topology and dated verification | [Implementation status](Tasks.md#implementation-status) |
| Worker, job, campaign and cancellation API | [Protocol version 1](#component-contracts-v1) |
| HTTPS OAuth broker setup and limits | [Google browser authorization](Google-Browser-Auth.md) |
| Scope and remaining work | [Scope](Plan.md#scope), [plan](Plan.md), [tasks](Tasks.md) |
| Native Gradio campaign operator screen | [Automation workflow](../Alphamailer-automation/docs/Operations.md#campaign-import-and-cancellation) |
| Original registry deployment notes | [Render notes](#render-deployment) |

The sections below describe the original registry. For current fleet operation,
use the linked status/setup guide and keep one coordinator process unless its
Gradio session/handle architecture is changed and tested. The Render notes are
historical setup guidance, not current hosting/pricing or deployment verification.

## Original registry

Small FastAPI app that accepts public URLs from the Alpha Mailer runners and exposes a lightweight admin panel.

## Features
- Bearer-protected `POST /api/instances` endpoint to capture Gradio public URLs
- Simple dashboard to view active/recent instances
- Admin login with cookie session
- Manage additional users from the admin panel
- SQLite storage by default (one file, no setup)

## Quick start

```bash
# Run from the Alphamilaer-Orchestrator directory.
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# set secrets for dev
export API_TOKEN="dev-api-token"
export SESSION_SECRET="dev-session-secret"
# Set DEV_ADMIN_PASSWORD privately in this shell before running the seed command.
python seed_admin.py --email admin@example.invalid --password "$DEV_ADMIN_PASSWORD"
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

Worker heartbeats and fleet/campaign APIs already exist. Use the
[current source review](Tasks.md#source-review-2026-11-07)
and [tasks](Tasks.md) for remaining legacy mapping, mixed-client recovery,
artifact persistence and operations. Run one coordinator process for the current
process-local Gradio bridge. Deployment is a separate requested operation;
historical Render notes do not establish a tested production release.


## Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<Tasks.md#maintenance-2026-11-05>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.


---

<a id="component-app"></a>

Component directory: `app/`. Commands and unlinked paths retain their original component context; explicit working-directory instructions take precedence.

<a id="component-app--coordinator-application-map"></a>
## Coordinator application map

Execution: [Plan.md](Plan.md#component-app) · [Tasks.md](Tasks.md#component-app).

[Project entry]() · [Architecture](Architecture.md) · [Protocol](#component-contracts-v1)

| Responsibility | Source |
| --- | --- |
| App startup, route registration and Flutter dashboard mount | [main.py](app/main.py) |
| Legacy instance URL registry | [api_routes.py](app/api_routes.py), [schemas.py](app/schemas.py), [models.py](app/models.py) |
| Admin sessions/users and credentials | [admin_routes.py](app/admin_routes.py), [auth.py](app/auth.py) |
| Settings and database/session ownership | [config.py](app/config.py), [database.py](app/database.py) |
| Canonical worker/job/campaign request models | [fleet_schemas.py](app/fleet_schemas.py) |
| Worker tokens, claims, leases, reports and queued-job cancellation | [fleet_service.py](app/fleet_service.py) |
| Fleet persistence and campaign tables | [fleet_models.py](app/fleet_models.py) |
| Campaign submission, assignments, aggregate state and queued cancellation | [campaign_service.py](app/campaign_service.py) |
| Public/operator/worker fleet route authentication | [fleet_routes.py](app/fleet_routes.py) |
| Legacy Gradio discovery and invocation handles | [gradio_adapter.py](app/gradio_adapter.py), [gradio_bridge.py](app/gradio_bridge.py) |
| Android Gmail/Drive/Calendar OAuth broker and refresh | [google_oauth.py](app/google_oauth.py), [scopes and reconnect setup](Google-Browser-Auth.md) |
| Admin rendering | [templates](app/templates), [static assets](app/static) |

The native [Automation Campaigns screen](../Alphamailer-automation/docs/Operations.md#campaign-import-and-cancellation)
uses the existing operator campaign/job endpoints; browser workers use separate
scoped credentials. The [Flutter dashboard](../Alphamailer-Android/README.md#component-lib)
is built by the Android project. The [engine](../Alphamailer-Engine/README.md)
executes business logic inside each runtime, not inside the coordinator.

For contract changes, update the Python models, run
[tools/export_contract.py](tools/export_contract.py), and reconcile browser and
Android consumers. Do not hand-edit client generated files. Route/claim/campaign/
OAuth/Gradio tests are in [tests](tests). Disposable integration servers and
benchmarks are in [tools](tools); use [current startup/evidence](Tasks.md#implementation-status)
and [remaining operations tasks](Tasks.md), including the single-process limit.

2026-11-04: campaign_service.claim_pacing computes the latest applicable account
deadline. fleet_service returns optional retry_after_ms on a paced empty claim.
The boolean paced_claim helper and all assignment/lease semantics remain.

Campaign admission has no fixed assignment-count or aggregate manifest-byte cap.
`campaign_service.py` checks historical lead identity in bounded SQL chunks and
validates standalone ownership once per account. See the
[canonical campaign contract](#component-contracts-v1--fleet-campaign-ownership) and dated
[verification](Tasks.md#implementation-status). Individual message checks remain.

<a id="component-app--maintenance-audit--2026-11-05"></a>
### Maintenance audit ? 2026-11-05

Removed five unused imports while preserving registration side effects and all route/schema contracts. Offline suite: 60 passed, 1 skipped.
See the [retained maintenance record](<Tasks.md#maintenance-2026-11-05>) for scope, checks and retained findings.
Existing feature and release milestones retain their current status.


<a id="component-app--dependency-maintenance---2026-11-05"></a>
### Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<Tasks.md#maintenance-2026-11-05>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.


---

<a id="component-contracts-v1"></a>

Component directory: `contracts/v1/`. Commands and unlinked paths retain their original component context; explicit working-directory instructions take precedence.

<a id="component-contracts-v1--fleet-protocol-version-1"></a>
## Fleet protocol version 1

Execution: [Plan.md](Plan.md#component-contracts-v1) · [Tasks.md](Tasks.md#component-contracts-v1).

The Python models in [app/fleet_schemas.py](app/fleet_schemas.py) are canonical. Regenerate JSON Schema
with `python -m tools.export_contract` from the orchestrator directory.
The browser build generates TypeScript request types from these schemas.
Android's contract tests read fixtures.json. Pydantic validators additionally
enforce operation/account/confirmation and attachment-content constraints which
JSON Schema alone cannot express.

<a id="component-contracts-v1--navigation-and-consumers"></a>
### Navigation and consumers

- [Application map](#component-app): route/service/model ownership.
- [CampaignCreate schema](contracts/v1/CampaignCreate.schema.json), [JobCreate schema](contracts/v1/JobCreate.schema.json) and [shared fixtures](contracts/v1/fixtures.json): generated protocol inputs.
- [Contract exporter](tools/export_contract.py): regenerate canonical exports.
- [Automation source](../Alphamailer-automation/README.md#component-extension-src) and [native campaign operator guide](../Alphamailer-automation/docs/Operations.md#campaign-import-and-cancellation): browser and Gradio consumers.
- [Android source map](../Alphamailer-Android/README.md#component-lib): Flutter/native consumers.
- [Dated status](Tasks.md#implementation-status): verified behavior and remaining gates.

<a id="component-contracts-v1--authentication-and-endpoints"></a>
### Authentication and endpoints

The additive [Google browser authorization extension](contracts/v1/google-oauth.md) defines
Android consent, secure handoff, and token refresh through a configured web client.

All paths below start with /api/v1. Use Authorization: Bearer <credential>.
Operator credentials are the coordinator's API_TOKEN; workers use the distinct
credential returned once by pairing. Never give a worker the operator token.

| Method / route | Credential | Response |
| --- | --- | --- |
| GET /protocol | None | Version, operations, lease duration |
| POST /workers | Operator | Worker metadata + one-time worker_token |
| GET /workers | Operator | Worker metadata, never credentials |
| GET /worker | Worker | Own worker metadata |
| POST /worker/heartbeat | Worker | Presence, renewed_job_ids, lease_seconds |
| POST /worker/claim | Worker | {job:null} or {job:{...},lease_token} |
| POST /worker/report | Worker | Updated own job |
| GET /worker/jobs | Worker | Latest 100 own jobs, no message/lease token |
| POST /jobs | Operator | Created or existing idempotent job |
| GET /jobs | Operator | Paged jobs: default 100, limit 1–500 and offset >= 0; no prepared message |
| GET /jobs/{id}/events | Operator | Ordered state/detail/at events |
| POST /jobs/{id}/cancel | Operator | Cancels only queued jobs |
| POST /campaigns | Operator | Atomic lead manifest with one job per assignment |
| GET /campaigns | Operator | Up to 100 recent aggregate campaign results |
| GET /campaigns/{id} | Operator | Lead and job drill-down |
| POST /campaigns/{id}/cancel | Operator | Cancel queued leads |

Native Gradio campaign import/review/launch uses these existing operator routes.
Individual cancellation succeeds only while a job is queued. Campaign cancellation
marks queued assignments cancelled and records the request; already leased,
running or sending work may finish. A `cancelling` campaign is not an acknowledged
in-flight stop. Operator controls, including fresh screen confirmation for imported
send assignments, are documented in the Automation guide linked above.

A job response includes id, worker_id, operation, execution, account_email,
state, slot_id, session_id, lease_expires_at, result, detail, created_at,
updated_at and protocol_version. Only a claim includes message and lease_token.
Claims include the stable job idempotency key; fleet jobs use `fleet:<assignment-id>`.
Timestamps are UTC. Heartbeat responses list only successfully renewed leases.

<a id="component-contracts-v1--fleet-campaign-ownership"></a>
### Fleet campaign ownership

Submit one or more assignments with globally stable lead IDs. There is no fixed
campaign assignment-count or aggregate manifest-size cap; individual message and
attachment limits still apply. Admission remains transactional and uses server
memory/time proportional to campaign size. A lead ID is reserved
across campaign history, including after cancellation; an intentional rerun needs
a new lead ID and campaign key. Existing assignment journals are checked when an
older database did not yet have the lead-identity table. The coordinator derives stable
assignment IDs from the campaign ID and lead ID, stores an input hash and creates
all jobs in one transaction. Reusing a campaign key with changed input is a
conflict. One account belongs to one worker within a campaign and can have only
one active fleet campaign at a time. A unique database account reservation
serializes competing campaign submissions; distinct accounts can run in parallel.
`min_interval_seconds` paces claims per account across consecutive campaigns.

Browser assignments carry a frozen prepared message. Engine assignments carry
immutable lead/config inputs. The instance prepares and stores one frozen message
per assignment, then uses its assignment ID as the execution journal key. Fleet
workers use `campaign.assignment`, without invoking the local campaign scheduler
for the same recipients. Coordinator assignments and instance delivery evidence
remain separate durable records.
Direct `POST /jobs` submission of `campaign.assignment` is rejected. An active
fleet assignment and a queued/running coordinator `campaign.start` for the same
worker account are mutually exclusive. Locally started campaigns outside the
coordinator still need operator care because their lead lists are private to
the device.

Campaign progress is derived from each job state. Cancellation stops queued claims
and leaves leased work to be acknowledged or reconciled. Expired leases remain
uncertain and are never automatically requeued. Command acceptance is distinct
from campaign completion and recipient inbox delivery.

<a id="component-contracts-v1--worker-loop"></a>
### Worker loop

1. Validate protocol 1 and paired capabilities/accounts.
2. Persist a runtime session ID. Heartbeat approximately every 30 seconds.
3. Claim using that session and a stable slot ID. Use account_email=null for
   runtime.probe; Gmail jobs require the exact paired mailbox.
4. Persist the assignment before page/native effects. Report running.
5. Renew current owned leases with each heartbeat; lifetime is 120 seconds.
6. A send job must receive a successful sending acknowledgement before the
   irreversible click. Preview cannot transition to sending.
7. Persist the terminal report, then send it. Retry the same report on a lost
   acknowledgement; never replay the external effect.
8. A lost/restarted browser operation is uncertain. An expired assignment is
   terminal and is not requeued.

A different session cannot take over a recently active worker. After it is offline,
the next heartbeat fences old work. HTTP 401 means invalid credentials; 403 means
forbidden ownership/send action; 404 means unavailable resource; 409 means conflict,
stale session/lease, or invalid transition; 422 means invalid payload/capability.
Do not convert these failures into permission to send again.

<a id="component-contracts-v1--bounds-and-sending"></a>
### Bounds and sending

At most twenty parallel slots and twenty distinct assigned mailboxes per worker.
Workers may select a lower `max_parallel` capacity; the default remains one.
Browser workers bind each distinct Gmail account to its own tab. Claims enforce
one active assignment per slot/account under concurrent requests, and each
heartbeat can renew up to twenty active leases. Existing one-to-ten-slot clients
remain compatible. Prepared messages support up to 50 To
recipients, four files of 2 MB each, and a 250,000-character body. Large campaigns,
BCC/CC, arbitrary MIME/headers and streaming artifact storage need later contracts.

Sending is disabled by default. An operator must set ENABLE_WORKER_DELIVERY=true
(ENABLE_BROWSER_SEND is the legacy fallback when that setting is absent)
and submit execution=send with confirmation=SEND. The enablement is checked again
at the sending transition. Disabling cannot retract a previously acknowledged
external send. The same gate applies to fleet delivery. The Flutter dashboard
has a structured fleet form with explicit send confirmation, while the Python
admin page shows aggregate progress and cancellation.

The Gmail adapter assumes English Gmail labels. Existing-draft lookup requires
the exact RFC 822 Message-ID and expected content. Canonical rich HTML and
downloaded attachment bytes are checked in local browser fixtures; real Gmail
attachment URLs, MIME normalization and provider behavior still need acceptance.
See [Automation's dated status](../Alphamailer-automation/Tasks.md#implementation-status)
for the exact verified browser/provider boundary.

<a id="component-contracts-v1--additive-pacing-hint---2026-11-04"></a>
#### Additive pacing hint - 2026-11-04

A pacing-blocked POST /worker/claim may return {"job":null,"retry_after_ms":N},
where N is a positive integer number of milliseconds until the earliest eligible
claim under all applicable account/campaign gaps. It grants no lease or permission
to send. Workers wait until that deadline and claim again normally; they must
continue heartbeats and preserve active-account/slot limits. Empty queues, busy
slots and cancellation can still return {"job":null} without a hint. Older
clients/servers can ignore/omit this additive response field. Request schemas
and protocol version remain unchanged.


<a id="render-deployment"></a>
## Render deployment reference

Historical hosting instructions, not a deployment result. Verify current Render pricing/availability; the old free-tier wording is not a current service guarantee. Configure secrets privately and use the current administrator setup above.

<a id="render-deployment-deploy-url-registry-to-render-free"></a>

This repo includes a Render Blueprint (`render.yaml`) to deploy the FastAPI site with a free Postgres database.

<a id="render-deployment-prereqs"></a>
### Prereqs
- A GitHub repo containing this code
- A Render account (free) at https://render.com

<a id="render-deployment-onetime-setup-ui"></a>
### One‑time setup (UI)
1. Push this repo to GitHub (make sure `render.yaml` is in the root).
2. In Render, click New → Blueprint.
3. Connect the GitHub repo and select it.
4. Fill required env vars when prompted:
   - `API_TOKEN` → your secret used by the app runners when posting URLs
   - `SESSION_SECRET` → any long random string
5. Click Apply; Render will provision:
   - `url-registry-db` (free Postgres)
   - `url-registry-admin` (FastAPI web service)

When it finishes, you’ll get a URL like `https://url-registry-admin.onrender.com`.

<a id="render-deployment-runners-colabdeepnotehugging-face"></a>
### Runners (Colab/Deepnote/Hugging Face)
Set these env vars when launching your mailer app so it posts the public URL:

```
URL_PUBLISH_WEBHOOK=https://url-registry-admin.onrender.com/api/instances
URL_PUBLISH_AUTH="Bearer <API_TOKEN>"
```

Sharing and publishing are ON by default in this repo.

<a id="render-deployment-optional-cli-deployment"></a>
### Optional CLI deployment
If you provide a Render API key, a blueprint can be triggered via API. Add an environment variable `RENDER_API_KEY` and I can run the API calls for you. Otherwise, the UI steps above are the quickest path.
