# Alphamailer Orchestrator — agent implementation guide

## Objective and protected boundary

Build the coordination service and dashboard independently while four existing
Alphamailer sprints continue. The sibling `../Alphamailer/` directory is protected:
do not edit it, install packages into it, generate files there, run migrations
there, or run commands which produce its caches or runtime data. Read-only source
inspection is permitted. All implementation, tests, fixtures, generated schemas,
and documentation for this project belong in this directory.

The sibling projects are `../Alphamailer-Android/` and
`../Alphamailer-automation/`. Changes there belong to their respective scopes.
Do not rename `Alphamilaer-Orchestrator`; its spelling is an existing path.
Preserve the user's untracked `Project Scope.md`, `Tasks and Status.md`, and
`Technical Specs.md`; they describe the earlier URL registry and are not ours to
silently replace.

## Architecture decisions

- Logical hierarchy: Dashboard → Orchestrator → Mailer Engine → Instances.
- The mailer engine is shared Python code deployed in each execution instance,
  not a mandatory additional central mail-processing server.
- Individual Colab/notebook/VM runners retain their Gradio UI and generated APIs.
- Android must ultimately execute the mailer locally. A remote-only controller
  must never be reported as completion of the standalone Android requirement.
- Browser automation is an engine delivery adapter with Chrome/Firefox workers:
  (1) send a previously created draft, (2) compose and send through Gmail UI.
- Browser target is Gmail with up to ten distinct verified accounts, one account
  per tab, following the 2026-10-19 capacity update. Preserve lower paired worker
  limits; the default worker capacity remains one.
- Turso remains the optional, read-only lead/content provider read directly by
  each active engine instance. It is not implicitly the coordinator job database.
- Existing mailer features and transports remain available during migration.
- New capabilities which the existing mailer cannot support are explicit pending
  integrations; never simulate success or silently switch to a different mode.

## Existing state and stack

The checked-in application is FastAPI + SQLAlchemy + Jinja templates, with
SQLite by default and PostgreSQL configuration support. It accepts existing
`POST /api/instances` publications, lists instances, and provides a login/admin
interface. This is a registry, not an already implemented campaign scheduler.
Keep those endpoints and existing tables backward compatible.

The long-term common web/Android presentation direction is Flutter. Extend the
existing dashboard now for independently useful fleet operations; do not block
backend work on a complete frontend replacement.

## Responsibilities

1. Preserve existing URL registration and public/local link display.
2. Add authenticated worker pairing, per-worker credentials, heartbeats,
   capabilities, protocol-version checks, and session identity.
3. Add durable jobs, explicit ownership, bounded claims, results, events,
   cancellation rules, uncertainty handling, and idempotent submission.
4. Provide dashboard views for online/offline/never-connected workers and job
   history, including failed and uncertain outcomes.
5. Provide the canonical versioned client contract and representative fixtures.
6. Add a legacy Gradio connector without changing the running mailer. Capability
   discovery is read-only; do not invoke campaign endpoints during discovery.
7. Route Flutter dashboard requests through Python rather than pretending the
   Gradio JavaScript client is a native Dart/Android package.

## Canonical contract and directory ownership

| Location | Ownership |
| --- | --- |
| `app/fleet_schemas.py` | Strict versioned Python request models |
| `contracts/v1/` | Exported JSON Schema, protocol description, shared fixtures |
| `app/fleet_models.py` | Additive worker, job, and event tables |
| `app/fleet_routes.py` | Operator and worker HTTP routes |
| `app/fleet_service.py` | Transactional state transitions and claims |
| `app/gradio_adapter.py` | Legacy endpoint inspection/translation boundary |
| `app/templates/`, `app/static/` | Existing dashboard integration |
| `tests/` | Offline API, persistence, concurrency, legacy compatibility tests |
| `tools/` | Contract export and safe local development helpers |

Contract changes are additive within version 1. Breaking changes require a new
version and explicit compatibility behavior. Browser and Android clients must
consume the published shape, not invent their own command names or states.
Do not duplicate mailer business rules in the coordinator or clients.

Initial operations are `runtime.probe`, `gmail.compose`, and `gmail.draft`.
Gmail jobs accept already prepared recipient, subject, body, and attachment data.
This does not claim that campaign rendering has already been extracted from the
legacy engine. Browser execution defaults to preview. Actual sending requires
explicit operator intent and a server-side enablement setting; never send as a
side effect of registration, health checking, page load, or demo startup.

## Identity, authentication, and data handling

