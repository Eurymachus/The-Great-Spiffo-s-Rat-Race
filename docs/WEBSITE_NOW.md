# Website: Current Focus

## Admin-first acceptance audit (28 November 2026)

Access controls, all seven offline provider checks, game preparation, matching
worker readiness, unattended backup/retention-preview checks and a fresh
coordinated backup passed on staging 14f7bb46. All 37 focused local checks passed.
Live was neither accessed nor changed.

**Next: approve and install the launch presentation package on staging.**
The rebuilt baseline has 5/8 package pages, 3/9 navigation entries, 3/4 themes
and 0/8 managed images; branding and challenge-mode values also differ.
Review first-release copy/required-mod policy and RR2 gates before import.
Real provider acceptance and live-specific provisioning remain distinct gates.
See [the audit and remaining checklist](ADMIN_FIRST_ACCEPTANCE_2026-11-28.md).
This supersedes older generic next-step and operational-gap notes below.

## Current launch checkpoint (28 November 2026)

- [x] Artwork launch check complete, explicitly accepted by the owner.
  Staging release 14f7bb46 has 4,810 verified PZWiki images, 326 exact game
  sprites and the approved Custom Occupation image. Existing artwork was
  preserved and 33 focused tests passed.
- Six object images are optional polish, not launch blockers: Hematite,
  HematiteLarge, Malachite, MalachiteLarge, Mov_WhiteHalfCounter and
  Mov_IndustrialDishwasher. Text labels are sufficient for the first release.
- Generic Base.Moveable is a template without a specific image. The 198 hidden
  character overlays do not require inventory icons. Retain accurate source
  explanations in the artwork report; completion does not mean every record
  has an image.
- Next: finish the administration-side acceptance checklist on rebuilt staging:
  verify provider configuration/setup routes, role restrictions, approved
  content/seed state, worker/release controls and a coordinated recovery backup.
  Steam installation, matching decompilation, catalogue approval and artwork
  preparation have already been exercised. Audit current evidence first and
  test only outstanding gaps.
- Public construction remains on, intake stays off, and live is untouched.
  This closes only the artwork gate, not the entire launch. Live deployment
  and public opening remain separate owner-authorized steps.

## Historical checkpoints

- Pending approval feedback and artwork console deployed to staging `208aa1ec`
  on 28 November. Operations migration 0004 applied; 27 Django and two Node
  tests passed on OSWALD. Static collection required a committed UTF-8 correction.
  Console rendering and access permissions verified. Artwork job 1 cancelled
  under explicit owner authorization after the old worker exceeded its
  cooperative-stop timeout and required bounded termination. Logger output
  was sealed and hash-verified. Catalogue review 1 remains Approved.
  Limited HTTP probes identified image-route HTTP 403 with
  `Cf-Mitigated: challenge`; ordinary wiki article returned 200. No full retry
  and no challenge bypass attempted. Artwork access remains unresolved.
  Staging ready with one web/worker; public construction and disabled intake
  preserved, admin login 200. Live remains ready on `6582cc4`, untouched.
  This supersedes the pending-deployment notes below.

- Artwork live output implemented/pushed as `a9b1c54f`, not deployed yet.
  Additive operations migration 0004 stores bounded timestamped output; worker
  streams entry counts, successes, skips and retry errors to the shared admin
  console. Permission-checked polling and terminal failure messages included.
  All 27 catalogue tests passed locally, including in-flight output persistence
  and failed-job polling. At 01:40 GMT artwork job 1 remained Running with zero
  PZWiki assets after nearly ten minutes. Earlier sample returned HTTP 403.
  This is no visible progress, not proof of a stopped worker. Existing worker
  cannot expose retrospective output; backup preflight still blocks deployment.
  Current staging and live unchanged. Approval feedback remains pending too.

- Catalogue approval feedback `c7a4011e`: native POST now displays Applying
  catalogue (or Rejecting review), disables both actions and blocks repeat
  submissions while preserving the chosen endpoint. Back navigation restores
  the controls. Two JavaScript interaction tests and all 17 catalogue review
  tests pass locally. Owner approval of review 1 was confirmed in the browser,
  attributed to Eurymachus at 01:30 on 28 November; the subsequent repeat attempt
  was correctly rejected because the review was already approved.
  Deployment pending: OSWALD passed the same 2 Node and 17 Django tests, but
  backup preflight will not pause the active artwork sync. At 01:37 GMT it had
  run seven minutes with zero PZWiki assets imported, 3,209 candidate keys, and
  a sampled image request returned HTTP 403. Sequential retries make completion
  soon unlikely. Job left running; staging remains 89068cf5, live untouched.

- Catalogue generation live progress implemented in `89068cf5`: timestamped
  category stages and record counts, comparison and terminal summary, bounded
  output, permission-checked polling, elapsed time and follow-output using the
  existing reference-job panel. Ready reviews refresh to show comparison and
  approval controls. Additive operations migration 0003 adds the output field.
  All 26 catalogue tests pass locally, covering progress persistence, failure,
  completion and endpoint access. Older reviews cannot recover prior output.
  Owner confirmed Steam authentication, installation and validated decompilation
  of build 26486631 through staging admin. Deployed to staging 89068cf5;
  26 tests passed on OSWALD, migration applied, panel rendered and endpoint
  permissions verified. Review 1 is ready: 5,342 additions, no changes or
  deactivations; it completed before logging was deployed and remains unapproved.
  Staging ready with one web/worker, construction and disabled intake retained;
  both shutdown logs sealed/hash-verified. Live 6582cc4 untouched.

- Steam Guard code submission fix `b9668a04`: the authentication wait reused
  the previous challenge prompt, immediately returning guard-required after
  sending the code and terminating SteamCMD before its response. Consume the
  old output before waiting for the new result. Regression covers delayed
  success and actual rejection; all 14 focused authentication tests pass locally.
  Deployed to staging on OSWALD; the same 14 tests passed there. Ready with
  one web/worker, public construction retained, admin login HTTP 200, intake
  disabled and both shutdown logs sealed/hash-verified. Live `6582cc4` unchanged.
  Owner must retry through the admin form to confirm real Steam authentication.
  No real Steam login was attempted by the agent and no credentials were logged.

- Public-host admin construction-mode fix deployed to staging `52d5a282`.
  Owner screenshot exposed that the earlier localhost-only acceptance missed
  public `/admin/` being blocked. Middleware now passes admin routes to normal
  Django authentication/permissions/CSRF. Seven tests passed locally and on
  OSWALD. External dev.tgsrr.com verification: `/admin/` redirects to login,
  password form and stylesheet return 200, `/` and `/account/` remain construction
  503. Ready with one web/worker; both shutdown logs sealed/hash-verified.
  Database, credentials and disabled intake flags preserved. Live `6582cc4`
  untouched. Owner can retry admin sign-in using existing credentials.

- Clean staging rebuild completed on OSWALD, 27 November, release `4378ceec`.
  Public host returns construction mode; preserved Eurymachus owner account
  passed local admin access. Registration, Workshop intake, RR1 intake, RR2
  and publishing are off. Ready with one web and one worker process tree.
  New public schema has one owner account and all seven preserved provider
  configurations; RR1/RR2 runs/submissions, RR1 claims, notifications and
  streaming connections are empty. Game reference preparation and RR1 import
  remain pending. Host credentials, keys and Steam session preserved.
  Staging login cannot CREATE DATABASE but owns database/schema: old public
  schema retained as `rr_staging_prebaseline_570ca25`, fresh public created
  within the same staging database at `127.0.0.1:5433/ratrace`. Old generated
  files and protected configuration retained for rollback. Application and
  retention previews use only new public; whole-database backups include both
  schemas. Fresh post-rebuild backup/integrity passed and all seven archived
  provider records decrypted offline. Backup/retention schedules unchanged.
  Live remains ready on `6582cc4`, untouched. Next: owner signs into staging
  admin, reviews preserved providers, then prepares Steam/game reference data.

- Fresh-install baseline implemented on 27 November under explicit owner
  approval to retire pre-launch migration history without a local/staging upgrade
  path. Replaces 174 project migrations with eight schema migrations and one
  final seed migration (226 setup records, no credentials/accounts/run data).
  SQLite fresh/repeat installation passed, all 95 tables match prior empty-install
  columns/constraints, and model drift is zero. Initial 88 regression tests and
  four new baseline tests passed. Full suite: 721 tests, 714 passed, three skipped,
  four failures reproduced with the original migration chain (see baseline doc).
  PostgreSQL 18.4 isolated cluster on OSWALD port 55441 passed fresh/repeat migrate,
  repeated role bootstrap, sequence insertion and zero model drift: 95 tables,
  27 applied migrations including nine project migrations. All 197 focused tests
  passed. Request-client smoke verified public construction HTTP 503 and synthetic
  superuser admin access. All seven archived provider records were recovered
  as ciphertext into the fresh schema and decrypted offline; probes rolled back.
  No provider calls. Isolated cluster stopped, listener and PID file absent.
  Local consistent database backup and environment byte comparison passed.
  OSWALD backup verified 9,595 entries, all seven archived provider records
  decrypt with the archived key, and Steam session copy is hash-verified.
  Candidate committed/pushed as `4378ceec`. Existing local/staging databases
  remain intact; no fresh baseline cutover yet. Live untouched. See
  MIGRATION_BASELINE.md. Next: use this verified baseline for the clean staging
  admin-first rebuild, retaining recovery material and host credentials.

- Browser RR1 acceptance completed: EuryDev claimed Eurymachus, owner approved,
  update declined with visible reason, resubmitted and approved, and public
  leaderboard displayed EuryDev/Columbus and approved stats. Claim decline was
  accepted based on automated evidence, not repeated in browser. Owner chose to
  leave the staging run Active and RR1 intake enabled for further testing;
  the earlier restoration reminder below is superseded.

- Temporary browser acceptance change, 27 November: imported Eurymachus RR1
  run `270` changed from Inactive to Active on staging at the owner's request.
  Only lifecycle changed; original state retained in a protected OSWALD receipt.
  Restore to Inactive after testing. Run is unclaimed and accessible through
  Hall of Fame; no current submission means it does not yet appear on the
  Active leaderboard. Live untouched.

- RR1 claims and update intake enabled on staging on 27 November for the
  owner's EuryDev browser acceptance using an imported active run. Protected
  configuration backed up; staging `570ca253` ready with one web/worker and
  both shutdown logs sealed/hash-verified. RR2 remains off; other flags and
  schedules unchanged. No claims/reviews/submissions made by this operation.
  Live `6582cc4` untouched. Next: user submits claim, tests decline/resubmit and
  approval, then submits an update for review.

- RR1 re-import and automated staging journey passed on OSWALD, 27 November,
  deployed release `570ca253`. Retained October CSV hashes matched; import
  audit `309eea75-fa32-4990-b611-faec1561f9f2` created 211 historical runs
  (14 active, 197 inactive) and 211 approved submissions. Results and both
  ranking orders verified; all 71 other protected tables matched pre-import
  fingerprints. Fresh backup verified all 9,595 entries.
  Synthetic deployed Django request-client checks passed for claim decline
  reason, resubmission, approval and competing-claim rejection; update ownership,
  active-run/VOD requirements, single pending update, decline preserving results,
  and death approval updating current/best results and deceased status.
  An initial fixture transaction rolled back because the harness queried
  notification `participant` instead of `recipient`; correcting the harness
  passed without re-importing or changing application code.
  Retained labelled run 425, claims 7/8 and submissions 429/430/431; final totals
  are 212 runs, 2 claims, 214 submissions. Three synthetic accounts use prefix
  `RR1Rehearsal20261127`; the reviewer was deactivated. No historical identity
  was claimed. In-memory mail and blocked outbound sockets prevented external
  delivery; intake override was test-process-only. Local focused suite passed
  27 tests; OSWALD isolated suite passed 23 tests. Staging ready with one
  web/worker; RR1 intake and RR2 remain off. Live `6582cc4` untouched.
  These are request-client checks, not browser acceptance. Next: interactive
  claim/review/update browser smoke check using the owner's chosen imported
  active run, with staging intake enabled as recorded above.

- Scoped staging RR1 reset completed on OSWALD, 27 November, at the owner's
  request for a fresh import/claim/review/update rehearsal. Deleted 211 runs,
  2 claims and 211 submissions; all three RR1 tables are empty. Deletion
  collector confirmed no cascade outside these tables. Four local reset tests
  passed. Fresh pre-reset backup verified all 9,595 manifest entries; staging
  writers paused for reset and both shutdown log segments sealed/hash-verified.
  Fingerprints matched across all 72 protected tables, including accounts,
  provider credentials, Workshop, RR2, catalogue, import audits and notifications.
  Staging ready on `570ca253` with one web/worker process tree; schedules and
  release flags preserved. RR1 intake remains off; no CSV imported yet.
  Live `6582cc4` untouched. Subsequent import and request-client acceptance are
  recorded above; reset verification alone does not validate user journeys.

- First live deployment phase agreed on 27 November: admin available to
  authorized administrators, public construction page retained, intake and
  publishing disabled. Configure live providers in admin, then connect Steam,
  prepare/decompile the game reference and import/review game data. Public
  opening is a separate step after administration-side acceptance. See
  PRODUCTION_DEPLOYMENT.md and FIRST_RELEASE_READINESS.md. Documentation only;
  no live changes authorized or performed by this update.

- Encrypted provider configuration implemented for Discord, Twitch, YouTube,
  Microsoft Graph email, Turnstile, OpenAI moderation and Steam Web API.
  Active-superuser-only admin, write-only secret replacement, field-name-only
  audit, separate host key ring, origin binding and explicit env/disabled modes.
  Key rotation/import are atomic and audited. See PROVIDER_CONFIGURATION.md.
  Across the focused suites, 98 distinct tests passed. Native admin save clears
  the submitted secret in the browser fixture. Staging deployed as `570ca253`
  on 27 November; 23 security tests passed again on OSWALD. All seven imported
  records decrypt and match prior environment credentials; seven audit entries
  recorded the import. Fresh coordinated backup and integrity check exited 0;
  all 9,595 manifest entries verified. The backed-up key decrypted all seven
  archived records offline. Deployed admin forms hide plaintext/ciphertext and
  deny non-superuser staff. Staging has one web/worker; four new log segments
  sealed and verified. Release flags, backup/retention-preview schedules and
  live `6582cc4` unchanged. Provider-side authentication was not repeated.

- Discord validation and Settings connection errors deployed to staging
  `9b32a36d` on 27 November. Invalid application IDs and unsafe or mismatched
  callbacks are blocked before redirecting; Twitch and Discord connection
  failures return to Settings with escaped, accessible, one-time alerts.
  111 tests passed before deployment; seven isolated regressions passed on
  OSWALD. Deployed Discord configuration validates successfully. EuryDev's
  Twitch and Discord connections were confirmed active before this rollout.
  Staging ready with one web/worker; previous logs sealed on cooperative stop.
  Backup and retention-preview schedules preserved; live `6582cc4` untouched.
  No provider calls or migrations during rollout. Isolated long-error Settings
  rendering passed at 320/390/430px in headless Edge on 27 November: no page
  or alert overflow, themed alert, 44px dashboard button. Real template rendered
  from a mocked Discord failure with an in-memory test database; reload removes
  the alert while notification history remains. Screenshots visually inspected.
  Actual iPhone acceptance remains. Provider-side failures cannot all be
  prevented locally.
  Encrypted superuser-managed provider configuration is the next workstream,
  recorded above.

