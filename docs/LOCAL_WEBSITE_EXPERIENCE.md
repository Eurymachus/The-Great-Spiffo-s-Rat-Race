# Local Website Experience

This document records the participant-facing navigation and the local journey
checks completed before deployment work begins.

## Public journey

1. Landing page offers nickname reservation and a clear login route.
2. Signup collects nickname, email, password, privacy-notice acknowledgement,
   and Turnstile verification.
3. Verification confirmation activates the participant login.
4. Login provides password recovery and verification-resend routes.
5. The draft privacy notice remains available from primary navigation and the
   footer.

## Participant journey

1. Verified participants log in with email and password.
2. The account page shows nickname, private email, status, and registration date.
3. Participants can change their password, download their account data, submit an
   account-closure request, or log out.
4. Authenticated visitors are redirected from signup and login back to their
   account.
5. Participants with a staff role can enter challenge administration using the
   same credentials.

## Accessibility and responsive baseline

- A skip link targets the main content landmark.
- Primary navigation has an accessible label and marks the current page.
- All tested form controls have associated labels and browser autocomplete hints.
- Validation summaries use alert semantics where appropriate.
- Keyboard focus is visibly outlined.
- The title scales without wrapping and the account/login layouts have no
  horizontal overflow at desktop or 390-pixel mobile widths.

## Remaining launch work

- Repeat the journey against the production-like Docker/PostgreSQL environment.
- Test real transactional email and production Turnstile credentials.
- Complete the final privacy notice and account-deletion operator procedure.
- Perform a broader accessibility review before inviting real participants.
