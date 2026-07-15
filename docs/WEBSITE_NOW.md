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
- Singleton Site Branding backend with safe environment defaults, immediate
  public rendering, and a scoped Branding Administrator role.
- Managed visual themes with three editable presets, private signup-page preview,
  duplication, restoration, activation, and validated design controls.
- Consistent primary navigation, authenticated-route redirects, accessible form
  metadata, keyboard focus treatment, and responsive local journey checks.
- Privileged, confirmation-protected closure processing with non-personal
  closure receipts and a documented nullable owner for future independent runs.
- Cloudflare Turnstile integration using official test credentials locally.
- Cache-backed request limits for signup, resend, and password recovery.
- Administrator roles, participant promotion, status management, and CSV export.
- Local development documentation and automated test coverage.

## Not Now

- Run update-code submission
- Leaderboards and statistics
- Report moderation
- Full mod integration

## Pending Team Decision

- Final public domain name. `spiffosratrace.com` is available and has been
  suggested, but registration is on hold until the team agrees.

## Recommended next action

Use the new theme previews to choose and refine the participant-facing visual
direction, then develop the logo/mark and imagery against that chosen theme.
Run/report ingestion remains deferred until Project Zomboid B42 Stable and the
challenge rules are finalised. Retention automation and a final pre-launch
privacy review still remain required.
