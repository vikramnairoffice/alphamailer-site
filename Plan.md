# Orchestrator development plan

Baseline: 2026-09-27. Owner: coordinator, fleet protocol and Gradio bridge.

Source reconciliation: 2026-10-23 at `d465e72`. The
[current source review](Implementation-Status.md) records implemented campaign,
OAuth and ten-slot behavior separately from remaining mixed-client, artifact,
final legacy mapping and operations acceptance. No new runtime tests ran here.

## Goal and baseline

Coordinate Colab/VM, Android and browser workers from one dashboard while reusing
the original Gradio APIs. Registry compatibility, worker jobs, leases/recovery,
Gradio sessions and shared dashboard integration exist. Durable fleet manifests,
per-lead assignments, account pacing, aggregate progress and queued cancellation
are implemented (`ORC-101`/`ORC-102`). Mixed real-client recovery and acknowledged
in-flight control results remain open (`ORC-103`/`ORC-105`).

Read [Agent.md](Agent.md), [Architecture.md](Architecture.md), [Scope.md](Scope.md),
[Implementation-Status.md](Implementation-Status.md) and [Tasks.md](Tasks.md).
Preserve the user's existing `Project Scope.md`, `Tasks and Status.md` and
`Technical Specs.md`; this new checklist tracks the migration workstream.

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

Updated 2026-10-19. Each maintained owner directory below has a local work
sequence and checklist. Subdirectories without their own pair inherit the nearest
owner's plan; generated output, dependencies and credential/data stores are excluded.
The project task IDs stay authoritative for cross-directory acceptance.

| Directory | Work sequence | Checklist |
| --- | --- | --- |
| app | [Plan](app/Plan.md) | [Tasks](app/Tasks.md) |
| contracts/v1 | [Plan](contracts/v1/Plan.md) | [Tasks](contracts/v1/Tasks.md) |

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
