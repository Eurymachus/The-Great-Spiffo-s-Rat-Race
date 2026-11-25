# Staging rehearsal, 25 November 2026

The owner authorized staging rehearsal after isolated PostgreSQL acceptance.
OSWALD deployed `f88086ed6b9dd13bb067c92b584df0f11196c8e8` to
`G:\RatRace_Staging\releases\f88086e`. Its application code matches tested
candidate `c9b7fead`; the intervening commit changes documentation only.
Live remains `6582cc4` behind its construction page (HTTP 503).

## Rollback capture and preservation

Staging web and worker writers were paused before capture and migration.
Worker queues were idle and no other staging database clients were observed.
Task Scheduler initially left child processes running; their staging scope was
verified before stopping the remaining processes. Live processes were untouched.

Protected rollback package on OSWALD:
`G:\RatRace_Staging\backups\backup-20261125T194208Z-dfa0f023`.
It contains PostgreSQL, configuration, media and private files. Archive catalogue
and file checks passed. Reference/decompiled data were outside the capture and
untouched by the cutover. This is a coordinated paused-writer capture for the
included stores, not proof of off-host recovery or a full restore of this package.

Audited before/after migration counts matched:

| Data | Count |
| --- | ---: |
| Accounts | 5 |
| RR 1 runs | 211 |
| RR 1 claims | 2 |
| RR 1 submissions | 211 |
| RR 2 submissions | 31 |
| Workshop catalogue records | 2 |
| Workshop votes | 0 |

## Initial acceptance

- Registration and Workshop requests enabled; signup, sign-in and catalogue
  returned HTTP 200.
- RR 1 intake and RR 2 disabled; checked intake routes returned HTTP 403.
- Outbound staging mail and leaderboard publishing disabled for rehearsal.
- Readiness, matching worker heartbeat, one logical web/worker tree each, and
  a production CSS asset passed.
- Retention preview identified 18 expired rate-limit buckets and deleted nothing.
- Independent in-app browser check confirmed home, signup age gate, RR 1-only
  rankings navigation, Workshop catalogue and anonymous submission sign-in modal.
  No browser form was submitted and no account was changed by that browser check.
- Workshop initially lacked a visible menu link: Mods was beneath the RR 2-gated
  Rules item. The existing staging item moved from parent 5/position 0 to the
  top level/position 11, preserving its destination and label. Independent
  browser verification confirmed the link. The install package now matches this
  arrangement, with its manifest updated and fresh-install coverage verifying
  the visible link while RR 2 is off.

## Signed-in acceptance and restart

A labelled synthetic account authenticated, submitted a pending Workshop request
using a mocked Steam lookup, and downloaded its own data including that request.
Anonymous submission redirected to sign-in; the participant was denied Workshop
administration. The verified account was created directly, so this check does
not prove registration verification or real Steam lookup. Fixtures were retained:
accounts increased from 5 to 6 and Workshop records from 2 to 3.

Both staging process trees restarted with new PIDs. Readiness and the matching
worker heartbeat recovered, with exactly one logical web and worker tree each.
Old log segments remained protected but unsealed after stopping, making them
ineligible for automatic expiry. Host reboot was not tested.

Protected evidence on OSWALD under
`G:\RatRace_Staging\backups\acceptance-receipt-20261125-194620`:
`journeys-retry.txt`, `restart.txt` and `navigation.txt`.

## Email acceptance window

The owner approved a single test recipient. Staging mail is enabled only for
that exact allowlist, with `STAGING_EMAIL_ALLOW_ALL=false`. A mocked-transport
backend check confirmed that unapproved recipients are blocked before Graph.
No real message has been sent by this check. The approved address has no account;
the owner must complete signup, receive/activate verification, then request and
complete password reset. Keep tokens and credentials out of receipts. Disable
the test mail window after acceptance. Publishing, RR 1 intake and RR 2 stay off.

## Modal follow-up

The owner reported an oversized anonymous Workshop submission dialog. The
signed-out dialog now uses content height and a narrower width instead of the
full form's minimum height, with Sign In first and responsive stacked actions.
The signed-in form retains its own layout. Twenty-one focused Workshop and
installation tests pass. Local browser startup exposed an existing missing
`pages_page.required_release` column; that database was not migrated. Staging
visual verification passed after the requested Git transfer and release update.
Staging and OSWALD's clean dev checkout now use `98aa0de4`. The in-app browser
confirmed compact desktop sizing, equal action styling, and stacked actions
at a narrow phone viewport without horizontal dialog overflow. The viewport
override was reset. Readiness and one web/worker tree each were verified again.
No migrations or presentation reimport occurred for these UI updates. Live
remained `6582cc4`, returning its construction-page HTTP 503.

## Remaining acceptance

Real inbox/link confirmation remains pending. Provider
callbacks and the reconciled RR 1 claim/update handover remain separate gates.
No wipe, live deployment, host reboot or retention deletion is authorized here.
RR 2 remains disabled; no final contract/statistics restructuring was undertaken.
