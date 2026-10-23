# Google browser authorization extension (version 1)

All `/api/v1/worker/google/*` routes use the existing per-worker bearer credential,
and only Android workers may use them. Start/refresh additionally check the
worker's allowed account binding. Never put the worker token in a URL.

| Route | Request schema | Response |
| --- | --- | --- |
| `POST /api/v1/worker/google/start` | `GoogleOAuthStart` | `protocol_version`, `session_id`, `handoff_key`, `authorization_url`, `expires_in` |
| `POST /api/v1/worker/google/poll` | `GoogleOAuthSession` | `protocol_version`, `status`, and `account` only when ready |
| `POST /api/v1/worker/google/ack` | `GoogleOAuthSession` | `protocol_version`, `status: consumed` |
| `POST /api/v1/worker/google/cancel` | `GoogleOAuthSession` | `protocol_version`, `status: cancelled` |
| `POST /api/v1/worker/google/refresh` | `GoogleOAuthRefresh` | `access_token`, `refresh_token`, `expires_in`, `scope`, `receipt` |

Statuses are `pending`, `exchanging`, `ready`, `failed`, `cancelled`, `consumed`.
Expired attempts return 404. A start replaces that worker's prior attempt. The
handoff key is required in addition to worker authentication; save it privately.
Polling is read-only and repeatable until acknowledgement. Ack is idempotent until
expiry. Persist the account before ack; ack destroys the temporary token copy.

The ready `account` has `id`, `email`, `auth_type: oauth`, and `oauth` containing
`type: authorized_user`, `token`, `refresh_token`, `client_id`, `scopes`, `expiry`,
and `alphamailer_broker: {origin, receipt}`. There is deliberately no client secret.
The Android platform credential adapter adds the worker token in encrypted local
storage. It refreshes through the broker rather than Google's direct token URL.
Never serialize these fields into fleet job payloads, event details, or diagnostics.

400 indicates a bad/expired encrypted receipt; 401 invalid worker authentication;
403 worker/account binding denied; 404 unavailable handoff; 409 invalid transition
or concurrent start; 422 invalid version/shape; 502 provider failure; 503 missing
broker configuration. Provider response bodies and invalid secret values are not
echoed. Client errors should direct the user to retry or reconnect, never render
raw token exchange responses.

`GET /oauth/google/callback` is Google's public state-protected callback; it is not
a worker API. It redirects to a fixed completion page. The fixed
`alphamailer://oauth/return` link only foregrounds Android. It is not registered as
a Google redirect URI and carries no authentication authority.
