# First release rollout and readiness audit

Agreed 25 November 2026. This document is the current rollout plan for the
community launch, RR 1.0 handover and later RR 2 activation.

## Agreed release boundary

Ship one application with RR 2 code and migrations included, but RR 2 disabled
in production. First release opens verified accounts and Workshop mod requests.
RR 1.0 claims and updates open after the separately verified spreadsheet
handover, as soon as that journey passes acceptance. RR 1.0 does not wait for
the final RR 2 export contract or statistics-page decisions.

Use independent server-enforced controls for registration, Workshop requests,
RR 1.0 claims/updates and RR 2. Keep account access available when new intake is
paused. RR 2 may have an approved concept/coming-soon page, but unfinished
submission, review and statistics functionality must not become available merely
because construction mode is removed. Gate direct GET/POST routes, background
and administrative entry points where applicable, and shared presentation.
Staff exercise RR 2 on local development or explicitly enabled staging, not
through an implicit production staff bypass. Missing RR 2 configuration must
leave it off. Switch changes must be deliberate and verifiable.

The initial production database is clean, created through migrations and an
explicit approved seed manifest. Do not clone local/staging databases. Both
editions' run datasets are empty before the real RR 1.0 handover. Once real
accounts or submissions exist, preserve production permanently: later RR 2
activation is an upgrade, never another clean database replacement.

The agreement initially authorized documentation and audit. The owner then
authorized beginning local release-control implementation and isolated tests.
Resetting existing data, applying live/development database migrations, changing
host configuration and deploying remain outside the current execution scope.

## Environment and rehearsal sequence

1. Develop and verify first-release fixes locally. Select an immutable candidate
   commit and approved presentation/seed package.
2. After separate execution authorization, inventory and back up hosted staging.
   Reset only its explicitly selected application database and disposable
   application files. Preserve infrastructure, protected environment, provider
   credentials, encryption keys and any deliberately retained reference assets.
   Exclude production, shared host services and Steam authentication storage.
   Record whether database-held test provider connections will be removed.
3. Install the candidate from empty staging, with RR 2 off. Prove migrations,
   roles, seed content, static assets, health and the first-release journeys.
4. Rehearse the RR 1.0 import, claim and update flow. Fix issues locally, choose
   the corrected candidate, and repeat the clean installation until reproducible.
   Staging email and provider effects must remain explicitly controlled.
5. Deploy the exact accepted candidate to clean production only when authorized.
   Verify readiness before opening registration and Workshop requests.
6. Agree the RR 1.0 cutover time, preserve final spreadsheet snapshots, preview
   and reconcile both CSV imports, import after live readiness, and verify
   results/rankings before opening claims and updates. Define handling of changes
   arriving during cutover. The website then becomes the official update route;
   preserve the spreadsheets as source evidence, not a competing update queue.
7. Later, stage the first-release version with representative accounts, provider
   connections, Workshop requests/rulings and RR 1.0 records/pending reviews.
   Rehearse upgrading that populated state to the RR 2 candidate. Prove protected
   records and workflows survive, then test RR 2 activation and rollback.
8. Deploy the accepted RR 2 upgrade to existing production, verify readiness and
   preserved data, then enable RR 2. Never promote a staging database to live.

Clean-install and populated-upgrade rehearsals are different acceptance gates.
The same isolated staging environment can serve both with recorded starting
states. Repeating empty installs alone cannot prove safe live upgrades.

## Audit scope and evidence

Static repository audit on `codex/rat-race-dev`, 25 November 2026. Reviewed
settings, middleware, routes, relevant views, management commands, migration
dependencies, deployment scripts, test cases and project records. Existing test
coverage is evidence of implementation, not a fresh passing test run. No host
inspection, browser acceptance, tests, database operations or deployment were
performed in this audit. Host configuration and recovery remain unverified here.
The implementation follow-up below is separate from that original static audit.

Primary evidence:

