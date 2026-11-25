# Production Deployment Contract

## Current rollout: community first, RR 2 dormant (25 November 2026)

The agreed sequence and first-release audit are in
[FIRST_RELEASE_READINESS.md](FIRST_RELEASE_READINESS.md). Ship RR 2 code and
migrations behind a server-enforced disabled production switch. Open accounts
and Workshop requests first, then RR 1.0 claims/updates after the verified
spreadsheet handover. The final RR 2 contract and statistics decisions do not
block this release if their functionality is properly isolated.

Rehearse clean installation repeatedly on isolated hosted staging before the
first production launch. Preserve staging infrastructure and protected secrets;
reset application data only through a separately authorized, scoped procedure.
Once real production accounts or submissions exist, all later releases preserve
them. RR 2 activation requires a populated-upgrade rehearsal, not another clean
production database. This sequence supersedes the combined-launch ordering in
earlier notes. No reset, migration or deployment is authorized by this record.

## Required RR 2 launch gate: consolidate the data contract (21 November 2026)

Before enabling live Rat Race 2 functionality, simplify the mod and website together
onto one supported launch schema. Earlier RR 2 development formats are not a
permanent compatibility obligation. This gate is pending, not completed.
The wider cleanup is audit-only during active development; implementation waits
until the code has settled. Launch admits fresh challenge runs and explicitly
approved rollbacks of tracked checkpoints. Rollback approval, lineage and
integrity protections are distinct from partial collector coverage. Arbitrary
mid-save bootstrap is not a supported launch entry path.

The initial community deployment starts with a clean production database, initialized through
the launch migrations and required setup/approved seed data. Do not clone a
development or staging database or carry over test runs, submissions, claims or
rehearsal imports. Both RR 1.0 and RR 2 challenge-run datasets are empty at
deployment. Import the real RR 1.0 results only AFTER deployment and its readiness
checks, when the team selects the spreadsheet handover date. Preserve the source
spreadsheets until that import is verified. The handover does not close RR 1.0.
This initialization happens once, before real accounts or submissions exist.
The later RR 2 deployment upgrades that database without replacing it.

- Freeze and document one launch data contract shared by collection, persistence,
  export, validation and approved-run normalization. Remove redundant section
  schema fields and obsolete development decoders, conversion paths, missing-field
  fallbacks and compatibility-only tests. Keep validation of the launch contract.
- Retain explicit version identification so unsupported input is rejected clearly.
  Any distinct package/event version that remains must serve a documented encoding
  or integrity purpose, not imply support for multiple historical data contracts.
  Do not renumber an incompatible format to an identifier already used by test
  exports, which would make them indistinguishable from launch data.
- Reset RR 2 development runs, submissions, derived authority and disposable
  caches through an explicitly scoped rollout procedure. Inventory targets and
  any retained test evidence first; do not treat this as a whole-database wipe.
  Preserve Rat Race 1.0 import/claim/update functionality and maintenance support.
  Protection of RR 1.0 records, accounts, site content and unrelated production
  data applies once those records exist after deployment; it does not require
  carrying development records into the clean initial database. Database migration history needs
  its own safe deployment treatment; a schema reset does not mean deleting it.
- Keep coverage flags required for genuinely incomplete observations during
  supported operation, plus recovery and integrity safeguards. Remove only
  compatibility that exists solely for obsolete development data.
- Prove a fresh launch run can save/reload, export, import, receive approval and
  populate cumulative/daily authority. Verify obsolete development exports are
  rejected clearly, reset scope is correct and preserved data remains intact.
  Update fixtures, contract documentation and deployment/rollback instructions.

The policy is approved for final rollout. Recording it does not execute a reset
or authorize deleting current data now. See the matching decision in `DECISIONS.md`.

## Deferred final contract audit and cleanup (22 November 2026)

Timing: continue developing and testing until the owner confirms the final
mod/export contract is settled. Then run a fresh audit against that code, perform
coordinated cleanup, and complete RR 2 activation acceptance. Do not start wider cleanup
from this inventory now. Entertainment is a separately authorized workstream;
recheck its finished contract without duplicating its implementation.

### Provisional audit inventory

Paths below are relative to the repository root. Lua run modules live beneath
`Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/`, in client or shared
`TGSRR/Run/`. Findings describe the inspected development worktree, not a promise
that these branches remain present at final audit.

