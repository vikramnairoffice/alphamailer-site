# Coordinator application tasks

Updated: 2026-10-19. Owner: coordinator application.

Sequence: [Plan.md](Plan.md). Navigation: [README.md](README.md).
Parent work and acceptance: [project Tasks.md](../Tasks.md).

## Completed documentation

- [x] `ORC-APP-001` Add and connect the local Plan.md/Tasks.md pair
  (2026-10-19; documentation only).

## Remaining work

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

## Update rule

Keep local IDs stable. Leave partial work unchecked and add a dated progress note.
Parent project tasks remain authoritative for cross-directory acceptance; do not
close them solely because a local documentation item is complete. Record the
actual verification scope and link dated evidence rather than copying historical
test totals into this file. This planning update ran no application/provider tests.

- [x] 2026-11-04 / `ORC-103`: Add retry_after_ms for pacing-blocked empty claims;
  preserve cross-campaign account pacing and active-job exclusion.
