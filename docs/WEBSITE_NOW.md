# Website: Current Focus

## Branch and worktree

- Development branch: `codex/website-dev`
- Website worktree: `The Great Spiffo's Rat Race - Website`
- Project Zomboid mod development is isolated in its own worktree and branch.

## Goal

Launch a small public website where prospective Rat Race participants can reserve
a nickname using a verified email address.

## Done When

- The registration page is publicly available.
- Participant nicknames are unique.
- Email addresses are verified.
- A human-verification check protects registration.
- Registrations can be viewed and administered securely.
- Basic privacy, deletion, and unsubscribe needs are covered.

## Implemented

- Permanent participant accounts using nickname, email, and password.
- Self-declared 18+ participation eligibility with versioned confirmation and no
  collection of dates of birth or identity documents.
- Email verification with pending, verified, expired, disabled, and removed states.
- Participant login and secure password recovery.
- Participant account summary, password change, staff administration link, and
  secure logout controls.
- Draft privacy notice, participant JSON data download, and authenticated
  account-closure requests visible to administrators.
- Central environment-backed `SITE_*` configuration for public operator identity,
  company details, privacy contact, eventual public URL, and brand fallbacks.
- Singleton Branding backend with safe environment defaults, immediate
  public rendering, and a scoped Branding Administrator role.
- Optional backend-managed header logo, favicon, social sharing image, homepage
  feature image, and decorative background image. Each slot has an independent
  enable switch and retains its text or theme fallback when disabled.
- Reusable image library with thumbnails, friendly names, original-file metadata,
  immediate validated multi-file uploads, and image selection from Branding.
- Configurable public attribution to The Indie Stone's terms, kept separate from
  the ordinary non-affiliation disclaimer.
- Managed visual themes with three editable presets, private signup-page preview,
  duplication, restoration, activation, and validated design controls.
- A protected backend-managed Homepage assembled from ordered, reusable,
  responsive sections without administrator-authored HTML or JavaScript.
- Flat backend-managed public pages at protected `/pages/<slug>/` addresses,
  with page-owned navigation labels, visibility, and ordering.
- Consistent primary navigation, authenticated-route redirects, accessible form
  metadata, keyboard focus treatment, and responsive local journey checks.
- Administration editing forms use one **Save** action that saves in place and
  continues editing. It activates only when the form has unsaved changes;
  workflow actions such as submission review remain separate.
- Privileged, confirmation-protected closure processing with non-personal
  closure receipts and a documented nullable owner for future independent runs.
- Cloudflare Turnstile integration using official test credentials locally.
- Cache-backed request limits for signup, resend, and password recovery.
- Administrator roles, participant promotion, status management, and CSV export.
- Local development documentation and automated test coverage.
- Mod-export ingestion into immutable, individually reviewed submissions, with
  integrity verification and explicit administrator approval or reasoned
  decline. The first approved submission officiates its run; each later approval
  alone advances the run's canonical snapshot.
- Current format-3 mod-export ingestion, including the signed ledger and complete
  character/trait projection, preserved on both the run and immutable submission.
- Independent run lifecycle tracking for active, deceased, abandoned, completed,
  and invalidated runs, presented as Active Runs and Past Runs on the participant
  dashboard. Lifecycle is moderator-managed until the tracker emits a terminal
  run signal.
- Participant notifications for submission receipt and moderation decisions.
- A dedicated Project Zomboid Catalogue administration section with stable IDs,
  display metadata, version ranges, aliases, a reusable resolver, and a scoped
  Zomboid Integration staff role.
- A provider-neutral connected streaming-account foundation for Twitch and
  YouTube, including immutable provider/channel identities, connection state,
  audit timestamps, administration and participant-facing account status.
- Production-shaped Twitch linking with encrypted rotating credentials,
  ownership proof, hourly-on-use validation, reactive refresh, explicitly
  cached recent broadcasts and clips, and immutable run-evidence snapshots for
  moderation.
- Real Twitch OAuth, channel linking, VOD/clip refresh, evidence selection,
  submission review and moderator approval verified end to end against a live
  Twitch channel on 24 July 2026.
- Twitch-side credential revocation is detected on the next validation or media
  refresh and changes the website account to Reconnect required.
- Official Twitch and YouTube brand marks shared across connected-channel rows
  and the run-submission journey.
- Optional Discord identity linking using the minimal `identify` permission,
  with encrypted credentials and participant-controlled disconnect.

Uploaded brand images live in deployment media storage rather than Git. A live
deployment must persist and back up that media directory alongside the database.

## Not Now

- Leaderboards and statistics
- Full mod integration
- YouTube OAuth linking and media retrieval.

## Future Core Deliverable: Moderated Run Updates

Run-update ingestion is deferred, but its integrity workflow is a settled
requirement:

- Every upload is a complete cumulative snapshot of one mod-generated run ID.
- Uploading creates an immutable pending submission and never changes approved
  run data automatically.
- A new submission is compared with the latest approved snapshot for that run.
- Previously approved daily data that differs in the pending snapshot must be
  highlighted clearly for moderator review.
- Automated validators, including debug-mode detection and future
  challenge-integrity checks, produce visible findings but never approve a
  submission.
- Only an authorised moderator's explicit approval may add to or replace the
  canonical approved run data.
- Denied or invalid submissions remain available as an auditable record and
  never become the comparison baseline for later submissions.

## Pending Team Decision

- Final public domain name. `spiffosratrace.com` is available and has been
  suggested, but registration is on hold until the team agrees.

## Hierarchical managed navigation

Pages now own canonical root or nested public addresses such as `/gallery/` and
`/media/gallery/`. Navigation placement is managed separately through ordered
Navigation Item records. An item may link to a Page or act as a non-clickable
heading, and may be nested to three visible levels. The public header renders
desktop dropdowns and expandable mobile submenus. Code-controlled routes remain
reserved, and provisional `/pages/<slug>/` addresses permanently redirect to a
Page's canonical address. The admin tree uses visual drag-and-drop insertion
between items: vertical movement selects the position, while moving right nests
under the nearest preceding item and moving left moves the item outward.

## Recommended next action

Verify the revised navigation tree drag-and-drop interaction with root, second-
level, and third-level moves before returning to the final mod export.

Retention automation and a final pre-launch privacy review remain required.