- Export acceptance: `ExportCodec.lua` accepts legacy format 3;
  `apps/website/registry/run_exports.py` accepts formats 3/4 and projection schemas
  1/2, with schema-dependent outpost validation. Retire obsolete acceptance paths
  together. Use a previously unused identifier for the incompatible launch
  contract, rather than making old test exports indistinguishable from launch.
- Saved state: `Identity.lua` automatically removes incompatible development
  state, supports mid-save bootstrap, and introduces missing collector counters
  with partial flags. Review `Runtime.lua`, `DevelopmentResetPrompt.lua` and
  `tests/lua/development_reset_test.lua` together. Reject unsupported saved state
  instead of silently restarting a partial run. Preserve fresh initialization
  and separately approved rollback/recovery handling.
- Collector compatibility: trace `DistanceTracker.lua`, `CookedFoodTracker.lua`,
  `FarmingTracker.lua` and the other collector initializers, then `DayTracker.lua`,
  `DailySnapshot.lua`, `Exporter.lua` and website `run_authority.py`. Remove
  obsolete missing-baseline initialization, bootstrap-only partial flags and
  historical missing-section/daily-map fallbacks. Fresh launch collectors must
  initialize their required state; missing required persisted state must not be
  silently accepted as zero or partial. Trace each flag before removing it.
- Nested schemas: assess cooked food, farming, literature, generator knowledge,
  locations, milestones, temperature, chosen region and death evidence. Remove
  redundant versions across producers, validators and normalized database fields.
  `death_evidence.py` retained schema-1 classification alongside schema 2 at audit;
  keep the final agreed classifier rather than historical classification branches.
  Review `chosen_region_schema`, death-summary `schema` and root contract
  provenance deliberately, not by indiscriminately deleting version columns.
- Tests: replace general format-3/schema-1 builders in `test_run_exports.py` and
  codec self-test fixtures with actual launch-contract fixtures. Retain
  `testdata/format3_event2_projection1.txt` only if useful for explicit rejection
  coverage. Review distance, death, bootstrap and collector compatibility tests.
  No separate general-purpose RR 2 export converter was found in inspected paths;
  most compatibility was in parallel decoders, defaults and initialization.
- Documentation: reconcile `RUN_EXPORT_AUTHORITY_CONTRACT.md`,
  `MOD_EXPORT_CHECKLIST.md` and current-focus notes with the settled contract.
  Older format descriptions and historical acceptance statements are not the
  final launch specification.

### Preserve separately from obsolete compatibility

- Approved rollback authorization, checkpoint lineage, recovery decisions,
  superseded evidence, ledger continuity and integrity checks. A rollback is not
  a reason to label collectors as having partial historical coverage.
- Checksums, ordered block boundaries, immutable submissions, atomic approval,
  exact-prefix verification, cache rebuilding and complete authority rebuilding
  when continuity cannot be established. These remain operational safeguards.
- Event, block/package, file, recovery and cache identifiers that serve distinct
  encoding or integrity purposes. Document their purpose without retaining
  multiple historical data contracts.
- Observation-specific unknowns, such as unavailable last-living thermal evidence,
  and supported recovery observations that cannot reconstruct death-time readings.
  Review these individually. Preserve intentional sparse zero/false semantics,
  Lua empty-table encoding, raw identifiers and catalogue registry provenance.
- RR 1.0 import, claim, participant-update and maintenance functionality, with
  source spreadsheets retained until the later handover import is verified.

### Migration and reset complications

- Registry migration 0029 loads `data/legacy_hall_of_fame.json` into an obsolete
  table; 0032 deletes that table and creates the current legacy-run models without
  transferring those rows. This is a historical packaged-file dependency and
  unnecessary transient work, not evidence that fresh migration leaves RR 1.0 runs.
- Migration 0047 imports current application code for historical preapproval
  backfilling, after an empty-submission guard. Removing old decoders can affect
  populated upgrade paths even where fresh installation skips that work.
- Coverage backfills and the passenger-distance add/remove sequence need not be
  deleted merely because launch starts clean. Decide migration history treatment
  separately, preserving applied dependency nodes and documenting supported
  upgrade/rollback paths. At audit, the 0075 merge depended on entertainment and
  0080; recheck the actual graph after concurrent changes. Numeric order alone
  does not establish execution order. Do not blindly erase or renumber migrations.
