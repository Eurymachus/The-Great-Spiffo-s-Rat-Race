# Fresh-install migration baseline

## Decision, 27 November 2026

The owner approved consolidating the pre-launch migration history without an
upgrade path for existing local development or staging databases. Live is not
changed by this work. Its first admin-first installation will use a fresh
application database under a separately executed deployment.

The baseline contains eight schema migrations across six project apps and one
final setup-data migration. Django and third-party migrations remain supported
dependencies. This replaces 174 project migration files, not the database engine
or operating system. Future RR2 export-contract changes are ordinary incremental
migrations which must preserve the configuration and data accumulated after this
baseline. Consolidation does not finalise or remove current RR2 contract code.

`manage.py migrate` rejects recorded pre-launch project migration history before
applying operations. Do not use `--fake`, erase migration records, or point the
new release at an old database. Old migration source remains in Git history.

## Setup data provenance

The frozen `administration/migrations/data/launch_seed.json` contains 226 records
obtained by migrating an empty disposable database with the previous migration
chain. It contains no host database export, credentials, participants, claims,
challenge runs, submissions, notifications or operational history. It records
the final setup state directly instead of replaying successive content rewrites.

| Setup model | Records |
| --- | ---: |
| Website themes / site branding | 3 / 1 |
| Reference source / run-data danger-zone settings | 1 / 1 |
| Code-managed pages / managed pages / navigation items | 7 / 5 / 3 |
| Page sections / blocks / section items | 9 / 58 / 3 |
| Required Workshop mod / exploit rulings / challenge modes | 1 / 6 / 3 |
| Run / participant / Workshop / RR1 saved views | 4 / 4 / 4 / 5 |
| Geography catalogue entries / versions / buildings | 34 / 34 / 40 |

These are existing application defaults, not an approval of all public launch
copy. Review the presentation package, required-mod policy and RR2-gated copy
before public opening. RR1 source CSVs remain a separate post-install import.
Geography seed records are not a substitute for the Steam catalogue import.
Provider configuration and the initial superuser are deliberately absent.

Seed insertion uses historical migration models, resets database sequences after
explicit IDs, and finishes after all project schema dependencies. Normal repeat
`migrate` does not replay or overwrite seeded content. `bootstrap_roles` remains
the repeatable deployment step for roles and permissions. Code-page registration
continues through the existing post-migrate hook.

## Credentials and reset boundary

Before resetting either environment, retain a restricted recovery bundle outside
Git containing its database, environment, provider encryption key ring, token
encryption key and required host/Steam session configuration. Verify that the
archived keys decrypt archived provider records. A database dump without its
keys is insufficient. Do not print values into transcripts or test reports.

OSWALD preservation on 27 November passed 9,595 backup manifest checks. The
archived protected environment matched staging byte for byte, and its key
decrypted all seven archived provider configurations offline. The SteamCMD
session was separately copied with restricted access and a matching hash.
Steam authentication and reprovisioning into a fresh baseline were not exercised
by that preservation check. Local environment and database recovery copies are
under restricted, Git-ignored temporary storage; originals remain intact.

Use an explicitly identified empty application database for installation. Keep
the recovery database/bundle available until credential recovery and installation
acceptance finish. Do not delete host services, backups, tool installations or
credentials as part of resetting application data. Do not copy the old database
back over the new schema to recover provider configuration.

## Installation acceptance

1. Confirm the environment identity, preserved credentials and empty database.
2. Select the immutable release and install its dependencies.
3. Keep public construction mode enabled and participant intake/RR2 disabled.
4. Run migrations, role bootstrap and static collection using the deployment
   preparation script. Repeat preparation to verify it is safe to rerun.
5. Create the first superuser and verify admin access and the public construction
   page. Configure providers through admin using the preserved recovery material.
6. Prepare Steam, decompile and import the game reference through the supported
   administration workflow. Verify readiness and backup recovery.
7. Import RR1 separately when ready for handover. Public opening remains a
   separate decision after administration-side acceptance.

## Verification of candidate 4378ceec

- Fresh SQLite installation and a second migration pass succeeded with no model
  drift. All 95 database tables matched the previous empty installation's columns
  and constraints. The initial focused regression run passed 88 tests, followed
  by four baseline-specific tests.
- Full local suite: 721 tests in 159.657 seconds, 714 passed, three skipped and
  four failures. The same four failures reproduced using the archived original
  migration chain in a separate empty test database with unchanged application
  code. This is not a fully green suite; no new baseline regression was found.
  Initial sandbox attempts stalled in Windows asyncio socket-pair creation;
  the completed run had local loopback access. Interrupted attempts are not
  counted as passes.
- Existing failing assertions: branding administrator inactive-theme deletion,
  Challenge Runs changelist layout, submission changelist title/clickable rows,
  and the public run page's older `Back to RatRacer` expectation. These need
  separate reconciliation against current intended UI/permissions.
- OSWALD isolated PostgreSQL 18.4 on loopback port 55441: fresh/repeat migration,
  repeated role bootstrap, sequence-backed insert and no model drift passed.
  Final database had 95 tables and 27 applied migrations (nine project migrations
  plus framework dependencies). All 197 focused tests passed.
- Request-client admin-first smoke: public construction response HTTP 503,
  synthetic superuser could access admin. This was not hosted browser acceptance.
- All seven backed-up provider records were inserted as ciphertext in the fresh
  schema and decrypted offline with the matching archived key. Probe rows were
  rolled back, no provider network calls occurred. The isolated cluster stopped;
  no listener or PID file remained.
- Existing staging stayed on `570ca253`, RR1 intake on and RR2 off. Live stayed
  on `6582cc4`. No existing database reset or baseline cutover was performed.
