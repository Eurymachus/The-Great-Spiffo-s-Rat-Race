# TGSRR Daily Leaderboard DEV test

Work in progress, not deployed or enabled on OSWALD.

The existing Unlisted Workshop test item is `3842654789`. Publication is
restricted to that item and staging settings. The separate main mod and
Team Test item are not targets.

The website worker checks a database schedule, defaulting to 09:00
Europe/London. It queues at most once per local date, with current-day catchup
after downtime. Unchanged standings and template files skip the upload.
The source currently uses the website's current Rat Race 2.0 leaderboard.
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
The worker needs exclusive operational access to its SteamCMD installation;
do not run interactive Steam authentication or manual SteamCMD commands while
a publication is running.

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
jobs. Host-side reconciliation tooling and deployment verification remain
unfinished. Do not enable the schedule until those checks are complete.

Local validation so far: eight publisher tests pass. The broader operations
run has two failures in existing changelist layout assertions, which still
need baseline investigation before release.