- `apps/website/config/{settings,settings_production,settings_windows_production,production_environment,middleware}.py`
- `apps/website/registry/{urls,views,tests,test_mods,test_legacy_rehearsal}.py`
- `apps/website/registry/management/commands/{expire_pending_registrations,reset_legacy_rehearsal,bootstrap_roles}.py`
- `apps/website/operations/deployment_checks.py`
- `deployment/windows/{Prepare-RatRaceRelease,Install-RatRaceStartup,Install-RatRaceStagingStartup}.ps1`
- [Staging rehearsal record](STAGING_REHEARSAL_2026-10-24.md),
  [retention policy](RETENTION.md) and [deployment contract](PRODUCTION_DEPLOYMENT.md).

## First-release blockers and required evidence

### Read-only operational checkpoint, 26 November 2026

Subsequent 27 November evidence: automatic staging capture and integrity checks,
cooperative application stop/log sealing and next-hourly-slot installation are
verified in HOST_MAINTENANCE.md. Isolated restore ownership/permissions and all
six stored provider-token decryptions passed in BACKUP_RESTORE_REHEARSAL.md.
Cluster login roles/passwords/memberships were not restored from the archive.
A subsequent isolated rehearsal recreated a non-superuser login with a fresh
SCRAM credential and verified Django database access, migration consistency and
home/Workshop/liveness HTTP 200 responses. A real isolated worker subsequently
drove readiness from 503 to 200 and back to 503 on cooperative stop, with queue
counts unchanged and network/tool guards. Reviewed retention execution remains
open; see BACKUP_RESTORE_REHEARSAL.md for recovery scope and limitations.
The older checkpoint below records the evidence available on 26 November.

[The host recovery audit](HOST_RECOVERY_AUDIT_2026-11-26.md) found no verified
recurring backup/retention execution or independent off-host recovery evidence.
Only 2 of 63 staging routine-log segments were sealed. The subsequently
[authorized isolated staging restore](BACKUP_RESTORE_REHEARSAL.md) passed in
71 seconds: all 9,595 manifest entries, 806 archive entries, 171 migrations and
audited snapshot counts matched. Its cluster was stopped and artifacts retained;
staging/live stayed unchanged. Off-host protection is a future improvement,
with host/storage-loss risk explicitly accepted by the owner. Credential decryption,
original grants, monitored scheduling and reviewed log/retention handling remain
launch gates. The 25 November snapshot excludes later staging changes.

### Current isolated host checkpoint, 25 November 2026

Candidate `c9b7fead` passed all 442 scoped tests on PostgreSQL18.4 with zero
skips and 14 operational tests. Both concurrency cases ran. A separate restore
of the construction-site database preserved its 129 migration entries and seeded
mod while applying 61 new migrations. This clone contained zero participant
accounts/submissions. The temporary cluster is stopped; live/staging remain on
their original releases. [POSTGRES_ACCEPTANCE_2026-11-25.md](POSTGRES_ACCEPTANCE_2026-11-25.md)
records evidence and limitations. This supersedes PostgreSQL gaps in the older
checkpoints only for the tested scope, not provider, scheduling or rollout gates.

### Current local checkpoint, 25 November 2026

[The local launch record](LOCAL_LAUNCH_CHECKS_2026-11-25.md) is the authoritative
follow-up to the original findings below. Downloads and reviewer permissions are
implemented and tested; Workshop submission throttling, first-release retention,
static bootstrap and managed-page routing/release classification are also fixed.
Fresh disposable installation repeats successfully. The packaged editorial RR 2
rules/rankings/exploits now have explicit release metadata, including safe older-
package import defaults and filtered navigation/cards. No existing DB was migrated.

Final reproducible scoped regression, including editorial gating: **439 tests,
437 passes and two PostgreSQL-only skips** in 118.210 seconds.
An earlier **98 targeted checks passed** after editorial gating. These overlapping
runs are not the entire repository suite. The original first-release static/menu/
managed-page failures are resolved; RR 2 public-statistics expectations remain
deferred. Reproduce using `scripts/test_first_release.ps1`.

