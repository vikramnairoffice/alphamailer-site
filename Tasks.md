# Orchestrator tasks

<a id="source-review-2026-11-07"></a>
## Source and contract review — 2026-11-07

HEAD `eee837a`. Reviewed registry/fleet routes, `fleet_schemas.py`,
`google_oauth.py`, configuration and exported v1 contracts. Worker capacity is
1 by default and bounded to 20; individual prepared messages retain limits of
50 recipients, four attachments and 250,000 body characters. Removed aggregate
campaign count/size caps do not remove those per-message checks.

The shared protocol still supports preview and explicit `confirmation=SEND`.
Automation's owned local coordinator enables delivery for its Send-driven UI;
an independently deployed coordinator retains its own enablement policy.
The OAuth broker requests email identity, gmail.compose, drive.file and
calendar.events, distinct from API Auth Validator's broader scope selections.
No schemas or endpoints changed in this documentation pass. Mixed-client,
original-endpoint compatibility, live OAuth/provider and deployment/retention
acceptance remain open; no server/provider tests were rerun here.


## Consolidated sections

- [Dated implementation and validation evidence](#implementation-status)
- [Dependency maintenance — 2026-11-05](#maintenance-2026-11-05)
- [Original URL-registry tasks and status](#registry-tasks)

These sections now live in this document. Task IDs, unresolved requirements and dated evidence retain their original meaning. This documents-only consolidation on 2026-11-06 ran no application, provider or device tests.

Consolidated 2026-11-06. This is the single repository Tasks.md.
Component material is merged below; dated results keep their original scope.
Update the relevant section here rather than creating directory copies.
This consolidation reviewed documents only and ran no application/provider tests.

## Component sections

- [app: Coordinator application tasks](#component-app)
- [contracts/v1: Fleet protocol version 1 tasks](#component-contracts-v1)

Baseline: 2026-09-27. Owner: coordinator/fleet. Sequence: [Plan.md](Plan.md).
Checked items are bounded code/local evidence from
[Tasks.md#implementation-status](#implementation-status), not production certification.

## Implemented checkpoint

- [x] `ORC-001` Preserve legacy URL registry compatibility and add scoped worker
  pairing, heartbeats, sessions, account slots and capability-aware job contracts.
- [x] `ORC-002` Implement durable jobs, leases, idempotency, reports, cancellation
  and uncertainty in [fleet service](app/fleet_service.py), with offline coverage.
- [x] `ORC-003` Implement authenticated Gradio discovery/execution, state, streaming
  and bounded uploads; test against a real local Gradio fixture.
- [x] `ORC-004` Integrate fleet admin pages and the shared Flutter dashboard;
  demonstrate browser-worker preview completion through the actual local server.

## Independent development

Source reconciliation 2026-10-23: router/service/test-file review confirms durable
campaigns, aggregate views, queued cancellation, the OAuth broker and twenty-slot
browser bounds. The [current status](#implementation-status) distinguishes these
implemented parts from the remaining acceptance of `ORC-103` through `ORC-107`.

- [x] `ORC-005` Add local application and protocol Plan.md/Tasks.md pairs, linked
  from the [project plan](Plan.md#directory-plans-and-tasks) (2026-10-19;
  documentation only; existing protocol and runtime acceptance remain unchanged).

- [x] `ORC-101` Define distributed campaign and assignment contracts with
  `ENG-104`: stable lead identities, immutable input manifests, partition ownership,
  per-account pacing, duplicate prevention and supported retries. Turso remains
  direct instance input; independent full-table reads must not duplicate campaigns.
  Completed 2026-09-27: `CampaignCreate` schema, UUID5 assignment identity,
  manifest hash, single-worker account ownership, historical lead-ID reservation,
  one active campaign per account and per-account claim pacing across campaigns;
  exported `CampaignCreate.schema.json` and documented the recovery rules.
- [x] `ORC-102` Implement durable campaign/assignment storage and dispatch against
  `ORC-101`. Verify database-enforced concurrent claims, restart reconciliation,
  cancellation and account/worker capacity with independent sessions. Never
  reassign uncertain external effects as fresh send jobs.
  Completed 2026-09-27: additive tables and atomic manifest/job insertion reuse
  database-locked claims; tests cover duplicate input and lead identities across
  campaign history, restart reads, cross-campaign account pacing,
  cancel of queued versus in-flight work and expired uncertain leases. Existing
  independent-session claim/capacity tests also pass. PostgreSQL remains untested.
- [ ] `ORC-103` Add aggregate campaign progress, assignment/job drill-down,
  partial failure and acknowledged control results. Coordinate Flutter UI with
  `AND-105` and browser reporting with `WEB-104`; command acceptance and final
  campaign completion must be separate states.
  Progress 2026-09-27: derived counts/state, API drill-down, admin and Flutter
  views, queued-lead cancel. In-flight stop acknowledgement and mixed-worker
  browser/Android end-to-end behavior remain open.
  Progress 2026-10-19: native Gradio campaign management now uses the existing
  campaign/job APIs; local fixtures verify queued cancellation and refusal after
  a racing claim. This does not close mixed-client recovery or in-flight stop
  acknowledgement. See [Automation evidence](../Alphamailer-automation/Tasks.md#implementation-status).
- [ ] `ORC-104` Map the final legacy Gradio endpoints/settings using `LEG-101`
  and refresh after `LEG-103`. Test hidden/stateful callback compatibility,
  uploads, defaults, schema changes and errors without writing to the original app.
- [ ] `ORC-105` Extend offline end-to-end tests across multiple engine/browser
  workers: disconnect, token revocation, session replacement, stale/expired lease,
  duplicate request/report and coordinator restart. Include campaign-level recovery
  after `ORC-102`, plus original registry regression checks.
  Progress 2026-09-27: mixed contract fixture, cancellation/expired-lease tests
  and a disposable SQLite 500-lead measurement now exist. Real mixed-client
  disconnect/restart and provider-effect reconciliation remain.
- [ ] `ORC-106` Implement bounded artifact/checkpoint persistence and retention
  with `ENG-107`. Define integrity, ownership, expiry and missing-artifact behavior;
  simulate deletion of a disposable runner before claiming Colab recovery.
- [ ] `ORC-107` Regenerate and validate canonical schemas/fixtures for client
  changes. Prove both Android and browser consumers agree on version, errors and
  state transitions; reject incompatible workers instead of guessing behavior.

## Later acceptance

- [ ] `ORC-201` Verify actual Colab Gradio instances, physical Android and live
  Gmail workers under dashboard control after designated resources arrive.
  Record each platform's outcomes; local Gradio fixtures are not cloud proof.
  Progress 2026-11-04: browser OAuth now requests Drive file and Calendar event
  access alongside Gmail. Offline scope/refresh tests pass; real consent and
  Drive/Docs/Calendar operations remain unverified. See [setup](Google-Browser-Auth.md).

## Operations and release

- [ ] `ORC-301` Verify intended database/deployment configuration, backup/restore,
  retention, credentials and rollback in an isolated environment. Include actual
  PostgreSQL claim/migration checks if that database is selected for deployment.
- [ ] `ORC-302` Record the supported process topology. Keep one process unless a
  shared Gradio-session/handle architecture is implemented and tested; PostgreSQL
  alone does not make multiple coordinator processes safe.
- [ ] `ORC-303` Prepare a pinned deployment/runbook and perform deployment only
  when requested. Verify deployed behavior and restore evidence separately.

Update rule: retain stable IDs and existing user-authored scope/status/spec files.
Add dated evidence when checking tasks; keep provider, cloud and production gates
open until tested. No runtime edits or generated files belong in `../Alphamailer/`.

2026-11-04 `ORC-103`: Pacing-blocked claims expose optional retry_after_ms;
1-second/600-second boundaries and active-account exclusion are fixture-tested.

2026-11-04 progress (`ORC-107`, Automation `WEB-124`): Removed fixed campaign
assignment-count/aggregate-byte caps, regenerated canonical/browser schema,
chunked historical lead lookup and retained atomic admission, idempotency,
account ownership and pacing. The full offline suite passed 60 tests with one
optional Gradio fixture skipped; real disposable Gradio submission was verified
in Automation. Broader all-client/mixed-worker acceptance remains open.


## Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<#maintenance-2026-11-05>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.


---

<a id="component-app"></a>

Component directory: `app/`. Commands and unlinked paths retain their original component context; explicit working-directory instructions take precedence.

<a id="component-app--coordinator-application-tasks"></a>
## Coordinator application tasks

Updated: 2026-10-19. Owner: coordinator application.

Sequence: [Plan.md](Plan.md#component-app). Navigation: [README.md](README.md#component-app).
Parent work and acceptance: [project Tasks.md]().

<a id="component-app--completed-documentation"></a>
### Completed documentation

- [x] `ORC-APP-001` Add and connect the local Plan.md/Tasks.md pair
  (2026-10-19; documentation only).

<a id="component-app--remaining-work"></a>
### Remaining work

- [x] `ORC-APP-106` Expand browser OAuth to `drive.file` and `calendar.events`
  (2026-11-04). Offline consent/handoff/refresh coverage passes; setup and
  reconnect guidance is in [Google browser authorization](Google-Browser-Auth.md).
  Parent live acceptance remains `ORC-201` / Android `AND-103`.

- [ ] `ORC-APP-101` Complete acknowledged in-flight stop/control reporting and real mixed-client failure recovery.
  Parent task dependencies: `ORC-103`, `ORC-105`.
- [ ] `ORC-APP-102` Map final Gradio defaults, hidden/stateful callbacks, uploads and errors.
  Parent task dependencies: `ORC-104`.
- [ ] `ORC-APP-103` Verify schema/fixture compatibility across Android and browser consumers.
  Parent task dependencies: `ORC-107`.
  Progress 2026-11-03: browser `max_parallel` and account list bounds are 20;
  Android pairing still forces one slot.
- [ ] `ORC-APP-104` Complete bounded artifact/checkpoint persistence, retention and missing-artifact behavior.
  Parent task dependencies: `ORC-106`.
- [ ] `ORC-APP-105` Verify the selected database, backup/restore and supported process topology.
  Parent task dependencies: `ORC-301`, `ORC-302`.

<a id="component-app--update-rule"></a>
### Update rule

Keep local IDs stable. Leave partial work unchecked and add a dated progress note.
Parent project tasks remain authoritative for cross-directory acceptance; do not
close them solely because a local documentation item is complete. Record the
actual verification scope and link dated evidence rather than copying historical
test totals into this file. This planning update ran no application/provider tests.

- [x] 2026-11-04 / `ORC-103`: Add retry_after_ms for pacing-blocked empty claims;
  preserve cross-campaign account pacing and active-job exclusion.

- [x] `ORC-APP-107` / parent `ORC-107`: Remove fixed campaign-wide bounds, chunk
  historical identity queries and validate standalone ownership once per account
  (2026-11-04). Large-campaign durable/idempotent admission and cancellation pass
  offline; broader consumer agreement remains under the parent task.

<a id="component-app--maintenance-audit--2026-11-05"></a>
### Maintenance audit ? 2026-11-05

Removed five unused imports while preserving registration side effects and all route/schema contracts. Offline suite: 60 passed, 1 skipped.
See the [retained maintenance record](<#maintenance-2026-11-05>) for scope, checks and retained findings.
Existing feature and release milestones retain their current status.


<a id="component-app--dependency-maintenance---2026-11-05"></a>
### Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<#maintenance-2026-11-05>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.


---

<a id="component-contracts-v1"></a>

Component directory: `contracts/v1/`. Commands and unlinked paths retain their original component context; explicit working-directory instructions take precedence.

<a id="component-contracts-v1--fleet-protocol-version-1-tasks"></a>
## Fleet protocol version 1 tasks

Updated: 2026-10-19. Owner: fleet protocol version 1.

Sequence: [Plan.md](Plan.md#component-contracts-v1). Navigation: [README.md](README.md#component-contracts-v1).
Parent work and acceptance: [project Tasks.md]().

<a id="component-contracts-v1--completed-documentation"></a>
### Completed documentation

- [x] `ORC-CON-001` Add and connect the local Plan.md/Tasks.md pair
  (2026-10-19; documentation only).

<a id="component-contracts-v1--remaining-work"></a>
### Remaining work

- [ ] `ORC-CON-101` Complete the final schema/fixture agreement check across browser and Android consumers.
  Parent task dependencies: `ORC-107`.
- [ ] `ORC-CON-102` Extend contract fixtures for remaining mixed-client cancellation and restart/control outcomes.
  Parent task dependencies: `ORC-103`, `ORC-105`.
- [ ] `ORC-CON-103` Record compatible consumer/build versions and regenerate exports whenever canonical models change.
  Parent task dependencies: `ORC-107`.
  Progress 2026-11-03: `MAX_WORKER_PARALLEL` is 20 for accounts, `max_parallel` and heartbeat leases; lower paired worker limits remain valid.

<a id="component-contracts-v1--update-rule"></a>
### Update rule

Keep local IDs stable. Leave partial work unchecked and add a dated progress note.
Parent project tasks remain authoritative for cross-directory acceptance; do not
close them solely because a local documentation item is complete. Record the
actual verification scope and link dated evidence rather than copying historical
test totals into this file. This planning update ran no application/provider tests.

- [x] 2026-11-04 / `ORC-103`: Document positive relative claim pacing hints and
  backward-compatible omission/ignore behavior.

2026-11-04 progress (`ORC-CON-101`, `ORC-CON-103`, parent `ORC-107`): Canonical
CampaignCreate and regenerated browser schema/types/validator accept campaigns
above the previous 500-row and 2 MB limits. Existing individual message limits
and protocol version remain. Offline API/extension checks pass; broader Android
and mixed-worker acceptance is not closed by this relaxation.


<a id="implementation-status"></a>
## Dated implementation and validation evidence

<a id="implementation-status-orchestrator-implementation-status"></a>

<a id="implementation-status-browser-drive-and-calendar-scopes---2026-11-04"></a>
### Browser Drive and Calendar scopes - 2026-11-04

Browser authorization now requests `drive.file` and `calendar.events` alongside
email identity and `gmail.compose`. The existing callback requires all requested
scopes and carries them into the device handoff and encrypted refresh receipt.
Drive sharing and Docs comments use app-created files; broader Drive access is
not requested. Existing Gmail-only receipts retain their original permissions
and remain refreshable; reconnect to grant the added scopes. Deployment/API
enablement and reconnect steps are in [Google browser authorization](Google-Browser-Auth.md).

Verification: project-local `python -m pytest tests -q` passed **59 tests**, with
**1 optional live Gradio fixture skipped**; existing dependency deprecation
warnings remain. Tests cover both added scopes in authorization/handoff/refresh,
individual missing-permission rejection, and old Gmail-only refresh compatibility.
Android verification is recorded in its [status](../Alphamailer-Android/Tasks.md#implementation-status).
No deployment, live consent, Google workflow operation, speed benchmark or device
test was performed. The protected original mailer worktree remains unchanged.

<a id="implementation-status-current-source-review---2026-10-23"></a>
### Current source review - 2026-10-23

Source revision `d465e72` contains the registry, scoped fleet/job API, durable
campaign assignments/progress, queued cancellation, Gradio bridge and Android
Google OAuth broker. Browser workers support up to twenty account slots while
preserving lower paired limits. See [registered routers](app/main.py),
[campaign ownership](app/campaign_service.py), [worker routes](app/fleet_routes.py)
and [OAuth implementation](app/google_oauth.py).

`ORC-103` is partly implemented: counts, drill-down and queued cancellation exist;
acknowledged in-flight stopping and real mixed-worker recovery remain open.
`ORC-104` through `ORC-107` still require final original callback mapping,
mixed-client restart coverage, external artifact recovery and complete consumer
agreement. Current source preserves process-local Gradio sessions/handles, so
one coordinator process remains the supported baseline. Database/backup/restore
and live cloud/device/provider acceptance remain separate.

This was source/test-file review only, not a new pytest or deployment result.
Use the [suite progress review](../Tasks.md#progress-review-orchestrator) for cross-project
dependencies. The historical checkpoints below retain their actual test dates.

<a id="implementation-status-historical-implementation-checkpoint---2026-09-27"></a>
### Historical implementation checkpoint - 2026-09-27

The coordinator now connects legacy Gradio sessions, Android engine workers and
Chrome/Firefox browser workers. The original user-authored registry documents were
preserved at this checkpoint; on 2026-11-06 their contents were consolidated into
[Plan.md](Plan.md#original-registry-scope), [this checklist](#registry-tasks), and
[Architecture.md](Architecture.md#registry-specification).

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

<a id="implementation-status-local-start"></a>
### Local start

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

<a id="implementation-status-tests"></a>
### Tests

    .venv/Scripts/python -B -m pytest -q

For the real Gradio fixture set GRADIO_FIXTURE_PYTHON to an interpreter containing
Gradio. The fixture is local and does not load original mailer accounts or send mail.

<a id="implementation-status-remaining-acceptance-and-deployment-work"></a>
### Remaining acceptance and deployment work

Real Colab endpoint compatibility, hidden/stateful legacy callbacks and frontend
feature mapping require validation against the final original UI. PostgreSQL
concurrency, multiple-process operation, retention, backups and deployment are
not production-certified. No live Gmail or physical-device pass is implied by
coordinator tests. See sibling status documents for their evidence.

<a id="implementation-status-fleet-campaign-update--2026-09-27"></a>
### Fleet campaign update — 2026-09-27

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

<a id="implementation-status-google-browser-authorization--2026-10-08"></a>
### Google browser authorization — 2026-10-08

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

<a id="implementation-status-browser-capacity-and-pacing-hints---2026-11-04"></a>
### Browser capacity and pacing hints - 2026-11-04

The version-1 worker/heartbeat limits and fleet pairing screen accept twenty
browser accounts/slots, retaining smaller worker capacities and one active job
per account. Generated WorkerCreate/Heartbeat schemas match the Python contract.
This is capacity validation, not live twenty-account acceptance.

Pacing-blocked empty claims return an optional positive retry_after_ms hint.
It is rounded up to the latest applicable cross-campaign/account deadline;
other empty claims can omit it. Existing boolean paced_claim callers remain
compatible. The browser schedules the next eligible claim without removing
server pacing or active-job exclusion. Exact deadline tests cover 1- and
600-second gaps, 250 ms remaining, and rejection while an account is active.

Pre-commit full coordinator suite: 56 passed, 1 skipped, 107 warnings. The skip
is the optional real Gradio fixture; local joined browser/Gradio checks in the
Automation sibling separately passed for one and five intercepted mailboxes.
Those checks measured 40 ms and 154-315 ms scheduling overhead respectively,
not live Gmail completion time. No provider traffic was generated by these
tests. Live twenty-account routing, recipient receipt and total subsecond Gmail
completion remain open. See the Automation implementation status for the
separate PDF sender-side evidence and post-extension-reload account readiness.


<a id="implementation-status-campaign-count-and-aggregate-size-limit-removal---2026-11-04"></a>
### Campaign count and aggregate-size limit removal - 2026-11-04

CampaignCreate now requires at least one assignment without a fixed maximum
assignment count or aggregate manifest-byte cap. Individual message/attachment
validation, send confirmation, account ownership, pacing and identity fencing
remain unchanged. Historical lead lookup uses bounded SQL parameter chunks, and
standalone ownership is checked once per account instead of once per lead.
Canonical schemas and Automation browser types/validators were regenerated.

Verification: all 60 coordinator tests passed, with one optional Gradio fixture
skipped and existing deprecation warnings. The new 601-assignment, >2 MB fixture
proved durable admission, identical-request reuse, complete queued cancellation
and historical identity rejection in a later SQL chunk. Automation additionally
proved real local Gradio upload/submission/download with the updated contract;
see its dated Tasks.md#implementation-status. tools/fixture_server.py has an opt-in
--admit-send-fixtures flag for isolated send-shaped API tests without live workers;
its default remains delivery-disabled. No provider, production database,
deployment or release was used. Memory/time still scale with campaign size.

<a id="implementation-status-maintenance-audit--2026-11-05"></a>
### Maintenance audit ? 2026-11-05

Removed five unused imports while preserving registration side effects and all route/schema contracts. Offline suite: 60 passed, 1 skipped.
See the [retained maintenance record](<#maintenance-2026-11-05>) for scope, checks and retained findings.
Existing feature and release milestones retain their current status.


<a id="implementation-status-dependency-maintenance---2026-11-05"></a>
### Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<#maintenance-2026-11-05>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.


<a id="maintenance-2026-11-05"></a>
## Dependency maintenance — 2026-11-05

<a id="maintenance-2026-11-05-maintenance---2026-11-05"></a>

Remove unused imports; update Python dependencies; migrate lifespan/templates and bcrypt compatibility; regenerate schemas.

<a id="maintenance-2026-11-05-validation"></a>
### Validation

Full suite: 64 passed, 1 skipped. Added password/login/template compatibility suite: 5 passed. Isolated test database; no provider effects.

<a id="maintenance-2026-11-05-compatibility"></a>
### Compatibility

Stable releases were checked on 2026-11-05. JavaScript projects require Node
26.13.0 or newer. Desktop Gradio uses Pillow 12.3.0 because it requires Pillow
below 13. Android retains vendor-native Pillow 11.0.0, cryptography 42.0.8,
lxml 5.3.0 and cffi 1.17.1. Flutter transitive constraints are retained.
The Windows embedded Python builder stays on supported 3.13.17.

This maintenance does not establish device, provider or release acceptance.


<a id="registry-tasks"></a>
## Original URL-registry tasks and status

The original registry checklist is retained below. Done describes its historical checkpoint; deployment, live publication and backlog items have no new acceptance evidence from this documentation pass.

<a id="registry-tasks-tasks-and-status-website"></a>

Scope: URL registry website only (separate from the mailer).

<a id="registry-tasks-done"></a>
### Done
- Admin + login + user management.
- `/api/instances` webhook with Bearer token; upserts and marks `last_seen`.
- Dashboard shows only currently running sessions, improved readability.
- Render blueprint and Postgres driver/URL normalization.

<a id="registry-tasks-in-progress"></a>
### In Progress
- Deploy to Render and seed the first admin user.
- Verify a live post from the mailer running on Colab/Deepnote/HF.

<a id="registry-tasks-next-postdeploy"></a>
### Next (post‑deploy)
- Update the mailer to point at the final Render endpoint:
  - `URL_PUBLISH_WEBHOOK=https://<your-service>.onrender.com/api/instances`
  - `URL_PUBLISH_AUTH="Bearer <API_TOKEN>"`
- Add optional heartbeat endpoint + client (every 60–120s) for true liveness.

<a id="registry-tasks-backlog"></a>
### Backlog
- Auto‑refresh dashboard.
- De‑duplication by session/machine.
- Mirror to Slack/Discord.
- Link health checks; show reachable/unreachable.
- Auto cleanup of old rows.
