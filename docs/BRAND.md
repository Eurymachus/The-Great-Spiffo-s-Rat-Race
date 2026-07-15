# Brand Foundation

## Names

- Official title: **The Great Spiffo's Rat Race**
- Short formal name: **The Rat Race**
- Alternative official name: **TGS Rat Race**, where TGS abbreviates
  **The Great Spiffo**
- Informal and social name: **Rat Race**
- Participant/community name: **Rat Racers**
- Upcoming B42 Stable era: affectionately **Rat Race 2.0**

Use the official title for page titles, formal challenge references, and the mod.
Use “The Rat Race” as the formal shortened name. Use “Rat Race” conversationally,
adjectivally, and where space is limited. “Rat Race 2.0” is an affectionate era
name, not a replacement for the official title.

## Current Era

- The currently live Rat Race challenge targets Project Zomboid's B42 Unstable
  game release channel. This does not refer to a Git or repository branch.
- The website/platform being prepared is associated with B42 Stable and is known
  informally as Rat Race 2.0.
- The Discord contains B42 Unstable and B42 Stable category structures; only the
  Unstable category is currently visible to participants.

## Meaning of “Official”

The website is the official Rat Race challenge website, and the mod is the
official Rat Race challenge mod.

The Great Spiffo's Rat Race is a community challenge. It is not an official
Project Zomboid or The Indie Stone challenge and must not imply endorsement by,
or affiliation with, The Indie Stone.

Prefer explicit wording such as:

- “The official Rat Race challenge”
- “Official Rat Race challenge mod”
- “Official Rat Race website”

Avoid an unqualified “official Project Zomboid challenge.”

## Preferred Language

- Participant welcome: **“Welcome to the Rat Race!”**
- Example conversational usage: “Rat Race character builds usually include
  Aiming skill points.”
- Example community address: “Rat Racers, you best be ready for this...”

## Visual Themes

The visual direction is theme-driven so complete looks can be compared without
editing templates. Three editable starting points are supplied: **Survival
Event**, **Retro Road Race**, and **Clean Competition**.

Only one theme is public. Branding administrators can privately preview another
theme, duplicate it for experimentation, edit its structured palette and
typography controls, and activate it when approved. Presets can be restored.
Fields use constrained choices and validated colours rather than arbitrary CSS.

## Website Configuration

Reusable website vocabulary is stored in the singleton Site Branding backend
record rather than repeated in templates:

- `SITE_FULL_TITLE`
- `SITE_SHORT_TITLE`
- `SITE_TAGLINE`
- `SITE_WELCOME_MESSAGE`
- `SITE_FORMER_PARTICIPANT_LABEL`
- `SITE_DISCLAIMER`

The approved defaults remain version-controlled in settings and `.env.example`
as a fallback while migrations run or if the record is unavailable. Superusers
and members of the Branding Administrator group can edit the record through
`/admin/`; it cannot be added twice or deleted. Changes do not alter participant
records.

The active visual theme is selected from this record. Individual themes are
managed in the Website Themes section.