Remaining gates are candidate/seed approval, real host/provider acceptance,
PostgreSQL concurrency, retention scheduling, log/backup expiry and recovery,
moderation ownership, and the final RR 1.0 handover. No wipe, deployment, process
stop or task installation has been performed. The historical findings below
describe the original baseline and should be read with this checkpoint.

Subsequent redaction follow-up (25 November 2026): reviewed RR 1.0/Workshop closure
is implemented, with signed stale-review protection, source-row redaction,
closed-run ownership guards and preserved results/rulings. The prior blanket
history blocker now remains only for unsupported relations, RR 2 and holds.
Focused tests: 37 pass; wider regression: 203/205 pass with two known baseline
failures. See [RETENTION.md](RETENTION.md) for the exact scope and required manual
source review. Host/PostgreSQL acceptance, broader retention, data-download
coverage and reviewer-role findings remain open. No existing database was migrated.

Account-retention follow-up (25 November 2026): preview/apply deletion of aged
unverified registrations, retention holds, guarded closure and transactional file
cleanup are implemented locally. Nineteen focused tests pass, including populated
migration preservation. Wider regression: 171/173 pass with the two known baseline
failures. No existing database was migrated or task scheduled. Historical-data
anonymisation and host retention/recovery acceptance remain blockers; see
[RETENTION.md](RETENTION.md). The guards preserve linked records pending review
and do not count as completed closure of history-bearing accounts.

### Database-readiness review: next checkpoint after release controls

Added by the owner on 25 November 2026. Status: source review recorded on that
date in [DATABASE_READINESS_REVIEW.md](DATABASE_READINESS_REVIEW.md).
Review completion does not mean remediation or runtime acceptance is complete.
Record findings here first, with source evidence, affected data/workflows,
launch impact and any verification still required. Do not treat a suspected
duplicate or an empty development table as proof that it is unused.

- [x] Inventory potentially unused or duplicate tables and fields. Trace readers,
  writers, migrations, administration, imports/exports and audit/provenance uses
  before deciding whether anything is redundant.
- [x] Review relationships, constraints and deletion behaviour, including cascade,
  protection and nulling effects. Trace account closure, retention and scoped
  resets through dependent records and associated files; preserve required
  results, ownership, evidence and audit history.
- [x] Review fresh-install migrations and approved seed dependencies. Record
  migration-graph or historical-code dependencies and the isolated installation
  evidence needed, without deleting or renumbering applied migration history.
- [x] Review populated-upgrade preservation for accounts, provider credentials,
  Workshop requests/rulings, RR 1.0 imports/claims/results, pending reviews and
  unrelated production records. Specify preservation and rollback checks.
- [x] Review retention against the approved schedule, including expiry versus
  deletion, anonymisation, retained source data/evidence, files, backups and
  exceptions/holds. Reuse the existing retention finding below rather than
  treating it as completed implementation.

Separate evidenced first-release blockers from optional simplification and
deferred RR 2 work. Deeper RR 2 restructuring remains deferred until the final
contract is confirmed. Reducing table count is not a launch requirement.
This checkpoint authorizes review and recording, not schema/data changes,
resets, migration execution or deployment. Findings must precede proposals.

Findings: no migration graph conflicts or model drift; no proven drop-safe table.
Before accounts open, resolve closure/anonymisation and retention acceptance and
ensure personal-data download coverage matches enabled features. Before RR 1.0
opens, verify reviewer permissions after bootstrap, ownership integrity and
closed-account handling. Fresh-install and populated-upgrade rehearsals must
account for historical migration dependencies, content replacement and recovery.
The detailed review separates confirmed source behaviour from pending database
engine/host verification. No existing database was queried or changed.

### 1. Independent release gates: implemented locally, hosted acceptance pending

