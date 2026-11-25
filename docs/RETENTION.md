# Participant Data Retention Schedule

Approved by the project owner on 2026-07-15 for Sentinel Tech Ltd's operation
of The Great Spiffo's Rat Race challenge platform.

| Information | Retention | End-of-period action |
| --- | --- | --- |
| Unverified registrations | 30 days from registration | Delete the account and identifying data. |
| Active participant accounts | While the account and challenge platform remain active | Retain unless closure is approved or the platform ends. Do not delete merely for inactivity. |
| Closed participant identity | Until an approved closure is processed | Remove login credentials, email, nickname, and other identifying account information. |
| Anonymised challenge reports and results | Indefinitely | Remove the participant link, retain each run independently, and display its owner as Former Rat Racer only when genuinely anonymised. |
| Moderation notes and evidence | Two years after the relevant run, decision, or closure | Delete or anonymise, unless needed for an active dispute or legal obligation. |
| Routine security and email-delivery logs | 90 days | Delete, unless needed for an active investigation. |
| Backups | Rolling 30 days | Allow deleted personal information to expire and do not restore it to the live service. |
| Non-personal closure receipts | Indefinitely | Retain only the random reference and request/process timestamps. |

Clarified by the owner on 25 November 2026: scheduled evidence expiry retains
evidence while a run is active, then uses the latest relevant end, decision or
closure date for its two-year period. Reviewed account-closure redaction remains
a separate explicitly confirmed action under the earlier-deletion provision below.

Sentinel Tech Ltd will review this schedule at least annually and whenever the
platform's purpose or data processing changes. Earlier deletion or anonymisation
may be appropriate when information is no longer needed.

## Implementation status

This document is the approved policy. Local code now implements unverified-account
expiry, reviewed first-release closure, retryable file deletion, two-year first-release
evidence expiry and expired runtime-bucket pruning. Host scheduling and recovery
are not yet accepted. Log/backup expiry and RR 2 evidence retirement remain open.
The subsections below retain the original audit and implementation sequence.

The 25 November 2026 first-release audit confirmed that
`expire_pending_registrations` only marks old pending accounts EXPIRED using
the latest verification-email timestamp. It does not delete identifying data
30 days after registration and does not satisfy that retention requirement.
See [FIRST_RELEASE_READINESS.md](FIRST_RELEASE_READINESS.md) for the required
implementation, scheduling and closure/related-data acceptance before launch.

The [database-readiness review](DATABASE_READINESS_REVIEW.md) found that closure
retains historical RR 1.0 names and evidence while deleting the ownership claim.
Nullable account links alone do not establish anonymisation. Original import
CSV, Workshop notes, evidence payloads and ownerless saved-view filters also
require lifecycle coverage. The original review did not change records; the
subsequent local remediation and remaining acceptance requirements are recorded below.

## Local implementation follow-up, 25 November 2026

This subsection records the initial safeguards. The subsequent reviewed
first-release redaction path below supersedes the blanket history blocker for
supported RR 1.0 and Workshop relationships.

`apply_account_retention` previews by default. `--apply` deletes pending/expired
registrations at least 30 days old with no verification timestamp. Resends do not
restart the period. Verified, disabled, staff and superuser accounts are excluded.
Retention holds and evidence-bearing relationships stop deletion. An applied run
with blocked accounts or failed file cleanup returns nonzero for operator review.
Output contains counts, not identities. `expire_pending_registrations` remains
a separate verification-status command, not the deletion mechanism.

Account admin now has a retention-hold checkbox. Record the purpose and next review
date in admin notes; review holds regularly, since they do not expire automatically.
Closure confirmation shows blockers and the confirmed action rechecks eligibility
transactionally. Deletion signals also protect queryset deletion.

Clean closure removes identity, provider credentials, notifications, personal
preferences and private saved views. Accounts with linked history, Workshop
evidence or shared records remain intact pending reviewed redaction. This prevents
ownership loss and false anonymisation; it does not complete historical closure.
Do not remove relationships manually to bypass these safeguards.

Avatar/quarantine file deletion is queued in `RetentionFileDeletion` in the same
database transaction. Cleanup happens after commit and failures remain for retry.
Referenced files and paths outside the expected roots are refused. The queue
contains sensitive file names until cleanup succeeds. Monitor outstanding jobs;
login deletion alone does not prove that all files have gone.

Migration `0083_account_retention` adds a hold field and queue without rewriting
existing records. Only disposable test databases were migrated. Nineteen focused
tests pass, including populated-upgrade preservation, closure, deadlines, holds,
rollback and retry. The wider run passed 171 of 173, with two known baseline failures.

### Rehearsal and scheduling

1. Migrate an isolated environment and run `python manage.py apply_account_retention`
   under its settings. Review held/blocked accounts and pending file jobs.
2. Use `python manage.py apply_account_retention --apply` on disposable fixtures;
   prove expired accounts disappear and unrelated records survive.
3. The Windows runner `deployment/windows/Run-RatRaceRetention.ps1` accepts explicit
   `-ReleaseRoot`, `-EnvironmentFile` and `-PythonExecutable`. It uses the protected
   environment loader and previews unless `-Apply` is supplied.
4. Rehearse a regularly scheduled invocation, with cadence sufficient for the
   registration deadline, nonzero-exit alerting and failed-job/hold review. No
   scheduled task was installed or applied command run against existing data.

Still open: historical-data anonymisation, two-year moderation/evidence retention,
expired rate-limit bucket cleanup, host log rotation, backup expiry and safe
restoration. Shared imports and RR 2 evidence are not deleted by this change.
The first-release retention gate remains open.

