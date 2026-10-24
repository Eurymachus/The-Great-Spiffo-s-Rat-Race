# Rat Race 1.0 staging deployment and first import rehearsal

Completed on OSWALD, 24 October 2026 (Europe/London).

## Deployment

- Remote `codex/rat-race-dev` was verified at
  `b580e48f384adec2c4d871b664276eddff18747c` before deployment. The commit
  was fetched from GitHub; no missing changes were recreated.
- Previous protected staging release identifier: `cf414cd`. The approved diff
  adds only the reset command, its tests and documentation; no migrations.
- Immutable release: `G:\RatRace_Staging\releases\b580e48`, extracted from
  `git archive` of the approved commit, with `.tgsrr-release-commit` recording
  the full commit SHA.
- Used `Install-RatRaceStagingStartup.ps1 -ReleaseRoot
  G:\RatRace_Staging\releases\b580e48` in an elevated Windows PowerShell
  session. Preparation ran migrations (none pending), role bootstrap and static
  collection. Tasks are `RatRaceStagingWeb` and `RatRaceStagingWorker`; web
  listens on port 8002, staging PostgreSQL on port 5433.
- Backup completed before environment/release preparation:
  `G:\RatRace_Staging\backups\pre-b580e48-20261024`. Includes PostgreSQL
  custom dump (validated with `pg_restore --list`), configuration, media,
  private storage, storage, reference/decompiled trees and logs. Steam session
  storage was not copied into the application backup.
- Database dump SHA-256:
  `a2069844371b412f90527fc1ee082c9f4684ee52befecef6b26a17c06c8248c7a`.
- Compared protected environment against the backup: only `RELEASE_ID`
  changed. Encryption keys, credentials and persistent paths were preserved.
- Installer confirmed both staging task trees running the selected release,
  readiness HTTP 200 and one logical reference-worker tree. Worker Python
  processes 12076 -> 13732 are a parent/child tree, not duplicate workers.
- Public homepage, `/legacyleaderboard/`, `/legacyhalloffame/`, liveness and
  readiness returned HTTP 200. Both health endpoints report `b580e48`;
  every readiness component, including the matching worker, passed.
- All production deployment checks passed. Django reports the existing
  `security.W021` warning: HSTS preload is not enabled.
- Production was not modified.

## Reset inspection

The existing staging dataset contained zero 1.0 runs, claims and submissions.
The deployed `reset_legacy_rehearsal` preview confirmed these counts. No reset
was confirmed or executed.

## Source snapshot and preview

Recorded source: <https://docs.google.com/spreadsheets/d/1qQWLEajgU58FXO83_Xn85rZ8jm6BhUv5VdpIraNfBUQ/edit>.
Downloaded on 24 October 2026 during this rehearsal.

- Leaderboard: **Active Runs Only**, gid `1499062142`. Used its direct CSV
  export of range `A1:K18`, preserving headings and all 14 participant rows.
  The full worksheet export has a farewell footer in rows 20–21; the existing
  importer rejects row 21's missing name and would treat row 20's prose as a
  participant. The range export excludes both non-data rows without editing
  participant values. The full export is retained alongside it.
- Hall of Fame: **Historical Leaderboard**, gid `1891335124`. Its title
  explicitly covers active runs and runs on hiatus, opted out or ended. Used
  its separate full CSV export, containing 215 participant rows.
- Retained the full XLSX snapshot as additional source evidence. Historical
  Leaderboard was not substituted for both input datasets.
- Importer-normalized UTF-8 CSV SHA-256 hashes:
  - Leaderboard: `803a531384a8fb913653b5568c1e317ccee0e9a925d02e98bb6a06b8f704d83f`
  - Hall of Fame: `2294f9c3bb416a00d893f0b52feb69c0b79249c1c583ad49569881fbde32899a`

| Preview measure | Count |
| --- | ---: |
| Leaderboard source rows | 14 |
| Hall of Fame source rows | 215 |
| Matched normalized names across worksheets | 13 |
| Hall of Fame duplicate rows collapsed | 5 |
| Merged identities | 211 |
| Active | 14 |
| Inactive | 197 |
| Deceased | 0 |

The duplicate warning was reconciled: WhazzupYo/whazzupyo, three Baataya
rows, Akyiro59/akyiro59 and PopocheEldidie/Popocheeldidie have matching
normalized names and matching source channels. The established importer keeps
the strongest record. No custom identity merges were introduced. `gorn_88rtx`
is active-only, adding one identity to the 210 distinct historical identities.

## Confirmed import and verification

- Used the existing `import_legacy_leaderboard` command, previewed against the
  deployed staging configuration, then confirmed once.
- Import audit UUID: `51f3bf12-4f28-4041-b769-0e7a5c90f378`.
- Result: 211 runs, 211 approved import submissions, 14 Active, 197 Inactive,
  no claims and no participant ownership links.
- Verified every imported current/best result's kills, survival days, outposts,
  skills and progress against the preview, including database decimal precision.
  Equal current/best results share one submission as designed; that submission
  retains the Leaderboard source rank.
- Both source-rank ranking builders match the preview's full identity order.
  The public pages show 14 Leaderboard and 211 Hall of Fame identities, with
  exact order matching their existing `weighted_completion` configuration.
  Some Hall of Fame ties differ from preview source-rank ordering because the
  page sorts on progress/kills, while preview also uses further tie-breakers.
  No page configuration was changed.
