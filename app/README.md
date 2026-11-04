# Coordinator application map

Execution: [Plan.md](Plan.md) · [Tasks.md](Tasks.md).

[Project entry](../README.md) · [Architecture](../Architecture.md) · [Protocol](../contracts/v1/README.md)

| Responsibility | Source |
| --- | --- |
| App startup, route registration and Flutter dashboard mount | [main.py](main.py) |
| Legacy instance URL registry | [api_routes.py](api_routes.py), [schemas.py](schemas.py), [models.py](models.py) |
| Admin sessions/users and credentials | [admin_routes.py](admin_routes.py), [auth.py](auth.py) |
| Settings and database/session ownership | [config.py](config.py), [database.py](database.py) |
| Canonical worker/job/campaign request models | [fleet_schemas.py](fleet_schemas.py) |
| Worker tokens, claims, leases, reports and queued-job cancellation | [fleet_service.py](fleet_service.py) |
| Fleet persistence and campaign tables | [fleet_models.py](fleet_models.py) |
| Campaign submission, assignments, aggregate state and queued cancellation | [campaign_service.py](campaign_service.py) |
| Public/operator/worker fleet route authentication | [fleet_routes.py](fleet_routes.py) |
| Legacy Gradio discovery and invocation handles | [gradio_adapter.py](gradio_adapter.py), [gradio_bridge.py](gradio_bridge.py) |
| Android Gmail/Drive/Calendar OAuth broker and refresh | [google_oauth.py](google_oauth.py), [scopes and reconnect setup](../Google-Browser-Auth.md) |
| Admin rendering | [templates](templates/), [static assets](static/) |

The native [Automation Campaigns screen](../../Alphamailer-automation/docs/Operations.md#campaign-import-and-cancellation)
uses the existing operator campaign/job endpoints; browser workers use separate
scoped credentials. The [Flutter dashboard](../../Alphamailer-Android/lib/README.md)
is built by the Android project. The [engine](../../Alphamailer-Engine/README.md)
executes business logic inside each runtime, not inside the coordinator.

For contract changes, update the Python models, run
[tools/export_contract.py](../tools/export_contract.py), and reconcile browser and
Android consumers. Do not hand-edit client generated files. Route/claim/campaign/
OAuth/Gradio tests are in [tests](../tests/). Disposable integration servers and
benchmarks are in [tools](../tools/); use [current startup/evidence](../Implementation-Status.md)
and [remaining operations tasks](../Tasks.md), including the single-process limit.

2026-11-04: campaign_service.claim_pacing computes the latest applicable account
deadline. fleet_service returns optional retry_after_ms on a paced empty claim.
The boolean paced_claim helper and all assignment/lease semantics remain.

Campaign admission has no fixed assignment-count or aggregate manifest-byte cap.
`campaign_service.py` checks historical lead identity in bounded SQL chunks and
validates standalone ownership once per account. See the
[canonical campaign contract](../contracts/v1/README.md#fleet-campaign-ownership) and dated
[verification](../Implementation-Status.md). Individual message checks remain.
