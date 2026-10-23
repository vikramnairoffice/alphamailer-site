# Coordinator application plan

Updated: 2026-10-19. Owner: coordinator application.

[Local tasks](Tasks.md) · [Directory guide](README.md) · [Project plan](../Plan.md) · [Project tasks](../Tasks.md)

## Current baseline

Registry compatibility, scoped workers, durable jobs, campaign assignment/progress, queued cancellation, Gradio sessions and the Google OAuth broker are implemented. Mixed-client recovery and production operations remain open.

Runtime evidence remains in the owning project's dated status/QA documents.
Creating or updating this plan does not rerun application tests.

## Work sequence

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