- Protected-data fingerprints before and after import match for every
  non-legacy registry model, auth roles/membership and administration settings.
  Includes five accounts and password hashes, 19 2.0 runs, 31 submissions,
  evidence and event blocks, primary-channel selections and 75 notifications.
  Streaming accounts/media both contained zero records and remain empty.
- No real participant records were claimed, no test notifications were sent,
  and no external provider operations were performed.

Source files, preview, protected-data digests, import result, provider presence
report, rendered ranking HTML, final readiness response and deployment transcript
are retained at `G:\RatRace_Staging\backups\rehearsal-b580e48-20261024`.
Protected environment contents are retained only in the host backup.

## Remaining work and provider gaps

The dataset is ready for authorized claim and submission testing. Claim approval
or decline, participant progress/death submissions and moderation have not been
rehearsed in this operation. Do not claim real historical identities or send
test notifications without authorization.

Twitch, YouTube, Discord, OpenAI, Steam Web API and SteamCMD username values
remain `STAGING_NOT_CONFIGURED`. Microsoft Graph configuration values are
present; mail delivery was not exercised. No Twitch/YouTube connections exist,
so stored-provider-token decryption checks pass without testing real tokens.
Provider setup and interactive connection approval are prerequisites for those
integration tests; they did not block the CSV rehearsal.

## Twitch configuration follow-up (24 October 2026)

The owner created a separate staging Twitch application and entered its client
credentials through a local elevated prompt. The protected environment was backed
up alongside `staging.env` with the original ACL. Only Twitch client credentials
and its staging callback were set, then the standard staging installer restarted
the same release. No credentials were placed in this document or chat.

Independent verification passed client-credentials token issuance, Twitch token
validation against the configured client ID, and a read-only Helix users request.
The callback is `https://dev.tgsrr.com/account/streaming/twitch/callback/`.
Public readiness remains healthy on `b580e48`, including the worker heartbeat.
There are still zero connected Twitch accounts: interactive participant consent,
the callback exchange and participant media retrieval remain to be exercised.
This supersedes Twitch's unconfigured status above. YouTube setup is next.

## YouTube configuration follow-up (24 October 2026)

The owner supplied the downloaded Web application OAuth JSON through the local
protected prompt. The prompt validated the staging redirect URI, backed up the
environment with its original ACL, updated only the three YouTube settings and
confirmed that other environment values were unchanged. The standard staging
installer restarted the same release. The prompt reported completion, and an
independent public readiness check passed every component on `b580e48`.
This supersedes YouTube's unconfigured status above. Interactive Google consent,
authorization-code exchange and YouTube channel/media access remain unverified.

## YouTube connection verified (24 October 2026)

After the owner added their Google account as an OAuth test user and approved
consent, staging has one connected YouTube channel, Eurymachus. Independent
verification passed encrypted access/refresh credential decryption, refresh-token
exchange, Google identity matching and YouTube channel identity matching. The
existing media refresh flow retrieved/cached 20 eligible videos. The granted
scopes include YouTube read-only access. No tokens were logged.

Legacy run/claim and notification counts remained unchanged. Public readiness
passed all components, including the worker, on `b580e48`. This supersedes the
unverified YouTube connection status above; claim/submission moderation testing
remains outstanding.

## Dashboard and claim workspace deployment (24 October 2026)

- Published and remotely verified commit
  `049f40fc6cfae742cb50bf622cf71353d8230746` on `codex/rat-race-dev`.
- All 28 reset, import, claim and Dashboard regression tests passed after
  rebasing on the previously deployed `b580e48` commit. No migrations added.
- Backed up staging database, protected configuration and persistent filesystem
  trees before cutover at `G:\RatRace_Staging\backups\pre-049f40f-20261024`.
  PostgreSQL custom dump was validated with `pg_restore --list`.
- Used the immutable archive release at
  `G:\RatRace_Staging\releases\049f40f` and the standard elevated
  `Install-RatRaceStagingStartup.ps1` process. Both task actions now use it.
- All deployment checks pass; public liveness/readiness report `049f40f` and
  the matching reference worker. One logical worker process tree remains.
- Before/after digests match for accounts (excluding last-login timestamps),
  provider connections/credentials, 1.0 imports/runs/claims/submissions, 2.0
  runs/submissions and notifications. Counts include 211 legacy runs, one
  claim, two provider connections, 19 2.0 runs and 79 notifications.
- Only `RELEASE_ID` changed in the protected environment. Production untouched.
- Browser tab opened at staging admin; authenticated visual acceptance is
  waiting for the owner to sign in. No claim approval/decline was performed.

## Dashboard layout correction (24 October 2026)

- Deployed remote commit `38b1bc8603bea56ff08e7c2e08ed99271926dcbd`
  through the same immutable staging installer; backup is
  `G:\RatRace_Staging\backups\pre-38b1bc8-20261024`.
- Home is now first in the sidebar across admin pages. Removed duplicate
  navigation from Dashboard content and Django's inherited 600px index width.
- Three focused Dashboard tests pass. An isolated rendered browser preview
  confirmed first-link Home, no duplicate navigation and three columns across
  966px of content at a 1280px viewport. It uses synthetic layout-only data.
- Deployment checks, readiness, matching worker and protected-data/environment
  comparisons pass. No claims or notifications changed. Authenticated live
  browser acceptance still requires owner sign-in in the in-app browser.
