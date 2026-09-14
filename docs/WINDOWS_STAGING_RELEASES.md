# Windows staging deployment and migration

Implemented and regression-tested, **not installed on the host**. This replaces
the workflow requiring the operator to open a shell as RatRaceStage.

The host handoff named `G:\RatRace\_Staging` as both existing and missing. This
revision explicitly selects `G:\RatRace_StagingSecured` as the destination.
Source: `G:\RatRace\_Staging`. Offline backup: `G:\RatRace_StagingBackup`.
These are fixed reviewed paths, not deployment inputs. Selecting another root
requires a reviewed code change before provisioning.

## Permanent control and request protocol

All tasks run as local **RatRaceStage**, **RunLevel Limited**:

| Task | Stable launcher |
| --- | --- |
| RatRaceStagingWeb | Start-RatRaceStagingProcess.ps1 -Process Web |
| RatRaceStagingWorker | Start-RatRaceStagingProcess.ps1 -Process Worker |
| RatRaceStagingDeploy | Start-RatRaceStagingDeployment.ps1 |

Actions reference administrator-controlled launchers, never immutable releases
or request arguments. Web/worker retain restart supervision. Deploy is on demand,
without automatic retry, so a crash cannot replay a partially completed migration.

The operator writes the existing `control\inbox\request.json`, then starts the
fixed task. Schema: `{"schema":1,"sequence":1,"commit":"<40 lowercase hex>"}`.
The client obtains the next sequence from protected `control\result\status.json`.
Paths, commands, environment overrides, duplicate/unknown fields, oversized data,
noninteger sequences and abbreviated commits are rejected.

The controller holds both the release-switch byte lock and an exclusive Windows
request handle throughout deployment. The operator cannot create or replace inbox
files. Sharing denies writes and rename/delete during processing. The protected
result is atomically replaced, durably consuming the sequence before side effects.
Replay is rejected. This is a single slot, not a queue: concurrent submitters may
race before claim, but only the claimed snapshot executes; a losing client must
inspect status and resubmit. No request can be replaced during processing.

Results contain status, consumed/next sequence, commit and verified release identity.
Detailed errors stay in protected `logs\deployment.error.log` and output in
`logs\deployment.log`. An interrupted request is
marked failed by the next controller run without execution. The client can trigger
that reconciliation, then stops for inspection before another deployment.

Publishing fetches only `Eurymachus/The-Great-Spiffo-s-Rat-Race` on GitHub and
requires ancestry in `codex/rat-race-dev`. Git prompting is disabled. A private repo
needs a read-only token provisioned once in protected `config\git-token`; expired
credentials fail into the result/log, never an operator password prompt.

## Ownership and authorization

| Object | Required rights |
| --- | --- |
| Secured root/ancestors | Administrators/SYSTEM control; no untrusted rename/delete-child rights. Runtime traverses/reads root. |
| launchers | Administrators control; runtime/operator Read/Execute only. |
| config/staging.env and optional git-token | Administrators control; runtime Read; no added operator access. |
| venv | Administrator-controlled, runtime Read/Execute. Keep dependencies compatible with rollback releases. |
| releases and repository.git | Runtime Modify; no added operator access. Releases are operationally immutable, with inventory/hash validation. |
| state, logs, runtime/static | Runtime Modify; no added operator access. |
| control/inbox directory | Administrator-controlled; runtime/operator Read/Execute, no create/delete. |
| existing request.json | Administrator-owned; runtime Read; operator Read, WriteData, Synchronize only. No Delete/ACL/owner rights. |
| control/result | Runtime Modify; operator Read/Execute only. |
| media/private/reference/decompiled trees | Scoped runtime write access; no external paths or reparse points. |
| PostgreSQL cluster | Administrators and separately reviewed DB service identity only. Preserve original offline copy and original service ACLs for recovery. |
| Web/worker task objects | Administrators/SYSTEM control; runtime GR/GX. No added operator access. |
| Deploy task object | Administrators/SYSTEM control; runtime/operator GR/GX, no definition Write/Delete/owner/DACL grant. |

OSWALD\admin remains an administrator when deliberately elevated. These grants
describe its **filtered, non-elevated** token, not an attempt to constrain a host
administrator. No task runs elevated. No writable release/venv code is executed by
an elevated deployment helper. Trusted branch code executes as RatRaceStage only.

The installer conservatively checks all administrator-supplied production/GSA roots
and descendants for runtime/general-user Allow access and reparse points. It fails
closed and never changes those trees. Include every code, data and secret root.
Review network service authentication separately: the staging DB role must not
access production databases. Staging remains loopback PostgreSQL 5433 and web 8002.

## One-time UAC procedure

Run reviewed scripts from a checkout protected against concurrent changes. This
is a host maintenance procedure, not something performed by this implementation.

1. Inventory existing staging tasks, DB service, storage and exact current commit.
   Record the current release's relative directory. Reserve space for two complete
   copies plus releases. Confirm destination/backup ancestors are owned by
   Administrators/SYSTEM and cannot be replaced by untrusted users; provisioning
   fails rather than broadly changing parent-volume permissions. Take logical DB
   backups as appropriate. Stop **only** the
   verified existing staging web/worker and its PostgreSQL service. Never delete
   postmaster.pid to bypass the offline-copy check.
