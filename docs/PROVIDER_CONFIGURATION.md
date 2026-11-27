# Provider configuration

Discord, Twitch, YouTube, Microsoft Graph email, Cloudflare Turnstile, OpenAI
moderation and Steam Web API credentials can be managed under
Admin > Website > Provider configurations. Only active superusers can view or
change these records, including through direct URLs. Model permissions alone
do not grant access. Database passwords, Django signing keys and encryption
keys remain host-managed.
SteamCMD interactive login and its existing connection flow remain unchanged.
Microsoft Graph sender/reply-to addresses remain host settings.

## Storage and behaviour

- Each provider has at most one record. The source is server environment,
  encrypted database record, or disabled. If no record exists, runtime uses the
  server environment.
- Database mode requires a secret or API key. OAuth integrations require a
  valid client ID and exact callback on `SITE_PUBLIC_URL`. Microsoft Graph
  requires client and tenant UUIDs; Turnstile requires its public site key.
  HTTPS callbacks are required except explicit
  debug loopback development. This checks structure, not provider registration
  or whether a secret is accepted by the provider.
- Secrets use [authenticated Fernet encryption](https://cryptography.io/en/stable/fernet/) with a separate
  `PROVIDER_CONFIG_ENCRYPTION_KEYS` key ring. The encrypted payload includes
  the provider and site origin. IDs and callback URLs are not secret.
- The site binding is assigned by the server and is not editable in admin.
  Database records restored onto another origin fail closed. Missing keys,
  corrupt ciphertext and invalid database records do not silently fall back.
- The password field is replace-only. Blank preserves the existing secret;
  changing the client ID requires a replacement secret. A native page save
  clears the input, including after validation errors. Saved plaintext and
  ciphertext are excluded from admin pages and history.
- Admin history records actor, time, provider and changed field names only.
  Deletion is unavailable. Select disabled or server environment instead.
- Runtime reads the database for each operation, without process-global caching.
  Changes apply without restarting web or worker processes. An in-flight OAuth
  flow may need to be retried after changing application credentials.
- Disabling blocks new connections and token exchanges. If credentials cannot
  be read, disconnect reports an error on Settings and preserves the local link.
  Existing participant tokens are not re-encrypted or rewritten by this feature.

## Provisioning and import

For the first live deployment, no existing live credentials are available to
import. Provision the host key ring and schema, then create the seven live
records through the superuser admin while the public construction page remains
up. Register live callback URLs with the OAuth providers. Do not copy staging
records or keys. Follow the admin-first phase in PRODUCTION_DEPLOYMENT.md;
public opening waits for completed administration-side acceptance.

The environment-import procedure below applies only where credentials already
exist, as they did on staging:

1. Generate a fresh Fernet key on the target host using `Fernet.generate_key()`.
   Store it privately in the protected environment as
   `PROVIDER_CONFIG_ENCRYPTION_KEYS`. Do not put keys in command arguments,
   Git, database records, screenshots or task output.
2. Apply migration `administration.0003_providerconfiguration` and
   `administration.0004_providerconfiguration_tenant_id_and_more`. Reload the host
   environment when restarting the services through the normal deployment flow.
3. Run `manage.py provider_configuration import --actor <superuser-email>`
   with that environment loaded. This imports all seven existing environment
   credentials atomically; use repeated `--provider discord` / `--provider twitch`
   / `--provider youtube` to select a subset; service names are `graph`,
   `turnstile`, `openai` and `steam`. It refuses existing records and
   requires an active superuser actor. Output contains only action and count.
4. Run `manage.py provider_configuration check` to verify decryption, binding
   and structural validity offline. It makes no provider requests.
5. Take a fresh coordinated backup of the database and protected configuration.
   Keep the host environment credentials temporarily for rollback. Once the
   database configuration is accepted, they may be removed separately: startup
   allows absent integration credential environment values when a valid provider key is present.

## Recovery, rollback and rotation

Database backups contain ciphertext, not the encryption keys. Recovery requires
both the database and its matching protected configuration. OSWALD's existing
backup captures the entire environment in `protected.env`, separately from the
SQL archive, with its own hash and restricted access. A holder of both artifacts
can decrypt secrets. Local-only host-loss risk remains accepted; off-host backup
is a future improvement. Do not copy staging configuration or keys onto live.

For rollback, select server environment for the affected provider after ensuring
its environment values are still valid. Keep the additive table during code
rollback. Older code ignores database records and uses environment credentials,
which may be stale if a provider secret has since been rotated.

For key rotation, prepend a new key to the comma-separated key ring and reload
both processes. Run `manage.py provider_configuration rotate --actor
<superuser-email>` and then `manage.py provider_configuration check`. Rotation is
atomic and audited without values. Capture and verify a new backup before
retiring the old key from the running key ring. Preserve old keys securely for
as long as retained backups need them. A lost key cannot be reconstructed from
the database; replace credentials using the provider console if recovery keys
are unavailable. Changing the site origin requires an explicit operator-reviewed
reprovisioning, not editing a restored record through admin.

Encryption protects a database-only disclosure. It does not protect credentials
from a compromised application host with key access. Superusers can replace
application credentials and disrupt or redirect future account linking, so this
role remains trusted. No reveal endpoint or plaintext export is provided.

## Verification

Focused tests cover superuser-only GET/POST/history access, CSRF, secret hiding,
blank preservation/replacement, invalid IDs/callbacks, origin and ciphertext
binding, wrong/missing keys, explicit fallback/disable, provider token exchanges,
atomic import, audited key rotation and production startup without OAuth env
credentials. Existing connection, Settings, Graph email, staging allowlist, password reset
and Workshop regressions also run. Turnstile configuration failures reject
verification; OpenAI failures queue manual moderation; Steam search failures
retain the ID/URL submission option. Live rejects Turnstile test credentials.

## Staging acceptance, 27 November 2026

Release `570ca253` deployed on OSWALD with both additive migrations. Seven
records were imported under Eurymachus and privately matched the previous
environment values. The environment copies remain for rollback. All 23 security
tests passed on the host; local suites covered 98 distinct passing tests.
Deployed form checks confirmed no saved plaintext/ciphertext and no access for
non-superuser staff. The browser fixture verified native save clears its input.

The coordinated backup and integrity check exited 0 with all 9,595 manifest
entries verified. The key in backed-up `protected.env` decrypted all seven
archived provider records offline. Four new log segments were sealed and their
hashes verified. Staging remains ready with one web and one worker process tree;
release flags and backup/retention-preview schedules are unchanged. Live remains
ready on `6582cc4`. No provider authentication calls or outbound emails were
performed during rollout; existing participant links were not changed.
