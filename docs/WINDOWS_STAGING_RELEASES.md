# Permanent Windows staging launchers

This supersedes the release-bound staging installer. The current root is
`G:\RatRace\_Staging`, not the older `G:\RatRace_Staging` path. These scripts
have deliberately fixed scope: tasks `RatRaceStagingWeb` and
`RatRaceStagingWorker`, loopback web port 8002 and PostgreSQL port 5433.
They never register, restart or configure a PostgreSQL service, production task,
GSA task, reverse proxy or firewall. PostgreSQL must already be supervised and
running. The production installer remains unchanged.

## Layout and trust

| Location | Ownership and permissions |
| --- | --- |
| Staging root | Administrators/SYSTEM control; no non-administrator write, delete-child or ACL ownership rights. Installer checks this rather than changing existing PostgreSQL ACLs. |
| `launchers` | Administrator-owned, explicit Administrators/SYSTEM Full Control and staging-account Read/Execute. Installer copies only the reviewed fixed launcher/control files here. Routine deployments cannot replace them. |
| `releases\<12-character-commit>` | Trusted staging publisher creates Git archives and manifests. Runtime reads only; publisher may create releases but must never edit published releases. With one staging account acting as publisher/runtime, immutability is an operational contract reinforced by full hash validation, not a protection from that account itself. No unrelated users may write. |
| `config\staging.env` | Protected secret file, Administrators Full Control, staging account Read only. Never copied from a release, overwritten by switching, printed or checked into Git. |
| `venv` | Administrator provisioned and owned; staging account Read/Execute. Dependency upgrades are a separate reviewed operation and must remain compatible with rollback releases. |
| `logs` | Administrators own the directory; staging account Modify. Only fixed `web.log` and `worker.log` launcher redirections. Arrange log rotation separately. |
| `state` | Administrators own the directory; staging account Modify. Contains `active-release.json` and a byte-locked `switch.lock`. No executable code belongs here. |
| `runtime\static\<full-commit>` | Staging account Modify, outside immutable code. Static output is prepared per release, so a failed preparation does not replace the active release's collected static files. The app uses this release-specific STATIC_ROOT. Any external static-file mapping must follow this same path/pointer contract. |
| Media, private uploads, reference and decompiled output | Staging-only writable paths with explicit least-privilege ACLs. Preserve existing PostgreSQL service/data ACLs. Django deployment checks also validate the configured toolchain and storage. |
| Worker runtime state | Staging database, not the production database or cache. Heartbeat contains release, PID and timestamp. |

The two tasks run **Limited**, under a dedicated enabled **local non-administrator
account**, with password logon for unattended startup. Never use SYSTEM, an
administrator, or a domain account with indirect administrator membership.
Protect the root's ancestors against untrusted rename/delete-child rights too;
the installer must be run only after the administrator confirms those host ACLs.
The deployment command runs as that same account, so it can clean up its own
child processes without elevation. An operator can run a normal shell as this
account using the host's approved account-access workflow. Merely granting task
restart rights to a different user is insufficient for complete process cleanup.

There is no privileged deployment helper. A user who can change the pointer or
published application code can run code only with the staging account's existing
permissions, not as administrator. Treat that account and the publisher as
trusted deployment principals. Keep production/GSA secrets and files inaccessible
to it. Secure the source checkout used for the one-time elevated installer against
untrusted writes while reviewing/running it. Manifest hashes detect corruption;
they are not signatures against a malicious trusted publisher.

## One-time administrator installation or repair

First provision the dedicated account, protected root, environment, venv and
explicit writable storage/release subdirectories using the table above. Grant
Log on as a batch job through the host's local security policy if required;
domain policy must not deny it. The installer intentionally fails on a broadly
writable staging root. Preserve explicit database subtree permissions before
any administrator changes parent inheritance.

From an elevated shell in the reviewed repository checkout:

```powershell
$credential = Get-Credential "$env:COMPUTERNAME\RatRaceStage"
.\deployment\windows\Install-RatRaceStagingStartup.ps1 -StagingCredential $credential
```

This stops old staging trees, installs/repairs the two permanent tasks, and
leaves them stopped. It does not prepare or execute release code as administrator.
It does not touch PostgreSQL. On repair, the existing pointer remains intact.
The fixed web action is:

```text
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "G:\RatRace\_Staging\launchers\Start-RatRaceStagingProcess.ps1" -Process Web
```

Worker uses the identical stable path with `-Process Worker`. The executable is
the absolute System32 Windows PowerShell path. Neither action contains an
immutable release path. Task Scheduler supervises each task with IgnoreNew,
startup trigger, no execution time limit and up to 999 one-minute failure restarts.

