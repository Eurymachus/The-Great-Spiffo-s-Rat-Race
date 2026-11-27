# Repeatable host maintenance

Implementation baseline, 25 November 2026. The 26 November read-only audit found
the tooling on staging but no verified recurring backup or retention job.
See [the current host audit](HOST_RECOVERY_AUDIT_2026-11-26.md) for recovery
evidence, incomplete log-segment coverage and remaining launch gates.
The separately authorized coordinated staging restore subsequently passed on
26 November; see [restore evidence](BACKUP_RESTORE_REHEARSAL.md). This does not
establish recurring maintenance or off-host protection.
Earlier candidate-only statements below describe the implementation baseline.

## Backup capture

`scripts/host_artifacts.py capture` requires an existing reviewed backup parent,
protected environment file, PostgreSQL bin directory, release ID and explicit
source directories. It creates a unique child, disables ACL inheritance and
grants only SYSTEM, Administrators and the invoking identity access before writing
data. It rejects source/destination overlap and symlinks/reparse points.

Credentials are passed through a temporary protected PostgreSQL password file,
removed after `pg_dump`; no password appears in command arguments or tool output.
Capture uses explicit loopback PostgreSQL and custom format, validates the archive
catalogue, copies configuration/files and compares source-before/source-after/copy
hashes. Completion metadata is written last. Failed captures remain unmarked for
manual review. They must not accumulate indefinitely without investigation.

The manifest explicitly describes separate database-snapshot and stable-file
evidence. It does not claim coordinated cross-store consistency. An operator must
still establish the write window/snapshot procedure in BACKUP_RESTORE_REHEARSAL.md
before treating a package as a coherent rollback point. Off-host copies are a future improvement under the owner's accepted
host/storage-loss risk (26 November), not an initial launch blocker.

## Log rotation and expiry

The candidate scheduled launcher uses `scripts/run_logged_process.py` to run
the web/worker child and capture stdout/stderr into private segment directories.
Segments rotate at 10 MiB combined output or UTC day change. Only closed segments
receive a complete manifest. A child exit code propagates; logging failure fails
the wrapper and terminates its direct child. Abruptly terminated/unsealed segments
require review. Startup diagnostics retain their existing log path.

`scripts/host_artifacts.py expire --root <reviewed-root>` previews only. `--apply`
deletes complete unchanged marked backup packages at 30 days and closed routine
log packages at 90 days from segment opening, not closure. Legacy segments with
unknown start times require review. Root/package `.hold` markers prevent expiry. Unknown,
incomplete, modified or reparse-linked content is never silently deleted. Keep
roots restricted and do not write into closed packages. A changed manifest/tree
fails the run, requiring review instead of continuing destructive cleanup.

Existing `web.log`, `worker.log`, error streams, PostgreSQL logs and old history
files are NOT adopted or expired automatically. Before adoption, classify content
and investigation holds and prove the streams are no longer active. Database/log
server rotation and existing historical-log remediation remain separate gates.

## Maintenance runner and future scheduling

`deployment/windows/Run-RatRaceMaintenance.ps1` binds the operations to explicit
release, interpreter, environment, PostgreSQL, backup and routine-log paths.
Default behavior previews account/evidence/runtime retention and artifact expiry.
`-Capture` makes a new backup but still previews deletion. `-Capture -Apply`
requires capture success before applying retention and expiry. Failures return a
nonzero status; later destructive steps do not run after a failed step.

Do not install or invoke apply against the old live/staging release. Candidate
commands/migrations and log layout must be present first. After acceptance,
schedule one reviewed daily invocation under the intended service identity with
explicit paths, one-instance behavior and failure monitoring. Record its trigger,
last result, age of newest complete backup, holds and incomplete artifacts. A
backup failure needs an alert, not an assumed success from a running task.

No task has been installed by this work. Scheduling, real backup capture by this
new runner, coordinated snapshots and 90-day historical log
handling remain hosted acceptance gates.

## Verification

