# Live backup and isolated restore rehearsal

## Executed coordinated staging restore, 26 November 2026

The owner authorized an isolated restore of the existing staging package.
OSWALD restored it into a new protected destination on PostgreSQL 18.4,
`127.0.0.1:55434`, database `staging_restore_rehearsal`. The rehearsal took
71 seconds, starting at 23:35:08 GMT. This is snapshot recovery evidence,
not a full application recovery-time target or launch approval.

- Source: `G:\RatRace_Staging\backups\backup-20261125T194208Z-dfa0f023`.
  This is the coordinated paused-writer capture from 25 November, release
  `f079ead`; it predates later staging migrations and interactive test records.
- New destination: `G:\RatRace_Staging_Restore_20261126-233508`.
  Non-secret evidence is in `receipt.txt` and `package-verification.txt` there.
- All 9,595 manifest entries matched source before/after and restored copy,
  including 9,572 media files, zero private files, the dump and protected config.
  Protected configuration matched byte-for-byte and remained inert. Destination
  ACLs were restricted, including the copied configuration.
- All 806 archive catalogue entries and 171 migration records matched.
  Restored baseline counts included 5 accounts, 211 RR 1 runs, 211 RR 1
  submissions, 31 RR 2 submissions and 2 Workshop records. No unvalidated
  constraints were found. Three streaming-account rows were restored.
- No application, mail, provider integration, worker or scheduler was started
  against the restored data. Original database ownership/grants and credential
  decryption were not tested. Restored rows alone do not prove usable tokens.
- The temporary cluster was stopped; its process and listener were verified
  absent. Artifacts were retained. No wipes, deletions or deployments occurred.
- Staging `80b4309` and live `6582cc4` remained ready before and after;
  existing services and tasks were unchanged.

This closes the isolated database/files/configuration restore gap for this
specific staging snapshot. Off-host recovery is a future improvement under the
owner's accepted host-loss risk. Credential decryption, original
ownership/grants, monitored recurring captures, accepted data-loss/recovery-time
targets and retention scheduling remain open. A restore of this older snapshot
cannot preserve writes accepted after capture; a real recovery needs explicit
reconciliation of later submissions, deletions and redactions.

## Executed file recovery result, 25 November 2026

OSWALD separately copied and restored live media/private/configuration to NEW
restricted directories. All 43 media files matched SHA-256 across source before
and after capture, backup and restored copy. Private avatar/reference/decompiled
directory structures matched, with zero files. Protected `acceptance.env`
matched byte-for-byte; both required key settings were present. Capture and
restore directories passed ACL checks. No app/provider used the copied config.

- Capture manifest: `G:\RatRace\backups\files-rehearsal-20261125-190240\file-manifest.txt`.
- Restore receipt: `G:\RatRace_File_Restore_20261125-190240\receipt.txt`.
- All three worker queues were empty before/after. This supports file stability,
  not a guarantee of an atomic cross-store snapshot.
- Live had zero streaming-account rows; real credential decryption is untested.
- Nine operational logs were inventoried separately and excluded from capture.
- Both environments still reported ready on their original releases. Only new
  restricted artifacts were created; existing application state was unchanged.

This file capture and the earlier database dump are separate recovery proofs.
These separate live captures do not establish a coordinated live rollback point.
The later coordinated staging restore is documented above.
Recurring backup, 30-day backup expiry and 90-day routine-log expiry remain open.

## Executed database-only result, 25 November 2026

OSWALD completed a fresh PostgreSQL 18.4 custom-format live dump and isolated
restore after the owner continued the work. Live and staging application data,
configuration, services and tasks were not changed. Only new restricted backup
and rehearsal artifacts were created. This is database-only recovery evidence,
not a coordinated media/configuration recovery point or candidate deployment.

- Dump: `G:\RatRace\backups\db-rehearsal-20261125-185122\database.dump`,
  232,310 bytes, catalogue validated (`archive-toc.txt` alongside).
- SHA-256: `3FF8224B7F1B56B19A93415305D909561CBBF9330140E7D13BE2101E2B5A8FBC`.
- New capture/initial rehearsal directories had inheritance disabled and access
  restricted to SYSTEM, Administrators and `OSWALD\admin`. The retry used the
  same restricted-storage requirement and a fresh target.
