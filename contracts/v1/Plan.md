# Fleet protocol version 1 plan

Updated: 2026-10-19. Owner: fleet protocol version 1.

[Local tasks](Tasks.md) · [Directory guide](README.md) · [Project plan](../../Plan.md) · [Project tasks](../../Tasks.md)

## Current baseline

Canonical request models are owned by app/fleet_schemas.py; this directory contains exported schemas, fixtures and protocol/OAuth guides. Current bounds permit ten account slots while preserving lower worker capacities.

Runtime evidence remains in the owning project's dated status/QA documents.
Creating or updating this plan does not rerun application tests.

## Work sequence

1. Start any contract change in the canonical Python models and preserve additive version-1 compatibility.
2. Regenerate schemas/fixtures and rebuild browser types/validators; reconcile Android consumers (`ORC-107`).
3. Verify version errors, account/lease/state semantics and mixed-worker recovery before claiming cross-client compatibility (`ORC-103`, `ORC-105`, `ORC-107`).

## Completion and ownership

Use [Tasks.md](Tasks.md) for the local checklist. Parent project IDs retain their
original meaning and completion state; local items are scoped follow-up work,
not a declaration that the entire parent milestone is complete. Add dated
acceptance evidence before checking runtime work, and update the relevant source
map/workflow guide when behavior changes. Child directories without their own
planning pair inherit this directory's scope.
