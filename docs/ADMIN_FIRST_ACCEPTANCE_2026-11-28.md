# Admin-first staging acceptance, 28 November 2026

## Scope and outcome

Audited rebuilt OSWALD staging release 14f7bb46 against the first live phase in
PRODUCTION_DEPLOYMENT.md. Access/security, game preparation, worker readiness,
scheduled operations and coordinated backup checks passed. Presentation/content
installation is now complete as recorded in the follow-up below. Final public
copy/policy acceptance remains open. This is not approval to deploy or open live.

Live was neither accessed nor changed during this audit. Construction mode and
all intake/publishing switches remain unchanged. The initial audit made no external authentication, email, retention, content
import or permanent synthetic account changes. The subsequently authorized
presentation import is recorded below.

## Evidence checked or refreshed

| Check | Result and limits |
| --- | --- |
| Public construction gate | Ten direct GETs and four POSTs returned construction HTTP 503. Admin redirects to login; password form returns 200. |
| Release switches | Registration, Workshop intake, RR1 intake, RR2 and automated publishing are all off. |
| Admin authorization | Anonymous/regular users redirected; non-superuser staff with provider model permissions receive 403. Superuser access and CSRF protection verified through deployed request-client probes. Synthetic changes rolled back. |
| Roles | All seven groups match current role definitions. |
| Provider configuration | All seven pass offline decryption/origin/structure checks. Forms/history disclose neither plaintext nor ciphertext. This does not prove external provider acceptance. |
| Steam/game preparation | Steam manifest and completed decompile marker match build 26486631. Previously exercised owner Steam Guard, install, decompile and catalogue approval retained as evidence. |
| Catalogue/artwork | Approved catalogue has 5,342 entries and 5,137 images. Artwork launch gate already accepted, including six optional-polish omissions. |
| Runtime | One web and one matching-release worker ready; no active jobs. |
| Clean staging state | One owner, one seeded required Workshop mod, two game-setup notices; no runs, claims, submissions, votes or streaming connections. |
| Scheduled operations | 04:00 backup, 05:00 retention preview and hourly checks recorded success. Timing corroborated by Application events and receipts; Task Scheduler Operational log is disabled. No retention deletion performed. |
| Coordinated backup | 10:37 GMT database/configuration/media backup passed all 5,151 manifest checks; archived keys recover all seven provider records offline. Backup contains both staging schemas. Full restore of this exact new snapshot was not performed. Earlier isolated database/app/worker restore evidence remains separately documented. |
| Repository package | All nine presentation manifest file hashes match. No package import performed. |
| Focused isolated tests | 37 distinct local tests passed: baseline/provider/construction-admin suites (32), presentation round-trip and first-release reviewer restrictions (5). No existing local DB migrated. |

Provider permission probes used Django's request client on staging with CSRF
enforcement and rollback-only synthetic users. GETs covered list/add/change/history
for four roles. Valid-CSRF change POSTs redirected anonymous/regular users and
denied non-superuser staff; missing-CSRF superuser POST was denied. A synthetic
Discord secret replacement succeeded inside the rolled-back transaction.
These are deployed application probes, not a new interactive browser sign-in.

## Original presentation gap, resolved by follow-up installation

The rebuilt environment contains baseline setup defaults, not the full checked-in
presentation package. Counts alone are not editorial approval.

| Content | Staging | Package |
| --- | ---: | ---: |
| Pages | 5 | 8 |
| Navigation entries | 3 | 9 |
| Themes | 3 | 4 |
| Managed images | 0 | 8 |

Missing page slugs are gallery, hall-of-fame and legacy-leaderboard. Gallery is
unpublished in the package; hall-of-fame is RR2-gated. Their absence is a package
parity finding, not a claim that those two pages must open at community launch.
Branding and challenge-mode fields also differ. The package's rules, exploits,
current leaderboard and hall of fame carry explicit RR2 release requirements.

