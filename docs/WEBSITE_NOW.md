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
- Email verification with pending, verified, expired, disabled, and removed states.
- Participant login and secure password recovery.
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

Add the basic participant account area and logout controls, then review the
registry milestone against its completion checklist. The final domain is not
required for local development.
