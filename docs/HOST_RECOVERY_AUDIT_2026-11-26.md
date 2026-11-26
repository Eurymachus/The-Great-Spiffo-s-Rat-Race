# Read-only host recovery and retention audit

26 November 2026, approximately 23:30 GMT. Source: OSWALD audit thread
`01a2139d-010f-7bf2-8277-5ac2e96d3fc8`. Staging release `80b43093`;
live construction release `6582cc4`. No restores, deployments, restarts,
task changes, new captures, deletions or data changes were performed.
No new retention previews were run. Existing receipts were inspected.

## Verified evidence

| Area | Observed state | Limit of evidence |
| --- | --- | --- |
| Scheduled operations | Four Rat Race web/worker tasks enabled and running as SYSTEM, startup triggers and additional one-minute triggers on live | These supervise services; their results do not prove backup or retention execution |
| Recurring maintenance | No matching Rat Race backup/retention task or service found | External or indirectly named facilities are not ruled out; none verified |
| Live database recovery | 25 November 18:51 capture and isolated restore matched 129 migrations and the seeded Workshop row | Construction database had no participant intake; database-only proof |
| Live file recovery | Separate 25 November 19:02 capture/restore matched 43 media files and protected configuration | Not a coordinated database/files restore; real provider credential recovery untested |
| Staging backup | Complete protected package at 25 November 19:43, about 28 hours old; PostgreSQL, config, media and private files; paused writers, archive catalogue and file checks passed | No isolated restore receipt for this package; newer deployment receipts/config copies are not newer full backups |
| Artifact retention | Staging tooling supports 30-day marked-backup and 90-day sealed-log expiry | No recurring execution verified; only 2 of 63 routine-log segments sealed |
| Application retention | Prior staging preview deleted nothing; implementation exists | No recurring account/evidence/runtime retention execution verified; no new preview in this audit |
| Off-host recovery | Verified artifacts and receipts are on OSWALD | No independent off-host copy or restore evidence found |

Host-local evidence paths:

- `G:\RatRace\backups\db-rehearsal-20261125-185122\database.dump`
- `G:\RatRace_Restore_Rehearsal_20261125-185423\receipt.txt`
- `G:\RatRace_File_Restore_20261125-190240\receipt.txt`
- `G:\RatRace_Staging\backups\backup-20261125T194208Z-dfa0f023\artifact.json`

## Authorized restore follow-up

After this read-only audit, the owner separately authorized the isolated staging
restore. It passed at 23:35 GMT in 71 seconds. All 9,595 manifest entries,
806 archive entries, 171 migrations and audited baseline counts matched.
The new cluster on loopback port 55434 was stopped and artifacts retained.
See [the restore receipt summary](BACKUP_RESTORE_REHEARSAL.md) for scope,
destination and limitations. Staging and live were unchanged. The table above
records the earlier audit state, before this restore was performed.

## Still required before launch

1. Complete remaining recovery coverage: original database ownership/grants,
   safe offline credential decryption and application recovery verification.
   The coordinated staging snapshot restore has passed, but its older contents
   cannot prove preservation of test records or migrations created afterward.
2. Off-host copies and recovery are a future improvement, not a launch gate.
   The owner accepted host/storage-loss risk on 26 November. No off-host
   transfer is authorized or claimed; local protection cannot survive that loss.
3. Define and accept recurring coordinated capture, service identity, schedule,
   single-instance behaviour and failure/stale-backup alerts. Verify an actual
   successful scheduled capture, not merely task installation. Agree acceptable
   data-loss and recovery-time targets and check them against the schedule.
4. Investigate the unsealed log segments. Distinguish active segments from
   interrupted historical segments and holds. Do not seal, adopt or delete them
   solely to make expiry run. Separately classify legacy and PostgreSQL logs.
5. Review current count-only account/evidence/runtime and artifact previews,
   preserving active-run evidence and holds. Then separately authorize scheduling
   and apply behaviour for the approved 30-day backup/90-day routine-log policy.
   Record monitoring and failure handling, including incomplete backup packages.

Next authorized action: automatic local staging backups with failure and
staleness checks. No expiry is authorized. Live stays unchanged; RR 2
restructuring is deferred. Off-host recovery remains a future improvement.
