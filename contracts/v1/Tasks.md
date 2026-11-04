# Fleet protocol version 1 tasks

Updated: 2026-10-19. Owner: fleet protocol version 1.

Sequence: [Plan.md](Plan.md). Navigation: [README.md](README.md).
Parent work and acceptance: [project Tasks.md](../../Tasks.md).

## Completed documentation

- [x] `ORC-CON-001` Add and connect the local Plan.md/Tasks.md pair
  (2026-10-19; documentation only).

## Remaining work

- [ ] `ORC-CON-101` Complete the final schema/fixture agreement check across browser and Android consumers.
  Parent task dependencies: `ORC-107`.
- [ ] `ORC-CON-102` Extend contract fixtures for remaining mixed-client cancellation and restart/control outcomes.
  Parent task dependencies: `ORC-103`, `ORC-105`.
- [ ] `ORC-CON-103` Record compatible consumer/build versions and regenerate exports whenever canonical models change.
  Parent task dependencies: `ORC-107`.
  Progress 2026-11-03: `MAX_WORKER_PARALLEL` is 20 for accounts, `max_parallel` and heartbeat leases; lower paired worker limits remain valid.

## Update rule

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