- Initial `G:\RatRace_Restore_Rehearsal` started on loopback port 55432, but
  inherited launcher output kept the command blocked. Only that new cluster
  was stopped; its PID file/listener disappearance was verified. Files retained.
- Successful retry: `G:\RatRace_Restore_Rehearsal_20261125-185423`.
  Redirecting launcher output to files resolved the hang. Non-secret receipt:
  `G:\RatRace_Restore_Rehearsal_20261125-185423\receipt.txt`.
- Restore matched all 129 migration records, audited aggregate counts and the
  seeded Workshop row fingerprint. Accounts, RR 1 runs/claims/submissions,
  RR 2 submissions and Workshop votes were zero. Source pre/post capture checks
  matched for those audited records; this is not a claim of full-table equality
  for changing runtime heartbeat state.
- The successful temporary cluster was stopped. Process, PID file and port
  55432 listener were verified absent. Both attempt directories and dump remain.
- Media, protected configuration, credential decryption, original database
  ownership/grants, off-host recovery and new candidate migrations were not tested.

The preparation below is retained as the plan and historical baseline. Its
unexecuted statements are superseded only for the database-only scope above.
Never reuse either existing rehearsal directory as an empty target or delete it
without a separately reviewed cleanup scope.

Baseline clarification: the single live Workshop row referenced below is the
required challenge-mod catalogue entry seeded by `0024_workshop_mods` (Workshop
ID `3554864233`). It is not a user submission. Live has zero accounts, participant
Workshop submissions, pending requests and votes. Restore comparisons may use
the seed row as an integrity check, not as proof that real intake has occurred.

Prepared 25 November 2026 from OSWALD inventory chat
`01a2139d-010f-7bf2-8277-5ac2e96d3fc8`. Original plan follows; see the executed
database-only result above for the later bounded backup/restore work.

## Verified preparation

Later elevation check resolved task visibility: the owner launched the actual
desktop executable elevated with `--do-not-de-elevate`. Desktop/backend and
approved unsandboxed commands retained High integrity, while sandboxed commands
remained restricted. All four tasks are enabled/running as SYSTEM, with 30-second
boot delay and 999 one-minute restart attempts. Live targets `6582cc4` (also an
enabled time trigger); staging targets `f079ead`. Actual restart/reboot recovery
and recurring backup/retention scheduling remain untested. This supersedes the
earlier task Access denied observation below.

- Live PostgreSQL 18.4: `127.0.0.1:5432`, database `ratrace`, service
  `RatRacePostgres`, data directory `G:\RatRace\postgres\data`.
  Staging uses `5433`, `RatRaceStagingPostgres` and
  `G:\RatRace_Staging\postgres\data`. Neither is a restore destination.
- Both installations have 18.4 `pg_dump` and `pg_restore`.
- Live database: 13.2 MB; media: 7.0 MB, 43 files. Staging database: 41.0 MB;
  media: 10.2 MB, 9,572 files. Both private avatar directories had zero files.
  G: had 283.8 GB free; C: had 56.8 GB free. Reference/decompiled data size
  and required log scope remain unmeasured.
- The live environment file explicitly grants SYSTEM, Administrators and
  `OSWALD\admin` access. Application secret and token encryption key are configured.
  Parent config/private/backups directories inherit broader local Users access.
  New capture and rehearsal roots need restrictive ACLs before copying data.
- Direct queries for all four expected web/worker tasks returned Access denied
  in the medium-integrity session. Installer source defines SYSTEM startup tasks,
  a 30-second delay and one-minute failure retries. Installed task definitions
  still need elevated read-only verification. Do not classify them as missing.
- No recurring live backup/pruning job is verified. Rolling backup retention
  policy is 30 days. This rehearsal does not authorize deleting old backups.

## Proposed destinations

### Elevated follow-up findings

The later elevated audit found no Rat Race scheduled task or service for recurring
database capture, 30-day backup expiry or 90-day log expiry. External or indirectly
named facilities remain possible, so this is not proof that no backup exists.
Live web/worker tasks also repeat every minute indefinitely from 18 October,
with `IgnoreNew`. Their origin was not established from the release installer.
Any future stop plan must prevent these triggers from relaunching writers;
no task changes are part of the present preparation.

