# Orchestrator development plan


## Consolidated sections

- [Scope and acceptance boundaries](#scope)
- [Original URL-registry scope](#original-registry-scope)

These sections now live in this document. Task IDs, unresolved requirements and dated evidence retain their original meaning. This documents-only consolidation on 2026-11-06 ran no application, provider or device tests.

Consolidated 2026-11-06. This is the single repository Plan.md.
Component material is merged below; dated results keep their original scope.
Update the relevant section here rather than creating directory copies.
This consolidation reviewed documents only and ran no application/provider tests.

## Component sections

- [app: Coordinator application plan](#component-app)
- [contracts/v1: Fleet protocol version 1 plan](#component-contracts-v1)

Baseline: 2026-09-27. Owner: coordinator, fleet protocol and Gradio bridge.

Current documentation reconciliation: 2026-11-07 at `eee837a`; see [current findings](Tasks.md#source-review-2026-11-07). The historical 2026-10-23 review at `d465e72` in the
[dated source review](Tasks.md#implementation-status) records implemented campaign,
OAuth and twenty-slot browser capacity separately from remaining mixed-client, artifact,
final legacy mapping and operations acceptance. No new runtime tests ran here.

## Goal and baseline

2026-11-04: extend browser consent to Drive/Docs comments and Calendar; verify
offline handoff/refresh, then perform designated provider acceptance (`ORC-201`).

Coordinate Colab/VM, Android and browser workers from one dashboard while reusing
the original Gradio APIs. Registry compatibility, worker jobs, leases/recovery,
Gradio sessions and shared dashboard integration exist. Durable fleet manifests,
per-lead assignments, account pacing, aggregate progress and queued cancellation
are implemented (`ORC-101`/`ORC-102`). Mixed real-client recovery and acknowledged
in-flight control results remain open (`ORC-103`/`ORC-105`).

Read [AGENTS.md#implementation-instructions](AGENTS.md#implementation-instructions), [Architecture.md](Architecture.md), [Plan.md#scope](#scope),
[Tasks.md#implementation-status](Tasks.md#implementation-status) and [Tasks.md](Tasks.md).
The original registry scope, checklist and specification are consolidated into
the [registry scope](#original-registry-scope),
[registry tasks](Tasks.md#registry-tasks) and
[registry specification](Architecture.md#registry-specification). Preserve their
unique requirements alongside the migration workstream.

## Ownership and invariants

- Preserve startup URL publication and registry payloads. Legacy startup
  publication is not a periodic heartbeat.
- Own canonical versioned fleet schemas, durable assignments, account/slot
  ownership, scoped credentials and aggregate results. Clients consume this
  contract; they must not invent separate coordinator protocols.
- Reuse Gradio discovery and generated APIs for individual Python instances.
  Android/browser workers connect outbound and do not need public inbound URLs.
- Shared mailer business logic executes in instances. Turso supplies leads/content
  directly to those engines and does not become a coordinator job database.
- Local and distributed campaigns need explicit scheduling authority. A successful
  command acceptance is not proof that its campaign has finished or stopped.

## Milestones

| Stage | Work | Acceptance |
| --- | --- | --- |
| O1: assignment design | `ORC-101` with `ENG-104` | Stable campaign/lead identities, explicit partition rules and recovery semantics |
| O2: fleet controller | `ORC-102`/`ORC-103` | Durable assignments, compatible routing, account pacing and aggregate progress under restart/concurrency |
| O3: legacy parity | `ORC-104` with `LEG-101`/`LEG-103` | Mapped final Gradio callbacks, state, files and parameter defaults |
| O4: reliability/storage | `ORC-105`/`ORC-106` | Offline multi-worker failure tests, retained artifacts/checkpoints and recovery proof |
| O5: real integration | `ORC-201` after resources arrive | Real Colab/Android/browser control with separately recorded provider outcomes |
| O6: operations | `ORC-301`/`ORC-302` | Reviewed deployment, retention, backup/restore and supported process topology |

Work on O1/O2/O4 does not require changes to the original mailer or real Gmail
accounts. O3 starts from current source and is refreshed after frontend changes.
Coordinate assignment/schema changes with both client projects before shipping.

## Directory plans and tasks

Consolidated 2026-11-06. Each repository has one root Plan.md and Tasks.md.
Directory work is maintained in named sections of that pair; the links below
open those sections. Generated output, dependencies and credential/data stores
are excluded.
The project task IDs stay authoritative for cross-directory acceptance.

| Directory | Work sequence | Checklist |
| --- | --- | --- |
| app | [Plan](#component-app) | [Tasks](Tasks.md#component-app) |
| contracts/v1 | [Plan](#component-contracts-v1) | [Tasks](Tasks.md#component-contracts-v1) |

## Reliability and release boundaries

Keep idempotency, stale session/lease rejection, per-account ownership and durable
uncertainty. Never automatically repeat a send after an ambiguous acknowledgement.
Test database conditions with independent sessions, not only in-memory locks.

Current Gradio clients and active handles are process-local: run one coordinator
process. PostgreSQL configuration does not remove this limitation. A multi-process
release requires a shared-session design and database-specific proof; a documented
single-process release is also possible if it meets the agreed deployment needs.

Do not deploy with fixture credentials or validate migrations against a real
production database. Record live Gradio/device/provider results separately from
local fixture success. Update [Tasks.md](Tasks.md) and the status evidence after
each bounded change, preserving existing user-authored planning files.

2026-11-04 (`ORC-103`): Add canonical claim pacing hints consumed by Automation
for deadline scheduling. Retain account exclusion, cross-campaign gaps and leases.

2026-11-04 (`ORC-107`, Automation `WEB-124`): Remove the fixed campaign assignment
count and aggregate manifest-size limits, regenerate canonical/browser schemas,
and verify large atomic admission, idempotency and cancellation. Chunk historical
lead lookup to respect database parameter limits without capping campaign size.


## Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<Tasks.md#maintenance-2026-11-05>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.


---

<a id="component-app"></a>

Component directory: `app/`. Commands and unlinked paths retain their original component context; explicit working-directory instructions take precedence.

<a id="component-app--coordinator-application-plan"></a>
## Coordinator application plan

Updated: 2026-10-19. Owner: coordinator application.

[Local tasks](Tasks.md#component-app) · [Directory guide](README.md#component-app) · [Project plan]() · [Project tasks](Tasks.md)

<a id="component-app--current-baseline"></a>
### Current baseline

Registry compatibility, scoped workers, durable jobs, campaign assignment/progress, queued cancellation, Gradio sessions and the Google OAuth broker are implemented. Mixed-client recovery and production operations remain open.

Runtime evidence remains in the owning project's dated status/QA documents.
Creating or updating this plan does not rerun application tests.

<a id="component-app--work-sequence"></a>
### Work sequence

Browser OAuth update 2026-11-04: request Drive file and Calendar event access
alongside Gmail, verify partial consent and refresh compatibility, then complete
live consent/provider acceptance under `ORC-201` and Android `AND-103`.

1. Finish mixed-worker progress/control acknowledgement and disconnect/restart fixtures (`ORC-103`, `ORC-105`).
2. Reconcile the final legacy Gradio callback/settings surface and client contract consumers (`ORC-104`, `ORC-107`).
3. Complete artifact retention/recovery and verify the intended database/single-process deployment topology (`ORC-106`, `ORC-301`, `ORC-302`).

<a id="component-app--completion-and-ownership"></a>
### Completion and ownership

Use [Tasks.md](Tasks.md#component-app) for the local checklist. Parent project IDs retain their
original meaning and completion state; local items are scoped follow-up work,
not a declaration that the entire parent milestone is complete. Add dated
acceptance evidence before checking runtime work, and update the relevant source
map/workflow guide when behavior changes. Child directories inherit this component's scope within the root planning documents.

2026-11-04 (`ORC-103`): Publish additive relative pacing hints from the canonical
claim path so browser workers can schedule the next eligible check precisely.

2026-11-04 (`ORC-107`, Automation `WEB-124`): Relax only campaign-wide bounds;
retain individual message checks, send confirmation, account ownership and pacing.
Bound historical identity SQL queries and avoid repeated per-account validation.

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

<a id="component-contracts-v1--fleet-protocol-version-1-plan"></a>
## Fleet protocol version 1 plan

Updated: 2026-10-19. Owner: fleet protocol version 1.

[Local tasks](Tasks.md#component-contracts-v1) · [Directory guide](README.md#component-contracts-v1) · [Project plan]() · [Project tasks](Tasks.md)

<a id="component-contracts-v1--current-baseline"></a>
### Current baseline

Canonical request models are owned by app/fleet_schemas.py; this directory contains exported schemas, fixtures and protocol/OAuth guides. Current bounds permit twenty account slots while preserving lower worker capacities.

Runtime evidence remains in the owning project's dated status/QA documents.
Creating or updating this plan does not rerun application tests.

<a id="component-contracts-v1--work-sequence"></a>
### Work sequence

1. Start any contract change in the canonical Python models and preserve additive version-1 compatibility.
2. Regenerate schemas/fixtures and rebuild browser types/validators; reconcile Android consumers (`ORC-107`).
3. Verify version errors, account/lease/state semantics and mixed-worker recovery before claiming cross-client compatibility (`ORC-103`, `ORC-105`, `ORC-107`).

<a id="component-contracts-v1--completion-and-ownership"></a>
### Completion and ownership

Use [Tasks.md](Tasks.md#component-contracts-v1) for the local checklist. Parent project IDs retain their
original meaning and completion state; local items are scoped follow-up work,
not a declaration that the entire parent milestone is complete. Add dated
acceptance evidence before checking runtime work, and update the relevant source
map/workflow guide when behavior changes. Child directories inherit this component's scope within the root planning documents.

2026-11-04 (`ORC-103`): Document additive claim retry_after_ms response guidance
without introducing a new request operation or changing version-1 request models.

2026-11-04 (`ORC-107`): Regenerate CampaignCreate without maxItems; rebuild browser
schemas/types/validators and verify a campaign above the prior row/byte caps.
Keep protocol version 1 and existing individual message/attachment limits.


<a id="scope"></a>
## Scope and acceptance boundaries

<a id="scope-alphamailer-orchestrator-scope"></a>

<a id="scope-goal"></a>
### Goal

Advance coordinator and client integration independently of the original AlphaMailer workstream; the old four-sprint count is historical. No edits or generated output are permitted in `../Alphamailer/`.

<a id="scope-current-baseline"></a>
### Current baseline

- Existing FastAPI URL registry, login/admin pages and SQLite/PostgreSQL support.
- Fleet tables/contracts, Android engine commands, browser workers, a live Gradio
  connector and the Flutter dashboard are integrated. See current verification
  in Tasks.md#implementation-status.
- Existing user-authored scope/status/specification documents are preserved.

<a id="scope-in-scope-now"></a>
### In scope now

| Workstream | Deliverable | Acceptance |
| --- | --- | --- |
| Contract | Version 1 request models, exported schema and fixtures | Both sibling clients validate the same shapes |
| Pairing | Distinct worker credentials and account/capability grants | Unauthorized and cross-worker requests rejected |
| Presence | Heartbeats and stable worker / runtime-session identities | Offline/never-connected/stale-session behavior explicit |
| Job submission | Durable records and idempotency | Repeated requests do not create duplicate jobs |
| Claims | Account/slot/capacity-limited leases | Concurrent claims cannot assign a job twice |
| Recovery | Fenced reports, lease renewal and uncertainty | Interrupted browser work is not blindly retried |
| Dashboard | Worker and job views plus preview/probe controls | Operator can review the actual state and errors |
| Legacy registry | Unchanged registration endpoint and payload | Original mailer publication still passes |
| Legacy adapter | Gradio API discovery, stateful execution and bounded file uploads | Session continuity, schema hash and idempotency tested |
| Testing/docs | Offline tests and reproducible local setup | Results distinguish code, fixtures and live proof |

<a id="scope-deferred-integration-not-silently-removed-scope"></a>
### Deferred integration, not silently removed scope

- Exhaustive parity mapping of the final original frontend and hidden Gradio callbacks.
- Fleet-level campaigns spanning multiple instances and lead assignment manifests.
- Frontend refinement beyond the implemented shared dashboard and advanced configuration.
- Production deployment, production credential provisioning and live account QA.
- Full artifact storage/retention for large campaigns beyond the initial bounded
  prepared-message protocol.

These require later milestones, not changes to the protected mailer during its
remaining sprints. Independent backend/client work continues meanwhile.

<a id="scope-explicit-exclusions"></a>
### Explicit exclusions

- Modifying or copying the current mailer engine/frontend.
- Running real campaigns, selecting arbitrary account tokens, or sending email as
  an automated development test.
- Publishing/deploying to external production services without a concrete request.
- Replacing Turso's lead/content role with a hidden job database.
- Claiming exactly-once external delivery, guaranteed Colab uptime, or full Android
  compatibility based only on a shared protocol.

<a id="scope-delivery-gates"></a>
### Delivery gates

1. Contract and additive storage are implemented and tested.
2. Pairing, ownership and version checks pass.
3. Claims, expiry, restart and idempotency pass concurrent/persistent tests.
4. Existing URL registration remains compatible.
5. Operator UI and sibling client flows work against a local test server.
6. Release notes identify unavailable engine operations and unverified live targets.

Record dated implementation evidence in Tasks.md as work lands. A planned row or
method stub is not a completed deliverable. Follow `AGENTS.md#implementation-instructions` and
`Architecture.md` for execution and design rules.


<a id="original-registry-scope"></a>
## Original URL-registry scope

Historical registry-only scope. Its early exclusions and web_admin layout are superseded by the fleet scope and current component map above; the registry success criteria remain compatibility requirements.

<a id="original-registry-scope-project-scope"></a>

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