The installer gives only these two task objects a protected DACL:
Administrators/SYSTEM Generic All; staging-account Generic Read + Generic Execute
(`GRGX`). It grants no task-definition write, delete, ownership or DACL rights and
does not weaken the Task Scheduler folder. If local policy blocks read/run/stop,
the switch fails with an explicit ACL message. The narrow one-time repair is to
have an administrator restore precisely that task-object ACE for the staging
account SID on these two tasks, using Task Scheduler's COM
`IRegisteredTask.SetSecurityDescriptor`. Do not grant Full Control or rights on
the entire Tasks folder. Rerunning this installer repairs these exact ACLs.
Verify run/stop with that account before scheduling unattended deployment.

## Publish and initialize

In a **non-elevated staging-account shell**, export an exact reviewed commit:

```powershell
& 'G:\RatRace\_Staging\venv\Scripts\python.exe' -E -B `
  'G:\RatRace\_Staging\launchers\staging_release.py' publish `
  'G:\path\to\reviewed-checkout' '<full-commit>'
```

The publisher uses `git archive` of the verified commit, never dirty working
files. It prints the short release ID. It writes `staging-release.json` with
schema 1, full 40-character commit and SHA-256 hashes for every exported file.
It rejects an existing destination, symlinks and a source-supplied manifest.
Release validation rejects missing/extra files, changed hashes, malformed
manifests, incorrect directory/commit identity, traversal and reparse points.

For the first conversion only, with no pointer present:

```powershell
& 'G:\RatRace\_Staging\launchers\Switch-RatRaceStagingRelease.ps1' `
  -Release '<short-commit>' -Initialize
```

Initialize prepares, writes the first pointer, starts and verifies the tasks.
On failure it stops the new trees and removes that first pointer. There is no
previous permanent release to roll back to during initial conversion; retain
the old host deployment evidence/backups before the one-time maintenance window.
Do not use Initialize once a pointer exists.

## Routine deployment and rollback

After publishing the candidate, from the same non-elevated staging account:

```powershell
& 'G:\RatRace\_Staging\launchers\Switch-RatRaceStagingRelease.ps1' -Release '<short-commit>'
```

No UAC prompt and no task registration or definition change occurs. The command:

1. Acquires a Windows byte-range lock and validates candidate and previous release.
2. Checks permanent task actions, limited identity and fixed staging environment.
3. Runs `migrate --noinput`, `bootstrap_roles`, `collectstatic --noinput`,
   `check --deploy --fail-level WARNING`, and `check_production_deployment` with
   staging settings and the candidate's full commit as `RELEASE_ID`.
4. Revalidates immutable files, snapshots process descendants, stops only the
   two staging tasks, kills surviving descendants with PID/creation-time checks,
   and proves cleanup. It atomically replaces the pointer using a flushed
   same-directory temporary file and `os.replace`.
5. Starts the existing tasks and allows up to 180 seconds for exactly one logical
   web runtime and worker runtime. Windows venv redirectors count as part of the
   same logical process tree. Port 8002 must have exactly one owning PID, matching
   the web runtime; legacy staging runtimes must be absent.
6. Requires HTTP 200 from `/health/ready/`, matching full release ID and worker
   check, plus a database heartbeat with the new worker PID, selected release ID
   and timestamp after cutover. Proxy environment and HTTP redirects cannot send
   this check to a different service.

Preparation failure leaves the pointer and running processes unchanged. Cutover
or verification failure stops the candidate, atomically restores the previous
pointer, starts its tasks and verifies fresh readiness/heartbeat again. A failed
rollback is reported explicitly as `ROLLBACK FAILED`, requiring operator action;
success is never reported for an unverified rollback. Retry an intentional rollback
with the same switch command and the previous short commit.

**Database and shared-state changes are not reversed.** Use expand/contract
migrations and compatible dependencies so the previous release remains runnable.
Take and verify staging database backups before migrations. Destructive migrations
or external side effects require a planned maintenance/restore procedure, not
this automatic process rollback. `bootstrap_roles` also changes database state.
Do not mutate a published release or the venv while a switch is in progress.

## Verification and host acceptance

Repository regression suite (no scheduled task mutation):

```powershell
python -B -m unittest discover -s deployment/windows/tests -p test_staging_release.py -v
powershell -NoProfile -ExecutionPolicy Bypass -File deployment/windows/tests/Test-RatRaceProcessHelpers.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File deployment/windows/tests/Test-StagingEmptyScope.ps1
```

Tests cover scope/path rejection, malformed manifests and hash inventory, atomic
replacement, preparation isolation, successful cutover, readiness and heartbeat
rollback, rollback failure reporting, fresh/PID-matched worker checks, command
ordering, concurrency locking, archive publishing and fixed limited task actions.
PowerShell syntax is also parsed without executing installer/task-control code.

The real host still needs one-time administrator acceptance of task DACLs, batch
logon, storage ACLs, restart supervision, reboot behaviour and the readiness
cutover. These cannot be certified using mocks on the development machine.
No host task installation or modification was performed while implementing this.
