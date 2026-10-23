# Alphamailer Orchestrator scope

## Goal

Advance coordinator and client integration while four existing Alphamailer sprints
continue. No edits or generated output are permitted in `../Alphamailer/`.

## Current baseline

- Existing FastAPI URL registry, login/admin pages and SQLite/PostgreSQL support.
- Fleet tables/contracts, Android engine commands, browser workers, a live Gradio
  connector and the Flutter dashboard are integrated. See current verification
  in Implementation-Status.md.
- Existing user-authored scope/status/specification documents are preserved.

## In scope now

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

## Deferred integration, not silently removed scope

- Exhaustive parity mapping of the final original frontend and hidden Gradio callbacks.
- Fleet-level campaigns spanning multiple instances and lead assignment manifests.
- Frontend refinement beyond the implemented shared dashboard and advanced configuration.
- Production deployment, production credential provisioning and live account QA.
- Full artifact storage/retention for large campaigns beyond the initial bounded
  prepared-message protocol.

These require later milestones, not changes to the protected mailer during its
remaining sprints. Independent backend/client work continues meanwhile.

## Explicit exclusions

- Modifying or copying the current mailer engine/frontend.
- Running real campaigns, selecting arbitrary account tokens, or sending email as
  an automated development test.
- Publishing/deploying to external production services without a concrete request.
- Replacing Turso's lead/content role with a hidden job database.
- Claiming exactly-once external delivery, guaranteed Colab uptime, or full Android
  compatibility based only on a shared protocol.

## Delivery gates

1. Contract and additive storage are implemented and tested.
2. Pairing, ownership and version checks pass.
3. Claims, expiry, restart and idempotency pass concurrent/persistent tests.
4. Existing URL registration remains compatible.
5. Operator UI and sibling client flows work against a local test server.
6. Release notes identify unavailable engine operations and unverified live targets.

Maintain a separate implementation status record as work lands. A planned row or
method stub is not a completed deliverable. Follow `Agent.md` and
`Architecture.md` for execution and design rules.
