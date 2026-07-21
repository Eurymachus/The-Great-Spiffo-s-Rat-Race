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
- Privileged, confirmation-protected closure processing with non-personal
  closure receipts and a documented nullable owner for future independent runs.
- Cloudflare Turnstile integration using official test credentials locally.
- Cache-backed request limits for signup, resend, and password recovery.
- Administrator roles, participant promotion, status management, and CSV export.
- Local development documentation and automated test coverage.

Uploaded brand images live in deployment media storage rather than Git. A live
deployment must persist and back up that media directory alongside the database.

## Not Now

- Run update-code submission
- Leaderboards and statistics
- Report moderation implementation
- Full mod integration

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
Page's canonical address.

## Recommended next action

Exercise the navigation editor with representative real content, including a
root Gallery link and a Media heading with nested pages, then refine the admin
ordering experience based on that test.

Afterwards, extend the structured content system only when the Rat Race needs
another proven section or block type.
Run/report ingestion remains deferred until Project Zomboid B42 Stable and the
challenge rules are finalised. Retention automation and a final pre-launch
privacy review still remain required.
