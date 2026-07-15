# Participant Registry — Minimum Specification

## Purpose

Allow a prospective Rat Race participant to reserve a public nickname using a
verified private email address before the full challenge platform launches.

## Participant Flow

1. Visit the Rat Race landing page.
2. Enter a participant nickname, email address, and password.
3. Confirm the 18+ participation rule, pass a human-verification check, and
   acknowledge reading the privacy notice.
4. Receive and follow an email verification link.
5. See confirmation that the nickname is reserved.
6. Log in to view the participant account, change the password, or log out.

The registration creates the participant's permanent account. Email is the login
identity and nickname is the public identity. Login remains disabled until the
email address has been verified.

The account page displays the participant's nickname, private email address,
account status, and registration date. It does not currently allow profile or
nickname editing. A placeholder identifies where cumulative run updates will be
submitted during a later milestone.

## Registration Rules

- Nicknames are public; email addresses are private.
- Nicknames must be unique without regard to letter case.
- Leading and trailing whitespace is removed before validation.
- Nickname length and allowed characters will be configurable.
- Blocked or inappropriate names can be rejected administratively.
- An unverified registration reserves its nickname temporarily, then expires.
- A verified email address cannot create unlimited registrations.

## Administrator Needs

An authorised administrator can:

- View verified, pending, expired, and removed registrations.
- Search by nickname or email address.
- Correct or release a nickname when necessary.
- Disable a registration with a recorded reason.
- Export the participant list in CSV format.

Administrator access must be authenticated and must not expose participant data
publicly.

## Minimum Stored Data

- Stable participant ID
- Display nickname and normalised nickname
- Email address and normalised email address
- Registration status
- Registration and verification timestamps
- Privacy-notice version and acknowledgement timestamp
- 18+ eligibility confirmation timestamp and policy version (not a date of birth
  or identity document)
- Administrative status and notes, if applicable

- Secure password hash; the original password is never stored

## Privacy and Safety

- Publish a concise privacy notice explaining purpose, retention, and contact.
- Do not display or expose email addresses publicly.
- Provide a verified-email route to request deletion or unsubscribe.
- Rate-limit registration and verification attempts.
- Protect registration with a human-verification service.
- Keep production secrets and participant data out of Git.

## Explicitly Out of Scope

- Run update codes and mod integration
- Participant profile editing beyond the basic account page
- Leaderboards, statistics, and charts
- Report moderation
- Social features
- Marketing email campaigns

## Acceptance Criteria

The milestone is complete when a real participant can register on the public
website, verify their email, receive confirmation of their nickname reservation,
and appear in a securely accessible administrator list. Duplicate nicknames,
unverified registrations, automated abuse, deletion requests, and private data
exposure are handled predictably.

## Implementation

The registry will be part of a single Django application backed by PostgreSQL.
See `docs/DECISIONS.md` for the hosting, email, and documentation decisions.