Eleven artifact tests cover preview/apply, segment-age boundaries, holds, unknown/changed
content, reparse rejection, config parsing, password-file lifecycle and failed
captures. Three logging tests cover output/exit preservation, rotation, active
segment exclusion and ACL failure. A real Windows temporary-directory check
verified ACL creation and a sealed log from a disposable child. The helper uses
the repository's per-process PowerShell execution policy and clears inherited
PowerShell 7 module paths when launching Windows PowerShell 5; it does not change
system policy. No existing application permissions were changed.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_host_artifacts.py
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_logged_process.py
```

PostgreSQL acceptance uses `config.settings_test_postgresql`: explicit
`RR_TEST_POSTGRES_ISOLATED=yes`, separate loopback port (5432/5433 rejected),
and dedicated `RR_TEST_POSTGRES_USER`/`RR_TEST_POSTGRES_PASSWORD`. Use a fresh
cluster with no existing `test_ratrace_launch` database. Never load host `.env`.
Run `scripts/test_first_release.ps1 -PostgreSQL` only with that isolated setup.
Its three profile safety tests pass locally. The scoped SQLite suite now runs
442 tests: 440 pass, two PostgreSQL-only tests skip. The corrected candidate
`c9b7fead` subsequently passed all 442 on isolated PostgreSQL18.4 with no skips,
plus all 14 operational tests and the real Windows logger fixture. A synthetic
PostgreSQL capture also passed. See POSTGRES_ACCEPTANCE_2026-11-25.md. This does
not install or activate any maintenance job in live or staging.

## Automatic staging backups

The staging-only scripts `Run-RatRaceStagingBackup.ps1` and
`Install-RatRaceStagingBackup.ps1` are separate from retention. They never invoke
expiry or application retention. Install a versioned bundle in the protected
`G:\RatRace_Staging\backup-operations` directory. The bundle contains the
scripts and existing ACL/process helpers. No application release switch is needed.

- SYSTEM task `RatRaceStagingBackup`: daily at 04:00 host local time,
  StartWhenAvailable and IgnoreNew. Brief staging outage during capture.
- SYSTEM task `RatRaceStagingBackupCheck`: hourly at :15, checks newest complete
  package hashes, 30-hour freshness, latest capture state, backup task result
  and enabled staging tasks. No outbound alerts or messages are sent.
- A shared named mutex prevents simultaneous backup/check runs. Operators must
  serialize staging deployments and manual DB/file changes with captures.
- Capture requires idle queues, matching web/worker release actions, 2 GiB free,
  stopped staging process trees and no other staging DB client. Only staging
  port 5433 is accepted. Media/private/config and PostgreSQL are captured.
  Reference/decompiled/leaderboard roots are outside this restore-proven scope.
- Existing web/worker triggers are disabled during capture and restored in
  finally, then readiness/release and one logical web/worker tree are checked.
  A host crash or forced termination can bypass finally: inspect status and
  restore staging tasks manually before retrying. No task timeout kills this runner.
- Status: protected `capture-status.json` and `check-status.json`. Failure exits
  nonzero and writes Windows Application event 4101, source
  `RatRaceStagingBackup`; success writes 4100. Task Scheduler also records results.
  The owner must inspect these local signals; this is not an off-host alerting
  service and cannot report a dead host or a disabled monitor independently.
- Daily cadence targets approximately 24 hours of local snapshot coverage;
  30 hours is the stale threshold. Neither is a guarantee during failures.
  The 71-second restore rehearsal is not a full application recovery-time promise.
- No old packages are deleted. Review disk growth and incomplete captures.
  Original 30-day backup/90-day log policy is not scheduled for apply here.

### Hosted acceptance, 26 November 2026

Installed operations bundle `5a3b13a6` on OSWALD under the protected
`G:\RatRace_Staging\backup-operations` directory. Both SYSTEM tasks are enabled,
IgnoreNew and StartWhenAvailable, with 04:00 daily and hourly :15 triggers in
GMT Standard Time (UK local time). Four monitor/queue tests passed and both
PowerShell scripts parsed successfully on the host.

Manually starting the installed tasks through Task Scheduler verified actual
execution, not merely registration. Capture and Check both returned 0 and logged
Application event 4100. Capture including staging recovery took about 70 seconds.
The first unattended clock-triggered run remains to be observed; do not treat
one successful execution as a history of reliable recurring captures.

- New package: `G:\RatRace_Staging\backups\backup-20261126T235530Z-44f4e1c4`.
- All 9,595 manifest entries passed integrity/freshness verification. The dump
  SHA-256 was independently compared with its manifest. Package ACLs passed.
- Web and worker were paused for capture; staging returned ready on `80b4309`
  with exactly one logical tree each. Live stayed ready on `6582cc4`, unchanged.
- Earlier bundle `419f040e` failed without producing a package. Both staging
  tasks recovered; the scheduled checker returned 1, wrote failed status and
  logged event 4101. The original cause is unverified. The installed revision
  records non-secret failure stage and line for future diagnosis.
- New package integrity is verified; the prior isolated restore rehearsal used
  the older 25 November package. Do not claim this new package was restored.
- No app deployment, retention apply, backup deletion or live changes occurred.

Owner follow-up: inspect the task/status/event results after the first 04:00
clock-triggered run. A failing check requires operator review; these local
signals do not send email or independently detect loss of OSWALD itself.

### First unattended trigger verified, 27 November 2026

Read-only OSWALD inspection confirmed the distinct 04:00:01 GMT scheduled run.
Backup completed 04:01:06 and staging recovered by 04:01:13, exit 0/event 4100.
All six hourly checks from 04:15 through 09:15 passed. Independent integrity
verification matched all 9,595 entries in
`G:\RatRace_Staging\backups\backup-20261127T040009Z-08d0afea`.
This package was not separately restored. Staging remained ready on `80b4309`
with one web/worker tree; live stayed on `6582cc4`. The pending first-trigger
follow-up above is now satisfied. Retention previews and the evidence-preview
locking blocker are recorded in RETENTION.md; no deletion was performed.

### Staging log classification, 27 November 2026

Read-only inspection of `G:\RatRace_Staging\logs\routine` found 71 segments.
No logs were changed, sealed, adopted or deleted; no services were restarted.
Live was untouched. Counts are a point-in-time inventory, not future expiry approval.

| Classification | Web | Worker | Stream bytes |
| --- | --- | --- | --- |
| Active unsealed | 1 | 1 | 0 |
| Historical unsealed | 34 | 31 | 121,067 |
| Sealed | 2 | 2 | 6,876 |

Active segments opened at 10:05:05 GMT, about one second after matching staging
logger processes started on release `8a3eb705`. Both streams in each returned
Windows sharing violations on an exclusive-read probe. Their zero sizes and
lack of growth in a four-second sample do not establish inactivity; process
correlation and open-handle evidence support their active classification.

The 65 historical unsealed directories date from 25 November 19:43 GMT and
predate current logger starts. Both streams in each permitted exclusive read.
This supports historical classification but does not prove why each failed to
seal or that its contents are complete. Forced termination during deployment
or backup is a likely contributor: it can bypass the logger's normal close and
manifest write. This is an inference, not a per-segment cause determination.

All four sealed manifests matched file hashes. No segment holds, reparse points,
unexpected files, missing streams or segment ACL anomalies were found. Zero
segments were eligible for expiry. Five fixed-name startup/error/PostgreSQL logs
remain outside routine expiry; web.log and worker.log still receive launcher
startup diagnostics and must not be treated as abandoned files.

Recommended next action: implement and verify graceful launcher shutdown so
future segments close normally. Keep historical unsealed directories unchanged
until a separately reviewed treatment exists. Do not manufacture completion
manifests or infer safe deletion from age, small size or absence of open handles.

### Cooperative staging application stop, 27 November 2026

Release `39a358b9` introduces a private, per-process stop request for the staging
web server and reference worker. This stops application processes, not Windows.
The web server drains in-flight requests; the worker finishes its current job.
The logger then drains output, seals its segments and records a successful exit.

The staging stop helper requires disabled task triggers, validates process
identity and waits up to 120 seconds. A timeout fails the operation without
forcing termination. Backup capture starts only after a successful stop; its
existing recovery path re-enables the application tasks. Old runtimes without
this protocol require a one-time bootstrap stop and cannot be retroactively
declared clean. Historical segments remain unchanged.

Local validation passed four logger tests, three process-control tests, two
existing worker tests, PowerShell process matching and script parser checks.
Hosted tests also passed, including a real loopback Uvicorn request that finished
after its stop request and produced hash-valid sealed output.

Staging application and protected backup-operations bundle `39a358b9` were
installed on OSWALD. The Task Scheduler capture started at 10:24:23 GMT:

- Web segment `routine-web-20261127T102341Z-2923e70e` sealed at 10:24:27.
- Worker segment `routine-worker-20261127T102341Z-281e270a` sealed at 10:24:31.
- Both matching exit-0 receipts were observed before replacement processes
  started at 10:25:17. Both segment manifests matched their stream hashes.
- Capture completed by 10:25:19; capture and integrity check exited 0.
  All 9,595 backup manifest entries matched. This package was not restored.
- All 69 segments already historical before cutover retained their metadata
  and hashes. The two old active segments were not retroactively sealed.
- Staging recovered ready with one web tree and one reference worker.
  Live remained ready on `6582cc4` behind the construction page.

Receipt on OSWALD:
`G:\RatRace_Staging\backups\cooperative-stop-20261127-102325\backup-verification.txt`.
No operating-system shutdown, retention apply or deletion was performed.

Daily capture remains at 04:00 UK time. The hourly checker was re-anchored to
11:15 GMT on 27 November because the installer currently starts its repetition
at 00:15 the following day. Remaining installer improvement: select the next
hourly :15 slot on installation, avoiding a monitoring gap after reinstall.
Until fixed, inspect and correct the next check time after each reinstall.
