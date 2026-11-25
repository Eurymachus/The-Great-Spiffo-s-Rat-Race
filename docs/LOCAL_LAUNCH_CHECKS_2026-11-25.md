# Local first-release checks, 25 November 2026

Scope: accounts, Workshop requests and RR 1.0 intake, with RR 2 present but off.
Evidence comes from the working tree based on `fe855cad`, not an immutable deployed
release. Existing local data and protected environments were not changed. No wipe,
deployment, host process stop or scheduled-task installation occurred.

## Local results

| Area | Result |
| --- | --- |
| Participant download | Format 2 covers own Workshop requests/votes and RR 1.0 claims, submitted evidence and linked results. Intake switches do not remove data access. Other people's evidence, shared CSVs, credentials and private staff notes stay excluded; responses use no-store. |
| Reviewer permissions | Role bootstrap is repeatable. Run Submission Approver and Challenge Administrator can review RR 1.0 claims/updates. Workshop approvers cannot. Raw ownership edits and import confirmation remain unavailable to reviewers. Import confirmation explicitly checks authority. |
| RR 1.0 integrity | Request/review paths lock account, run, then evidence; review locks avoid nullable joined rows. Ordinary admin ownership edits are read-only. PostgreSQL concurrency proof is still required. |
| Workshop abuse control | Submission POSTs are limited before Steam calls: five per account and twenty per IP per ten minutes. Failed upstream attempts count; anonymous requests do not call Steam. Lookup retains its separate limit. |
| Account and evidence retention | Preview-first commands, holds, transactional closure/file cleanup, active-run protection and two-calendar-year first-release evidence expiry tested. Results, decisions and current published Workshop policy survive. |
| Runtime maintenance | Expired database rate-limit buckets can be previewed/pruned without touching active limits or worker heartbeats. Windows retention runner executes all three maintenance commands and preserves failure status. |
| Fresh installation | Fresh disposable SQLite migration, repeated role bootstrap and packaged presentation import pass with no participant/run/claim/submission data. Hashed static collection succeeds from an empty temporary directory. Production settings import no longer resolves manifest assets during admin module import. |
| Editorial release boundary | Managed pages have explicit release metadata. RR 2 rules, rankings and exploits are withheld with RR 2 off, including direct URLs, staff requests, navigation and homepage cards. Older presentation packages cannot silently reopen the known RR 2 pages. Workshop copy identifies its upcoming-edition scope. |
| Deployment preparation | Staging wrapper rejects running deployment processes and releases outside the installation root before preparation. Pure process fixtures and PowerShell syntax checks pass; no installer was executed. |

The final reproducible scoped regression ran **439 tests in 118.210 seconds**:
437 passed and the two PostgreSQL rate-limit/claim concurrency tests were skipped
on SQLite. This run includes the final editorial classification and older-package
fallback changes. An earlier **98 targeted tests passed**; these runs overlap and
must not be added together. The whole repository suite is not
claimed to pass. The existing RR 2 public-statistics presentation test remains
deferred with that feature's activation work.

Reproduce the scoped checks from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test_first_release.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deployment\windows\tests\Test-RatRaceProcessHelpers.ps1
```

Async tests need internal loopback sockets available. Tests use disposable Django
databases and temporary media/static directories, with provider calls mocked.
They do not establish real provider delivery/callbacks or host recovery. Offline
migration metadata reports no conflicts or model drift. No PostgreSQL tools were
found on PATH; this is not proof of the host's installed database state.

## Candidate and seed preparation

1. Select an immutable candidate after reviewing the working-tree changes.
2. Use its complete migrations, including registry `0083`/`0084` and pages `0044`.
   Do not delete or renumber historical migrations. Establish the host's starting
   versions before choosing a populated-upgrade path.
3. Use the reviewed presentation manifest. The current package has eight pages
   and eight managed images. Its updated presentation checksum is
   `fbf431c3477df1e090669d23333a993a48a6188540e36f61cbf3731e8a1eb06f`.
   Release metadata was added; assets and RR 2 content remain in the package.
4. Ratify first-release copy and Workshop seed policy. Successful package validation
   does not approve its wording or turn historical pending mod imports into rulings.
5. Keep all intake closed during setup. Open accounts/Workshop only after their
   acceptance gates, then RR 1.0 after its independently reconciled handover.

## Still required before opening live intake

Host follow-up: database-only recovery passed on 25 November in a separate
temporary PostgreSQL cluster, with 129 migration records, audited counts and
seed-row fingerprint matching. See [BACKUP_RESTORE_REHEARSAL.md](BACKUP_RESTORE_REHEARSAL.md).
This narrows the recovery gap below, but does not establish media/configuration,
decryption, ownership/grants or populated candidate-upgrade acceptance.

- Read-only inventory received: [HOST_INVENTORY_2026-11-25.md](HOST_INVENTORY_2026-11-25.md).
  Resolve its remaining backup/supervision/scheduling uncertainties. Live's one
  Workshop row is the migration-seeded challenge mod, not a user submission;
  neither host release has independent intake switches.
- Candidate-specific PostgreSQL migration/preservation and concurrency checks in
  an isolated disposable environment. Test simultaneous claims, review/closure,
  import handover and retry behaviour, not only SQLite outcomes.
- Real email verification/recovery, Turnstile, Steam failures and provider callbacks
  using ordinary accounts, plus credential continuity after restart.
- Install and observe retention scheduling and failed-job/hold review. Verify host
  security/email-log expiry at 90 days and rolling backup expiry at 30 days.
- Restore matching database, media, code and protected configuration in isolation;
  demonstrate encryption-key preservation, deleted-identity handling and recovery
  without silently losing writes accepted after a backup.
- Verify staging isolation, exactly one logical worker tree, health/heartbeat,
  restart/reboot recovery, monitoring and named moderation ownership.
- Reconcile the real RR 1.0 source snapshot and complete claim/update/death,
  moderation, notification and ranking acceptance before opening RR 1.0 intake.

## Later hosted rehearsal sequence, not executed

First inventory and back up the selected environment. Record explicit database
identity, resolved application paths and protected assets. Any clean-staging reset
needs separate authorization and a reviewed exact target inventory; this document
does not authorize one. Existing local and live data must not be wiped.

Pause writes, stop and prevent restart of the selected web/worker task trees,
then verify they are stopped before preparation/migrations. The staging wrapper
now enforces the active-process check; the generic preparer still requires this
operator sequence. Import approved setup content only on the intended fresh
installation, never as an automatic populated-upgrade step. Start the candidate
and verify health, switches, jobs and enabled journeys before reopening writes.
Later RR 2 activation upgrades the populated live database and never replaces it.