The original audit found only the all-site construction gate. The local follow-up
adds `config/release_controls.py` and `ReleaseControlMiddleware`, independent
environment switches, shared presentation filtering and worker/approval guards.
All switches default to false and reject malformed environment values. There
is no staff bypass. No migration or deployment is needed to author these changes.

The boundary covers RR 2 entry points: submission,
evidence editing, deactivation, run details, account dashboard fragments,
participant profiles, rankings/managed blocks, admin review actions and any
automated leaderboard publishing. RR 1.0 components remain on shared pages.
Pending RR 2 statistics decisions remain behind this boundary. Repeat the
route/worker inventory when adding new RR 2 functionality.

Acceptance: with RR 2 off, direct requests cannot decode exports, create or
change RR 2 evidence/authority, or expose unfinished functionality. Verify
anonymous, participant and staff requests, including POST and fragment routes.
Prove registration, Workshop and RR 1.0 controls work independently, disabling
intake preserves existing records, and local/staging can explicitly enable RR 2.
Include the effective release mode in deployment verification without secrets.

#### Local configuration and testing

| Environment variable | Effect when false |
| --- | --- |
| `REGISTRATION_ENABLED` | Closes new registration/field validation; existing login, verification, resend and password recovery remain available |
| `WORKSHOP_SUBMISSIONS_ENABLED` | Closes participant requests and Workshop lookup; published rulings and staff moderation remain available |
| `RR1_SUBMISSIONS_ENABLED` | Closes new claims/updates; results, linked profiles and existing staff reviews remain available |
| `RR2_ENABLED` | Closes RR 2 routes and admin, hides shared run/statistics presentation, pauses approval routing and leaderboard publishing |

Configure switches deliberately for each environment; absence means closed,
including local development. To resume full local RR 2 development, explicitly
enable its switch in the local environment. No local `.env` was edited by this
implementation. Restart web and worker together through the canonical launcher
or host deployment procedure; switches are process settings, not live DB toggles.
Both health responses and the production deployment command report the effective
non-secret state. Keep construction mode until the enabled journeys pass.

Tests use disposable Django test databases, never the development database.
`config.settings_test` explicitly enables all features for existing functional
regressions; boundary tests override individual switches to exercise closure.
From the repository root:

```powershell
.\.venv\Scripts\python.exe apps/website/manage.py test config.test_release_controls --settings=config.settings_test --noinput
```

Fifteen boundary tests pass locally, covering populated records, anonymous/
participant/staff requests, independent opening, retained verification/account
access, managed rankings and disabled approval/publication. Fresh test-database
migrations passed. This is not yet the complete approved-seed installation
rehearsal, hosted provider acceptance, or proof of PostgreSQL recovery.

The final relevant regression run completed 394 tests: 388 passed, six failed.
All six failures were reproduced separately against an isolated archive of
unchanged commit `fe855cad`; no new regression failure remains in this set.
The archive and its disposable database were removed without changing the
development database. Async media/notification tests required execution with
Python's internal loopback sockets permitted; the restricted run stalled in
Windows socket-pair creation and was stopped, not counted as a pass.

Existing failures to resolve or reconcile during first-release cleanup:

- `RegistrationTests.test_published_managed_pages_render_and_join_navigation_in_order`:
  expected page returns 404.
- `ModsPageTests.test_admin_has_pending_queue_and_focused_review_page`:
  expects the older `Mod approval queue` heading.
- `ManagedPageTests.test_admin_sidebar_renders_collapsible_section_controls`:
  expects the older `admin-sidebar-section-toggle` markup.
- `PublicRunDetailTests.test_verified_run_is_player_facing_after_sign_in`:
  expects `Back to RatRacer`. This RR 2 assertion can remain a separate activation
  cleanup item while the feature is disabled.
- Both `ProductionSettingsImportTests` cases fail during startup because the
  staticfiles manifest lacks `registry/admin_legacy_claim_review.css`. Resolve
  the fresh production bootstrap/asset-loading dependency before first release;
  a disabled RR 2 switch does not exempt shared admin startup.

