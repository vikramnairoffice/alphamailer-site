# Fleet protocol version 1

Execution: [Plan.md](Plan.md) · [Tasks.md](Tasks.md).

The Python models in [app/fleet_schemas.py](../../app/fleet_schemas.py) are canonical. Regenerate JSON Schema
with `python -m tools.export_contract` from the orchestrator directory.
The browser build generates TypeScript request types from these schemas.
Android's contract tests read fixtures.json. Pydantic validators additionally
enforce operation/account/confirmation and attachment-content constraints which
JSON Schema alone cannot express.

## Navigation and consumers

- [Application map](../../app/README.md): route/service/model ownership.
- [CampaignCreate schema](CampaignCreate.schema.json), [JobCreate schema](JobCreate.schema.json) and [shared fixtures](fixtures.json): generated protocol inputs.
- [Contract exporter](../../tools/export_contract.py): regenerate canonical exports.
- [Automation source](../../../Alphamailer-automation/extension/src/README.md) and [native campaign operator guide](../../../Alphamailer-automation/docs/Operations.md#campaign-import-and-cancellation): browser and Gradio consumers.
- [Android source map](../../../Alphamailer-Android/lib/README.md): Flutter/native consumers.
- [Dated status](../../Implementation-Status.md): verified behavior and remaining gates.

## Authentication and endpoints

The additive [Google browser authorization extension](google-oauth.md) defines
Android consent, secure handoff, and token refresh through a configured web client.

All paths below start with /api/v1. Use Authorization: Bearer <credential>.
Operator credentials are the coordinator's API_TOKEN; workers use the distinct
credential returned once by pairing. Never give a worker the operator token.

| Method / route | Credential | Response |
| --- | --- | --- |
| GET /protocol | None | Version, operations, lease duration |
| POST /workers | Operator | Worker metadata + one-time worker_token |
| GET /workers | Operator | Worker metadata, never credentials |
| GET /worker | Worker | Own worker metadata |
| POST /worker/heartbeat | Worker | Presence, renewed_job_ids, lease_seconds |
| POST /worker/claim | Worker | {job:null} or {job:{...},lease_token} |
| POST /worker/report | Worker | Updated own job |
| GET /worker/jobs | Worker | Latest 100 own jobs, no message/lease token |
| POST /jobs | Operator | Created or existing idempotent job |
| GET /jobs | Operator | Paged jobs: default 100, limit 1–500 and offset >= 0; no prepared message |
| GET /jobs/{id}/events | Operator | Ordered state/detail/at events |
| POST /jobs/{id}/cancel | Operator | Cancels only queued jobs |
| POST /campaigns | Operator | Atomic lead manifest with one job per assignment |
| GET /campaigns | Operator | Up to 100 recent aggregate campaign results |
| GET /campaigns/{id} | Operator | Lead and job drill-down |
| POST /campaigns/{id}/cancel | Operator | Cancel queued leads |

Native Gradio campaign import/review/launch uses these existing operator routes.
Individual cancellation succeeds only while a job is queued. Campaign cancellation
marks queued assignments cancelled and records the request; already leased,
running or sending work may finish. A `cancelling` campaign is not an acknowledged
in-flight stop. Operator controls, including fresh screen confirmation for imported
send assignments, are documented in the Automation guide linked above.

A job response includes id, worker_id, operation, execution, account_email,
state, slot_id, session_id, lease_expires_at, result, detail, created_at,
updated_at and protocol_version. Only a claim includes message and lease_token.
Claims include the stable job idempotency key; fleet jobs use `fleet:<assignment-id>`.
Timestamps are UTC. Heartbeat responses list only successfully renewed leases.

## Fleet campaign ownership

Submit up to 500 assignments with globally stable lead IDs. A lead ID is reserved
across campaign history, including after cancellation; an intentional rerun needs
a new lead ID and campaign key. Existing assignment journals are checked when an
older database did not yet have the lead-identity table. The coordinator derives stable
assignment IDs from the campaign ID and lead ID, stores an input hash and creates
all jobs in one transaction. Reusing a campaign key with changed input is a
conflict. One account belongs to one worker within a campaign and can have only
one active fleet campaign at a time. A unique database account reservation
serializes competing campaign submissions; distinct accounts can run in parallel.
`min_interval_seconds` paces claims per account across consecutive campaigns.

Browser assignments carry a frozen prepared message. Engine assignments carry
immutable lead/config inputs. The instance prepares and stores one frozen message
per assignment, then uses its assignment ID as the execution journal key. Fleet
workers use `campaign.assignment`, without invoking the local campaign scheduler
for the same recipients. Coordinator assignments and instance delivery evidence
remain separate durable records.
Direct `POST /jobs` submission of `campaign.assignment` is rejected. An active
fleet assignment and a queued/running coordinator `campaign.start` for the same
worker account are mutually exclusive. Locally started campaigns outside the
coordinator still need operator care because their lead lists are private to
the device.

Campaign progress is derived from each job state. Cancellation stops queued claims
and leaves leased work to be acknowledged or reconciled. Expired leases remain
uncertain and are never automatically requeued. Command acceptance is distinct
from campaign completion and recipient inbox delivery.

## Worker loop

1. Validate protocol 1 and paired capabilities/accounts.
2. Persist a runtime session ID. Heartbeat approximately every 30 seconds.
3. Claim using that session and a stable slot ID. Use account_email=null for
   runtime.probe; Gmail jobs require the exact paired mailbox.
4. Persist the assignment before page/native effects. Report running.
5. Renew current owned leases with each heartbeat; lifetime is 120 seconds.
6. A send job must receive a successful sending acknowledgement before the
   irreversible click. Preview cannot transition to sending.
7. Persist the terminal report, then send it. Retry the same report on a lost
   acknowledgement; never replay the external effect.
8. A lost/restarted browser operation is uncertain. An expired assignment is
   terminal and is not requeued.

A different session cannot take over a recently active worker. After it is offline,
the next heartbeat fences old work. HTTP 401 means invalid credentials; 403 means
forbidden ownership/send action; 404 means unavailable resource; 409 means conflict,
stale session/lease, or invalid transition; 422 means invalid payload/capability.
Do not convert these failures into permission to send again.

## Bounds and sending

At most ten parallel slots and ten distinct assigned mailboxes per worker.
Workers may select a lower `max_parallel` capacity; the default remains one.
Browser workers bind each distinct Gmail account to its own tab. Claims enforce
one active assignment per slot/account under concurrent requests, and each
heartbeat can renew up to ten active leases. Existing one-to-five-slot clients
remain compatible. Prepared messages support up to 50 To
recipients, four files of 2 MB each, and a 250,000-character body. Large campaigns,
BCC/CC, arbitrary MIME/headers and streaming artifact storage need later contracts.

Sending is disabled by default. An operator must set ENABLE_WORKER_DELIVERY=true
(ENABLE_BROWSER_SEND is the legacy fallback when that setting is absent)
and submit execution=send with confirmation=SEND. The enablement is checked again
at the sending transition. Disabling cannot retract a previously acknowledged
external send. The same gate applies to fleet delivery. The Flutter dashboard
has a structured fleet form with explicit send confirmation, while the Python
admin page shows aggregate progress and cancellation.

The Gmail adapter assumes English Gmail labels. Existing-draft lookup requires
the exact RFC 822 Message-ID and expected content. Canonical rich HTML and
downloaded attachment bytes are checked in local browser fixtures; real Gmail
attachment URLs, MIME normalization and provider behavior still need acceptance.
See [Automation's dated status](../../../Alphamailer-automation/Implementation-Status.md)
for the exact verified browser/provider boundary.