2. Open one elevated PowerShell and run:

   ```powershell
   $commit = '<current-full-commit>'
   $relative = 'releases\<current-release-directory>'
   .\deployment\windows\Move-RatRaceStagingHost.ps1 -Mode Preflight -CurrentCommit $commit -CurrentReleaseRelative $relative
   .\deployment\windows\Move-RatRaceStagingHost.ps1 -Mode DryRun -CurrentCommit $commit -CurrentReleaseRelative $relative
   $credential = Get-Credential "$env:COMPUTERNAME\RatRaceStage"
   .\deployment\windows\Move-RatRaceStagingHost.ps1 -Mode Provision -CurrentCommit $commit -CurrentReleaseRelative $relative -StagingCredential $credential
   ```

   Preflight/dry run are read-only. Provision creates the non-admin account if
   absent, copies the entire source twice, verifies SHA256 inventories, rechecks
   source stability, exports task XML and protects destination/backup. It retains
   source unchanged, rewrites only exact root prefixes in destination staging.env
   and applies scoped runtime ACLs. No copied executable runs as administrator.
   A manifest or clean Git checkout must prove the current commit; unidentified
   archives need a verified manifest before migration. Existing destinations,
   external storage, reparse points and live clusters fail closed.
3. Review destination PostgreSQL absolute paths (data, WAL, logs, HBA, certificates)
   and clean-shutdown state using matching PostgreSQL tools. Validate cluster/data
   and service identity/ACLs. Configure only the staging service's supervised
   destination and port 5433, retaining its original definition. The script does
   not edit/start services. Never run both clusters or cross-reference their data.
   Keep old data and service definition recoverable.
4. Review the copied venv/base interpreter and dependencies. The Limited controller
   checks sys.prefix; deployment checks validate dependencies. Rebuild only the
   destination venv if relocation fails. Review reference-tool configuration,
   persisted absolute DB paths and maintenance jobs. Provision a read-only Git
   token if needed, protected like staging.env. Preserve backup venv/config.
5. Install the three tasks. Substitute actual production/GSA roots, including
   separate secrets/data paths, for the read-only isolation check:

   ```powershell
   $isolationRoots = @('<production-root>', '<GSA-root>', '<additional-secret-root>')
   .\deployment\windows\Install-RatRaceStagingStartup.ps1 -StagingCredential $credential -OperatorAccount 'OSWALD\admin' -IsolationRoots $isolationRoots
   ```

   Confirm Log on as a batch job and no administrator membership for RatRaceStage.
   Check task DACLs. If policy blocks the operator, grant Read/Execute only on the
   **RatRaceStagingDeploy task object**, never Tasks-folder or definition Write
   permissions. Installation leaves tasks stopped. Start the reviewed destination
   database service separately, then close the elevated shell.
6. From ordinary OSWALD\admin, submit the current known full commit first using
   the command below. If no pointer exists the controller initializes one after
   preparation. A copied existing pointer is validated and switched normally.
   The current commit must remain reachable from the development branch.

## Normal prompt-free command

```powershell
& 'G:\RatRace_StagingSecured\launchers\Submit-RatRaceStagingDeployment.ps1' -Commit '<40-character-commit>'
```

This publishes, prepares, switches and waits for verification. No UAC, account
switch, password entry or task-definition change. Read status separately with:

```powershell
Get-Content 'G:\RatRace_StagingSecured\control\result\status.json'
```

## Acceptance and rollback

Before retiring source/backup, verify:

- All three task actions/principals and actual filtered-token permissions. Operator
  can submit/read/run but cannot modify definitions, launchers, result, pointer,
  environment, venv or releases. Runtime cannot access production/GSA inventory.
- No production/GSA task, service, process, ACL or listener changed. Staging DB
  credentials cannot access production storage.
- One logical web tree and one worker tree, HTTP 200 readiness for RELEASE_ID and
  a fresh heartbeat matching release and PID. Deployment performs these checks.
- DB counts/runtime state, media/private uploads and reference/decompiled data
  reconcile with backup. Check upload privacy, static delivery and protected logs.
- A second prompt-free deployment succeeds. Replay/concurrency do not execute
  twice. Failed preparation leaves pointer/processes unchanged; readiness/heartbeat
  failure restores previous release. Test supervision after reboot.

Preparation: migrate --noinput, bootstrap_roles, collectstatic --noinput,
check --deploy --fail-level WARNING, check_production_deployment. Only successful
preparation permits atomic pointer cutover. Failed cutover stops candidate trees,
restores the previous pointer and starts/verifies previous processes. Failed
rollback is explicit in the protected log and public result reports failure.

Migrations/role changes are **not reversed**. Require backward-compatible schema
changes. First initialization has no previous secured runtime: on failure it
removes the pointer and stops tasks. For failed host acceptance, stop secured tasks
and its database, restore old task/service definitions and restart the unchanged
source cluster/release. Reconcile writes made during acceptance first. The scripts
never delete source/backup or automatically restore a database.

## Regression checks

Run Python discovery for test_staging*.py and Test-RatRaceProcessHelpers.ps1,
Test-StagingEmptyScope.ps1, Test-StagingMigrationPreflight.ps1 and
Test-StagingSubmit.ps1. These cover release
validation/preparation/rollback, protocol/replay/exclusive Windows handles/status,
ACL source contracts and actual preflight/dry-run execution on temporary fixtures.
Host effective ACLs, PostgreSQL service migration and reboot remain acceptance
checks, not claims made by fixture tests.
