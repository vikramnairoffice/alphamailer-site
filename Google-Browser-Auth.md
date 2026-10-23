# Google browser authorization for Android

Android can connect a Gmail account in an external browser and receive the result
automatically. This flow never calls Android AccountManager or adds a system Google
account. Google may retain a browser sign-in session; that is separate from Android
system accounts. The app never collects the Google password.

## Coordinator setup

1. Create a **Web application** OAuth client in your Google Cloud project. Enable
   Gmail API and configure its consent screen and authorized test users as needed.
2. Register the exact redirect URI
   `https://YOUR-COORDINATOR/oauth/google/callback` in that client.
3. Download the client JSON and keep it outside the repository and web/static
   directories, readable only by the service account. Its top-level key must be
   `web`, with `client_id`, `client_secret`, and `redirect_uris`. Android/desktop
   client JSON and service-account JSON are not interchangeable with this file.
4. Configure the coordinator:

   ```text
   GOOGLE_OAUTH_CLIENT_FILE=/private/path/google-web-client.json
   GOOGLE_OAUTH_REDIRECT_URI=https://YOUR-COORDINATOR/oauth/google/callback
   GOOGLE_OAUTH_ENCRYPTION_KEY=<Fernet key from a secret manager>
   ```

   A Fernet key is a URL-safe base64 encoding of 32 random bytes. Provision it
   through your secret manager; keep it stable across restarts and replicas.
   All replicas must use the same database, OAuth client, and encryption key.
   Install the updated requirements and restart the coordinator. The additive
   `google_authorization_sessions` table is created by the normal startup path.
5. Pair the device as an Android worker, with the exact Gmail email in its allowed
   accounts. Enter the coordinator URL and per-worker token in Android's **Worker
   connection** screen. An operator token must never be placed in the Android app.
6. Open **Local mailer → Accounts**, enter that Gmail email, and tap **Connect Google
   in browser**. Complete consent on Google's website. The completion page returns
   to Alphamailer automatically where the browser permits it, or offers **Open
   Alphamailer**. Credentials are imported automatically either way; there is no
   copy/paste code or token JSON step.

Suppress query strings on `/oauth/google/callback` in reverse-proxy, hosting,
tracing, and access logs. This route strips the query from Uvicorn's request scope
before responding, but cannot control upstream logs. Use HTTPS in production; this
flow deliberately has no HTTP, out-of-band, or mobile loopback fallback.

## Behavior and boundaries

- The initial permission set is email identity plus `gmail.compose` (drafts and
  sending). Drive, Calendar, Forms, and mailbox-reading features need their own
  additional scopes; this button does not request them silently.
- Google is requested to provide offline access, with consent and account
  selection. Missing refresh tokens, incomplete permissions, unverified email,
  or a different email cause the attempt to fail without importing an account.
- State and PKCE protect authorization. The callback is claimed once through a
  database conditional update. The browser's app link contains no credentials.
- An attempt expires after ten minutes; expired rows are purged on the next OAuth
  session request. Context and ready credentials are encrypted in the database.
  The authenticated phone receives its result repeatedly until it acknowledges
  successful storage. Acknowledgement clears temporary server credentials.
- The refresh token, access token, scope information and worker-bound refresh
  receipt are stored in the Android Keystore-backed credential vault. The Google
  web client secret stays exclusively on the coordinator.
- Future token renewal uses the coordinator. Preparation and mail execution still
  run locally. An unavailable coordinator prevents renewal after the access token
  expires; app-password and imported direct-OAuth accounts retain their behavior.
- Revoking/rotating a worker token, removing its allowed account, changing the
  Google client, or rotating the encryption key requires connecting that Google
  account again. Google can also expire or revoke authorization independently.
- Closing the app preserves the pending handoff in encrypted storage. When it
  resumes it can finish an unexpired attempt. It does not require background
  polling or a system Google account. A stable account ID makes retrying import
  safe; the app acknowledges only after local storage succeeds.
- OAuth consent alone never sends mail, creates drafts, or schedules a campaign.

## Verification

Automated tests use fixture credentials and fake Google responses. They cover
worker scoping, account identity, partial consent, missing refresh tokens, callback
replay/races, expiration, cancellation, encrypted storage, refresh binding,
save-before-acknowledgement, and recovery. These tests do not prove Google consent
or physical-device behavior. Real provider acceptance requires the configured
HTTPS deployment, the operator's Web client, and a designated test account.

References: [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server),
[Google OAuth best practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices),
[mobile redirect restrictions](https://developers.google.com/identity/protocols/oauth2/native-app).
