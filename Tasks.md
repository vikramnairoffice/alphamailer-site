# Orchestrator tasks

Baseline: 2026-09-27. Owner: coordinator/fleet. Sequence: [Plan.md](Plan.md).
Checked items are bounded code/local evidence from
[Implementation-Status.md](Implementation-Status.md), not production certification.

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
campaigns, aggregate views, queued cancellation, the OAuth broker and ten-slot
browser bounds. The [current status](Implementation-Status.md) distinguishes these
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
  acknowledgement. See [Automation evidence](../Alphamailer-automation/Implementation-Status.md).
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