## Reviewed first-release history redaction

The existing closure action now previews the affected RR 1.0 runs, submissions,
claims, Workshop records/votes, source rows and admin log entries. Administrators
must inspect those records and confirm that no dispute or retention obligation
prevents redaction. They must also check identifying information in other shared
records and external source copies. This deliberately chooses earlier removal of
the listed personal evidence following an approved closure, while preserving
numeric results and rulings. It is not automatic deletion of all moderation data.

The preview carries a signed digest of the relevant record contents. It expires
after one hour and is rechecked inside the closure transaction with row locks.
Changed evidence, source snapshots or holds require a fresh review. A bulk action
may close one account and require a fresh preview for another when both share a
source snapshot. No receipt or partial redaction survives a failed transaction.

For owned RR 1.0 runs, closure retains each run separately with its numeric results,
current/best submission pointers and lifecycle. It replaces the historical name
with `Former Rat Racer`, clears character names and relevant evidence/review text,
and replaces the name-derived source/normalised keys with independent random keys.
The `identity_removed` marker and database constraint prevent owner reassignment.
Claim routes, rankings, approval actions and ordinary run administration prevent
reclaiming or updating these retained records. Pending updates and competing claims
on the run are declined. The departing account's claims are removed.

Matching historical-name rows are removed from all stored import CSV snapshots,
including unapplied/rejected snapshots and ignored columns such as source channels.
Corresponding preview records are removed. Unrelated source rows remain. Affected
filenames become generic, checksums describe the retained files, and `redacted_at`
records the change. These are explicitly no longer the original validated sources.
Redacted imports cannot be applied, and any retained identity-removed run blocks
replacement imports. Invalid source formats stop closure for review.

Workshop titles, public source metadata, rulings, recommendation flags and vote
decisions remain. The departing account's submission reasons, affected public
rationale/moderation notes, and its vote name/reason are removed. Reviewer-only
relationships remove the departing review note/link while preserving the other
participant's submission or claim evidence. Holds belonging to participants whose
shared evidence would be touched also prevent closure.

Affected admin log entries retain actor, event type and timestamps, with identifying
representations/messages replaced. Account-object links are cleared. Unrelated
log entries remain. The non-personal closure receipt remains unchanged in scope.

Direct/bulk account deletion and the scheduled unverified-account command cannot
bypass this reviewed history path. RR 2 history, shared saved views, unsupported
relationships and active holds remain blockers. External originals, old backups
and free-text mentions outside the structured relationships are not automatically
redacted; the review and host recovery procedure must cover them. Do not describe
retained results as genuinely anonymous before completing those checks.

Validation: 37 focused tests pass, including stale/expired/forged confirmation,
source-row and unrelated-record preservation, rollback, holds, closed-run guards,
admin confirmation and populated migrations. Wider account/Workshop/rankings/
release regression: 203 of 205 pass; only the two recorded baseline failures remain.
Migration `0084_legacy_identity_removal` is additive and was applied only in
disposable tests. PostgreSQL concurrency and host recovery/scheduling remain
acceptance requirements, not claims established by SQLite tests. No existing
database, protected environment, scheduled task or deployment was changed.

## Scheduled first-release evidence expiry and runtime cleanup

`apply_evidence_retention` previews by default; `--apply` performs the planned
redaction. It covers RR 1.0 evidence/review notes and Workshop request/vote/private
moderation text. RR 2 is deliberately excluded pending its final contract.

Active RR 1.0 runs are excluded regardless of the age of their evidence. For an
inactive/deceased run, the conservative anchor is the latest run update, submission,
claim decision or affected source-upload/import date. Using the last run update
also covers lifecycle changes without guessing an earlier end date. Missing decision
dates, pending reviews, recent/unresolved source reviews and retention holds defer
expiry. Two years means calendar years, with leap-day handling, not a fixed 730 days.

After expiry, scores, current/best pointers, ownership and decision records remain;
submission evidence/review text and claim evidence/review text are cleared. Affected
source rows are retired through the same selective CSV/preview redaction used for
closure. Other source rows remain. Retiring another row in the same source does not
restart an unrelated run's clock. Public identity is not removed merely because
its evidence expires; active account identity follows the account policy.

Workshop expiry uses the latest record/decision or vote activity. Pending decisions
and missing decision dates are retained. Request reasons, private historical notes
and vote reasons expire; titles, published policy rationale, rulings and vote
decisions remain. Published policy is current site content, not an expired evidence
attachment; reviewed account closure can separately redact identifying public text.

Holds protect related submitters, reviewers, claimants, voters and affected source
uploaders. Changed snapshots cause retry rather than partial retirement. Preview
and apply report counts without personal identifiers. The command does not remove
whole run/claim/decision records. A separate `prune_runtime_state` command previews
and removes only expired database rate-limit buckets, preserving active limits and
worker heartbeats.

`Run-RatRaceRetention.ps1` now runs account retention, evidence retention and runtime
pruning. It previews unless `-Apply` is supplied, attempts independent maintenance
even if one command fails, and returns failure if any command fails. Nothing has
been scheduled or applied against existing local/host data. Monitor held/blocked
work, retries and file deletion queues when scheduling is later authorized.

Local checks cover active/pending protection, latest-date anchoring, holds, source
row preservation, retained scores/policy, preview behaviour and repeat application.
See [the local launch record](LOCAL_LAUNCH_CHECKS_2026-11-25.md). Host log expiry,
backup expiry/restoration, scheduling and PostgreSQL concurrency remain required.