- Any separately authorized development reset must inventory run submissions,
  evidence revisions, run-owned authority, submission/block links, shared verified
  block caches and local ledger/recovery files, including retained test evidence.
  It must not become a whole-database wipe. A development reset is not required
  to populate the independently created clean production database.

### Implementation and acceptance order after the contract settles

1. Re-audit the settled code and agree a field-by-field contract matrix covering
   required state, sparse defaults, observation-specific unknowns and rollback
   evidence. This is the recommended first action when the cleanup gate opens.
2. Coordinate saved-state validation, exporters, website decoders, normalization
   and any necessary model changes. Remove obsolete acceptance, bootstrap paths,
   redundant nested versions and compatibility-only tests together.
3. Prove a fresh run saves/reloads, exports active and deceased states, imports,
   receives approval and populates cumulative and daily authority. Test approved
   rollback evidence, unauthorized rollback rejection, corruption handling and
   clear rejection of obsolete development saves/exports. Desktop tests alone
   do not prove in-game lifecycle behavior.
4. Verify fresh installation remains supported, then rehearse upgrading the
   earlier community release with representative accounts, Workshop requests,
   RR 1.0 claims/results, credentials and pending reviews. Prove preservation
   and document application/database rollback compatibility. Empty-install
   success alone does not satisfy the populated-upgrade gate.
5. Upgrade existing production without replacing its database or erasing real
   records. Verify readiness and protected data, then enable RR 2 only after
   its separate acceptance. Initial clean community deployment and the RR 1.0
   handover follow FIRST_RELEASE_READINESS.md and can precede this work.

These notes record audit findings and future acceptance requirements only. They
do not execute or authorize a current reset, migration application or deployment.

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
- The Django ASGI application using the selected production settings profile.
- One `run_reference_update_worker` process.
- PostgreSQL for durable application data.
- Shared runtime state: PostgreSQL for the native Windows profile, or Redis
  for the cache-backed container profile.

A host scheduler may enqueue routine reference updates. It must not replace the
continuously supervised worker.

`compose.production.yml` retains the web, reference worker, PostgreSQL, and
Redis topology for the container alternative. The current rollout uses native
Windows and the isolated hosted staging described below. Compose binds the web service to
the VM loopback interface only. The selected host HTTPS or tunnel layer must
forward to that listener. WhiteNoise serves versioned static assets from the web
container. Persistent uploaded and generated catalogue media is served by the
application's explicit `/media/<path>` route from `MEDIA_ROOT`, including for
the direct-Uvicorn/Cloudflare-Tunnel deployment. The route precedes application
catch-alls, resolves real paths beneath `MEDIA_ROOT`, rejects traversal and
symlink escapes, preserves MIME types, and sends ordinary public cache headers.

## Production settings

`config.settings_production` is the common production boundary;
`config.settings_windows_production` selects database runtime state and
`config.settings_windows_staging` adds the isolated staging controls.
They validate the complete environment before Django starts. Missing integrations
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
- Redis only when selecting the cache-backed runtime-state profile.
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
- `/health/ready/` verifies PostgreSQL, configured runtime state, persistent storage, and a recent
  heartbeat from a reference worker running the same release.

Health responses expose component status only. They must not reveal paths,
credentials, exception details, or participant data.

## Release sequence

The steps below describe the general release obligations. For the current
native Windows rollout, use the explicit staging/production paths and scripts
in FIRST_RELEASE_READINESS.md; container/image steps are not Windows commands.
Back up and pause writes before incompatible migrations. The local candidate's
staging wrapper rejects active scoped web/worker processes before preparation;
it does not stop writers for the operator. The generic preparer also requires
an explicit write pause. Do not assume these safeguards exist in older deployed
scripts. See BACKUP_RESTORE_REHEARSAL.md for the prepared recovery rehearsal.

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
- Create production from approved setup/seed data, not a development database
  snapshot. See FIRST_RELEASE_READINESS.md for the complete current blocker list.

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
As of the 25 November launch checks, this wrapper requires elevation and rejects
active staging web/worker processes before preparation. Pause incoming writes,
stop and prevent automatic restart of the scoped tasks/process trees, and verify
the backup/recovery point before calling it. The generic preparer does not stop
writers; it must never be called against a populated live database while writes
continue. This guard has been tested with process fixtures, not by deploying.
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