- Mobile settings header fixed and deployed to staging `a58896da`: separate
  Account settings title and wrapping email, compact avatar/joined row, and
  full-width return button instead of the inherited two-column action grid.
  Two existing settings tests passed. Synthetic long-email Chromium checks
  stayed within bounds at 320/390/700/844/1160px; actual iPhone acceptance remains.
  Staging ready with one web/worker; backup/preview schedules and live unchanged.
  Resume provider-connection acceptance after the mobile visual check.

- Staging retention preview scheduling installed on 27 November from protected
  operations bundle `0b7f84cd`: daily 05:00 UK preview, hourly :45 health check,
  SYSTEM/StartWhenAvailable/IgnoreNew. Both Task Scheduler-triggered runs passed
  with exit 0/event 4200. PostgreSQL previews enforce read-only transactions;
  no apply path. Results: accounts/evidence/artifact candidates zero, evidence
  retained 201, expired runtime buckets 34. No deletion/restart/live changes.
  First clock-triggered execution remains to be confirmed. Monitoring is local,
  with a 30-hour freshness limit; no outbound alerts. See RETENTION.md.

- Disposable retention rehearsal passed on OSWALD, 27 November: 30 PostgreSQL
  tests and 11 artifact tests. Read-only previews, real apply and repeat apply
  verified eligible synthetic cleanup and protected-record preservation.
  Corrupt artifact blocked deletion; held/fresh/unmarked fixtures survived.
  Cluster 55440 stopped, test databases retained, staging/live unchanged.
  No hosted retention or existing-artifact deletion. Next: agree staging
  retention scheduling and failure monitoring; no automatic apply authorized.
  See RETENTION.md for detailed evidence and remaining operational acceptance.

- Isolated worker recovery passed on 27 November using `39a358b9`: readiness
  returned 503 before startup, 200 with two real matching-release heartbeats
  15 seconds apart, then 503 after cooperative stop cleared the heartbeat.
  Other readiness checks passed; four job-queue status counts unchanged.
  Publishing disabled and rehearsal network/tool guards installed. Logger
  exited 0 with hash-valid sealed streams. Cluster 55439 and rehearsal processes
  stopped; staging/live unchanged. Stale/wrong-release heartbeat cases and
  external job execution were not exercised. Next: disposable retention rehearsal.

- Isolated application-login recovery passed on 27 November with matching
  `39a358b9` code: fresh SCRAM login rejected an incorrect password and allowed
  Django access without superuser privileges. All 190 migration records were
  consistent, none pending; home, Workshop and liveness returned HTTP 200.
  Restored 9,572 media files; sequence-backed test insert rolled back and absent.
  Cluster 55438 stopped; staging/live unchanged. Worker-dependent readiness was
  not exercised. See BACKUP_RESTORE_REHEARSAL.md for the role-provisioning limit.

- Isolated staging recovery checks passed on 27 November: restored archive
  ownership/privileges matched current staging across 520 public objects and
  the public schema. Reconstructed application role had CRUD on 94 tables and
  access to 81 sequences; representative writes rolled back. All three access
  and three refresh tokens decrypted offline with the backed-up key.
  Cluster on loopback 55437 stopped; staging/live unchanged. Cluster roles,
  passwords and memberships are not in the archive; subsequent login-role
  reconstruction and application smoke verification are recorded above.

- Cooperative staging application shutdown verified on 27 November, release
  and backup-operations bundle `39a358b9`. Web and worker loggers sealed with
  valid hashes and exit-0 receipts before replacements started. Scheduled
  capture/check passed; all 9,595 backup entries matched. Historical logs
  unchanged, staging ready with one web/worker, live `6582cc4` untouched.
  No Windows shutdown or retention deletion. See HOST_MAINTENANCE.md.
  Backup-operations bundle `a1b28bc9` subsequently installed the next-slot fix:
  seven boundary cases passed, and OSWALD selected 18:15 GMT on 27 November
  without manual adjustment. On-demand integrity check exited 0 at 17:15:56.
  Daily backup remains 04:00 UK time; no application restart or capture needed.

- Staging log classification completed read-only on 27 November: 71 routine
  segments, comprising two active, 65 historical unsealed (34 web/31 worker,
  121,067 bytes) and four sealed. Active status supported by process timing and
  sharing violations; historical streams permitted exclusive reads. Four sealed
  manifests verified; zero expiry candidates or segment ACL anomalies/holds.
  Five fixed-name logs remain outside expiry. No logs changed or services
  restarted during classification; live untouched. Subsequent graceful shutdown
  verification is recorded above. Historical segments remain unchanged.

- Evidence-preview blocker fixed and deployed to staging `8a3eb705` on
  27 November. Preview avoids row locks; apply retains transaction/lock order
  and eligibility rechecks. All 10 focused tests passed on isolated PostgreSQL,
  including an enforced read-only transaction. Hosted read-only preview passed:
  retained=201; eligible/held/changed/blocked/empty=0. No retention applied.
  Staging has one web/worker tree; live `6582cc4` unchanged. Backup operations
  bundle remains `5a3b13a6`. Next: classify unsealed logs before proposing expiry
  scheduling; no automatic retention deletion is enabled.

- 27 November staging retention previews: account, backup and routine-log
  expiry returned zero eligible items; runtime preview found 34 expired buckets.
  Evidence preview failed because SELECT FOR UPDATE is forbidden by the enforced
  read-only PostgreSQL session. Next: remove locking from preview only, retain
  apply-mode locks, test and rerun the hosted read-only preview. No deletion,
  retention scheduling, restart or live change was performed.
- First unattended backup confirmed: 27 November 04:00:01 GMT trigger,
  package completed 04:01:06, staging ready 04:01:13; exit 0/event 4100.
  Six hourly checks through 09:15 passed; all 9,595 manifest entries verified.
  Package: backup-20261127T040009Z-08d0afea. Staging/live releases unchanged.

- Automatic staging backups/checks installed on OSWALD from operations bundle
  `5a3b13a6`: daily 04:00 and hourly :15 UK time, SYSTEM, no retention apply.
  Task Scheduler capture and check both passed, with event 4100 and a fresh
  package `backup-20261126T235530Z-44f4e1c4`; all 9,595 manifest entries verified.
  Capture/recovery took about 70 seconds. Earlier failed capture correctly
  produced failure status/event 4101; its cause is unverified, safe stage/line
  diagnostics now installed. Staging `80b4309` recovered with one web/worker;
  live `6582cc4` unchanged. Next: inspect the first unattended 04:00 run.
  See HOST_MAINTENANCE.md for evidence and local monitoring limitations.

- Owner accepted local-only host/storage-loss risk on 26 November. Off-host
  backups are a future improvement, not a launch blocker. Automatic local
  backups and failure/staleness checks are authorized on staging only; live
  and retention deletion remain outside scope. See DECISIONS.md.

- Authorized isolated staging restore passed on OSWALD at 23:35 GMT on
  26 November, in 71 seconds. Existing 25 November package restored into a new
  protected directory and PostgreSQL cluster on loopback 55434. All 9,595
  manifest entries, 806 archive entries, 171 migrations and audited baseline
  counts matched. Rehearsal cluster stopped; artifacts retained; staging/live
  unchanged. See BACKUP_RESTORE_REHEARSAL.md. Off-host recovery is now deferred under the owner's accepted risk.
  Credential decryption, grants, scheduling/monitoring and retention remain open.

- Read-only OSWALD backup/retention audit completed on 26 November. No verified
  recurring backup/retention task; latest complete staging package about 28 hours
  old, with no isolated restore receipt; off-host recovery unverified. Only 2/63
  staging routine-log segments sealed. See HOST_RECOVERY_AUDIT_2026-11-26.md for
  evidence and remaining gates. Next recommended action is a separately scoped
  isolated restore of the staging package. No previews, restores, deletions,
  deployments, restarts or task changes were performed in this audit.

- Owner completed reviewer acceptance on staging: changing EuryDev's Discuss
  vote to Allow replaced the vote (Allow 1, Discuss 0), retaining Pending Review.
  Removing Workshop Mod Approver and retaining Participant turned staff status
  off; refreshing the existing admin session blocked access while normal account
  access remained functional. Voting-control styling was accepted. Temporary
  reviewer access is removed. Next gate: hosted backup/recovery and retention
  scheduling evidence, starting with read-only inventory and previews.

- Owner confirmed EuryDev's reviewer vote on Better Crafting: empty Discuss
  reason rejected, reasoned vote persisted after reload as Discuss 1 attributed
  to EuryDev, and final ruling stayed Pending Review. Review controls now use
  padded theme-aware buttons, selectable radio tiles and a readable reason box.
  Next acceptance: change the existing vote without duplication, then remove
  the temporary reviewer role and verify access revocation.

- Permission-page presentation now reuses dashboard card styling, theme colours,
  spacing and typography, with a lock icon and an outlined dashboard action.
  This replaces the bare Django module/button presentation rejected by the owner.
  Both permission-page tests still pass; staging visual acceptance is pending.

- Reviewer acceptance confirmed participant administration is blocked by HTTP
  403. Denied admin pages now retain the admin shell and permitted navigation
  for active staff, with a contextual message and Return to dashboard link.
  The response remains 403 and is not cached. Nonstaff/anonymous admin login
  requirements remain unchanged. Both focused permission-page tests pass.

- Workshop dashboard Open queue now explicitly selects Pending Review and
  clears its remembered overrides, instead of saving a Pending filter onto All.
  Explicit links reveal their destination tab if previously hidden. Regression
  coverage checks queue selection, hidden-tab handling and unchanged All filters.

- Reviewer acceptance exposed chosen groups disappearing after asynchronous
  admin Save. Explicitly prepare Django's chosen-select cache before FormData,
  including filtered-out choices. This avoids depending on submit-listener
  ordering. JavaScript checks cover chosen/hidden groups, removal and empty
  selections using Django's actual SelectBox implementation. Staff access is
  already synchronized from role membership; do not manually grant superuser.

- Bulk Allow/Disallow now requires a confirmation form with a nonblank public
  reason. Changed rulings save that reason and include it in notifications;
  required mods and already-matching rulings remain unchanged. Superuser-only
  enforcement, row locks and transactional notifications are retained, with
  admin change logging added. All 20 Workshop tests pass, including both bulk
  actions, missing/whitespace reasons, saved reasons and notification contents.
  The owner identified the earlier empty rationale as a bulk-action outcome.

- Owner supplied the real EuryDev JSON download (format 2, 26 November 22:03 UTC).
  It contains the verified participant profile, acknowledgement timestamps,
  four notifications and both Workshop requests with their final rulings.
  No other participant's private data, credentials or internal reviewer notes
  were present in this sample. Empty run/provider/vote collections match this
  participant's tested scope. Better Item Info has an empty public rationale;
  check the final-ruling validation path separately, rather than treating this
  as proof that the export omitted a stored reason. Reviewer-role acceptance
  remains the next check.

- Owner accepted the catalogue layout on iPhone after the landscape thumbnail
  follow-up (3bb5f355): compact rows, square images and rotation spacing now
  look correct. Continue first-release acceptance with a real participant data
  download containing the completed Workshop submission/ruling journeys.

- Owner confirmed rotation spacing is fixed. Landscape illustrated rows still
  exposed a gap below their fixed eight-rem thumbnails when copy grew taller.
  Extend square row-height thumbnail fitting to illustrated rows at wider
  widths, preserving compact portrait styling and the outer normal-flow layout.
  Desktop compact-list sizing remains unchanged.

- Catalogue outer-layout follow-up: owner screenshots show the recommended
  section overlapping the required card after returning to portrait. Replace
  the outer grid with normal block flow and explicit one-rem sibling spacing;
  exclude dialogs so their positioning remains independent. Compact rows and
  square-thumbnail sizing are unchanged. Physical iPhone acceptance is pending.

- Owner accepted compact mobile rows but reported required-card clipping after
  iPhone rotation. Give that standalone card a content-sized flex layout instead
  of a clipped grid, and render its Workshop ID as a block contributing to height.
  Recommended/ruling rows retain their accepted square-thumbnail layout.
  Physical iPhone rotation acceptance remains required.

- Mobile row refinement: reduce copy padding and vertical gaps, and size square
  thumbnails to the measured row height after font loading and viewport changes.
  Reset measurements on resize so rows shrink again after rotation. Thumbnail
  width is bounded to half the row to preserve text space for exceptional titles.
  Local browser checks at 320px and 390px confirmed square full-height thumbnails
  for current catalogue titles, including portrait/landscape/portrait reflow.

- Mobile catalogue follow-up: place ruling badges below titles/Workshop IDs,
  allow section counts to wrap as a unit, and remove fixed card heights so text
  cannot be clipped after reflow. Scope consistent mobile text sizing to the
  catalogue for orientation changes. In-app portrait inspection reproduced
  cramped recommended titles; iPhone rotation clipping needs owner acceptance.

- Owner confirmed both Workshop decision journeys on staging: notification
  receipt, removal from awaiting review and correct catalogue ruling/reason.
  The disallowed journey generated its notification automatically.
- Password reset now handles staging allowlist rejection and transport failures
  with the generic confirmation, without exposing account existence or a debug
  reset link. Logs contain only the exception type. HTTP 429 responses show the
  later active email/IP cooldown expiry (UTC, rounded up to a minute) and include
  Retry-After seconds. Limits remain enabled; no production data is reset.

- Better Containers approval exposed a missing notification integration: both
  individual and bulk Workshop rulings saved decisions without notifying the
  submitter. These paths now create in-app submission notifications on changed
  Allowed/Disallowed rulings only, with the public reason and catalogue link.
  Long reasons are excerpted to the notification limit; full text remains in the
  catalogue. Re-saving the same ruling does not duplicate the notification.
  Owner approved restoring the missing Better Containers notification on staging.
  Exactly one unread notification was created for EuryDev using the saved public
  reason and catalogue destination. Ruling/review details and live were unchanged;
  no email was sent. Participant visual acceptance is next.

- 26 November password-reset follow-up: staging rejected a recipient outside
  its email allowlist, raising an unhandled ValueError and returning HTTP 500
  before reaching Microsoft Graph. Owner approved adding eury@machus.co.uk
  alongside dev@sentineltech.co.uk, keeping allow-all disabled. Staging restarted
  healthy on e862c7f with one web and worker tree each; owner will retry delivery.
  No email was sent during the change and live was untouched.
  The password-reset handling fix above supersedes the remaining HTTP 500 issue.

- Agreed next dashboard change (26 November): add "Your mods awaiting review"
  for the signed-in participant's pending submissions only; hide when empty and
  remove decided items. Results and public reasons belong in notifications and
  current rulings in the catalogue. The full review queue remains private.
  Implemented in the shared dashboard fragment, with responsive title/date rows.
  Regression coverage checks participant isolation, removal after either final
  ruling and hiding the empty section with RR 2 disabled. Hosted ownership checks
  passed. Styling follow-up aligns panel spacing with the Workshop action card,
  using bordered rows, stacked submission dates and awaiting-review badges.
  Visual acceptance remains pending because local browser control is blocked.