Verified live tools are `G:\RatRace\postgres\runtime\pgsql\bin\pg_dump.exe`
and `pg_restore.exe`, version 18.4. Media totals 6,975,803 bytes in 43 files;
logs total 20,403 bytes in nine files. No files were observed at configured
`G:\RatRace\private\avatars`, `G:\RatRace\reference` or `G:\RatRace\decompiled`.
Database credentials are present in protected `config\acceptance.env` and can
be supplied to the child process without command-line disclosure. Do not echo
the file or persist credentials in a generated runner or report.

Maintenance exempts loopback requests. The worker writes heartbeats and can
claim reference, catalogue and artwork jobs. All three queues were empty at
inspection. Heartbeats alone do not invalidate a PostgreSQL snapshot, but an
empty queue is not a guarantee that file-changing jobs will remain absent.

Proposed bounded capture: retain maintenance, agree no loopback admin requests,
direct data edits, job submissions or media/config changes for the duration;
recheck queues, and compare file/config manifests across capture. Stop and
classify the result as database-only if cross-store consistency cannot be
established. Manifest equality is supporting evidence, not a substitute for
controlling writers. No service stop is required merely for heartbeat writes.
The restore root and port were rechecked unused; repeat checks at execution.

Capture into a new timestamped child under `G:\RatRace\backups`, protected before
data is written. Keep protected configuration out of ordinary report artifacts.
A same-volume backup supports rehearsal but not recovery from host/disk loss;
an independently protected off-host copy is a future improvement. The owner
accepted local-only host/storage-loss risk on 26 November.

Restore into a separate cluster rooted at `G:\RatRace_Restore_Rehearsal`, database
`ratrace_restore_rehearsal`, on loopback `127.0.0.1:55432`. The directory was absent,
the database name unused on both existing clusters, and the port unused/not
IPv4-excluded when checked. Recheck immediately before execution, including
resolved paths/reparse points. Fail if the root exists, never wipe or reuse it.
Use separate credentials and no new service or startup task.

## Reviewed sequence, not executed

1. Record the exact capture ID, source database identity, running release,
   executable paths and versions. Verify destination permissions and space.
2. Establish a consistent capture window. Maintenance mode does not hold worker
   or administrator writes. Identify all writers and coordinate a write hold
   or supported snapshot covering DB/media/private/configuration state before
   declaring a coherent rollback point. A service stop is not assumed authorized.
   A PostgreSQL dump alone is internally consistent; an independent file copy
   is not automatically consistent with that database snapshot.
3. Use verified PostgreSQL 18.4 `pg_dump` with custom format and explicit source
   host `127.0.0.1`, port `5432`, database `ratrace`. Supply credentials securely,
   never in logged command arguments. Record return code, timestamps and hash.
   Do not substitute a copy of the running PostgreSQL data directory.
4. Capture media/private files and matching protected configuration/keys with
   manifests and ACL evidence. Record release/dependency versions. Scope reference
   outputs and required logs explicitly. Keep SteamCMD session secrets outside
   ordinary application backups. Never publish secret values or file contents.
5. Initialize only the new independent cluster, bind it to loopback, and inspect
   the dump catalogue. Restore into its empty database with explicit port `55432`
   and `pg_restore --exit-on-error --single-transaction --no-owner --no-privileges`.
   Use a role capable of restoring the archive. These flags intentionally do not
   reproduce production grants/ownership; verify those separately before claiming
   full production recovery. Never use drop/clean against an existing cluster.
6. Keep application, workers, public tunnel and outbound integrations disconnected.
   Verify SQL/files first. Do not load the unchanged live environment file into
   an app: it still points to live database/storage/providers. Later app testing
   requires separately reviewed isolated configuration and suppressed integrations.
7. Compare migration ledger and aggregate counts with the captured baseline.
   Privately compare the live Workshop row's key and full row fingerprint and
   report only pass/fail. Current live baseline is one Workshop record and zero
   accounts/RR 1/RR 2 submissions. Reconcile at capture time; independent counts
   taken during writes are not a reliable snapshot baseline.