Regression command used (with `--settings=config.settings_test --noinput`):
`manage.py test config registry.tests registry.test_mods registry.test_legacy_rehearsal registry.test_submission_policy pages operations.test_leaderboard_publish operations.test_deployment_checks registry.test_run_exports.RunSubmissionTests registry.test_leaderboard registry.test_public_runs`.
These results cover the release-control change, not the entire repository suite.

### 2. Clean installation and seed manifest: rehearsal required

`Prepare-RatRaceRelease.ps1` runs migrations, role bootstrap and static
collection. It does not install the approved presentation package, historical
mod policy or a complete first-release seed manifest. The presentation importer
already offers a narrow transfer mechanism that excludes operational records.

Document and rehearse the complete Windows sequence: pinned release and
dependencies, protected environment, migrations, roles, approved content/assets,
authorised mod-policy seed data and readiness. Historical mod imports start
pending review; do not treat imported provenance as a ratified current ruling.
Check required-mod and rules copy does not instruct users to use unreleased RR 2.

The existing `reset_legacy_rehearsal` is staging-only and preview-first, but
deliberately preserves accounts, RR 2, notifications and import audits. It is
not the clean-site reset required by this plan. Prepare a separately scoped,
previewable reset/runbook with database identity and resolved-path checks,
backup, stopped writes, preserved-assets inventory and explicit confirmation.
Do not execute it as part of this audit.

Acceptance: repeat a clean install without manual database repair; record zero
RR 1.0/RR 2 runs, claims and submissions before handover and only approved setup
accounts/content. Verify all seed operations can be safely repeated.

### 3. Migration and deployment cleanup: required now

RR 2 being off does not stop its migrations or imports from executing.
Migration 0029 still loads the packaged legacy snapshot; 0032 replaces that
obsolete table without transferring its rows. Retain its packaged dependency
until deliberately addressed, and verify final emptiness rather than assuming
there are no historical data operations. Migration 0047 imports current review
code after an empty-submission guard, which needs attention when that code is
later simplified. The current 0075 merge depends on 0071 and 0082, superseding
the older audit's 0080 observation. Recheck the actual graph at each candidate.

Do not delete or renumber migration history merely to make the repository look
clean. Prove a fresh database migrates fully and document the supported later
upgrade path. Contract-dependent model cleanup remains deferred, but any defect
that prevents first-release installation or safe upgrades must be fixed now.

The staging wrapper currently prepares/migrates before the installer stops old
processes. Specify a write-pause/stop sequence or prove compatibility before
using this order with existing data. The generic Windows installer does not
itself invoke preparation. An operator must not assume it performs the whole
release procedure or that backup/rollback is automatic.

### 4. Retention: implementation gap

The approved policy requires deletion of unverified identifying data after
30 days from registration. `expire_pending_registrations` only changes PENDING
to EXPIRED based on the latest verification email; it is not that deletion job.
Implement and test the policy-driven cleanup, safe treatment of related data
and holds, moderation/evidence retention, log expiry and rolling backup expiry.
Wire scheduling and failure reporting into the actual host operation.

Verify account closure/data access against RR 1.0 claims, submitted evidence,
Workshop reasons, provider tokens and retained import-source CSVs, not just the
original account fields. Complete the recorded privacy review before opening.
This is a project-policy implementation audit, not a new legal determination.

### 5. Accounts and integrations: implemented paths, live proof outstanding

Registration, verification, recovery and account-management tests exist. Run
the relevant suite on the candidate, then exercise real hosted email delivery,
production Turnstile, request limits, failed/expired verification and password
reset, account closure and data download. Verify public host/proxy settings.

Current production validation requires Graph mail, OpenAI, Twitch, Discord,
YouTube and Steam/reference configuration. The Windows profile uses database
runtime state, not mandatory Redis, and production mail uses Graph, not SMTP.
Configuration presence and decryptable stored tokens are not proof of provider
success. Test production callbacks and credential continuity across restart.
Do not copy the staging environment or use test placeholders in production.

