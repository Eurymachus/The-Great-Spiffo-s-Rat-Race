# Streaming Account Integrations

## Purpose

Rat Race runs must be streamed. The website should therefore be able to verify
ownership of a participant's Twitch or YouTube channel and help the participant
attach the correct VOD and supporting clips to a run submission.

The provider-neutral connected-account model and Account Settings presentation
are implemented. Twitch now supports the server-side authorisation-code flow,
one-use state validation, ownership collision protection, encrypted token
storage, channel linking, reconnection and revocation. Twitch credentials are
validated at most hourly when used and refreshed reactively when Twitch rejects
an expired access token. Participants can explicitly cache their 20 most recent
broadcasts and 20 recent clips, then attach a broadcast, timestamps and clips to
a run submission. YouTube now supports Google-authorised channel linking,
ownership proof, encrypted credentials, reconnection and disconnect. Recent
YouTube video and archived livestream retrieval remains pending.

Participants can explicitly select one owned, connected Twitch or YouTube
account as their primary streaming channel. The current ranking table uses that
selection for its provider icon and external channel link. The website does not
guess a replacement when the selection is cleared, disconnected or invalidated.

The participant UI uses the supplied official Twitch Glitch and YouTube icon
assets in connected-channel rows and provider-specific actions. Shared template
and CSS treatments keep full-size row marks and compact button marks consistent;
the YouTube asset's transparent padding is cropped at display time while the
versioned source PNG remains unchanged.

## Twitch configuration

Register the site in the Twitch developer console and add the exact callback
address used by the deployment. Supply these environment values:

- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`
- `TWITCH_REDIRECT_URI` (for local development:
  `http://localhost:8000/account/streaming/twitch/callback/`)

Twitch permits plain HTTP specifically for `localhost`; it rejects the equivalent
`127.0.0.1` callback. Open the local site through `http://localhost:8000/` while
testing so the registered callback and browser session use the same host.
- `STREAMING_TOKEN_ENCRYPTION_KEY`, generated as a Fernet key using the command
  documented in `.env.example`

The Account Settings control remains visibly unavailable until all four values
are present. The client secret and encryption key must be injected by the
deployment environment and must not be committed.

## YouTube configuration

Create a Google OAuth web client, enable the YouTube Data API v3 and register the
exact callback address used by the deployment. Supply these environment values:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REDIRECT_URI` (for local development:
  `http://localhost:8000/account/streaming/youtube/callback/`)
- the shared `STREAMING_TOKEN_ENCRYPTION_KEY`

The connection requests OpenID identity and the read-only YouTube scope. The
client secret and encryption key must be injected by the deployment environment
and must not be committed.

### Operational requirements

- Development must use the project's canonical startup command, which loads the
  local uncommitted `.env` before starting Django. A bare `manage.py runserver`
  is not an approved project start procedure.
- Production must inject provider credentials and the Fernet key through the
  deployment environment. It must not depend on a repository `.env` file.
- Startup must reject a missing or malformed Fernet key whenever a provider is
  configured, before the application accepts traffic.
- The Fernet key is persistent application data. Rotating it requires an
  explicit migration that decrypts and re-encrypts stored provider credentials.
- Deployment checks must confirm that existing encrypted credentials can be
  decrypted without logging their plaintext values.
- Restart tooling must terminate the complete previous process tree and verify
  that exactly one process is listening on the intended port.

## Separate identity from platform connections

Signing into the Rat Race website and connecting a streaming channel are
different operations.

- A Participant remains the single local Rat Race account and owns challenge
  history, submissions, notifications and privacy choices.
- A participant may connect no streaming account, Twitch, YouTube, or both.
- Connecting another provider to an authenticated Participant must not create a
  second Participant.
- Accounts must never be silently merged merely because providers return the
  same email address.
- Previously submitted evidence must remain intelligible if a provider is later
  disconnected.

The initial deliverable should add connected streaming accounts to existing Rat
Race accounts. Alternative sign-in through Twitch or Google can follow after
linking and account-recovery behaviour is proven.