- Workshop final-ruling feedback: rename the form label to "Public reason for
  this ruling" and explain that it appears in the public catalogue, not private
  reviewer notes. Workshop admin validation now uses persistent, dismissible
  admin error toasts while retaining field highlighting, accessible error
  descriptions and save-state detection. Server validation remains authoritative.
  JavaScript syntax check and all 19 Workshop tests pass. No ruling was changed.

- 26 November hosted submission acceptance: Better Containers (3586216562)
  exists exactly once, submitted by EuryDev at 09:43:40 GMT, pending with no
  reviewer, review timestamp, votes or final ruling. The owner confirmed the
  differing reason was their own wording, not a submission defect.
  EuryDev has no Workshop admin/vote permissions. One active Workshop Mod Approver
  can view/vote; the staging superuser can finalize. Existing-item checks and the
  unique Workshop ID constraint prevent duplicates. Next: reviewer vote and final
  ruling journey. These checks were read-only; live was untouched.

- Workshop modal now intercepts empty or whitespace-only reasons before POST,
  keeps the dialog open and focuses the reason with the shared feedback toast.
  Typing a nonblank reason clears the client error. Server validation remains
  authoritative; all 19 Workshop tests pass. The mobile follow-up removes the
  forced-height grid and gives the modal body its own scroll area, bounded by
  the visual viewport so keyboard resizing cannot overlap form controls.

- Steam name search now passes on staging. The owner replaced the provisioner's
  placeholder directly in protected configuration. After the authorized staging
  web/worker restart, `world item remo` returned eight results, led by World Item
  Removal List [SP] (3764947570). Staging remains `55ec1e7`, ready with one logical
  web and worker tree each. Live remains `6582cc4` behind construction (503).
  No key was exposed or committed. Real submission/review acceptance continues.
- Owner confirmed password-reset acceptance: old password rejected, new password
  accepted and used reset link invalid. This supersedes the earlier pending note.

- Password reset rehearsal: owner received the reset message, reset in another
  browser and signed in. They reused the same password, so old-password rejection
  is not yet proven manually. Signed-in reset request/completion pages now
  redirect to the dashboard with no-store caching; token validation remains
  unchanged. Continue with a different test password and used-link rejection.

- Dashboard presentation follow-up: while RR 2 is off, show a small
  "Rat Race 2.0 Â· Finalising" notice beneath the welcome copy. When Workshop
  requests are open, make mod submission the main action, linking directly to
  the submission dialog with a secondary catalogue link. Preserve RR 1 history
  and the enabled RR 2 dashboard. No release switches or data change.

## Staging rehearsal authorized and deployed (25 November 2026)

- Staging initially ran `f88086ed`, application-identical to accepted `c9b7fead`,
  then received the modal fix through `98aa0de4`. OSWALD's dev checkout was
  fast-forwarded too. Desktop and narrow phone browser checks pass; 21 focused
  installation/Workshop tests passed for the UI and seed navigation changes.
  Protected paused-writer capture preceded migration; audited populated data
  counts were preserved. Live remains `6582cc4` behind its construction page.
- Registration and Workshop requests are on for testing. RR 1 intake, RR 2
  and leaderboard publishing are off. Staging mail is restricted to the owner's
  single approved recipient for signup/reset acceptance. Real verification mail,
  link activation and EuryDev sign-in succeeded; host status is verified/active.
  The stale pending message on `/thanks/` is fixed on staging `d01eadb2`.
  All 102 registration tests pass; host checks of both current and legacy
  signup sessions show verified status with no-store caching. Live is unchanged.
- Health, matching worker, unique process trees, static asset, retention preview
  and anonymous in-app browser checks pass. Synthetic signed-in Workshop/data
  download/permission checks and a staging web/worker restart also pass. Real
  mail delivery checks are proceeding with the owner's approved test recipient.
- [STAGING_REHEARSAL_2026-11-25.md](STAGING_REHEARSAL_2026-11-25.md) records
  the rollback package, actual evidence and remaining gates. The earlier
  no-deployment statements below describe history before this authorization.

## Operational cleanup candidate (25 November 2026)

- Candidate `c9b7fead` now passes all **442 PostgreSQL tests, zero skips**, plus
  **14 operational tests** on OSWALD. Both concurrency checks ran. A separate
  construction-site DB clone preserved 129 migration entries and the seeded mod,
  applying 61 newer migrations. Temporary cluster stopped; live/staging untouched.
  See [POSTGRES_ACCEPTANCE_2026-11-25.md](POSTGRES_ACCEPTANCE_2026-11-25.md).

- Added repeatable protected backup capture, preview-first manifest-scoped
  30-day backup/90-day closed-log expiry, and daily/size-based web/worker log
  segmentation. The maintenance runner requires capture success before apply.
  Nothing is deployed/scheduled and existing logs/artifacts are not adopted.
- [HOST_MAINTENANCE.md](HOST_MAINTENANCE.md) records usage and limitations.
  Fourteen artifact/logging tests and a real disposable Windows ACL/log check
  pass. Scoped SQLite regression: 442 tests, 440 passes and two PostgreSQL skips.
- Isolated PostgreSQL settings reject production/staging ports. Git on
  `codex/rat-race-dev` was used for candidate transfer into a separate host test
  checkout, not source payloads in chat. Unrelated `docs/IDEAS.md` edits remain
  uncommitted. Next gate is an explicitly authorized candidate staging rehearsal
  and the remaining hosted/provider/operational checks, not more schema cleanup.

## OSWALD inventory received (25 November 2026)

- Read-only host audit reports staging `f079ead` and live `6582cc4`, both healthy.
  Live remains behind its construction page. Its sole Workshop catalogue row is
  the challenge mod seeded by migration `0024`, not a participant submission.
  Live has zero accounts, Workshop submissions or votes. Staging contains
  populated account/run data.
- Independent launch switches are not in either deployed release. Database-only
  backup/restore now passes in a separate temporary cluster: 129 migration rows,
  audited counts and seeded mod fingerprint match. The cluster was stopped and
  restricted artifacts retained. Separate file recovery also passes: 43 media
  hashes, empty private/reference structures, protected configuration and ACLs
  match. No real streaming credentials exist to exercise decryption. Coordinated
  cross-store recovery and candidate upgrade preservation remain untested.
  Maintenance scheduling remains unverified; installed startup
  supervision is now inspected, but actual reboot recovery is untested.
- [HOST_INVENTORY_2026-11-25.md](HOST_INVENTORY_2026-11-25.md) records database
  identities, migration baselines, aggregate counts and evidence limits.
  [BACKUP_RESTORE_REHEARSAL.md](BACKUP_RESTORE_REHEARSAL.md) now records the
  proposed separate cluster, capture/restore sequence and acceptance criteria.
  Task visibility is now verified after the owner relaunched the actual app
  elevated with `--do-not-de-elevate`. All four tasks run as SYSTEM and target
  the observed releases, with startup and retry policies configured. Sandboxed
  commands remain restricted. Actual reboot recovery is still untested.
  Backup-root ACLs need restriction before any capture.
  Elevated inventory found no Rat Race backup/expiry job. Live tasks also repeat
  every minute with `IgnoreNew`, so future write-pause plans must account for
  automatic relaunch. Capture requires an agreed quiet window for local writes;
  worker heartbeats can continue, but file-changing jobs must remain absent.
  No wipes, deployments, migrations or existing service changes were performed.
  New isolated backup/restore artifacts are recorded in the rehearsal document.

## Data download, reviewer roles and launch checks (25 November 2026)

- Self-service download format 2 includes own Workshop requests/votes, RR 1.0
  claims, submissions and linked numeric results, even when intake is closed.
  Decline reasons are included; private staff notes, other people's evidence,
  source CSV files and credentials are excluded. Responses are not cacheable.
- Standard Run Submission Approver and Challenge Administrator roles can review
  RR 1.0 claims/updates. They cannot directly edit ownership or apply imports.
  Import confirmation now checks its own permission, not just staff membership.
- Fixed production startup's early static-manifest lookup and the managed
  `media/.../` page collision. Old sidebar/Workshop menu assertions now check
  the current UI. RR 2 public-statistics expectations remain deferred.
- Added Workshop POST limits before provider calls, safe expired-bucket pruning,
  and preview-first two-year RR 1.0/Workshop evidence expiry using the owner's
  clarified active-run rule. Scores, decisions and public policy survive.
- RR 1.0 request/review locks use account, run, then evidence order without
  nullable joined locks. A PostgreSQL-only claim concurrency test is prepared;
  PostgreSQL tools were not found on PATH, so that proof remains pending.
- Fresh disposable database tests successfully repeat the packaged presentation
  import and role bootstrap, retain empty participant/run datasets, and collect
  a new hashed static manifest. This does not approve package copy for launch.
- Added explicit managed-page release classification and gated the packaged RR 2
  rules/rankings/exploits, including direct access, staff access and homepage cards.
  Updated only release metadata/manifest in the eight-page/eight-image seed package.
  `pages.0044` classifies existing known RR 2 pages; older imports retain safe defaults.
- Staging preparation now refuses active deployment processes before migrations
  and checks the release is inside its installation root. Process-helper fixtures
  pass; no real processes were stopped and no host script was executed.
- Final reproducible scoped regression: 439 tests in 118.210 seconds, 437 passed
  and two PostgreSQL-only skips, including the final editorial release gates.
  A further 98 targeted editorial/install/migration checks pass (overlapping runs).
  [LOCAL_LAUNCH_CHECKS_2026-11-25.md](LOCAL_LAUNCH_CHECKS_2026-11-25.md) records
  the reproducible command, tested candidate scope and remaining host acceptance.
  Existing local data and protected environments remain unchanged. No wipe,
  deployment or scheduler installation has taken place.

## First-release history redaction implemented locally (25 November 2026)

- Account closure now supports reviewed RR 1.0 and Workshop history rather than
  blocking all such accounts. Admin preview shows the concrete affected records;
  confirmation requires acknowledgement and a signed, one-hour review token.
  Changed records invalidate the review. Holds and unsupported relations still block.
- RR 1.0 scores, result pointers and lifecycle survive. Names, character/evidence
  text and source-name hashes are removed. Independent random keys replace identity
  keys. `identity_removed` prevents new claims, owner reassignment, ordinary admin
  editing and replacement imports. Pending updates/competing claims are declined.
- Matching source rows are removed from every stored CSV snapshot and preview,
  including ignored provider columns. Other source rows remain. Changed snapshots
  have new checksums and an explicit redaction marker and cannot be reapplied.
- Workshop metadata, rulings and vote decisions survive with the specified personal
  text removed. Reviewer-only relationships preserve the other submitter's evidence.
  Affected admin logs retain event metadata with identifying text replaced.
- Added migration `0084_legacy_identity_removal`; only disposable databases were
  migrated. Focused tests: 37 pass. Wider run: 203/205 pass with the same two known
  managed-page/Workshop-menu failures. Offline migration metadata has no drift.
- Remaining acceptance: PostgreSQL concurrency, host scheduling/recovery, external
  source copies and retention holds. RR 2 redaction remains contract-dependent.
  Other first-release findings (data-download coverage, reviewer roles and broader
  retention) remain tracked in FIRST_RELEASE_READINESS.md. Nothing deployed or wiped.

## Account retention safeguards implemented locally (25 November 2026)

- Added preview-first `apply_account_retention`; `--apply` removes unverified
  pending/expired registrations at 30 days from registration, independently of
  verification-email resends. Verified, disabled and staff accounts are excluded.
- Closure and bulk deletion stop on retention holds or related evidence/history
  needing review. RR 1.0 ownership stays intact when blocked. This is a safeguard,
  not completed historical-data anonymisation.
- Clean closure removes provider credentials, notifications and private saved
  views. Avatar/quarantine deletion is queued transactionally and retried after
  commit; rollback preserves files. Failed jobs remain available for retry.
- Added migration `0083_account_retention`, hold control, corrected closure text
  and a Windows retention runner. No existing database was migrated, no retention
  task installed, and no host changed.
- Validation: 19 focused tests pass, including a populated migration test.
  Wider account/Workshop/release run: 171 of 173 pass; the two failures are the
  recorded managed-page and Workshop-admin heading expectations. Offline
  migration metadata has no conflicts or drift.
- The subsequent reviewed redaction path is recorded above. Scheduled retention
  and recovery acceptance still require disposable rehearsal. RR 2 restructuring
  remains deferred. See [RETENTION.md](RETENTION.md).

## Database-readiness review recorded (25 November 2026)

- Next checkpoint after release-switch work: review unused/duplicate tables and
  fields, relationships/deletion behaviour, fresh-install migrations,
  populated-upgrade preservation and retention.
- Record evidenced findings in FIRST_RELEASE_READINESS.md before proposing
  changes. Distinguish first-release blockers from optional cleanup and deferred
  RR 2 restructuring. Fewer tables is not a launch requirement; deeper RR 2
  restructuring waits for the final contract.
- Source review is complete: [findings](DATABASE_READINESS_REVIEW.md). No migration
  conflicts or model drift found. No table is classified as safe to drop.
- Launch findings cover closure/anonymisation, retention, personal-data download
  coverage, RR 1.0 reviewer permissions and ownership, and import/upgrade safety.
  Runtime acceptance and host state remain unverified.
- The owner authorized account-closure and retention follow-up, recorded above.
  Deeper RR 2 restructuring
  remains deferred. No schema/data change, reset, migration or deployment occurred.

## First-release controls implemented locally (25 November 2026)

- Added environment-owned `REGISTRATION_ENABLED`, `WORKSHOP_SUBMISSIONS_ENABLED`,
  `RR1_SUBMISSIONS_ENABLED` and `RR2_ENABLED`. All default closed; invalid values
  fail startup. No local `.env` or host configuration was changed.
- Server-side gates cover direct routes and RR 2 admin access without a staff
  bypass. Shared dashboards/profiles hide RR 2 while retaining RR 1.0; managed
  rankings/statistics, navigation and intake controls follow the same policy.
  RR 2 approval routing and leaderboard publication stop while disabled.
- Existing account access/verification/recovery and published Workshop/RR 1.0
  results remain available when their new intake closes. Effective non-secret
  feature states appear in health responses and deployment-check output.
- Fifteen boundary tests pass using disposable Django test databases. Full-feature
  regressions can use `--settings=config.settings_test`; release-boundary tests
  explicitly override switches. No existing database was reset or migrated.
- Relevant regression run: 388 of 394 passed. All six failures reproduce on
  unchanged `fe855cad` in an isolated archive. FIRST_RELEASE_READINESS.md records
  them, including the shared production-startup/static-manifest blocker. Async
  tests passed with internal loopback sockets permitted; no live server was started.
- Configuration, limits and remaining release gates are recorded in
  [FIRST_RELEASE_READINESS.md](FIRST_RELEASE_READINESS.md). This does not complete
  hosted acceptance or make the site ready for release. The database review is
  now recorded above; a separate disposable local acceptance environment and
  approved-seed installation rehearsal must be informed by its findings.

