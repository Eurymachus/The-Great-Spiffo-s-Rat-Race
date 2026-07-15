# Participant Registry Data

The first local implementation stores one pending registration per normalised
email address and one reservation per case-insensitive nickname.

Each registration is the permanent participant login account. Email is used to
sign in, nickname is public, and Django securely hashes the password. Login is
disabled until verification succeeds.

## Stored Fields

- Random stable participant ID
- Public display nickname and private normalised nickname
- Private email address and normalised email address
- Pending, verified, expired, disabled, or removed status
- Registration, consent, latest verification-send, and optional verification times
- Privacy-notice version
- Private administrator notes

Normalised values exist only for reliable matching. They are not shown publicly.

## Current Development Limitations

- Verification emails use Django's local console backend rather than Microsoft
  365. With debug mode enabled, the confirmation page displays a test shortcut.
- The privacy notice is a labelled draft rather than final legal copy.
- Local development uses Cloudflare's official always-pass Turnstile test keys.
  Production must supply its own site and secret keys through environment
  variables.
- The local SQLite database contains development-only data and is excluded from
  Git. PostgreSQL will replace it for production.

## Email Verification

- New registrations begin in the pending state.
- The website emails a signed verification link containing no readable personal
  data.
- Links expire after 24 hours and cannot be altered without invalidating them.
- A valid link marks the matching participant as verified and records the time.
- Reopening a valid link is harmless; disabled or removed registrations cannot be
  verified.
- Participants can request another link without the page revealing whether an
  email address is registered.
- A repeat signup using an existing email offers the resend page without revealing
  whether the existing registration is pending, expired, or verified.
- Pending registrations expire after seven days without a newer verification
  email. A scheduled production task will run the expiry command.
- Resending an expired registration returns it to pending with a fresh link.

## Abuse Protection

- Signup and verification-resend forms require a Turnstile token that is
  validated by the server before any account or email action occurs.
- Signup attempts are limited per IP address. Resend attempts are limited both
  per IP address and per normalised email address.
- Rate-limit cache keys contain hashes rather than raw email addresses or IPs.
- Local limits use Django's in-process cache. Deployment must configure a shared
  cache so limits apply consistently across all website processes.
- Cloudflare's connecting-IP header is ignored unless the production proxy
  configuration explicitly enables trust for it.

## Password Recovery

- The login page links to an email-based password-reset request.
- The request response is identical whether or not an active account exists.
- Reset requests require Turnstile and are limited per IP and per normalised
  email address.
- Reset links expire after one hour. Changing the password immediately
  invalidates the link so it cannot be reused.
- Only active, verified participant accounts receive reset mail. Disabled,
  removed, pending, and unknown accounts receive no message.
- Debug mode displays a local testing shortcut; production will only send the
  reset link by email.

## Participant Account

- Verified participants can view their nickname, email, status, and registration
  date after login.
- Participants can change their password by supplying the current password and
  remain logged in after a successful change.
- Logout is a CSRF-protected POST action rather than a state-changing ordinary
  link.
- Staff participants see a link to challenge administration; ordinary
  participants do not.
- Run-update submission is labelled as a future feature and does not accept data
  during the registry milestone.
- Participants can download a JSON copy of their account data. Password hashes,
  normalised lookup fields, and administrator notes are excluded.
- Participants can submit an account-closure request after confirming their
  current password. The request is timestamped and queued for administrator
  review; it does not automatically erase or disable the account.
- A Challenge Administrator processes an approved request through a separate
  destructive confirmation page. Staff accounts are refused until demoted.
- Processing deletes the login identity and leaves a non-personal closure receipt
  containing only a random reference and request/process timestamps.
- Future runs use a nullable participant relationship with `SET_NULL` deletion.
  Account closure detaches each run from the deleted identity while preserving
  the run and its daily data independently. Detached runs display as `Former Rat
  Racer`, have no participant profile link, and may remain in aggregate statistics.

## Privacy Notice Status

- A clearly labelled development draft describes collected data, purposes,
  public/private boundaries, transactional email, planned service providers, and
  participant controls.
- Sentinel Tech Ltd is the data controller for the challenge website and its
  participant data. Its public legal identity is supplied to templates through
  central `SITE_*` Django settings rather than participant database records.
- Privacy and account-data enquiries use `thegreatspiffo@machus.co.uk` as the
  provisional contact address. It can move to the final Rat Race domain later.
- The approved retention schedule is recorded in `docs/RETENTION.md` and
  summarised in the participant privacy notice.
- The lawful-basis map and legitimate-interests assessment are recorded in
  `docs/LAWFUL_BASES.md`.
- The draft notice explains applicable UK rights, the normal one-calendar-month
  response period, Sentinel Tech Ltd's contact route, and the ICO complaint route.
- The operator procedure is recorded in `docs/PRIVACY_REQUESTS.md`.
- The system currently sends no marketing messages, so there is no marketing
  subscription from which to unsubscribe. Any future optional communications
  must use explicit preferences.

## Administration

- Django's authenticated administrator site provides search and status/date
  filtering.
- Administrators can edit status and private notes, resend verification, and
  export selected registrations as CSV.
- Ad hoc database deletion is disabled. Authenticated participant closure
  requests use the privileged, confirmation-protected redaction workflow; use
  Removed status for ordinary moderation removals.
- See `docs/ADMINISTRATION.md` for the operator procedure.
- Administrators can promote the same participant account to Approver, Moderator,
  or Challenge Administrator without changing its email or password.
- Signup never grants staff or superuser access automatically.