## Provider behaviour

### Twitch

Use Twitch OAuth 2.0 / OpenID Connect with the server-side authorisation-code
flow. Store Twitch's stable user and broadcaster identifiers rather than relying
on a mutable display name.

Once connected, the website presents cached recent broadcasts and clips,
including their titles, dates, durations, thumbnails and canonical URLs. It
does not call Twitch merely to render a page. Twitch tokens are encrypted,
validated before media refresh when their hourly validation is stale, and
reactively refreshed after an unauthorised API response.

### YouTube

Google provides authentication; YouTube provides the channel relationship.
Public UI should therefore say **Continue with Google** for authentication and
**Connect YouTube** for channel authorisation.

Use Google OpenID Connect for identity and the YouTube Data API with the smallest
practical read-only scope for channel access. Store the stable Google subject and
YouTube channel ID. Recent uploads and archived livestreams can be obtained from
the channel and its uploads playlist.

YouTube's user-created Clips feature is not currently exposed as a dependable
first-class YouTube Data API resource. Accept YouTube clip links manually unless
the platform adds suitable official API support.

## Expected data model

A provider-neutral connected-account record should include:

- Participant owner
- provider (`twitch` or `youtube`)
- immutable provider identity
- channel/broadcaster identity
- current display name and channel URL
- granted scopes
- access-token expiry and refresh capability
- connection, refresh and revocation timestamps
- current connection status

Provider credentials and refresh tokens must be treated as secrets, encrypted at
rest, excluded from exports and logs, and deleted when no longer required.
Disconnecting a provider must revoke access where supported.

## Submission journey

The submission UI:

1. Uses a compact inline selector for connected Twitch and YouTube channels.
2. Offers a cached list of recent VODs from that participant's verified channel.
3. Record the selected video's stable platform ID and canonical URL.
4. Allow start and end timestamps plus optional supporting clips.
5. Preserve a human-readable evidence snapshot for moderation and audit.
6. Follow the agreed [submission review policy](SUBMISSION_REVIEW_POLICY.md):
   new runs and significant findings require human approval; routine eligible
   updates may be Auto-Approved with valid VOD evidence. Platform linkage alone
   does not qualify as evidence of the submitted gameplay. This policy is
   implemented locally and replaces the previous blanket manual requirement.
   Direct Twitch/YouTube video checks require a connected matching channel for
   automatic approval; unavailable verification routes to a moderator.
7. Embed the supplied VOD on its submission record where supported, with evidence
   timestamps and a direct provider link. An embed does not preserve deleted VODs.
8. Keep accepted submissions available in Submission Audits. Use a seven-day
   operational audit window from broadcast, sooner where possible; later
   disputes require team discussion rather than assuming expired footage means
   wrongdoing.

Manual evidence URLs should remain available as a fallback when a provider is
unavailable, a VOD is unlisted, or official API support is insufficient.

## Privacy, security and operations

- Request permissions incrementally and only when the participant chooses to
  connect a provider.
- Explain which channel information and media metadata will be read.
- Cache recent media results rather than polling providers on every page load.
- Provide clear Connected, Reconnect required and Disconnected states.
- Permit participants to disconnect either provider independently.
- Do not request video-management, upload or deletion permissions.
- Review Google verification requirements before public YouTube authorisation.
- Keep provider data and retention behaviour in the versioned privacy notice
  accurate as integrations change. **Implemented for the current provider set.**

## Intended implementation order

1. Provider-neutral connected streaming account model and account-settings UI.
   **Implemented.**
2. Twitch linking and ownership proof. **Implemented.**
3. Twitch token validation/reactive refresh and recent VOD/clip selection.
   **Implemented.**
4. Google/YouTube linking, ownership proof, token renewal and recent video or
   archived livestream selection. **Implemented.**
5. Attach selected evidence to run submissions and moderator review.
   **Implemented for Twitch, YouTube and manual URLs.**
6. Consider Twitch and Google as alternative sign-in methods only after linking,
   unlinking, collision handling and account recovery are tested.
