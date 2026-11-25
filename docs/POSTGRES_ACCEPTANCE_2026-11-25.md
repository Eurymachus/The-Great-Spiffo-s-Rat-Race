# Isolated PostgreSQL candidate acceptance, 25 November 2026

Tested application candidate: `c9b7fead1d37743af9b26b7aa4ef9cc0170f46f8`
on `codex/rat-race-dev`. Source was committed and pushed to the existing Git
origin, fetched on OSWALD and archived into a fresh test directory. No source
overlay was sent through chat. Original OSWALD checkout stayed at `f079ead`;
neither deployed release changed. Local unrelated IDEAS edits were excluded.

## Verified results

- PostgreSQL 18.4: all **442 scoped application tests passed, zero skips**.
- Both concurrency cases ran and passed: atomic shared rate-limit increments,
  and simultaneous RR 1 claims for different runs by one participant.
- The suite includes fresh migrations/seed/role/static checks and a synthetic
  populated retention-upgrade test preserving account password and RR 1 ownership.
- All **14 artifact/logging tests passed**. A real Windows child-process fixture
  produced sealed log segments with restrictive ACLs and preserved exit behavior.
- The earlier real synthetic PostgreSQL capture with the same capture code
  generated a custom dump, validated catalogue, protected configuration/media
  copies and completion manifest; transient password file was absent afterward.
- A separate clone of the retained live dump upgraded successfully: all **129**
  existing migration entries survived and **61** newer migrations applied.
  The migration-seeded Workshop row retained its identity and ruling. Accounts,
  RR 1/RR 2 data and Workshop votes remained zero. No presentation seed was
  reimported into this populated schema.
- Temporary PostgreSQL shut down; its PID file and loopback port **55433**
  listener were verified absent. No existing services/tasks/data were changed.

The initial workspace interpreter lacked `django_countries`. A dedicated test
venv was created from the candidate's requirements, without modifying the
workspace/live/staging interpreters. The first complete PostgreSQL run exposed
two test-fixture defects: the snapshot test incorrectly used TestCase's outer
transaction, and a checksum fixture generated 128 characters. They were fixed
using TransactionTestCase and a 64-character hex fixture respectively; no
application behavior was changed to hide the failures. The complete suite then
passed on the corrected commit above.

## Host evidence

OSWALD audit chat: `01a2139d-010f-7bf2-8277-5ac2e96d3fc8`.
Evidence root:
`C:\Users\admin\Projects\RatRace\.codex-runtime\candidate-c9b7fead-20261125-192755`.

- `pg\tests.stderr`: full application test output.
- `host-tests.log`: operational tests.
- `pg\upgrade-receipt.txt`: clone-upgrade comparison.

These are host-local paths, not files in the development checkout. Retain them
for review. The 442-test suite is the scoped launch suite, not every repository
test; deferred RR 2 public-statistics presentation expectations remain excluded.

## Remaining launch gates

This is isolated source/database acceptance, not a staging deployment or launch
sign-off. The construction-site clone contains no real users or credentials,
so it does not prove migration of representative provider credentials or a full
RR 1 handover. The synthetic preservation/concurrency tests narrow those gaps
but do not replace the documented hosted journeys.

Still required before intake opens: approved presentation/seed and immutable
deployment candidate; candidate staging/provider journeys; moderation ownership
and final privacy review; recurring maintenance/backup monitoring and expiry;
existing-log classification; coordinated database/media/configuration recovery
and off-host storage; restart/reboot proof; and the reconciled RR 1 source handover
before RR 1 intake. Existing data resets and deployments still require the
owner's separate execution instruction. RR 2 contract/statistics work remains
deferred behind its disabled switch.