## Agreed staged rollout and first-release audit (25 November 2026)

- Ship one application with RR 2 included but disabled through server-enforced
  release controls. Open accounts and Workshop requests first; open RR 1.0
  claims/updates after its accepted rehearsal and verified spreadsheet handover.
- Repeat clean-install rehearsals on isolated hosted staging, preserving its
  infrastructure and protected configuration. Initial production starts clean;
  all real records then survive subsequent releases. Later RR 2 activation
  requires a populated-upgrade rehearsal and never replaces the live database.
- [FIRST_RELEASE_READINESS.md](FIRST_RELEASE_READINESS.md) records the agreed
  sequence, current source evidence, blockers and acceptance criteria. No wipe,
  migration, configuration change or deployment was performed or authorized.
- The earlier cleanup remains required in two stages: first-release installation,
  migration, seed/presentation and operational cleanup now; final contract,
  compatibility and RR 2 statistics/review work before RR 2 activation, once
  the contract and relevant decisions settle. Do not force unresolved RR 2
  decisions merely to open the community features.
- Original audit gaps: independent feature gates, retention deletion (expiry only
  changes status), Workshop submission POST rate limits and a scoped full-site
  staging rehearsal procedure. Enabled journeys and host recovery need fresh
  candidate-specific acceptance. Release controls are now implemented locally
  as recorded above; the other gates remain outstanding.

## Build 42.22.2 decompilation (10 November 2026)

- Local Vineflower job 17 completed for installed Steam build `26486631`.
  Output: `tgsrr_decompiled/build-26486631-job-17`; verified the build marker,
  `PerkFactory.java` and `LuaManager.java`. The reference-source record was
  refreshed by the existing decompilation workflow. Older outputs remain.
- Three method-writing warnings affect bundled Kotlin/Okio code; see
  `docs/MOD_NOW.md`. No catalogue review, promotion or deployment was performed.

## Build 42.22.1 decompilation (4 November 2026)

- Local decompile job 16 completed and validated installed pre-release build
  `26409601` using the existing Vineflower workflow. Output:
  `tgsrr_decompiled/build-26409601-job-16`.
- Verified the build marker and `PerkFactory.java`; the local reference-source
  record now identifies `26409601` as installed and decompiled. Older reference
  directories remain intact. No catalogue review or promotion was performed.

## Pre-release reference branch (27 October 2026)

- Reference update forms and the enqueue command accept `pre-release`, alongside
  `public` and `unstable`. Migration 0014 records the additional branch choice.
- Local `STEAMCMD_BRANCH` is now `pre-release`. Other deployments retain their
  configured defaults until explicitly updated and restarted.
- A successful decompile also refreshes the installed build ID, supporting
  installations updated directly through Steam desktop.
- Build detection uses the newest valid manifest when Steam desktop and SteamCMD
  have separate manifests for the same installation. Regression coverage tests
  both update directions.
- All 40 focused reference, live-job, authentication and catalogue review tests
  pass. The local migration is applied. No staging or production deployment.
