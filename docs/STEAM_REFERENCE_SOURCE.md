# Project Zomboid reference source

The website catalogue is derived from a full, authenticated Project Zomboid
installation. A dedicated-server installation is not treated as a complete
catalogue source.

## Security boundary

Only a Django superuser may start the connection flow, and the superuser must
re-enter their Rat Race administrator password. The Steam password is sent to
SteamCMD over standard input and discarded immediately. The same short-lived
SteamCMD process remains available for at most five minutes if Steam Guard is
required. The password and Steam Guard code are never written to the
database, session, command line, environment, application log, or notification.
Repeated failed administrator confirmations are rate limited.

SteamCMD retains its own reusable login session in `config/config.vdf`. Protect
that file using the operating-system account and filesystem permissions used by
the updater. Do not commit it, copy it into deployment environment files, expose
it through Django, or include it in ordinary application backups.

The web process never invokes SteamCMD during an update request. It creates a
queued database job only. A separately supervised worker invokes only the
configured SteamCMD executable and fixed commands; it does not accept arbitrary
command-line options or shell input.
On Windows, the application uses `pywinpty` to provide SteamCMD with a real
pseudo-console because SteamCMD ignores redirected standard input. This keeps
the password out of process arguments while still supporting Steam Guard.

## Configuration

Host filesystem paths are deployment configuration, not administrator-authored
data. The singleton **System operations → Project Zomboid reference source**
record accepts only the Steam account login name and the temporary Steam
authentication flow. It displays the resolved deployment paths read-only for
diagnosis. Legacy path columns remain in the database for compatibility with
existing records, but no update, authentication, decompilation, or catalogue
operation reads them.

The protected deployment environment supplies:

```text
STEAMCMD_EXECUTABLE=/opt/steamcmd/steamcmd.sh
STEAMCMD_USERNAME=steam-account-login-name
PZ_REFERENCE_ROOT=/srv/tgsrr/project-zomboid-reference
STEAMCMD_UPDATE_TIMEOUT_SECONDS=1800
STEAMCMD_AUTH_TIMEOUT_SECONDS=15
JAVA_EXECUTABLE=/srv/tgsrr/project-zomboid-reference/jre64/bin/java
VINEFLOWER_JAR=/opt/vineflower/vineflower-1.12.0.jar
PZ_DECOMPILATION_TIMEOUT_SECONDS=3600
```

Validated decompiled outputs live beneath
`PZ_REFERENCE_ROOT/tgsrr_decompiled` in immutable build/job directories.

The Windows development equivalents may point at `steamcmd.exe` and the local
Project Zomboid reference directory. Press **Connect Steam** on the reference
source, enter the Steam credentials and the administrator confirmation, then
enter a Steam Guard code if requested.

## Update queue

Press **Check for updates** on the reference source to create a manual job. The
request returns immediately and the job records who requested it, when it was
queued, when work began and how it finished. A queued or running job is reused
instead of starting a duplicate.

Run the worker continuously under the restricted SteamCMD service account:

```text
python manage.py run_reference_update_worker
```

For a service health check or deterministic test, process at most one job:

```text
python manage.py run_reference_update_worker --once
```

A production scheduler creates a scheduled job through the same queue:

```text
python manage.py update_pz_reference
```

The enqueue command does not run SteamCMD. The worker uses a fixed Steam App ID
(`108600`) and fixed SteamCMD arguments. It compares the installed manifest
build ID before and after the update, records an immutable job result, and
updates the singleton reference-source status.

The live deployment must supervise the worker independently from the ASGI web
service and restart it after failure. Its scheduler should invoke the enqueue
command at the desired interval. This same split is used in local development,
so testing exercises the production execution boundary.

For local development, use the canonical launcher from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_website_dev.ps1" -Port 8001 -Background
```

The launcher loads `.env`, starts the web server and the independently running
reference worker, records both the Windows launcher and socket-owner PIDs, and
refuses ambiguous duplicate listeners or workers. It uses `netstat` for the
listener check so a denied CIM query cannot silently turn process discovery into
an empty result.

An installed-build change creates a super-admin notification. Authentication
failure or another update failure also creates a notification. A superuser can
repair the cached Steam session using **Reconnect Steam**.

## Decompiled Java reference

Provision a pinned [Vineflower](https://vineflower.org/usage/) JAR on the host
and record its path in the protected `VINEFLOWER_JAR` setting. Java may use
Project Zomboid's bundled runtime through `JAVA_EXECUTABLE`. The JAR is a
deployment dependency and is not committed to this repository; verify the downloaded
release checksum as part of provisioning.

The locally verified Vineflower 1.12.0 full JAR has SHA-256:

```text
1DFCFE974395734FA467CE620661C7623D05BA83670DE0529B1FBD63FF548B9D
```

After a successful Steam update, open **System operations → Project Zomboid
reference source** and press **Decompile installed build**. The web request only
queues an audited job. The same separately supervised worker runs Vineflower.

Each run writes into a new build/job directory under
`PZ_REFERENCE_ROOT/tgsrr_decompiled`,
checks for `zombie/characters/skills/PerkFactory.java`, writes a
`.tgsrr-build-id` marker and only then marks the decompiled build current. A
failed or partial run therefore cannot replace the previous
known-good decompiled tree. The source record clearly reports whether its
decompiled build matches the installed Steam build.

The catalogue importer accepts the promoted tree explicitly:

```text
python manage.py import_pz_catalogue \
  --game-root /srv/tgsrr/project-zomboid-reference \
  --decompiled-root /srv/tgsrr/project-zomboid-reference/tgsrr_decompiled/build-BUILD-job-JOB \
  --game-version 42.x
```

Old build/job directories are retained for rollback and should be pruned only
by a deliberate host maintenance policy.

## Catalogue promotion

An updated game installation is evidence that a catalogue review is needed; it
does not silently rewrite the live catalogue. The intended deployment pipeline
is:

1. Update the staging Project Zomboid reference installation.
2. Queue and validate decompilation of the changed build.
3. run the catalogue importer against staging;
4. inspect the generated difference;
5. approve and promote the catalogue change;
6. retain the previous known-good catalogue for rollback.

The current operations queue implements steps 1 and 2. Catalogue reviews and
reviewed promotion remain separate follow-on work.

## Recovery

If Steam invalidates the cached session, use **Reconnect Steam**. Do not paste
credentials into chat, source control, environment files, or support tickets.
Back up catalogue data and managed imported media; do not back up Steam
credentials with ordinary application backups.
## Catalogue review and approval

Catalogue promotion is deliberately separate from Steam update and Java
decompilation:

1. A super-administrator opens **System operations → Project Zomboid reference
   source** and selects **Generate catalogue review**.
2. The request resolves the protected deployment settings and captures the
   installed build ID, decompiled build ID, installation root, selected
   build/job directory, and chosen game-version label. The background worker
   parses that exact source into an immutable review snapshot.
3. The review lists additions, changed presentation/detail fields, and records
   that would be deactivated. Generating the review never changes catalogue
   records.
4. **Approve and apply catalogue** promotes the stored snapshot in one database
   transaction. **Reject review** records the decision without changing the
   catalogue.

Approval is blocked as stale if the installed build, decompiled build, or
resolved deployment paths have changed since the review. Missing records are
deactivated,
not deleted, so existing run evidence and relationships remain valid. Notes,
aliases, captions, and other website-owned editorial data are not replaced by
the automated source snapshot.
