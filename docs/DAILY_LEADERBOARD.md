# TGSRR Daily Leaderboard DEV test

The publisher is disabled by default. Deploy to OSWALD DEV before enabling the schedule.

The existing Unlisted Workshop test item is `3842654789`. Publication is
restricted to that item and staging settings. The separate main mod and
Team Test item are not targets.

The website worker checks a database schedule, defaulting to 09:00
Europe/London. It queues at most once per local date, with current-day catchup
after downtime. Unchanged standings and template files skip the upload.
The snapshot ranks each registered Rat Race 2.0 challenge mode independently
using the website's leaderboard rules. Each racer can place once per mode.
Schema 2 adds the challenge mode key and display name to each row.
The package contains data only; an in-game display remains separate work.

Required protected DEV environment settings:

```text
LEADERBOARD_PUBLISH_ENABLED=true
LEADERBOARD_WORKSHOP_ID=3842654789
LEADERBOARD_STEAM_USERNAME=Eurymachus
LEADERBOARD_PACKAGE_ROOT=<absolute durable directory outside release folders>
STEAMCMD_EXECUTABLE=<host SteamCMD executable>
```

Use host-local Steam authentication under the worker's Windows identity.
Do not copy passwords into Django or commit cached Steam credentials.
DEV already records Eurymachus as the authenticated Reference Source account.
The reference updater, website authentication and leaderboard publisher share
an exclusive lock per SteamCMD installation. Run manual SteamCMD commands only
while those application operations are idle.

After deployment and migration, run with the protected DEV environment:

```text
python manage.py configure_daily_leaderboard --enable --hour 9 --timezone Europe/London --enqueue
```

Superusers can inspect jobs and change the schedule in Django administration.
The admin action queues work; the supervised worker performs uploads.
Disabling the schedule stops future scheduled jobs, but does not cancel a
queued manual job. The environment flag disables all processing.

Every upload explicitly requests Unlisted visibility. Success requires a
Steam upload confirmation and a downloaded package matching all generated
file hashes. Steam output is not persisted because authentication output may
contain sensitive details. Failed snapshot generation never uploads an empty
replacement. A genuinely empty leaderboard is a valid snapshot.

Ambiguous upload outcomes block further jobs pending reconciliation. A worker
interrupted during an upload leaves its job running and also blocks subsequent
jobs. From the release with the protected DEV environment loaded, run:

```text
python manage.py reconcile_daily_leaderboard <job-id>
```

The command checks the retained package against a fresh Workshop download.
A verified match closes the job as published. A recorded interruption before
SteamCMD starts closes as failed before upload. A mismatch keeps the job blocked
for operator review. The command issues no upload.

The two changelist layout failures in the operations suite also reproduce on
the pre-publisher DEV release `782bd5e`.
