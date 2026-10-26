# Production Deployment Contract

## OSWALD Cloudflare Tunnel maintenance (26 October 2026)

The host's shared tunnel connector was upgraded from **2026.7.3** to
**2026.10.4** following the [eMudhra certificate compromise notice](https://blog.cloudflare.com/emudhra-certificate-compromise).
The target was verified against the [official stable release](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.4).
Follow [Cloudflare's update guidance](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/update-cloudflared/)
and re-check the latest supported version for future maintenance.

### Installation and preserved configuration

- Windows MSI installation, tracked by WinGet as `Cloudflare.cloudflared`.
- Executable: `C:\Program Files (x86)\cloudflared\cloudflared.exe`.
- Service: `Cloudflared`, automatic startup, running as `LocalSystem`.
- Remotely managed tunnel; the service uses `tunnel run --token-file` with
  `C:\ProgramData\cloudflared\token`. Never print the token or unredacted
  service/process command lines. The token remains protected by its existing ACL.
- Service recovery settings, executable path, startup type, service account and
  token-file configuration were compared before/after and remained unchanged.
- Metrics/readiness bind to `127.0.0.1:20241`. `/ready` reports connector
  readiness; `/metrics` exposes the version of the running process. The local
  `/config` endpoint exposes the active remotely managed configuration: treat it
  as operational configuration and do not publish its full contents.

The active ingress configuration was inspected before upgrading. It contains:

| Public hostname | Origin |
| --- | --- |
| `tgsrr.com` | `http://127.0.0.1:8000` |
| `www.tgsrr.com` | `http://127.0.0.1:8000` |
| `dev.tgsrr.com` | `http://127.0.0.1:8002` |
| Catch-all | `http_status:404` |

No HTTPS origins were configured, so origin certificate-chain replacement was
unnecessary. TLS verification was not disabled. Reinspect actual configuration
before each future upgrade; do not assume this route inventory remains current.

### Upgrade procedure used

1. Established the public/local baseline and inspected the running service,
   package registration, token-file mechanism and active ingress configuration.
2. Downloaded the official `cloudflared-windows-amd64.exe` for 2026.10.4 and
   verified GitHub's published SHA-256:
   `411b16d40c8d872243efeb52c550053d00af0a8a97fbb32e730fb8aba429eaa8`.
3. Created an administrator/SYSTEM-only backup directory at
   `C:\ProgramData\cloudflared\security-upgrade-20261026`. It retains the
   previous executable, service registry export, protected token backup, active
   configuration, package-manager log and final verification receipt. Do not
   expose these backup contents or restore the vulnerable binary as routine
   rollback.
4. Started the verified new binary as a separate manual-start LocalSystem
   service named `CloudflaredSecurityUpgrade`, display name
   `Cloudflared Security Upgrade Replica`, using the same protected token file
   and metrics bound to `127.0.0.1:20242`. This follows Cloudflare's requirement
   for distinct Windows service names/display names. No new tunnel or DNS
   record was created.
5. Required replica readiness and identical active configuration before stopping
   the original service. The replica had two ready edge connections before
   cutover. New requests can use the replica; stopping a connector can still
   interrupt existing long-lived HTTP/WebSocket/TCP sessions.
6. Upgraded through the existing package-management mechanism:

   ```powershell
   winget upgrade --id Cloudflare.cloudflared --exact --source winget --version 2026.10.4 --silent --disable-interactivity --accept-package-agreements
   ```

   Specify `--source winget` to avoid unrelated Microsoft Store source prompts.
   Select a freshly verified version for future updates. Do not substitute
   `cloudflared update` for a package-managed installation.
7. Verified the installed executable and original service settings, restarted
   `Cloudflared`, and verified its actual process executable path plus the
   running version in metrics. Compared active configuration and token hash/ACL
   against baseline. Checked public staging readiness before stopping and
   removing the temporary service.
8. Confirmed the original connector has four ready edge connections and the
   temporary service is removed. Retained the secured backup for audit.

### Verification and coverage

- Running service executable and `build_info` both report 2026.10.4.
- Final elevated OSWALD inventory found one running cloudflared process and one
  automatic `Cloudflared` service. Docker inventory succeeded and found no
  running cloudflared containers. The separate temporary service is absent.
- Original service startup/recovery configuration, token hash/ACL and active
  ingress configuration match their pre-upgrade values.
- Public staging returns HTTP 200 and readiness passes all components on
  application release `0ec0ba7`. No application was redeployed or restarted.
- `tgsrr.com` returns HTTP 503, matching its pre-upgrade public baseline.
  `www.tgsrr.com` also returns HTTP 503 after the upgrade and uses the same
  origin. Raw local HTTP checks still redirect with HTTP 301, as before;
  origin requests with forwarded HTTPS headers return staging 200/live 503.
- This records OSWALD's connector. Other account tunnels/connectors on other
  machines have not been inventoried or verified through the Cloudflare
  dashboard and must not be considered covered by this host upgrade.

This document defines the production shape of the Rat Race website. Codex may
provision, release, diagnose, and maintain the host, but the deployed platform
must continue operating independently after a deployment task ends.

## Runtime boundary

Production runs these independently supervised services:

- A reverse proxy providing HTTPS and forwarding to the ASGI application.
- The Django ASGI application using `config.settings_production`.
- One `run_reference_update_worker` process.
- PostgreSQL for durable application data.
- Redis for shared caching, rate limits, and worker health.

A host scheduler may enqueue routine reference updates. It must not replace the
continuously supervised worker.

`compose.production.yml` provides the web, reference worker, PostgreSQL, and
Redis topology decided for the Ubuntu production VM. It binds the web service to
the VM loopback interface only. The selected host HTTPS or tunnel layer must
forward to that listener. WhiteNoise serves versioned static assets from the web
container. Persistent uploaded and generated catalogue media is served by the
application's explicit `/media/<path>` route from `MEDIA_ROOT`, including for
the direct-Uvicorn/Cloudflare-Tunnel deployment. The route precedes application
catch-alls, resolves real paths beneath `MEDIA_ROOT`, rejects traversal and
symlink escapes, preserves MIME types, and sends ordinary public cache headers.

## Production settings

`config.settings_production` is the only supported production settings module.
It validates the complete environment before Django starts. Missing integrations
are startup failures because production is expected to provide every documented
website capability.

The application is served through ASGI. `POSTGRES_CONN_MAX_AGE` must therefore
be `0`; startup validation and the deployment check both reject positive values.
Each request closes its database connection instead of accumulating persistent
connections in the ASGI process. Do not compensate by raising PostgreSQL's
`max_connections` setting.

`.env.example` is the non-secret inventory. Real values must be supplied by the
host's secret and configuration mechanism and must never be committed.

## Required host software

- A supported Python release and all packages in `apps/website/requirements.txt`.
- PostgreSQL client tools suitable for backup and restore.
- Redis.
- SteamCMD, including a persistent installation directory and Steam session.
- Java and the pinned Vineflower JAR used by reference decompilation.
- A reverse proxy, service supervisor, and scheduler appropriate to the host.

The container image installs Java and SteamCMD. Place the approved pinned
Vineflower JAR at `deployment/runtime/vineflower.jar` on the host before building
or starting the services. That runtime directory is intentionally excluded from
Git.

## Persistent state

Back up and preserve:

- PostgreSQL.
- Uploaded media.
- The private avatar quarantine directory.
- Project Zomboid reference and decompiled-build directories.
- Deployment configuration and secrets through the host's secure mechanism.
- Operational logs required for diagnosis and audit.

SteamCMD session material is sensitive host state. Preserve it securely when
appropriate, but do not place it in ordinary application backups or the
repository. Collected static files are release output and can be rebuilt.

SteamCMD, Project Zomboid, Java, and Vineflower filesystem locations come only
from the protected `STEAMCMD_EXECUTABLE`, `PZ_REFERENCE_ROOT`,
`JAVA_EXECUTABLE`, and `VINEFLOWER_JAR` settings. Decompiled build/job outputs
live beneath `PZ_REFERENCE_ROOT/tgsrr_decompiled`. The reference-source
administration displays these resolved paths but cannot edit or override them.
`PZ_DECOMPILED_ROOT` is no longer read. Before the first decompilation after
upgrading, move retained build/job directories beneath the derived directory or
allow the worker to create a new validated output there. Existing database path
values require no migration and are ignored operationally.

`MEDIA_URL` is always the root-relative `/media/`. `MEDIA_ROOT` remains
persistent deployment state and must not point into an immutable release or
collected-static directory. WhiteNoise does not serve this media tree.

## Health contract

- `/health/live/` confirms that the application process can answer and reports
  its release identifier.
- `/health/ready/` verifies PostgreSQL, Redis, persistent storage, and a recent
  heartbeat from a reference worker running the same release.

Health responses expose component status only. They must not reveal paths,
credentials, exception details, or participant data.

## Release sequence

1. Fetch the approved commit into a new release directory.
2. Supply `.env.production` through the host's protected deployment storage.
3. Put the pinned Vineflower JAR in `deployment/runtime/` and build the images.
4. Back up durable state.
5. Prepare the release with a one-shot website process. Run migrations, then
   `python manage.py bootstrap_roles`, then build static files. Role bootstrap
   is idempotent and mandatory after every migration so fresh and existing
   databases reconcile the code-owned role and permission definitions. On a
   Windows deployment, use `Prepare-RatRaceRelease.ps1` to enforce this order.
6. Run `python manage.py check_production_deployment` in a one-shot website
   container. This also proves that stored provider credentials remain
   decryptable with the supplied Fernet key.
7. Restart the web and worker services onto the same release identifier.
8. Confirm liveness, readiness, and the production acceptance journey.
9. Move traffic only after those checks pass.
10. Retain the previous release and its compatible configuration for rollback.

Database migrations require an explicit rollback assessment. If a schema change
is not backward compatible, restoring the previous application also requires the
documented database restore path.

## Human-controlled actions

Codex must stop for owner authority when work requires new production
credentials, Steam Guard interaction, DNS or TLS ownership, live traffic
switching, destructive data changes, or approval of public policy wording.

## Repository work remaining before launch

- Record host-specific service, scheduler, backup, restore, and rollback commands
  after auditing the host.
- Add a production-shaped acceptance runner.
- Complete retention automation and the final privacy review.
- Exercise the legacy import and claim journey with representative data.
- Remove development-only records before the final production data snapshot.

## Windows staging deployment

The persistent acceptance environment mirrors the production layout beneath a
separate installation root, `G:\RatRace_Staging`. Production defaults remain
`G:\RatRace`; staging must pass explicit identity and port values:

- deployment name `RatRaceStaging`;
- web port `8002`;
- PostgreSQL port `5433`;
- tasks `RatRaceStagingWeb` and `RatRaceStagingWorker`;
- service `RatRaceStagingPostgres`;
- hostname `dev.tgsrr.com`.

`Install-RatRaceStartup.ps1` validates that every supplied release, environment,
Python, PostgreSQL, and log path stays beneath its `InstallationRoot`. Process
cleanup is installation-root scoped so staging cannot terminate production. A
cutover stops both deployment tasks, terminates only Rat Race launcher process
trees beneath that installation root, and fails if an old tree remains. It then
requires both requested task trees to run the selected release and waits for the
readiness endpoint, including the matching worker heartbeat, before succeeding.
Use `Install-RatRaceStagingStartup.ps1 -ReleaseRoot <release>` for the standard
staging identity, paths and ports; this keeps the elevated invocation short and
repeatable. Routine deployment requires one UAC confirmation and continues to
replace the two staging tasks for the selected immutable release.
The standard staging installer invokes `Prepare-RatRaceRelease.ps1` with the
release, protected staging environment file, and staging Python executable. The
preparation command applies migrations, reconciles all standard roles, and
collects static files before the web and worker processes are replaced.
Create the protected staging environment with
`New-RatRaceStagingEnvironment.ps1` only after its isolated PostgreSQL fragment
exists. Cloudflare routing and any optional Access policy are configured last,
after the local staging readiness endpoint passes.

Update individual non-secret deployment values such as `RELEASE_ID` or an
explicit staging feature switch with `Set-RatRaceEnvironmentValue.ps1`. This
preserves the protected environment and its existing secrets instead of
regenerating the complete file.

### Current deployed staging state (2026-08-14)

- Release `1676dba` is deployed beneath `G:\RatRace_Staging\releases`.
- The isolated PostgreSQL cluster is registered as `RatRaceStagingPostgres` and
  listens only on `127.0.0.1:5433`.
- `RatRaceStagingWeb` serves `127.0.0.1:8002`; `RatRaceStagingWorker` runs the
  reference-update worker. Release `1676dba` is currently running, but updating
  the scheduled-task actions to this release still requires an actual elevated
  Windows PowerShell session. No reboot was performed during installation.
- The protected environment is `G:\RatRace_Staging\config\staging.env`. It has
  staging-only Django and encryption secrets, filesystem roots, callback URLs,
  database credentials and Turnstile test keys. Staging defaults
  `STAGING_EMAIL_ALLOW_ALL` to `true`, permitting invited testers to
  self-register with arbitrary email addresses.
  Graph mail still uses the dedicated Rat Race sender, and the ordinary
  Turnstile and registration, resend and password-reset rate limits remain
  enforced. Set it to `false` to restore `STAGING_EMAIL_ALLOWLIST` enforcement.
- Only the working Microsoft Graph mail configuration is reused from the
  protected production environment. OpenAI, Twitch, Discord, YouTube, and Steam
  provider credentials remain explicitly unconfigured until each integration
  is set up and tested deliberately.
- The database began empty, all migrations were applied, and the deterministic
  repository presentation package imported 8 pages and 8 images. No production
  participant or run data was copied.
- The existing Cloudflare tunnel publishes `dev.tgsrr.com` to
  `http://127.0.0.1:8002`; Cloudflare created the corresponding proxied CNAME.
- Staging is intentionally public for team acceptance rather than protected by
  Cloudflare Access. Normal account verification still applies. Every staging
  response sends `X-Robots-Tag: noindex, nofollow, noarchive`, `robots.txt`
  disallows all crawling, browser titles begin `[DEV]`, and every ordinary and
  administration page carries a persistent development/test warning.
- Local staging readiness and the public staging homepage returned HTTP 200;
  production readiness remained HTTP 200. GSA services were not modified.
- Open staging email registration is enabled, allowing testers to complete the
  ordinary self-registration, verification and password-recovery journeys
  without administrators maintaining a recipient list.
