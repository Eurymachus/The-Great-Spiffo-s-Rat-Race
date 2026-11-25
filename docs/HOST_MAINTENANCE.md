# Repeatable host maintenance

Candidate implementation, 25 November 2026. Not deployed or scheduled on either
host environment. Existing fixed log files and rehearsal artifacts are untouched.

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
before treating a package as a coherent rollback point. Off-host copies remain
an outstanding operational requirement.

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
new runner, coordinated snapshots, off-host recovery and 90-day historical log
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