If an optional integration is intentionally withheld, explicitly gate its UI
and service calls and adapt validation/tests deliberately. RR 2 off does not
automatically relax existing production requirements. Reconfirm provider
availability to ordinary participants, beyond provider-console test accounts.

### 6. Workshop requests and moderation: acceptance plus abuse control gap

`mods_catalogue` checks authentication, existing IDs, Steam validation and
duplicate creation; requests become pending. Tests cover voting and final
review authority. `workshop_mod_lookup` has a search rate limit, but the
submission POST path calls Steam without its own request limit. Add a suitable
submission limit and exercise upstream failures without duplicate records.

Rehearse valid/invalid requests, duplicates, voting, final rationale and public
publication using normal role accounts. Ensure votes alone cannot publish and
private reasons remain private. Name the responsible queue reviewers. Final
mod-ruling participant notifications remain approved later work, not a new
first-release dependency.

### 7. RR 1.0: import proven historically, full journey outstanding

The October staging rehearsal imported 211 identities (14 active), checked
results and protected unrelated data. That source snapshot and those counts
are historical evidence, not the required totals for the final handover.
Claim/update tests exist, including declined-claim resubmission, ownership,
pending-update restrictions, approval, decline and death handling. The recorded
host rehearsal did not complete the full claim/update acceptance journey;
later local UI and claim fixes require deployment in the tested candidate.

Before opening RR 1.0 intake, rehearse import preview/warnings, authorised test
claims, decline/resubmit, collisions, manual/connected VOD evidence, updates,
moderation, notifications, current/best rankings and death. Test permissions,
mobile pending-action controls and duplicate/repeated requests. Preserve source
evidence and reconcile the final handover independently. Do not claim real
historical identities for testing without authority.

### 8. Host operations and recovery: fresh evidence required

Existing scripts support root-scoped process replacement, distinct staging
ports/tasks and matching web/worker readiness. The October record reports
successful checks and backup archive validation. It does not prove a complete
restore or this candidate's production readiness.

Record the actual live/staging release, database, protected paths, callbacks,
task identities and maintenance mode through a later read-only host audit.
Prove independently restarted web/worker processes, one logical worker tree,
restart after reboot, backup scheduling/expiry, isolated restoration of database
and persistent files, and application/database-compatible rollback. Include
credentials/key preservation and the effect on writes accepted after a backup;
restoring a snapshot must not silently discard later participant submissions.
Assign health/backup failure monitoring and review-queue ownership. Recheck
staging isolation and its test-email effects on the shared Graph integration.

## Cleanup allocation and deferred RR 2 gates

### Current cleanup status, 25 November 2026

| Gate | Current evidence | Still required |
| --- | --- | --- |
| Release boundaries, downloads, reviewer permissions, abuse controls | Candidate passes all 442 scoped PostgreSQL tests, including concurrency | Hosted/provider journeys on accepted staging candidate |
| Installation, migration history, roles, seed and static bootstrap | PostgreSQL scoped suite and construction-site clone upgrade pass | Approve seed copy; broader representative credential/RR 1 upgrade acceptance |
| Account closure, evidence retention and expired runtime state | Implemented and tested locally; active-run retention decision captured | Hosted scheduling, failed-job/hold review and end-to-end acceptance |
| Existing host inventory and startup supervision | Live/staging identities and installed task settings inspected with elevated access | Actual restart/reboot recovery; explain extra live repeating triggers |
| Database recovery | Fresh live dump restored and candidate upgrade passed in a separate cluster; 129 existing migrations preserved and 61 applied | Original grants/ownership; newer snapshot coverage and application recovery |
| File/configuration recovery | 43 media files, config and empty private/reference structures restored; hashes/ACLs match | Real credential decrypt test; off-host recovery deferred under accepted risk; coordinated staging snapshot restore passed 26 November |
| Backup and routine-log expiry | Candidate tooling passes 14 tests on OSWALD plus real synthetic capture/logger checks | Hosted scheduling acceptance and classification of existing fixed logs; off-host copies are a future improvement |
| Release artifacts and housekeeping | Temporary clusters stopped; restricted evidence retained | Immutable candidate selection; separately scoped artifact cleanup, no deletion authorized |
| RR 1 handover and operational ownership | Existing workflow/local evidence recorded | Reconciled final source, hosted journey, moderator ownership and privacy review |
| RR 2 contract/statistics restructuring | Deferred behind disabled release switch | Final contract decisions before RR 2 activation, not fewer tables for launch |