**Original recommendation, now completed for package installation:** review the checked-in presentation package and
required-mod policy for the first community release, then install the accepted
package on staging behind construction mode. Verify assets, navigation, intended
RR1 destinations and RR2 isolation, and capture the accepted package checksum.
Do not automatically replace content merely to equalize row counts.

## What remains before each boundary

### Admin-first live deployment

- Presentation/package technical installation checks passed on staging.
  Confirm required-mod policy and final owner editorial acceptance separately.
- Select the accepted immutable application and content package.
- Owner separately authorizes the live admin-first installation. Provision live
  host keys and provider records for the live origin, never copy staging keys
  or database records. Public construction remains in place.
- Repeat environment-specific admin, provider configuration, game setup and
  coordinated recovery checks on that installation before calling live admin-ready.

### Public opening

- Complete real integration acceptance: email verification/reset delivery,
  Turnstile and the intended OAuth/provider paths. Earlier Twitch/Discord
  successes predate the clean rebuild; seven offline-valid records do not prove
  all seven services work. Stage controlled tests without sending unsolicited mail.
- Approve public copy/navigation and required-mod policy; confirm reviewer
  responsibility and repeat any outstanding normal-user/browser checks.
- Public opening remains a separate owner-authorized switch change.
- RR1 import/claim/update acceptance already has prior browser and automated
  evidence. The final spreadsheet handover, current source snapshots and live
  totals are separate; do not repeat destructive rehearsals or import test runs.
- RR2 remains disabled pending its own contract/activation gates.

Off-host backup remains a future improvement with owner-accepted host-loss risk.
The six optional object images and hidden overlays do not reopen artwork gating.

## Presentation package review follow-up (28 November 2026)

The owner authorized installation on staging behind the construction page.
Local review verified all nine manifest hashes and decoded and visually inspected
all eight managed images: the rat logo, outpost map, Project Zomboid banner,
rules poster and four fence examples. Five isolated presentation round-trip and
first-release reviewer tests passed again.

Reviewed package checksum:
`1cf40ba67459f4c537154cbce493c00da5b74f0ac13179bf5df9a0fd029029bf`.
RR1 leaderboard and hall-of-fame copy correctly describes the original challenge
as still running. RR2 rules, exploits, leaderboard and hall of fame remain gated;
gallery remains unpublished. Homepage cards use the release-aware destination
filter, including registration and RR2 links. The package importer transaction
replaces editorial pages, navigation, themes and exploit rulings, and updates
branding and challenge modes. It does not import provider credentials or the
required Workshop mod policy.

The authenticated staging admin and public construction page were observed in
the in-app browser during review. This is not a browser layout check of the
underlying public pages while construction is enabled.

### Staging installation result

Installed on 28 November 2026 after a verified protected pre-import backup.
All nine hashes passed on OSWALD. The declared content fields and navigation
structure match the package: 8 pages, 9 navigation entries, 4 themes and 8 images.

Deployed application request-client checks used a maintenance override confined
to that test process. Both RR1 rankings and the Mods catalogue rendered, RR2
routes remained blocked, and gallery remained unpublished. The anonymous home
page had no broken internal links and exposed neither Rules nor the RR2
Leaderboard card. All eight managed image URLs served the expected bytes.
These checks do not claim desktop/mobile screenshot acceptance of public pages.

All 81 non-editorial tables, the 5,137 existing media files and protected
environment were unchanged. External public requests still receive construction;
admin login returns HTTP 200. Staging remains on release 14f7bb46 with one web
and one worker ready. Live was not accessed or changed.

Import validation initially attempted to create a default Website Settings row.
That attempt was rolled back; the successful import used the same default image
limit within the process without persisting the additional settings row. Future
fresh-install automation should account for this validation side effect.

Next is controlled real email verification/reset and intended provider acceptance.
Final copy, required-mod policy, reviewer ownership and public opening authorization
remain separate from this technical package installation. No RR1 data import or
RR2 activation was performed.