8. Verify media/private manifests, permissions and key preservation. Distinguish
   key presence from a successful safe offline decrypt test, and record whether
   encrypted records existed. Before any restored data returns to live, reconcile
   later deletions/redactions and accepted writes so recovery neither resurrects
   removed identities nor silently discards newer submissions.
9. Record a non-secret receipt: versions, times, hashes, restore/comparison results,
   duration and gaps. Leave cleanup/pruning separately scoped. Successful restore
   is not deployment approval or proof of candidate migration preservation.

Do not invoke the inspected staging deployment helper simply to make its backup:
it also changes configuration and replaces tasks. No standalone complete live
backup/restore runner has been verified. Exact executable paths, credential
mechanism, capture window and reference/log scope remain execution preconditions.

Accept the rehearsal only after a fresh archive restores without errors into the
independent cluster, data/file baselines match and secrets remain protected.
Then separately test the immutable candidate's populated upgrade and PostgreSQL
concurrency behavior. Fresh-install testing and RR 1 handover remain distinct.

## Isolated ownership and credential verification, 27 November 2026

OSWALD restored a verified staging backup from release `39a358b9` into a new
protected environment at `G:\RatRace_Staging_AccessRestore_20261127-180339`,
using an isolated PostgreSQL cluster on loopback port 55437. Archive ownership
and privileges were enabled during restore, rather than bypassed with
`--no-owner` or `--no-privileges`.

- Owners and ACLs matched current staging across 520 public relations, indexes
  and sequences; the public schema also matched. This is comparison with current
  staging metadata, not proof that cluster-role definitions were backed up.
- The archive had no explicit ACL or default-privilege entries. The rehearsal
  reconstructed the database owner and used a NOLOGIN application role.
- Under that role, 94 tables had CRUD privileges and 81 sequences were usable.
  Representative reads and writes passed; the test insert was rolled back.
- All three access tokens and three refresh tokens decrypted offline in memory
  with the backed-up encryption key. No plaintext credentials were printed or
  saved, and no providers were contacted. Decryption does not prove that tokens
  remain valid with their providers.
- The isolated cluster was stopped and its listener verified gone. Protected
  artifacts and `verification.txt` were retained. Staging and live remained
  ready on their original releases; no application deployment was performed.

Remaining recovery limits: cluster roles, passwords and memberships are outside
this database archive. Reconstructing a NOLOGIN role and testing its privileges
is not a restored application-login test. Document and rehearse login-role
provisioning and full isolated application recovery before claiming complete
recovery. No email, provider refresh or public application exposure is needed
for those checks. Off-host protection remains an accepted future improvement.

## Isolated application login recovery, 27 November 2026

Successful receipt:
`G:\RatRace_Staging_LoginRestore_20261127-180801\verification.txt`.
The isolated cluster used loopback port 55438 and matching `39a358b9` code.

The rehearsal recreated the database owner and a non-superuser LOGIN role
separately from the archive, with a fresh private SCRAM password. Archive
ownership and grants were retained. PostgreSQL rejected an incorrect password,
and Django successfully authenticated over TCP using the isolated credential.
This proves explicit role provisioning, not recovery of original role passwords
or memberships from the backup. Keep provisioning as a separate recovery step.

Django verified 190 consistent migration records with none pending. In-process
requests to `/`, `/mods/` and `/health/live/` returned HTTP 200; the Workshop page
contained the restored required mod. A sequence-backed insert succeeded inside
an isolated transaction, was rolled back and was verified absent afterward.

The initial smoke setup omitted the restored branding files. A fresh retry
verified and restored all 9,572 media files before rendering the pages; that
successful run took 43 seconds. This is a bounded rehearsal duration, not an
end-to-end recovery-time commitment. Restore the database, protected configuration
and media together before attempting application page verification.

The isolated cluster was stopped and its listener verified gone. No provider,
email, worker or public web service ran. Staging and live remained ready and
unchanged; artifacts were retained. Worker-dependent readiness and complete
service recovery remain outside this check, as does provider-side token validity.
