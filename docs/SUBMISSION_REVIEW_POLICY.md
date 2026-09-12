# Submission review and audit policy

Agreed by the project owner on 11 September 2026. Implemented in the local
website worktree, pending team acceptance and deployment. Applies to tracked
run submissions, not legacy claims or mod-policy voting.

Team proposal: [Website - Run Approval System](https://discord.com/channels/1355647558227333231/1544122725013000212/1547751912429060180).

## One run moderation workspace

Challenge Runs is the single top-level administration area. Saved filtered tabs
start with Needs Review, No Recent Audit, Active and All. Moderators can create
personal views, hide or reorder tabs, and return to their last selected view.
Administrators can create shared views; sharing never changes data permissions.

Each run has Overview, Submissions and Audits tabs. The complete submission
history remains available, including automatic, human and declined decisions.
Submission approval, audit outcomes and run validity remain separate decisions.
Declining one submission does not itself invalidate the run.

## Submission routing

| Condition | Outcome |
| --- | --- |
| New run without an approved baseline | Pending Approval; requires a moderator. |
| Existing approved run, validation passes, valid VOD evidence supplied, no new review triggers and no unresolved earlier submission | Auto-Approved. |
| New mod changes, debug use, outpost completion, time-deviation or reconciliation/recovery events, or other significant findings | Pending Approval; requires a moderator. |
| Missing VOD, malformed link or unsupported evidence destination | Awaiting Evidence; explain what the participant must correct. |
| Evidence cannot be checked conclusively, including temporary provider failure | Pending Approval with the uncertainty explained. |
| Broken integrity, changed approved event history or another blocking validation failure | Block both automatic and manual approval; retain the finding. A technical failure alone is not a cheating verdict. |

Awaiting Evidence means participant action is needed. Pending Approval means a
moderator must decide. New runs still need human approval after evidence is
corrected. Correcting evidence reassesses eligibility without replacing the
immutable export. Later submissions cannot bypass an unresolved predecessor;
reassess them against the accepted baseline after that predecessor is resolved.

Triggers concern new activity since the accepted baseline. Previously reviewed
debug events, outpost completions and recovery history in cumulative exports
must not trigger review again. Compare mod changes, including removals, against
the baseline. Preserve full event-prefix validation and atomic canonical updates
for both automatic and human approval.

Time deviation specifically means the recorded game-time uncertainty event
where the player chooses to correct or continue, for example after interrupted
logging. Either choice requires human review when newly submitted. It does not
mean an invented comparison between VOD duration and gameplay duration.

Additional significant findings include changed starting conditions or challenge
settings, unsupported or partial tracking history, unexplained progression,
challenge completion and terminal events. Exact event mappings and classifications
are checked against the current export contract. The current explicit clock
repair event is `run.clock.repaired`; new clock, recovery and reconciliation
events also require review.

## Evidence and review presentation

- Support connected-provider VOD selection and manually supplied Twitch/YouTube
  video links. Validate supported hosts and video URL forms; attempt provider
  existence/accessibility checks where supported. A correctly formed URL or
  linked channel alone does not establish gameplay coverage or fair play.
- Preserve the submitted evidence and its revision history. Represent the
  relevant video intervals and support coverage across multiple broadcasts;
  reusing a VOD must not silently stand in for unrelated gameplay.
- Embed the VOD on the submission record page where supported, alongside evidence
  details, selected timestamps and a direct provider link. Embedding does not
  archive the footage. Keep a direct link when embedding is unavailable.
- Lead human review with changes since the accepted baseline and specific
  findings. Make significant events and full event details inspectable, with
  earlier history available when needed. Only map events to video timestamps
  where that mapping is reliable.

## Approval provenance and audits

- Auto-Approved is a moderator-only label. Participant-facing approval wording
  must not imply that footage was watched.
- Record whether acceptance was automatic or human, its timestamp, baseline and
  policy/check version; record the reviewer for human decisions.
- Keep audit state separate from acceptance. Selecting an accepted submission
  for audit does not itself revoke approval, and a later audit must preserve
  the original automatic-approval provenance.
- Record the footage intervals inspected and the audit conclusion. An accepted
  baseline is not necessarily a VOD-reviewed baseline; keep unreviewed intervals
  identifiable. Include clean submissions in audit selection.
- Use seven days from the broadcast as the maximum operational VOD audit window,
  reviewing sooner where possible. Submission does not restart that clock;
  late submission or earlier deletion may leave less time. This is an operational
  policy, not a guarantee of provider retention or a limit on later disputes.
- Submissions remain selectable and visible after that window. Disputes when
  footage has expired require nuance and team discussion; expiry alone does not
  imply wrongdoing. Adverse findings require a deliberate decision about the
  run and any affected later submissions.

## Scope boundary

Do not add mass approval to the revised journey. Routine eligible updates
advance automatically; manual work is reserved for new runs, findings and audits.
Implementation must define audit controls and adverse-finding handling without
silently changing accepted results or treating missing evidence as an invalid run.

## Implementation and acceptance notes

- Routing runs after a new upload, evidence correction or moderator decision.
  Existing untouched queue entries are not retroactively auto-approved by a migration.
- Automatic VOD verification requires a connected matching provider account.
  Manually supplied supported links remain reviewable when provider verification
  is inconclusive. Provider checks verify availability and ownership, not footage content.
- A primary broadcast supports start/end seconds and an embedded player. Up to
  five additional broadcasts are preserved as direct links and checked too.
  Reused footage without a clearly new interval requires human review.
- Audit controls record selection, work in progress, pass or action required.
  Passing requires inspected intervals and a conclusion. Adverse findings leave
  acceptance unchanged until a moderator makes a deliberate run-level decision.
- Local migrations are applied. Automated tests cover routing, queue ordering,
  immutable history, rollback, evidence corrections, permissions and audit provenance.
  The 113 targeted regression tests pass. Signed-in browser checks cover the
  three areas, run history and submission detail. Live provider playback and a
  representative team submission remain acceptance checks.
- The wider 313-test run has 16 temporary-filesystem permission errors and one
  managed-page `/media/rules` routing failure outside this approval change.
- No mod or Error Debug build changes are required by this website implementation.