- Distinguish stable worker identity, runtime session identity, account identity,
  job identity, slot identity, and lease token.
- The existing registry API token is an operator credential, not a token to ship
  in an extension or Android application.
- Pairing returns a random per-worker token once; store its digest server-side.
- Worker tokens can only access their own assignments and account bindings.
- Pairing and job creation require operator authorization. Cookie-based UI
  mutations require CSRF protection, not merely an authenticated cookie.
- Do not expose tokens in URLs, logs, HTML after initial pairing, job payloads,
  exceptions, or shared fixtures.
- A coordinator login does not protect a separate Gradio public URL. Document
  that boundary; do not silently assume remote runner authentication exists.
- Attachment handling must be bounded and authenticated. Reject unsafe filenames,
  malformed base64, excessive size, and arbitrary caller-supplied fetch targets.
- Preserve selected Turso/local source behavior; do not preload or modify real
  lead/content data during development.

## Job semantics

- Submission uses an idempotency key plus a canonical request hash. Repeating an
  identical request returns the existing job; changing the request with the same
  key is a conflict.
- A claim is transactional: one owner, one account, one slot, one session, one
  lease. Worker/account/slot limits must hold under concurrent HTTP requests.
- States: `queued`, `leased`, `running`, `sending`, `succeeded`, `failed`,
  `uncertain`, `cancelled`. Validate transitions server-side.
- A preview cannot transition to `sending`.
- Persist `sending` before instructing a worker to click Send. Losing contact
  thereafter is uncertain, not a reason to automatically resend.
- Expired browser leases can also be uncertain before sending: opening Compose
  may already have created a draft. Do not blindly recreate it.
- Lease renewal and result reports require the matching worker, runtime session,
  unexpired lease, and lease token. Old sessions cannot finish new assignments.
- Retrying a report must not duplicate events or reinterpret a completed result.
- Cancellation is safe while queued. In-flight cancellation needs an acknowledged
  stop and cannot undo a send already accepted by Gmail.
- `succeeded` describes the requested operation. A successful preview is not a
  sent email; Sent-folder confirmation is not recipient inbox delivery.
- No exactly-once delivery guarantee is possible across ambiguous external sends.

For a distributed campaign, the coordinator owns assignment records and runners
own execution journals. For a standalone campaign, its local runtime is the
scheduling authority. Never let two independent schedulers assign the same
campaign's recipients simply because both can read the same Turso table.

## Persistence and compatibility

Add tables without destructive changes to the existing registry. Test startup
against a database containing only the old tables and records. Do not run
development against a real `app.db` or configured production database.

SQLite is acceptable for the initial single-coordinator deployment; claims must
use database-checked conditions, not only an in-memory Python lock. PostgreSQL
remains supported. Local runner journals and coordinator assignments have distinct
roles. Colab runtime storage is disposable; recovery requires external checkpoints
and stable prepared artifacts, not a claim that Gradio sessions are durable.

## Implementation sequence and acceptance gates

| Milestone | Required evidence |
| --- | --- |
| Contract and pairing | Exported schema; invalid-version and unauthorized calls rejected |
| Durable worker/job lifecycle | Restart persistence; idempotency; scoped credentials; stale lease/session rejection |
| Parallel claims | Duplicate-claim and account/slot/capacity race tests |
| Dashboard | Pair/list workers; submit preview/probe; inspect job state and events |
| Legacy compatibility | Original registration payload works unchanged; old tables preserved |
| Gradio adapter | Read-only endpoint inventory; unsupported operations reported explicitly |
| Sibling integration | Browser and Android clients use the same fixtures and error semantics |
| Sending readiness | Explicit enablement, transition fencing, uncertainty handling, user-designated live QA |

## Verification and completion reporting

Use a project-local virtual environment. Run focused pytest tests against temporary
databases, then the relevant full suite. Validate exported schema against client
fixtures. Test concurrency with independent database sessions and persistence with
a new application/session, not only mock dictionaries. Inspect the rendered fleet
page locally. Never send live mail or contact real accounts as an implicit test.

Report separately: code implemented, automated tests passed, local UI verified,
real service behavior verified, and remaining device/provider gates. Do not call
a fake worker, fixture Gmail page, or runtime capability probe a production pass.
Confirm the protected mailer directory was not changed by this work.

## Starting checkpoint

`app/fleet_models.py` and `app/fleet_schemas.py` were started before these guides
were requested. They are unfinished and unverified until integrated and tested.
Python and Node are available. Flutter/Android tooling was not found during the
initial environment inspection; Android APK verification must be stated separately.
