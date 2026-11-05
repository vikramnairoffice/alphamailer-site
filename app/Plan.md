# Coordinator application plan

Updated: 2026-10-19. Owner: coordinator application.

[Local tasks](Tasks.md) · [Directory guide](README.md) · [Project plan](../Plan.md) · [Project tasks](../Tasks.md)

## Current baseline

Registry compatibility, scoped workers, durable jobs, campaign assignment/progress, queued cancellation, Gradio sessions and the Google OAuth broker are implemented. Mixed-client recovery and production operations remain open.

Runtime evidence remains in the owning project's dated status/QA documents.
Creating or updating this plan does not rerun application tests.

## Work sequence

Browser OAuth update 2026-11-04: request Drive file and Calendar event access
alongside Gmail, verify partial consent and refresh compatibility, then complete
live consent/provider acceptance under `ORC-201` and Android `AND-103`.

1. Finish mixed-worker progress/control acknowledgement and disconnect/restart fixtures (`ORC-103`, `ORC-105`).
2. Reconcile the final legacy Gradio callback/settings surface and client contract consumers (`ORC-104`, `ORC-107`).
3. Complete artifact retention/recovery and verify the intended database/single-process deployment topology (`ORC-106`, `ORC-301`, `ORC-302`).

## Completion and ownership

Use [Tasks.md](Tasks.md) for the local checklist. Parent project IDs retain their
original meaning and completion state; local items are scoped follow-up work,
not a declaration that the entire parent milestone is complete. Add dated
acceptance evidence before checking runtime work, and update the relevant source
map/workflow guide when behavior changes. Child directories without their own
planning pair inherit this directory's scope.

2026-11-04 (`ORC-103`): Publish additive relative pacing hints from the canonical
claim path so browser workers can schedule the next eligible check precisely.

2026-11-04 (`ORC-107`, Automation `WEB-124`): Relax only campaign-wide bounds;
retain individual message checks, send confirmation, account ownership and pacing.
Bound historical identity SQL queries and avoid repeated per-account validation.

## Maintenance audit ? 2026-11-05

Removed five unused imports while preserving registration side effects and all route/schema contracts. Offline suite: 60 passed, 1 skipped.
See the [suite YAGNI audit](<../Maintenance-2026-11-05.md>) for scope, checks and retained findings.
Existing feature and release milestones retain their current status.


## Dependency maintenance - 2026-11-05

Framework and dependency manifests were upgraded to current stable versions,
with documented native-package compatibility limits. See the
[suite upgrade record](<../Maintenance-2026-11-05.md>) for versions, migration changes,
validation results and compatibility exceptions. Existing feature and release
acceptance milestones retain their current status.