- Follow [the release checklist](STEAM_REFERENCE_SOURCE.md#new-game-release-checklist)
  to generate and inspect a versioned review before approving catalogue changes.
- Local decompile job 15 validated build `26221929` in
  `build-26221929-job-15`. Catalogue review 10 for `42.22` was approved on
  27 October: 5,342 additions, zero changes and zero deactivations.
- Artwork job 8 completed: 4,810 PZwiki images imported; 532 unavailable
  (327 placeholder icons requiring world artwork, 205 without a supported icon
  key). No download failures were reported.
- Job 14 was marked failed after detecting stale-manifest provenance; its output
  is retained as `invalid-manifest-job-14`, outside selectable build directories.
  The previous valid 42.21 reference remains `build-25485521-job-13`.
- Final local health check: HTTP 200 and one logical reference-worker process tree.

## Repeatable Rat Race 1.0 staging rehearsals (18 October 2026)

- `reset_legacy_rehearsal` previews by default; `--confirm` transactionally deletes
  1.0 runs, claims and submissions. It refuses non-staging settings.
- Accounts, platform connections and credentials, primary-channel selections,
  2.0 records, import audit history and notifications remain intact.
- Re-upload both CSVs after reset to repeat the import, claim and update journey.
  Pause staging writes during reset. See [ADMINISTRATION.md](ADMINISTRATION.md#repeatable-rat-race-10-staging-rehearsals).
- Local regression tests cover preview, environment refusal, preservation,
  repeat import and rollback. Deployed and rehearsed on staging on 24 October:
  the dataset was already empty, so no reset was performed. Imported 211 real
  spreadsheet identities (14 Active, 197 Inactive). Twitch and YouTube are now
  configured; YouTube channel/media access was verified. See
  [the staging rehearsal record](STAGING_REHEARSAL_2026-10-24.md).

## Claim review workspace (24 October 2026)

- Declined claims are claimable again by the same participant (27 October).
  Resubmission reuses the existing claim, resets its decision fields and updates
  the submission timestamp. Existing ownership and other-open-claim checks still
  apply. Prior decline notifications remain; the claim holds the latest review
  state. All 23 legacy import/claim tests pass. Not deployed.

- Claim modal now has adjacent Approve and Decline buttons. Decline sends the
  existing review note as its reason, or opens a required-reason dialog when
  the note is blank. Browser checked opening, required validation, cancellation
  and focus return without deciding the local claim. 22 claim/import tests pass.

- Direct legacy list URLs now retain saved-view defaults instead of clearing
  and remembering all filters. Claim review defaults to Pending review;
  Approved and All remain available through filters. Local personal view reset
  and browser-verified on 25 October. All 29 saved-view and import/claim tests
  pass. Not deployed.

- Local modal styling follow-up (25 October): shared-style section bar and close
  icon, compact metadata, bordered result panels, scrolling evidence and separate
  action footer. All 22 legacy import/claim tests pass. Local browser check confirms the
  approved-claim layout, body scrolling, fixed header, close icon, Escape and
  focus return. Pending-action footer and mobile checks remain outstanding.
  Local website returns HTTP 200 with one logical reference-worker tree; not deployed.

- The 1.0 claims list now includes claimant/channel summaries, evidence excerpts,
  historical bests and inline approval. Full details opens a modal containing
  both historical results, channels, full evidence and decision history.
- Old individual claim URLs redirect to the list and open the requested modal,
  even outside the current filters/page. Generic claim editing is refused.
- Approval/decline still use the existing locked, permission-checked actions;
  decline requires a reason and completed reviews cannot notify twice.
- All 21 legacy import/claim tests pass, including filtered modal links,
  view-only access, escaped evidence, decline and repeated approval.
- Deployed to staging as `049f40f` on 24 October. Health, protected data and
  matching worker checks pass. Authenticated browser acceptance awaits sign-in.

## RR Admin Dashboard (24 October 2026)

- The full-width header contains navigation, breadcrumbs and account controls
  in three coloured sections. Breadcrumbs replace the separate Back bar and
  retain list filters and return-to-run destinations. Only the content inset
  reserves unused scrollbar space.
- The notification bell shows the latest ten personal notifications in admin;
  mark-all-read returns to the same admin page. Opening it does not mark read.
- Hover menus share one close timer and the active dropdown stacks above its
  neighbours, without overlapping invisible hover bridges.


- The top-right controls use View site and Notifications icons plus an approved
  avatar (or initial) and nickname. Your settings opens a dropdown containing
  identity, Automatic/Light/Dark theme choices, account settings, password change and
  CSRF-protected POST logout. The Rat app icon is non-interactive branding;
  the hamburger opens the Rat Race Admin drawer.

- VELMA-inspired Top Bar navigation now opens the existing menu in an overlay
  drawer, leaving page content full width. A persistent header hamburger is
  available at every width; above 1300px, named icon shortcuts open section
  dropdowns without opening the drawer. Dropdowns support arrow keys, Escape,
  outside-click dismissal and one open section at a time. Dashboard links directly
  to the Dashboard. Escape, the close button
  and backdrop dismiss the drawer, with keyboard focus returned to its trigger.
  Menu grouping, permissions, ordering and per-account section preferences remain.
  VELMA was read only as a reference; local changes are not yet deployed.

- Menu section expansion is remembered per account in this browser. Saved open
  and closed choices take priority over automatic current-section expansion;
  without a saved choice or available storage, the server defaults apply.

- Local navigation redesign replaces the filterable model tables with an icon
  menu: Dashboard, Rat Race 2.0, Rat Race 1.0, Community, Rules and mods, Website,
  Game catalogue and System. Links retain Django permission filtering; current
  destinations are highlighted and their section opens automatically. Native
  disclosures support keyboard use; the drawer supports Escape and unavailable
  browser storage. No filter or sidebar Add shortcuts remain.
- The project override of Django's base template replaces its filter-dependent
  sidebar script with `admin_menu.js`; compare that template when upgrading Django.
  Local browser checks cover expansion, participant navigation and returning to Dashboard.
  This menu change has not been deployed to staging.

- Dashboard review cards are grouped under Rat Race 2.0, Rat Race 1.0 and
  Accounts and operations. Sections without permitted queues are omitted;
  existing queue permissions, counts and destinations remain unchanged.

- Layout follow-up: Dashboard is the first sidebar link on every admin page. The
  Dashboard contains review queues and runtime status only; duplicate section
  navigation was removed. It extends the admin base directly, avoiding Django's
  `.dashboard #content { width: 600px; }` rule. Browser preview at 1280px confirms
  966px available content, three card columns and no duplicated navigation.
- Layout correction deployed as `38b1bc8`; public release/readiness, installer
  worker checks and protected-data comparisons pass. Three focused Dashboard
  tests pass. Visual check used an isolated rendered preview; authenticated
  staging browser acceptance still requires owner sign-in in the in-app tab.

- `/admin/` now opens a role-aware Dashboard instead of redirecting into a
  model list. Cards link to pending 2.0 submissions, 1.0 claims/updates, avatar
  reviews, closure requests, catalogue reviews and reference jobs needing attention.
- Counts use each registered admin's view permission and queryset. Existing
  administration section links remain available; branding-only staff see no
  participant queues. Reference-source staff see release and worker heartbeat.
- Five focused tests pass, covering all standard roles, restricted branding
  access, a real pending-claim count and filtered queue destinations.
- Deployed to staging as `049f40f` on 24 October. Authenticated browser
  acceptance awaits sign-in in the in-app browser.

## Version-aware authority catalogue links (17 October 2026)

- The shared resolver collapses applicable versions of the same kind/stable ID
  to the latest applicable definition. Distinct alias identities remain ambiguous.
  Approval therefore links known items instead of recording null catalogue links
  after a second catalogue version is installed.
- `reconcile_broken_weapon_catalogue` is dry-run-first; `--apply` fills only null
  broken-weapon cumulative/daily links for exact item IDs. Existing links, raw
  identifiers, quantities and submitted evidence remain unchanged.

## Shared run breakdown dialogs (16 October 2026)

- Nine breakdown types now inherit `includes/run_breakdowns/base.html`: charts,
  weapon lists, activity lists/injuries, skills, landmarks and outposts. The
  shared shell takes section, title and optional description, with blocks for
  specialized content and formatted summaries.
- Shared footers hold totals, sorting notes and coverage warnings outside the
  scrolling content. Injuries use the same footer; empty footers are omitted.
  Header descriptions explain content, while chart captions stay with graphs.
  Four template tests and two focused activity/weapon regressions pass. Browser
  checks confirmed that a long list scrolls to its end without moving the footer.
- A narrow dark section bar holds an accessible close icon above the original
  heading font and description. Lists share a 44rem width; charts use 54rem.
  Existing scrolling, chart controls and dialog dismissal hooks are retained.
- Zombie kills belongs to Challenge progress; chart captions say Kills per
  day/week/month. Activity breakdowns use the Activity section label.
- Two shared-template tests and two kill-chart tests pass. The public-run suite
  passes 20 of 21 tests; the existing Back to RatRacer navigation-label failure
  remains unrelated. Synthetic browser previews checked titles, descriptions,
  landmark rows, icon closing and Escape dismissal. Production deployment is
  outstanding.

## Catalogue artwork continuity (15 October 2026)

- The icon map includes the occupation actually linked to an approved character,
  not only the newest catalogue lookup. Upgrading the catalogue cannot strand
  historical profession links; artwork resolution never rewrites those links.
- Public run/build artwork prefers the selected catalogue entry's imported
  Wiki/manual icon. While new-version artwork is pending, use the latest older
  imported icon with exactly the same kind and stable identifier. Never borrow
  from a different identity or a newer version, or change approved run evidence.
- Regression coverage checks fallback, replacement, version/kind/identifier
  boundaries and manual-artwork priority. No migration is required.

## Interactive injury body (14 October 2026)

- Health artwork uses the original game PNGs at native size, shrinking only
  when needed to fit the viewport. SVG tracing was rejected for edge artifacts.
  Re-run the health artwork importer if an installation imported the SVG trial.

- Injury modal uses original male/female game silhouettes, outlines and red
  body-part overlays with pixel-based pointer hit testing. Hover or tap opens
  an injury popup; arrow keys explore injuries and Escape dismisses details.
  The centred body replaces the previous dropdowns and permanent details panel. Paired counts come from approved injury metrics;
  missing type detail is explicitly unclassified. Partial history remains visible.
- New exports record character sex and approval stores starting/current values.
  The injury view selects the recorded body automatically; older exports retain
  the manual selector. No identity is inferred. Casey's synthetic injury pairs now match its existing
  type and body-part totals (19 injuries). Casey's local demo character now records
  male for starting/current sex, selecting the body automatically. Injury
  overlays use a brighter health-display red (#cc2424), with muted white
  uninjured areas.
- Migration 0011 adds body-part catalogue artwork. Normal game import without
  `--no-assets` imports health art from UI2.pack; targeted command:
  `import_health_body_artwork --game-root <path> --game-version <version>`.
  No bundled body images. 38 game-derived managed assets imported locally.
- Male/female rendering, chest counts, and hand selection verified in a local
  rendered-modal preview. Missing artwork retains the existing list UI.


## Trapping species artwork (14 October 2026)

- Trapping import prefers matching adult species artwork when available, avoiding
  placeholder caught-item images such as the game's rabbit item for raccoons.
  Catalogue display prefers the current icon key; manual overrides still win.
- Demo Casey now has one raccoon caught in a cage, taking both trapping totals
  to 32. Previous demo trapping data is backed up in outputs.


## Breakdown icon audit (14 October 2026)

- Activity and weapon breakdown icons now read exclusively from catalogue assets.
  Removed the last display-specific mapping for trapped animal categories.
- Animal import and review discover registered `TrapAnimals` types and resolve
  their caught-item texture from game scripts. Existing live-animal definitions
  retain priority for shared IDs. The local import added four trapping categories,
  with all four wiki images available. 26 focused tests pass.
- Injury and body-part rows remain text-only; unknown IDs do not get substitute
  artwork. No run evidence was changed.


## Fluid catalogue artwork (14 October 2026)

- Fluid records and translated names now import from generated game scripts.
  The importer reads the shared fluid texture from the vanilla crafting UI;
  wiki reconciliation fetches it as a normal catalogue asset.
- Milk breakdowns resolve fluid entries rather than using the hardcoded
  `Base.Milk` carton. Approved fluid metrics now link to fluid catalogue entries;
  previously unlinked rows resolve at display time without rewriting evidence.
- Local migration 0010 is applied. All 61 game fluids, including cow and sheep
  milk, imported with wiki artwork. No separate image package is required.


## Animal catalogue import (14 October 2026)

- Game imports and catalogue review snapshots read raw animal IDs, breed icon
  references, sex and baby relationships from installed animal definitions.
- Wiki reconciliation includes animal entries, translating `Item_` texture
  keys to wiki filenames and using normal managed catalogue assets.
- Removed the temporary animal icon pack and its deployment command. Normal
  catalogue approval queues the existing wiki sync. Both import commands accept
  `--kind animal` for targeted refreshes. No animal images need packaging.
- Local Build 42.21 validation imported 30 animal records and all 30 wiki
  images successfully. Repeat imports leave them unchanged. 23 focused tests pass.
- Representative breed artwork is deterministic; adult carcass artwork avoids
  the calf icons the game reuses for live adult inventory pickup.

## Activity breakdown cells (14 October 2026)

- Recorded injuries, fish caught, animals trapped, animals slaughtered, animal
  births and milk collected now open breakdown modals when positive detail rows
  exist. Trapping has separate animal/trap groups; injuries have separate
  injury-type/body-part groups. These dimensions are never added together.
- Uses whole-cell links and muted chevrons. Hover and keyboard-visible focus
  share Long Road's inset amber outline and subtle background tint. Both interactive
  cells scale to 104% from their centre on hover or keyboard focus, including
  text, background and border; reduced-motion
  preferences disable the transition. Normalized approved summaries/metrics
  take precedence over legacy approved projections, including empty authority.
  Cells with totals only remain plain. Names/icons resolve through catalogues
  where available; partial coverage and fractional milk litres are retained.
- Four focused presentation regressions pass. No migration is needed.

## Outdoor temperature history (14 October 2026)

- The character toolbar now has a thermometer with approved run-wide high/low
  values and a matching history modal. Highest/Lowest checkboxes control two
  distinct lines; daily, weekly and monthly grouping uses the same range menus
  as weight. Weeks/months retain period extrema, not averages. Tooltips retain
  each extreme's date/time; unknown history stays absent and partial coverage
  is disclosed. The modal supports pointer and keyboard inspection.
- Approval stores independent exported run records in `RunTemperatureSummary`
  and daily values in nullable typed `RunDailyRecord` fields. Full timestamp
  observations are retained beside each value. Pending submissions do not
  change this authority, and no daily-sum reconstruction is used.
- Migration 0065 is applied locally. Temperature and export regression tests
  pass, as do JavaScript grouping tests. The wider public-run suite has one
  pre-existing navigation-label assertion failure, reproduced with the original
  template. Daily/weekly/monthly controls, both line toggles and timestamp
  tooltips were browser-checked using synthetic data without altering runs.
- Local website responds HTTP 200 with one logical reference-worker process
  tree. Production deployment and real in-game temperature export verification
  remain outstanding.

## Kills by weapon modal (14 October 2026)

- The favourite weapon button opens a modal matching Broken weapons, with
  catalogue icons, counts and proportional bars sorted by kills then name.
  Approved weapon authority takes precedence over legacy approved projections;
  the button and list use the same source. Partial tracking and empty records
  have explicit messages. Existing dialog dismissal and focus handling apply.
- Three focused weapon-modal and broken-weapon tests pass. No migration is
  required; public deployment remains outstanding.

## Weight history graph (14 October 2026)

- Sandy Isaacs' local 3,650-day demo history now has synthetic measured weights
  and calendar dates for all chart groupings, ending at 80 kg. Only its demo
  daily rows were updated; original submission evidence remains unchanged.
  Previous daily values are backed up in `outputs/sandy-demo-weights-before-20261014.json`.

- Replaces the initial delta plot with a Better Daily Reports-style measured
  weight graph: By Day/Week/Month, Last 7/28 days, Last 12/52 weeks, Last 12
  months or All Time. Weekly/monthly points average available daily weights.
- Compact square points, hover/touch and keyboard inspection and active-run
  In Progress markers replace the large daily table. The vertical scale spans
  the selected range's daily minimum minus 1 kg to its daily maximum plus 1 kg,
  retaining daily extremes when displaying weekly or monthly averages.
- New mod exports carry measured daily weights. Approval stores them in nullable
  `RunDailyRecord.weight_kilograms` (migration 0064). Older omissions remain
  unknown, without back-calculation or modification of immutable evidence.
- Daily gaps remain disconnected. Calendar months require recorded dates.
- Migration 0064 is applied locally. All 75 export tests, two chart-data tests,
  three JavaScript grouping tests and three focused desktop Lua checks pass.
  The controls and point tooltips were browser-checked with a synthetic fixture.
  The local site was restarted and verified with HTTP 200 and one worker tree.
  In-game export verification and public deployment remain outstanding.

## Missing catalogue artwork audit (12 October 2026)

- Item artwork now uses explicit Icon first, then the first non-empty
  IconsForTexture variant as the representative image. The catalogue importer
  and PZwiki reconciliation both support this, including existing blank-key
  records via their retained raw properties. Manual icons remain protected.
- Local missing-only reconciliation imported 469 assets across catalogue
  versions, retained 8,926 existing assets and protected 35 manual assets.
  All five demo weapons now resolve icons, including Crowbar and Hunting Knife.
- The remaining 532 distinct records were audited: 327 moveable/default-icon
  entries need world artwork rather than default.png; 198 clothing records are
  wound, bandage, makeup or stubble overlays; six are mounted animal skulls;
  one is Custom Occupation, whose public presentation already has a local icon.
  These are not missing IconsForTexture mappings. Do not substitute unrelated
  inventory images or claim complete artwork coverage.
- Placeholder default icons are explicitly reported as requiring world artwork,
  rather than repeatedly requesting default.png. The missing-only command
  retries unresolved entries without downloading existing PZwiki/manual images.
- Eight catalogue regression tests pass. Code deployment remains outstanding;
  run import_pzwiki_icons --missing-only on each deployment to reconcile assets.

## Broken weapons details (12 October 2026)

- The Broken weapons activity label opens the shared public detail modal with
  weapon counts sorted descending, then alphabetically for ties. Rows share
  trait styling and show catalogue icons and counts, with proportional fills
  representing their share of total breaks. No percentage text is shown. Approved
  normalized statistics take priority over older export projections. Partial
  tracking is labelled explicitly. Without a breakdown the label is plain text
  and no modal is rendered. Deployment pending.

## Partial outpost progress (12 October 2026)

- The public outpost bar and weighted leaderboard score now average individual
  outpost progress over the catalogue target, including partial progress. The
  completed count remains separate. Unrounded ratios are used for scoring.
- Approved authority and older projection paths both follow the agreed
  aggregate formula in MOD Decision 002. Deployment remains outstanding.

## Event evidence review (11 October 2026)

- Integrity findings linked to events and chronology review markers open an
  evidence dialog with payload fields, event time, day and raw event JSON.
- Every chronology event opens the evidence dialog, including events without
  review warnings. All 16 registered event types have readable titles. Catalogue
  names resolve skills, outposts, requirements, towns, locations, items, recipes
  and mods where available; unknown identifiers remain explicit. Kill milestones
  and outpost requirements have contextual labels. Extension fields remain visible.
- Nested payloads display as labelled facts rather than JSON excerpts. Review
  reasons use readable descriptions, clock values use hours/minutes, and elapsed
  hours use days/hours/minutes. Technical hashes remain in raw JSON.
- Grouped findings offer Previous/Next navigation through their related events.
  Covered-by-approval events remain inspectable. Opening details never records
  approval; existing submission decisions and audit workflows remain authoritative.
- Native dialog keyboard handling, explicit Close, backdrop dismissal and focus
  restoration are supported. Inline evidence disclosures remain usable without
  JavaScript. No migration is required; deployment remains outstanding.

## Challenge edition names (11 October 2026)

- Rat Race 1.0 is the original challenge and is still running. Rat Race 2.0 is
  the next edition in development; standings remain separate.
- Public profiles, dashboards, claims, update forms and moderation copy use
  numbered editions. Stored page/navigation copy receives a wording migration.
- The import cutoff is a spreadsheet handover date, not challenge closure.
  Existing approved claimants can continue submitting Active 1.0 run updates.
- Internal legacy identifiers and existing URLs remain compatible.
- Deployment remains outstanding.


## Leaderboard progress authority (5 October 2026)

- Verified-run rankings now calculate weighted completion from the same approved
  category ratios as the public run page, rather than the obsolete exported
  `challengeProgress` field. Sparse exports no longer receive a zero score.
- Preserve the 50% kills, 25% outposts, 25% skills weighting and existing
  renormalisation when a category is unavailable. Use unrounded ratios before
  rounding the final score to two decimal places. Landmarks do not affect rank.
- Eleven focused leaderboard and partial-skill checks pass. A broader run-page
  check has a pre-existing Back to / Return to wording mismatch, reproduced
  with the unchanged run presentation code. Deployment remains outstanding.

## Collapsible submission video (4 October 2026)

- Submission review embeds use a keyboard-accessible Embedded video disclosure.
  Only the player collapses; evidence status, audit window, provider, broadcast
  link, timestamps and clip links remain visible.
- Expanded is the first-visit default. Each moderator's choice is remembered
  across submissions in this browser using account-scoped local storage.
  The disclosure remains usable when storage is unavailable or JavaScript is off.
- No migration is required. Deployment remains outstanding.

## Embedded VOD referrer policy (28 September 2026)

- The submission evidence iframe explicitly uses `strict-origin-when-cross-origin`
  so YouTube receives the site origin required to avoid player Error 153.
  The site-wide `same-origin` policy remains unchanged, and cross-origin embeds
  do not receive moderation-page paths or query strings.
- Playback verification on DEV remains necessary after deployment.

## Submission validation feedback (27 September 2026)

- The submission form checks supplied VOD URL formats after a 500 ms typing
  pause, on blur and on submit. A floating dismissible amber helper beneath the
  URL field requests a valid Twitch or YouTube VOD without moving page content.
- Both the VOD helper and Submit Evidence helper use `RatRaceHint.create` in
  `anchored_hint.js`. Supply `anchor`, `element` and `placement` (`top`, `bottom`,
  `left` or `right`); the returned control exposes `show`, `hide`, `position`
  and `destroy`. Helpers follow scroll/resize, flip when the opposite side has
  more room, and clean up on page departure or modal close. Modal helpers mount
  inside the dialog so they remain in its top layer.
- Helpers support `type: "info" | "error" | "warning" | "success"` (default
  information). They use a tinted surface with consistent text weight and a
  semantic border, pointer and icon instead of the filled button appearance. Submission field errors use
  the error variant and matching error-colour field outlines.
- Invalid submissions show a toast and focus/scroll to the first invalid field,
  revealing collapsed export inputs when needed. Server-returned field errors
  receive the same feedback; active-run blocks retain their existing dialog.
- Empty evidence remains a server-side challenge-policy decision. URL format
  checks do not establish video availability or ownership.
- Other submission field errors (including required export, timestamps, extra
  broadcasts and server validation) and export-file errors use the same floating
  control. Error lists remain available as a no-JavaScript fallback.
- Submission feedback uses the dedicated top-centre `RatRaceToast.show` control
  (`message`, `type: "info" | "error"`, optional `title`, `signal`, `duration`).
  It has a severity icon/accent, dismiss action, accessible announcements and
  hover/focus timeout pausing. Live site notifications retain their separate
  bottom-right toast. Field hints remain anchored beside the relevant control.
- Floating hints hide when their anchor is inside collapsed details, and
  reposition on reopening. Toggle events explicitly refresh their visibility.
- Fifteen focused JavaScript checks, syntax validation and Django system checks
  pass. The owner accepted the local browser presentation after testing.
  Deployment remains outstanding.

## Staging navigation fallback fix (26 September 2026)

- Cloudflare injects its email decoder into HTML and removes the script node after
  execution. The fetched response still contains it, so the previous unknown-script
  guard rejected every page on staging. Local development has no Cloudflare injection.
- The guard now exempts only the same-origin, known Cloudflare decoder outside main.
  Other unknown scripts, account changes and admin/auth destinations still fall back.
  Protected email links in swapped content are decoded without executing fetched scripts.
- Fallbacks emit a console warning and `page:navigation-fallback` event containing a
  reason and pathname, without query strings, response bodies or account identifiers.
- Regression command: `node tests/javascript/page_navigation.test.cjs` (12 checks).
  Browser fixture: `python tests/javascript/navigation_fixture_server.py`, port 8766.
  Old code reproduced two GETs and a changed header token; fixed code made one GET
  per navigation and retained the header. Email text and mailto links were verified.
- DEBUG=False plus WhiteNoise CompressedManifestStaticFilesStorage collectstatic
  succeeded locally (444 assets). Django system checks pass. Standard release
  collectstatic is required; no migrations or environment changes. Not deployed here.

## Persistent participant navigation (26 September 2026)

- Participant browsing now replaces main content across home, rankings, rules,
  mods, exploits, dashboard, profiles, runs and settings. GET filters and query
  links also use this navigation; titles, focus and history follow the destination.
- Page lifecycle callbacks initialise controls on arrival and release gallery
  timers and document/window listeners on departure. Notification history shares
  the same navigation rather than maintaining a second history handler.
- Notification links follow participant redirects with smooth navigation and refresh
  the unread badge. Admin destinations continue with a full page load.
- Authentication, provider connections, downloads and POST submissions retain
  normal navigation. Changed identity, unknown scripts and failed loads fall back.
- Browser checks covered home, leaderboard build dialogs, rules tabs, mod search
  and information dialogs. JavaScript syntax and Django system checks pass.
  No deployment has been performed.


## Live reference-job progress (24 September 2026)

- The update form offers Stable / Unstable and records the chosen branch on
  each job. SteamCMD receives that saved branch explicitly. `STEAMCMD_BRANCH`
  sets the default (public unless configured; local development uses unstable).
  Migration `operations.0013` is applied locally.
- Running Steam updates also read timestamp-filtered progress lines from the
  SteamCMD console log because redirected Windows output may remain buffered
  until exit. Login/session lines are excluded. Branch and progress regression
  coverage passes (25 focused tests).

- Steam update and decompilation job pages poll permission-checked status every
  two seconds, showing elapsed time, current activity, completion details, and
  an optional auto-scrolling output tail capped at 64 KB.
- Workers capture merged tool output while processes run. SteamCMD percentages
  describe the current stage; Vineflower INFO output reports activity without
  an estimated overall percentage. Steam account names are redacted from the
  stored update output. Existing jobs have no retrospective output capture.
- Local migration `operations.0012` is applied. Focused worker, authentication,
  permission, output-capture, and timeout tests pass (22 tests).

## Optional signup country / territory (20 September 2026)

- Signup includes an optional country/territory dropdown labelled Country / territory,
  defaulting to Prefer not to say. Existing participant records remain blank.
- `django-countries==9.1.0` supplies the choices; migration `0060` adds the field.
  The country / territory is editable by participants in account settings (including clearing it) and in participant administration and included in the
  participant's own data export. Rankings display its flag after the participant name, with the country name as accessible text and a tooltip. Blank selections show no flag.
- The privacy notice records this optional information, version `2026-09-20`.

## Staging deployment decision (14 September 2026)

- Keep `G:\RatRace_Staging` as the sole staging root, with immutable releases.
- Routine deployment uses `Install-RatRaceStagingStartup.ps1` with one UAC
  confirmation. Preparation automatically runs migrations, role bootstrap and
  static collection before replacing the staging web/worker tasks.
- Retain existing release/process-tree, readiness and worker-heartbeat checks
  and production/GSA isolation. This repository change performs no host actions.

## Branch and worktree

- Canonical development branch: `codex/rat-race-dev`
- Canonical local worktree: `The Great Spiffo's Rat Race`
- Website and Project Zomboid mod contracts evolve together on the unified
  development branch.
- The canonical local development runtime now lives here too. Its ignored
  `.env`, SQLite database, and media library were migrated from the obsolete
  `The Great Spiffo's Rat Race - Website` worktree on 2026-08-15. Do not start
  or update the obsolete worktree as the local website deployment.

## Goal

Prepare the community release: verified accounts, Workshop requests, managed
rules/mod policy and RR 1.0 handover with claims, updates and rankings. Include
RR 2 in the application but keep it disabled until its separate contract and
activation acceptance. See FIRST_RELEASE_READINESS.md for the staged scope.

The Project Zomboid catalogue remains a lean lookup and resolver layer.
Kind-specific classifications and gameplay fields belong to typed detail
records, while aliases and assets remain shared catalogue relationships.

## Done When

- The production environment, database, persistent media, web process, and
  reference worker are deployed and recoverable.
- Required secrets and provider integrations pass deployment health checks.
- Registration, account, Workshop review, RR 1.0 and public information journeys
  pass representative production-shaped acceptance, with RR 2 proven disabled.
- Retention automation and the final pre-launch privacy review are complete.
- The Rat Race 1.0 handover dataset is imported only after the team selects its
  spreadsheet handover date.

## Submission review journey: implemented locally

The owner agreed the revised [submission review policy](SUBMISSION_REVIEW_POLICY.md)
on 11 September 2026. The local website now implements:

- **Challenge Runs** is the single moderation workspace. Shared starting views
  are Needs Review, No Recent Audit, Active and All. Needs Review is the first
  visit default; the last selected accessible tab and filters are remembered
  per moderator in the database.
- Moderators can save personal filter/sort views and hide, restore or reorder
  available tabs. Administrators with `manage_shared_run_views` can publish
  and edit shared views. New shared views append without resetting user order.
- Only the earliest unresolved submission can be opened for review. Later pending
  rows remain visible but locked until reassessment after the earlier decision.
  Completed submissions remain available for inspection and audits.
- Run-local Overview, Submissions and Audits tabs retain the complete ordered
  history and preserve run context when reviewing. Old list links redirect to
  the unified workspace; approval and audit decisions remain separate.
- Audit filters include unfinished audits and VOD windows closing within 48
  hours, elapsed windows and unknown broadcast dates. No Recent Audit finds
  accepted submissions without a latest passed audit, rather than inventing
  an obligation based only on elapsed time.
- Challenge Modes configure Evidence required (default on). Required modes reject
  new submissions without a supported VOD and block manual approval without evidence.
  Optional modes permit manual review and clean automatic updates without footage. Accepted records are not retroactively changed.
- Automatically approve routine updates only after validation and applicable VOD evidence
  checks pass, with no review trigger or unresolved earlier submission.
- Require human review for new mod changes, debug use, outpost completions,
  explicit time-deviation events and reconciliation/recovery events. Previously
  reviewed cumulative events do not trigger again.
- Embed VOD evidence where supported. Audit within seven days of broadcast where
  possible; later disputes require team discussion. No mass approval is planned.

Next action: a signed-in team acceptance pass covering a first submission,
clean VOD-backed update, flagged update, evidence correction and recorded audit.
Migrations are applied locally; production deployment and live provider checks
remain outstanding. Earlier manual-only descriptions below describe prior behaviour.

## Implemented

- Production-shaped direct-Uvicorn deployments serve persistent branding,
  uploaded, and generated catalogue media from the root-relative `/media/`
  route independently of `DEBUG`. The asynchronous route precedes editorial
  catch-alls, rejects path and symlink escapes, preserves content types, and
  provides browser caching without treating media as collected static assets.

- Project Zomboid reference administration accepts the Steam account identity
  and temporary authentication only. SteamCMD, installation, Java, and
  Vineflower paths resolve from protected deployment settings and appear
  read-only for diagnosis. Legacy database path values remain compatible but
  cannot override updates, decompilation, or catalogue-review snapshots.

- Production-shaped ASGI deployments require request-scoped PostgreSQL
  connections with `POSTGRES_CONN_MAX_AGE=0`; startup validation, deployment
  checks, environment examples, and Windows generators reject or avoid a
  persistent connection value.
- Windows startup-task replacement now stops the complete Rat Race process tree
  within the selected installation root, proves web and worker task startup,
  and waits for web readiness plus the matching worker heartbeat without
  affecting another Rat Race environment or unrelated processes.
- Run approval limits its PostgreSQL row lock to the submission while retaining
  the separate Challenge Run lock, including first approval with no baseline.
- The live-notification event stream supplies an explicitly asynchronous
  iterator to Django under ASGI.

- The first normalized run-authority slice now stores the approved export
  contract version, one character, selected starting traits, spawned starting
  traits, mutable current traits, and starting-location evidence on the run.
  Trait and occupation rows retain raw Project Zomboid IDs and link directly to
  catalogue entries when resolved. Starting-location rows can also link to the
  versioned geography catalogue.
- Run-submission approval now locks the submission and run, refreshes the first
  authority slice, updates the approved snapshot, and sends its notification in
  one database transaction. A forced importer failure is covered by a rollback
  test and leaves the submission received and the run pending.
- The Run data danger zone provides a staging and local-development moderation
  reset for one run or all runs. It transactionally returns submissions to the
  review queue, clears approval-derived authority and baseline links, and
  preserves uploaded exports, evidence, run identities, and participant
  notifications. The permanent data purge remains a separate operation.
- Pending run submissions now support evidence-only corrections without
  replacing their immutable tracker export. Participants can update evidence
  proactively from the dashboard or follow a moderator's direct Awaiting
  Evidence notification. Every evidence snapshot remains in an audit history,
  later submissions stay chronologically blocked, and corrected evidence is
  reassessed before review. Approval independently rejects red blocking
  findings and any change to the currently approved event prefix. New uploads
  must also be at least as current as the newest existing submission.
- The signed-in player run page presents `Spawn choice` and `Starting location`
  from run-owned authority. Starting location is an icon-only link using the
  newest active `Base.Map` catalogue artwork, with `View map` alternative text;
  coordinates remain hidden in the presentation but preserved in the canonical
  `https://map.projectzomboid.com?{x}x{y}x{z}` destination. A random choice remains
  labelled `Random Spawn, KY` without revealing its resolved region.
- Projection schema 2 outpost imports preserve sparse current-state evidence and
  validate first completions against their sole permanent ledger events. Approval
  rebuilds only observed `RunOutpost` and `RunOutpostDeliverable` records with
  bounded lifecycle summaries, raw IDs, and nullable catalogue links. Missing
  catalogue-backed records mean unexplored or incomplete. Public run cards,
  rankings, and community outpost counts now prefer run-owned authority.
- Approved sparse skill and kill evidence now rebuilds normalized `RunSkill`,
  `RunKillSummary`, and `RunWeaponKill` authority. Missing catalogue skills and
  kill-source rows resolve to zero for presentation, while partial baselines and
  raw Project Zomboid source IDs remain stored evidence.
- A persistent production-shaped staging environment is live at
  `https://dev.tgsrr.com` from the isolated `G:\RatRace_Staging` root. It uses
  its own PostgreSQL cluster, protected configuration, filesystem state, empty
  application data and repository-controlled
  presentation. `[DEV]` titles, a persistent development/test banner,
  anti-indexing headers and a full-disallow `robots.txt` distinguish it from
  production. Only the working Graph mail integration is currently shared;
  all other external providers remain deliberately unconfigured. Release
  `1676dba` is running; its web and worker scheduled-task actions still need to
  be updated from an actual elevated Windows PowerShell session before restart
  recovery can be accepted for this release.
- Permanent participant accounts using nickname, email, and password.
- Self-declared 18+ participation eligibility with versioned confirmation and no
  collection of dates of birth or identity documents.
- Email verification with pending, verified, expired, disabled, and removed states.
- Participant login and secure password recovery.
- Participant account summary, password change, staff administration link, and
  secure logout controls.
- A versioned participant privacy notice, participant JSON data download, and
  authenticated account-closure requests visible to administrators. The notice
  identifies the configured providers and purposes, international processing,
  essential storage, automated checks, retention schedule, rights and the
  `support@tgsrr.com` contact. Staging adds a test-data warning.
- Central environment-backed `SITE_*` configuration for public operator identity,
  company details, privacy contact, eventual public URL, and brand fallbacks.
- Singleton Branding backend with safe environment defaults, immediate
  public rendering, and a scoped Branding Administrator role.
- Optional backend-managed header logo, favicon, social sharing image, homepage
  feature image, and decorative background image. Each slot has an independent
  enable switch and retains its text or theme fallback when disabled.
- Reusable image library with thumbnails, friendly names, original-file metadata,
  immediate validated multi-file uploads, and image selection from Branding.
- Configurable public attribution to The Indie Stone's terms, kept separate from
  the ordinary non-affiliation disclaimer.
- Managed visual themes with three editable presets, private signup-page preview,
  duplication, restoration, activation, and validated design controls.
- A protected backend-managed Homepage assembled from ordered, reusable,
  responsive sections without administrator-authored HTML or JavaScript.
- Managed Pages include dedicated Separator sections for intentional spacing.
  Editors may choose space only, a subtle line or an accent line, with small,
  standard or large spacing and the usual managed section widths.
- Managed sections can also contain Separator blocks for the same spacing and
  rule treatments within an individual section column.
- Existing content blocks can be dragged between sections and columns. Moves,
  removals and their resulting parent changes are saved atomically with the
  page, preventing an emptied source section from cascade-deleting blocks that
  have been moved elsewhere in the editor.
- A public managed Rules page at `/rules/` provides the Stable challenge's
  concise fair-play contract, objectives, mod policy, evidence requirements,
  bug-recovery boundary, run endings and moderation expectations. Its seeded
  sections remain fully editable through the existing page builder, and a
  top-level Rules navigation item exposes it to everyone.
- Managed Pages support Tabbed Content sections containing two, three or four
  tab panels. Each panel reuses the ordinary column block editor, so blocks can
  be added, reordered and dragged between tabs without introducing a separate
  content system. Editors manage each tab's label, short description and
  default selection, plus a horizontal or vertical section orientation. Vertical
  tabs use a left-hand rail on wider layouts and the established horizontal
  scroller on narrow layouts. Public tabs use accessible keyboard controls,
  direct-link URL fragments and a reduced-motion-aware content fade. The Rules
  page presents its detailed material through Getting
  Started, Fair Play, Evidence, and Endings & Rulings tabs.
- A public managed Exploits page at `/exploits/` sits beneath Mods in the Rules
  navigation branch. Exploit rulings are server-managed catalogue records with
  a classification, concise ruling, optional guidance, publishing state, and
  display order. The public vertical tabs contain one entry per published
  exploit, including the settled Spiffo's Council rulings on zombie
  force-spawning, trapped-animal Nimble farming, and combat-built fence or
  window grids. Each ruling can include ordered example images selected from
  the managed image library, with required alternative text and optional
  captions. Accidental-discovery and evidence guidance avoids treating
  unpublished edge cases as
  approved behaviour.
- Managed Pages include dedicated Community Statistics and Card Group blocks.
  Standard and linked action cards can be mixed within one group. The homepage
  uses three destination-led linked cards and replaces
  its embedded leaderboard with an edge-to-edge alternate-surface statistics
  bar, framed by full-width top and bottom rules only, calculated exclusively
  from verified runs with approved canonical submissions. Editors choose and
  order supported metrics without controlling database queries. The initial
  metrics are Rats in the Race, Zombies Eliminated, Days Endured, Outposts
  Claimed, Fallen Survivors, Average Kills per Day and Real Hours Raced. Real
  Hours Raced sums cumulative active-gameplay milliseconds from each run's
  approved canonical projection rather than estimating from in-game time.
  Each action card is itself a keyboard-accessible link with managed alt text,
  a validated destination, an optional manually authored number or short label,
  and a restrained hover or focus lift. Cards size to their content rather than
  reserving space for a separate footer action. Every card inherits its card
  group's audience by default, or can independently target everyone, signed-out
  visitors, signed-in participants, or remain hidden. Editors add either card
  type from a split Add card control, and linked-only destination fields remain
  contextual to linked cards.
- The reusable `Ranking Table` block and editorial `/leaderboard/` Page share
  one official-run query implementation. Editors can configure additive mode,
  build, lifecycle, and participant filters; result selection; ordering; row
  limits; visible columns; and supporting presentation without controlling
  eligibility or canonical values. Public rendering preserves signed-in detail
  gates and uses a horizontally scrollable compact table on narrow screens.
- Flat backend-managed public pages at protected `/pages/<slug>/` addresses,
  with page-owned navigation labels, visibility, and ordering.
- An immutable Code-managed Pages registry in Website Content administration.
  Version-controlled definitions install stable keys, display identities,
  descriptions, fixed audiences, availability and route metadata. Navigation
  Items may target available fixed application routes alongside editorial
  Pages, while planned and address-driven routes remain non-selectable. The
  editorial Homepage remains solely in Pages and is not duplicated in the
  Code-managed Pages catalogue. Run Django migrations after changing the
  version-controlled registry definitions so the deployment reconciles their
  availability and route metadata into the database.
- A public Mods catalogue at `/mods/` with search, Allowed and Disallowed ruling
  filters, illustrated and compact list views, a pinned Required TGSRR Workshop
  entry, a curated Recommended section for selected Allowed mods, and responsive
  rules and submission modals. Recommended is a separate feature flag rather
  than a ruling, and recommended entries are not duplicated in ordinary
  results. The page states that only
  mods explicitly listed as Allowed or Required may be used; Disallowed and
  unlisted mods cannot be used. Its More Info modal explains the cosmetic and
  vanilla-information rules with generalised examples. Signed-in participants
  can find a mod by Workshop name, numeric ID or full Steam URL and provide a
  required reason. Name search uses Steam's supported `QueryFiles` API with a
  protected `STEAM_WEB_API_KEY`. Exact ID and URL resolution remain available
  without that key. The website does not parse Steam's rendered Workshop pages
  as an integration fallback. Steam confirms that the item exists for Project Zomboid, duplicates
  report their existing Required, Allowed, Disallowed or Pending review state,
  and valid new items enter Pending review without becoming public rulings.
  The Discord mod-policy record supplied on 1 August 2026 has been normalised
  into 59 unique historical entries and resolved against Steam: 54 retain a
  Previous Unstable ruling of Allowed and 5 retain Disallowed. All 59 current
  rulings remain Pending review until the permanent Stable voting workflow
  produces an authorised final decision.
- The permanent mod-approval journey is implemented in administration. Its
  Mod approval queue sorts Pending review records first, exposes a dedicated
  Pending shortcut and opens a focused review page containing the participant
  reason, Steam destination, previous Unstable provenance and editable final
  decision fields. Eligible Workshop Mod Approvers, Challenge Administrators and super
  administrators cast one attributable `Allow`, `Disallow` or `Discuss` vote
  per Pending mod and may revise it while voting remains open. Disallow and
  Discuss require a reason. Vote totals produce an advisory recommendation or
  discussion-needed state but never publish a ruling automatically. Moving a
  Pending record to Allowed or Disallowed requires a public rationale and
  records the authorised reviewer and timestamp. The final reviewer can insert
  a consistent Allowed or Disallowed rationale template, then edit and confirm
  the public wording before publication. Workshop Mod Approvers may
  vote in the queue; Challenge Administrators may edit final decisions. Run
  Submission Approvers are separately scoped to run reviews. Participant decision
  notifications remain the next slice.
- The current Workshop Mod records are development fixtures and imported
  preparation data. The project owner intends to wipe this table before the
  completed approval journey is tested from a clean state.
- Consistent primary navigation, authenticated-route redirects, accessible form
  metadata, keyboard focus treatment, and responsive local journey checks.
- Signup validates nickname and email availability, password policy and password
  confirmation when each control loses focus. Availability checks remain
  age-gated and rate-limited, while ordinary server-side validation remains the
  final authority on submission.
- Administration editing forms use one **Save** action that saves in place and
  continues editing. It activates only when the form has unsaved changes;
  workflow actions such as submission review remain separate.
- Registry-backed administration is presented by concern without moving its
  database models: Participant administration, Challenge configuration, Run
  moderation, and Platform integrations.
- A superuser-only System Operations danger zone previews and atomically purges
  every challenge run, run submission, and submission notification after exact
  typed confirmation. Participant accounts, platform integrations, challenge
  modes, catalogue data, managed content, and site configuration are preserved.
- Privileged, confirmation-protected closure processing with non-personal
  closure receipts and a documented nullable owner for future independent runs.
- Cloudflare Turnstile integration using official test credentials locally.
- Cache-backed request limits for signup, resend, and password recovery.
- Administrator roles, participant promotion, status management, and CSV export.
- Local development documentation and automated test coverage.
- Mod-export ingestion into immutable, individually reviewed submissions, with
  integrity verification and explicit administrator approval or reasoned
  decline. The first approved submission officiates its run; each later approval
  alone advances the run's canonical snapshot. A later generated snapshot may
  advance with an unchanged verified ledger so current-state changes are not
  discarded merely because no new semantic event occurred.
- Format-4 event blocks are retained as content-addressed verified records.
  Matching checksum, sequence range, starting hash and terminal hash allow later
  submissions and review pages to reuse decoded events while every manifest and
  complete ledger chain is still verified. Approval detects an exact approved
  event prefix, retains sealed daily authority, processes only appended events,
  and replaces the current active-day record. Any discontinuity uses the full
  rebuild path inside the same atomic approval transaction.
- The participant submission form accepts the tracker-generated `.txt` file by
  file picker or drag and drop, with direct export-text paste retained as a
  secondary fallback. All three paths use the same authoritative validation and
  immutable submission workflow. Pasting a Windows `.txt` path is detected and
  presents a focused file-chooser action with instructions to paste that path
  into the operating system's File name field.
- The canonical local background launcher performs a controlled restart on
  every invocation. It records both the Windows virtual-environment wrapper PID
  and the actual Python socket-owner PID, stops both, and discovers listeners
  with `netstat` because CIM process and TCP queries may be unavailable. It
  refuses unrelated port owners, then requires exactly one listener before
  reporting success. Route-specific changes must also be verified through the
  running HTTP server, using an authenticated request when the route is gated.
  In-process Django rendering is not proof of what port 8001 is serving.
- Current format-3 mod-export ingestion, including the signed ledger and complete
  character/trait projection, preserved on both the run and immutable submission.
  Current event-schema 2 ledgers are accepted; legacy and unknown event schemas
  are rejected. The run-snapshot projection remains schema 1. Decoder parity
  covers the mod's canonical number, map, event-metadata, framing, integrity and
  size rules, with a real current-contract mod export retained as a golden test.
- Optional raw `challenge.id` and `challenge.gameMode` evidence within the
  schema-1 projection. Exact IDs map to managed Challenge Modes; unknown IDs are
  accepted as unmapped, empty IDs may map by the exact game-mode name, and legacy
  exports remain unspecified. Starting evidence and the current approved
  snapshot are preserved separately.
- Independent run lifecycle tracking for active, deceased, abandoned, completed,
  and invalidated runs, presented as Active Runs and Past Runs on the participant
  dashboard. A validated, hash-chained `run.ended` event and matching projection
  evidence now mark an approved death export as Deceased automatically. Other
  lifecycle decisions remain moderator-managed. Each Challenge Mode also has a
  configurable per-participant active-run limit, defaulting to one. Updates to
  an existing active run do not consume another slot. Participants can
  irreversibly deactivate their own active run without review; this marks it
  Abandoned, declines its pending submissions, prevents future updates to the
  same run ID, and immediately releases the mode slot.
- Active-slot admission uses the latest integrity-validated reported lifecycle
  without treating it as approved authority. Pending deceased runs release their
  active slot and are unlimited by default; Challenge Modes and expiring,
  reasoned participant overrides can bound active or pending-deceased runs.
  Approval still owns official lifecycle and prevents a newer active run from
  being approved before earlier terminal evidence is resolved.
- Challenge Run administration presents lifecycle as a dedicated `Set status`
  moderation action rather than an ordinary editable field. The moderator must
  choose a status and provide a reason; the previous status, new status, acting
  moderator, timestamp, and reason are retained in the run's administration
  history.
- The protected two-file Rat Race 1.0 Leaderboard and Rat Race 1.0 Hall of Fame importer,
  merged Unstable run records, public legacy ranking sources and participant
  claim journey are implemented. Signed-in participants can claim one legacy
  run for team review. A focused approval screen records the reviewer and
  decision, links approved historical identity to the participant and sends an
  account notification. The participant dashboard shows pending and declined
  claim states or, after approval, a dedicated Rat Race 1.0 panel containing
  one imported historical result. Active legacy runs use their current
  Leaderboard result; Inactive and Deceased runs use their Hall of Fame best.
  A separate edition divider and lifecycle tag keep legacy results explicitly
  separate from verified Rat Race 2.0 runs.
- Approved claimants with an Active legacy run can submit participant-authored
  updates containing character name, kills, Time Survived, Level 10 skill count,
  completed outposts, Alive or Dead state and Twitch or YouTube VOD evidence.
  Time Survived accepts `YY:MM:DD:HH` or plain words and is normalized into the
  full display plus decimal days without moderator arithmetic. The website
  calculates weighted progress from the established one-million-kill, 13-outpost
  and 35-skill targets. Only one update may await review per legacy run. A
  focused moderation screen approves or declines the immutable submission with
  a retained reason
  and notifies the participant. Approval advances the current result,
  advances the historical best only when stronger, and marks the run Deceased
  when the submission reports death. Pending and declined submissions never
  affect public rankings.
- Signed-in Rat Racers can open another participant's profile from their linked
  name in Stable or claimed Legacy ranking tables. The profile presents only
  approved participant-facing records: Personal Best, Active Runs, Past Runs
  and the claimed Rat Race 1.0 result when available. It does not expose
  submission history, pending or declined submissions, or moderation details.
- Signed-in verified-run page presentation at UUID-based addresses. Challenge
  progress is the first section and uses four short, responsive cards for
  kills, skills, outposts and landmarks. The Outposts card opens a dialog with
  all 13 catalogue-backed outposts, expanding the sparse authoritative run data
  for presentation only. Missing run records appear as collapsed Undiscovered
  entries without invented deliverable evidence. Discovered entries provide
  compact deliverable status details. Public rows
  mirror the mod's requirement, current-value and Passed/Pending columns and
  omit backend lifecycle counts. Each outpost is a bordered disclosure card
  with visible hover and focus feedback linking its rows to their owning outpost.
  The former summary grid and standalone World Progress section are removed.
  The character header has a compact build control that opens the starting
  occupation, selected starting traits and currently effective traits. The run
  page and leaderboard use one shared build-dialog template; the run page adds
  accessible Starting Traits and Current Traits tabs when both sets exist.
  Starting traits are ordered by catalogue point cost, zero-cost traits are
  presented as Passive, and the occupation shows its catalogue point value.
  When Project Zomboid omits a trait description, the tooltip derives a factual
  fallback from the trait's structured starting skill boosts.
  Current traits omit build costs and distinguish gained traits from traits that
  are no longer effective. A small
  state row exposes current weight and the favourite weapon from approved
  cumulative weapon-kill evidence through accessible hover text; their future
  history graphs remain pending authoritative history tables. Spawn choice and
  map-linked starting coordinates remain concise evidence in the header. Broken
  Weapons remains in Recorded Totals and can become interactive when its
  authoritative breakdown exists. Current skills follow in a grouped
  Project Zomboid-style panel using the complete version-controlled 35-icon
  in-game artwork pack from `deployment/assets/skill-icons`, installed into the
  catalogue as the preferred manual presentation with PZwiki artwork retained
  as a fallback. The Skills progress card opens that panel in a dedicated
  details dialog, matching the Outposts interaction and keeping the main run
  page concise. Town visits expand the sparse export against the 12 canonical
  town definitions, presenting omitted towns as unvisited. Activity totals and
  clearly distinguished in-game
  export and website receipt timestamps without exposing raw run IDs, checksums
  or ledger hashes. Charts remain a later signed-in presentation layer.
- Participant notifications for submission receipt and moderation decisions,
  with ASGI/SSE live invalidation, immediate bell/dropdown refresh, unobtrusive
  title toasts, a visible-tab polling fallback, and in-place refresh of
  participant dashboard run and moderation panels.
- A dedicated Project Zomboid Catalogue administration section with stable IDs,
  display metadata, version ranges, aliases, a reusable resolver, and a scoped
  Zomboid Integration staff role.
- Super-admin Project Zomboid reference operations with short-lived Steam
  authentication, a separately supervised queue worker, installed-build checks,
  and website-triggered Vineflower decompilation. Decompiled output is generated
  into immutable build/job directories, validated before activation, and tracked
  against the installed Steam build so stale Java reference data is visible.
- Catalogue imports use a two-stage super-admin workflow. A background review
  stores the exact interpreted snapshot and clearly separates additions,
  changes, and deactivations without mutating live catalogue data. Explicit
  approval applies only that reviewed snapshot; changed build IDs or source
  paths make the review stale and require a new comparison.
- Automated Catalogue v2 ingestion from an installed Project Zomboid build for
  traits, occupations, skills and items. Generated game definitions and English
  translations populate typed detail records (costs, descriptions, XP boosts,
  exclusions, granted traits and recipes) without manual transcription.
  Items retain their exact full type (for example `Base.BoneClub`), raw item
  definition, tags, weight and texture key. Exact display-category identifiers
  and translated names live in a dedicated table, and deterministically
  resolved weapon skills reference the existing Skill Details records rather
  than duplicating strings. A deterministic
  analysis layer records overlapping capabilities rather than forcing items
  into one category: the same item may be a weapon and a tool, while literature
  may additionally be a book or magazine. Weapon categories resolve to their
  governing skill where Project Zomboid exposes enough evidence.
  Deterministic texture relationships are retained for every available icon,
  including shared item texture keys used by weapons, tools, books and magazines.
  Approval queues a background PZWiki reconciliation which uses those keys to
  import matching catalogue PNGs into managed media. PZWiki is the presentation
  authority for supported catalogue artwork; installed Project Zomboid files
  remain authoritative evidence for identity, details, texture availability and
  checksums but do not replace a served PZWiki image. Manual overrides remain
  protected. A super administrator can also queue the same reconciliation from
  the Project Zomboid reference source page. Catalogue approval and PZWiki
  reconciliation are separate operational concerns: every reconciliation has
  its own job record, trigger, lifecycle timestamps, status and final summary.
  Completed jobs also retain a structured unavailable-artwork report, grouped
  by catalogue kind and failure reason in administration, so unsupported icon
  keys and expected PZWiki files that do not exist remain directly inspectable.
  The approved catalogue review remains immutable and records only the reviewed
  game-data decision. Shared filenames are fetched once per job and reruns do
  not duplicate unchanged assets. Missing Wiki artwork is reported rather than
  guessed. Transient PZWiki download failures are retried per asset and, if still
  unavailable, are recorded in the structured report without aborting the
  catalogue-wide job. The latest reconciliation completed successfully on
  31 July 2026: 16 images were imported, 4,483 were unchanged, 748 unavailable
  results were recorded for review, and no manual assets were overwritten.
  Local and production deployments must run `run_reference_update_worker` as a
  separately supervised process alongside the web server. The web server does
  not consume queued reference or artwork jobs by itself. Avoid concurrent
  database polling during long write-heavy jobs when developing with SQLite;
  production uses PostgreSQL and must supervise and restart the worker.
- Website-owned animal taxonomy maps known raw Project Zomboid animal
  identifiers to display names, species and life stages while preserving unknown
  or modded identifiers as unclassified evidence.
- A host-managed full Project Zomboid reference source records installed Steam
  build state and auditable update jobs. Admin and scheduler requests enqueue
  work without blocking HTTP; a separately supervised worker runs the fixed
  SteamCMD update using the host's protected cached login. Jobs record their
  trigger, requester, queue/start/finish times and result, suppress duplicate
  active work, and notify super-admins when a build changes, an update fails, or
  authentication must be renewed. Catalogue diff, review and promotion
  automation remains next.
- A provider-neutral connected streaming-account foundation for Twitch and
  YouTube, including immutable provider/channel identities, connection state,
  audit timestamps, administration and participant-facing account status.
- Production-shaped Twitch linking with encrypted rotating credentials,
  ownership proof, hourly-on-use validation, reactive refresh, explicitly
  cached recent broadcasts and clips, and immutable run-evidence snapshots for
  moderation.
- Real Twitch OAuth, channel linking, VOD/clip refresh, evidence selection,
  submission review and moderator approval verified end to end against a live
  Twitch channel on 24 July 2026.
- Twitch-side credential revocation is detected on the next validation or media
  refresh and changes the website account to Reconnect required.
- Official Twitch and YouTube brand marks shared across connected-channel rows
  and the run-submission journey.
- Optional Discord identity linking using the minimal `identify` permission,
  with encrypted credentials and participant-controlled disconnect.
- Google-authorised YouTube channel linking using the read-only YouTube scope,
  stable Google and channel identities, encrypted credentials, ownership
  collision protection, reconnection and participant-controlled disconnect.
- Provider-selectable run evidence using connected Twitch or YouTube channels.
  Switching providers and refreshing recent media updates only the evidence
  controls, preserving the pasted run export and the rest of the submission
  form. Twitch supplies broadcasts and clips; YouTube supplies recent public or
  unlisted uploads and archived livestreams through the official Data API.
- A participant may explicitly select one owned, connected Twitch or YouTube
  account as their primary streaming channel. That provider-neutral selection
  supplies the linked provider icon in live ranking tables. Clearing,
  disconnecting or invalidating the selected account safely removes the icon.

Uploaded brand images live in deployment media storage rather than Git. A live
deployment must persist and back up that media directory alongside the database.

Approval now rebuilds sealed and active daily authority into run-owned
`RunDailyRecord` rows. Fixed scalar deltas live on the daily record, while
non-zero keyed deltas use sparse `RunDailyMetric` rows. Missing deltas are
interpreted as zero, and active-day partial provenance is retained.

Current cumulative observed statistics are normalized independently into one
typed `RunStatisticSummary` row per metric family and sparse
`RunStatisticMetric` dimension rows. This supports indexed filtering and graph
queries without reading projection JSON. Headline cumulative values come from
these current-state rows or an existing dedicated authority table. Daily charts
come from `RunDailyRecord` and `RunDailyMetric`; cumulative totals are never
reconstructed by summing daily deltas.

## Not Now

- Expanded analytical charts and detailed statistics beyond the launch views
- Full mod integration
- Participant notifications when an authorised reviewer records the final mod
  ruling. The submission, team voting and final-ruling administration journey
  is implemented.
- Expanded public weapon-kill, literature, and collectible presentation using
  the item catalogue. The implemented run export already supplies the underlying
  `weaponKills` and `literature` evidence; this is parked while launch-critical
  public pages are completed.

## Confirmed domain infrastructure

- The project owns `tgsrr.com`, purchased through Spaceship.com on 1 August
  2026. The Spaceship website is the current control surface for the domain's
  DNS records and related registrar settings.

## Hierarchical managed navigation

Pages now own canonical root or nested public addresses such as `/gallery/` and
`/media/gallery/`. Navigation placement is managed separately through ordered
Navigation Item records. An item may link to a Page or act as a non-clickable
heading, and may be nested to three visible levels. Each item has an enforced
audience of Everyone, Signed-out visitors, Signed-in participants or Staff.
Hiding a menu group by audience hides its nested branch, while code-managed
destinations retain their own stricter audience checks. Editorial managed Pages
use the same audience choices, enforced for both direct addresses and navigation
visibility. The public navigation bar
sits at the top of the page before the branded masthead. Desktop renders
dropdowns in a navigation bar that remains visible at the top while scrolling.
Mobile renders expandable submenus in a compact control bar that hides while
scrolling down and returns when scrolling up. Open navigation,
account, and notification panels keep the mobile bar visible. Guest Sign In
and Sign Up actions remain directly available beside the hamburger instead of
being hidden inside the expandable navigation. Code-controlled
routes remain reserved, and provisional `/pages/<slug>/` addresses permanently
redirect to a Page's canonical address. The admin tree uses visual drag-and-drop
insertion between items: vertical movement selects the position, while moving
right nests under the nearest preceding item and moving left moves the item
outward.

## Recommended next action

Complete and record the database-readiness review specified in
[FIRST_RELEASE_READINESS.md](FIRST_RELEASE_READINESS.md) before proposing changes.
Then use the findings to inform the separate disposable local acceptance
environment and approved-seed installation rehearsal, preserving current
development data. The RR 2 submission review/audit journey remains a
separate activation gate under [SUBMISSION_REVIEW_POLICY.md](SUBMISSION_REVIEW_POLICY.md).

Production deployment acceptance remains required, including persistent database
and media storage, independent web and worker supervision, secret validation,
health checks, backup, restore, restart, and rollback procedures.

The customized public presentation now has a checksum-validated, transactional,
idempotent export and import path through `deployment/site-presentation`. Use it
to transfer approved local editing work without moving users, participants,
runs, submissions, credentials, notifications, or operational state.

## Remaining work

### Before first community release

- Complete the database-readiness review after release controls; record findings
  before proposals and resolve evidenced launch blockers. Do not restructure
  unsettled RR 2 data or target a lower table count as a release condition.
- Verify the locally implemented server-side release gates on the accepted
  hosted candidate. Keep RR 2 off in production while the contract/statistics evolve.
- Complete installation/migration and approved seed-content cleanup. Rehearse
  clean staging installation; do not clone local or staging records into live.
- Close the source-audited blockers and acceptance gaps in FIRST_RELEASE_READINESS.md.
- Complete retention automation and the final privacy review.
- Run a production-shaped acceptance test across registration, account,
  Workshop requests/review, RR 1.0, Rules, Mods, and Exploits, plus restore/rollback.
- Test the full legacy import, claim, and participant-update journey with a
  representative export outside production. At initial deployment, both RR 1.0
  and RR 2 challenge-run datasets must be empty. Import real RR 1.0 results only
  after deployment/readiness checks and the agreed spreadsheet handover date.
- Replace any remaining development-only navigation or gallery records before
  launch.

### Before RR 2 activation

- Once the owner confirms the final mod/export contract, re-audit and complete
  the coordinated cleanup in PRODUCTION_DEPLOYMENT.md. Consolidate one supported
  contract and remove obsolete development compatibility without weakening
  integrity or approved tracked-checkpoint rollback protections. No mid-save bootstrap.
- Resolve the relevant RR 2 statistics/page decisions and complete submission
  review/audit acceptance, including automatic-approval safeguards.
- Scope any development-data reset separately. Rehearse a populated upgrade on
  hosted staging and preserve live accounts, Workshop requests, RR 1.0 records,
  credentials and pending reviews. Never replace the live database at activation.

### Approved later work

- Notify participants when an authorised reviewer publishes a final mod ruling.
- Add separately cached provider online status to the leaderboard.
- Add signed-in participant search.
- Build the planned Top Ten summary and signed-in Run History pages when their
  product requirements are agreed.

## Launch-critical operational safeguards

Local development uses the canonical environment-aware
`scripts/start_website_dev.ps1` launcher. It loads the repository's uncommitted
`.env`, starts and verifies the web server and independently running reference
worker, avoids duplicate processes, and reports the local and LAN addresses.
The Django management entry point rejects a bare `manage.py runserver` so local
startup cannot silently omit the environment or reference worker.
Production must receive secrets from its deployment environment, never from the
repository, and supervise its web and worker processes independently.

Startup validation must fail before accepting traffic when a configured Twitch
or Discord integration has a missing or malformed Fernet encryption key. The
deployment health check must also identify the running build and verify that
required integration configuration is present without revealing secret values.
Restart procedures must stop the complete previous process tree and confirm that
only one listener owns the intended port before announcing the site as ready.

Do not rotate `STREAMING_TOKEN_ENCRYPTION_KEY` without an explicit credential
migration. Existing encrypted provider tokens must remain decryptable across
deployments, restarts and rollbacks. A pre-deployment check should verify this
against stored credentials without printing decrypted tokens.

The repository now includes a strict `config.settings_production` boundary and
the non-secret environment contract in `.env.example`. Production startup
requires PostgreSQL, configured runtime state, Graph email, live Turnstile, avatar moderation, all
supported connected providers, and the complete Steam reference and
decompilation toolchain. The Windows profile uses database runtime state;
Redis is required only for the cache-backed production profile.
`/health/live/` identifies the running release, while
`/health/ready/` verifies the database, configured runtime state, persistent storage, and a
recent reference-worker heartbeat from that same release. The full audited
contract and remaining host-specific work live in
`docs/PRODUCTION_DEPLOYMENT.md`.

## Admin consistency, first step (13 September 2026)

- Rollback checkpoint: `c33e873` contains the shared list filters, Participant
  saved views and UI audit before the record-header work.
- Shared admin change-form header now leads with the record name and groups
  History/View on site alongside it. Run and submission banners use the same
  action sizing while retaining their metadata, statuses and local navigation.
- Record headers now use the unboxed list-title layout, with 28px pill actions
  on the right and metadata/statuses underneath. Footer actions remain 36px.
- Search toolbars share 46px height, 284px by 30px search fields and consistent
  positioning, including lists without filters.
- Checked all 41 registered admin list entries locally (34 expose toolbars),
  plus Participant, Page, Run and Submission detail headers. Browser screenshots
  confirmed the run and participant layouts; 48 regression tests passed.
- Workshop Mods now has shared/personal saved views, seeded by migration 0059.
  All three tabbed lists persist selection, filters and live drag ordering.
- Tab actions use an arrow menu and per-tab context menu; save dialogs have
  title/footer bars, separate Update/Save New actions and backdrop dismissal.
- Run metadata uses a toolbar-height strip with permission-aware participant
  links that preserve the originating run for Back navigation.
- Pre-commit verification: 51 relevant tests pass, migration drift and whitespace
  checks pass. Browser checks covered layout and menu/dialog actions; animated
  drag cursor behaviour still needs broader manual verification.

## Unified Rat Race 1.0 workspace (24 October 2026)

- Runs and reviews is the single 1.0 menu destination. Built-in saved tabs cover
  runs, active runs, update review, claim review and data imports; each retains
  the appropriate table and existing review actions.
- Personal and shared saved views support filters, search, sorting, per-user
  last-tab memory, drag reordering, hide/restore and reset. Shared edits require
  `registry.manage_shared_legacy_views`; imports remain superuser-only.
- Migration 0067 creates the view and preference tables and seeds shared tabs.
  Migration 0068 prioritises Claim review, then Update review, for default tab
  orders while retaining customised orders. First visits open Claim review.
  Apply migrations before deploying the workspace. Existing direct list and
  claim-review links remain supported.
- Content width and centring now compensate for both visible and absent
  scrollbars. Header backgrounds remain full width.
- System diagnostics use cards for release, worker, installed game build and
  catalogue counts/imports. Rat Race 2.0 includes pending mod reviews.
- Invalid stored approved exports show a warning on run pages instead of
  crashing; approval comparison is unavailable and stored records stay intact.


### PZWiki original-image route (2026-11-28)

- OSWALD verified ordinary File pages and their advertised original PNGs for all
  six supported artwork kinds: HTTP 200, image/png and PNG signature validated.
  The Special:Redirect shortcut was challenged.
- The importer now resolves div.fullImageLink#file links on normal File pages,
  accepting only HTTPS pzwiki.net /w/images/ originals. It retains filename
  caching, checksums, manual protection and PNG validation.
- Confirmed Cloudflare challenges stop reconciliation immediately without
  retrying every entry. No challenge cookies or browser impersonation are used.
- Deployed staging release 750b6b27. All 29 focused tests passed locally and
  on OSWALD. Artwork job 2 completed at 02:21 GMT on 2026-11-28.
- Imported 4,810 of 5,342 supported entries (90.0%); all 4,810 stored PNGs
  matched recorded hashes. No Cloudflare challenge occurred.
- Coverage remains unfinished for 532 entries: 327 placeholder keys requiring
  world artwork and 205 without supported icon keys, covering 531 items and
  one occupation. None has an exact preserved-artwork match. Retrying the
  same mapping cannot resolve these; next work is evidence-based artwork
  mapping for these entries, without guessing or replacing manual artwork.
- Approved catalogue review and preserved prebaseline artwork remain intact.
  Staging construction mode stays on and intake stays off. Live remains
  untouched on 6582cc4.


### Missing icon-key audit (2026-11-28)

- The 205 missing-key entries were traced against installed build 26486631.
  198 are hidden character clothing overlays: 74 zombie damage, 60 wounds,
  34 worn bandages, 27 makeup and 3 stubble entries. Their clothing/material
  textures are not inventory icons. Keep their catalogue identities and
  report this source distinction explicitly; do not invent inventory images.
- The remaining occupation is base:unemployed (displayed as Custom Occupation).
  Its game definition has no IconPathName, but the existing website-owned
  Profession_custom.png provides its approved artwork. The earlier report
  incorrectly treated the missing game key as missing website artwork.
- Six jawless wall skulls have exact WorldObjectSprite references:
  Bull, Sheep and Pig use constructedobjects_signs_01_48; Cow uses _56;
  DeerStag uses _64; DeerDoe uses _72. Shared sprites reflect the game source.
  Their PZWiki articles did not establish the same wall artwork.
- Artwork reconciliation now accepts the reviewed install root and extracts
  these missing-key moveable sprites from Tiles2x.pack, preserving original
  crop offsets and recording game provenance, sprite key and SHA-256.
  Wiki/manual presentation stays protected. The 327 default-icon entries
  remain outside this change.
- 32 focused tests pass, including a synthetic PZPK extraction, repeated-run
  idempotence, missing-file repair, manual/wiki protection and classification.
- Deployed immutable staging release 8a152979 after all 32 tests also passed
  on OSWALD. New artwork job 3 used missing-only reconciliation and made zero
  network requests. It recovered six exact wall-skull icons; all six files
  match extracted sprite hashes. All 4,810 existing PZWiki images are unchanged.
- All 205 missing-key cases are accounted for: six recovered images, 198 hidden
  overlays without inventory icons, and one iconless occupation. The report
  retains those 199 explicit explanations; it does not claim they gained icons.
  The separate 327 placeholder entries still need world-artwork work.
- Job 2 remains preserved. Staging construction mode and disabled intake remain
  in place, admin login returns HTTP 200, and live remains on 6582cc4.


### Existing custom icon and placeholder objects (2026-11-28)

- Corrected the missing occupation artwork claim: Profession_custom.png is the
  existing approved briefcase/prohibition image, already used by public runs.
  Reconciliation installs this exact file as a protected manual catalogue
  asset and excludes the occupation from unavailable artwork.
- The 327 default-icon entries are all moveables: 310 Furniture, 11 Gardening,
  four Material, one Tool and one Camping. They include chairs, paintings,
  ore chunks, workstations and a hide tent. 326 specify WorldObjectSprite;
  Base.Moveable is the generic template with no specific object sprite.
- Extended exact sprite extraction to default-icon moveables, with
  Tiles2x.floor.pack as an additional source. Do not infer names or replace
  approved wiki/manual artwork. Local source audit resolves 320 of 327.
- Six explicit references were absent from every installed texture pack:
  Hematite, HematiteLarge, Malachite, MalachiteLarge, Mov_WhiteHalfCounter and
  Mov_IndustrialDishwasher. These and generic Base.Moveable remain unresolved.
  Staging verification completed on release 14f7bb46: 320 placeholder images
  recovered, approved Custom Occupation icon installed, all 4,810 wiki images
  and six skull images unchanged. Both recovery jobs made zero network requests.
- The first run recovered 319 sprites. A regression fix permits the hyphen in
  signs_one-off_07_85 (Out of Gas sign), recovering the remaining exact sprite.
  All 33 focused tests passed on OSWALD. Prior job records remain intact.
- Current report has 205 explained entries: 198 character overlays and seven
  unresolved objects (six absent sprite references and the generic template).
  This supersedes the earlier report of missing Custom Occupation artwork.
  Staging construction stays on, intake stays off, and live remains untouched
  on 6582cc4. Both staging shutdown logs were sealed and hash-verified.