Recovery receipts and limitations are in [BACKUP_RESTORE_REHEARSAL.md](BACKUP_RESTORE_REHEARSAL.md).
These updates supersede original audit gaps only where verification is stated.
No existing environment was wiped, migrated or deployed. Recovery operations
created new restricted artifacts and started/stopped only temporary clusters.

The earlier cleanup audit remains in scope, split by activation stage:

| Work | Required stage |
| --- | --- |
| Database-readiness review with findings recorded before proposals | After release controls, before first-release database changes |
| Clean seed content, no test users/results, correct public navigation/copy | First release |
| Full migration graph, packaged dependencies, safe preparation and upgrade procedure | First release |
| Release gates and suppression of unfinished shared RR 2 UI | First release |
| Retention, integration validation and operational documentation corrections | First release |
| Final export/saved-state contract and obsolete decoder/fallback removal | Before RR 2 activation, after owner confirms contract settled |
| Redundant nested versions, bootstrap-only compatibility and contract fixtures | Same coordinated RR 2 cleanup |
| RR 2 statistics decisions, public pages and review/audit workflow acceptance | Before those RR 2 features open; not first-release blockers while isolated |
| Scoped RR 2 development-data reset | Separate explicit execution step, never a live whole-database reset |

Keep the detailed provisional inventory in
[the deferred contract audit](PRODUCTION_DEPLOYMENT.md#deferred-final-contract-audit-and-cleanup-22-november-2026).
Re-audit the settled implementation before changing it. Preserve integrity,
approved rollback lineage, superseded evidence and justified observation-specific
unknowns. Do not finalize uncertain statistics or remove evolving compatibility
merely to launch accounts. Any dormant RR 2 dependency that breaks enabled
features is still a first-release defect and must be isolated or fixed.

## Recommended next action and sign-off

The independent release controls and first-release fixes are tested locally;
database-readiness findings and host inventory are recorded. Separate database
and file recovery checks, operational tooling tests and isolated PostgreSQL
candidate/clone-upgrade checks pass with the limitations above. Next agree the
exact candidate staging rehearsal and finish hosted/provider/operational gates.
Preserve existing development, staging and live data. Close the remaining blockers before the
separately authorized hosted rollout rehearsal.
Keep each item's candidate SHA, result, evidence and remaining issues.

First-release sign-off requires the recorded database-readiness review and
resolution of its launch blockers, plus gates, clean installation, enabled journeys,
retention/privacy and host recovery to pass. RR 1.0 opening additionally requires
its accepted rehearsal and verified final handover. RR 2 sign-off remains a
separate contract, in-game lifecycle, statistics/review and populated-upgrade
acceptance decision. No release is declared ready by this audit.

## Local backup scheduling acceptance, 26 November 2026

The owner accepts local-only host/storage-loss risk; off-host backup is a future
improvement. Staging SYSTEM backup/check tasks are installed at 04:00 daily and
hourly :15 UK time. Actual Task Scheduler executions passed with fresh package
hash verification and staging recovery. Failure status and event 4101 were also
observed on an earlier failed capture; its original cause remains unverified.
See [host maintenance](HOST_MAINTENANCE.md) for the bundle, receipts and limits.
Observe the first unattended clock trigger. Live backup scheduling is not changed
or proven by staging acceptance, and retention deletion remains unscheduled.
