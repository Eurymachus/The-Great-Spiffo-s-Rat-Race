# Decision 015: Feature-oriented source layout

## Decision

The active `42.20` implementation uses a feature-oriented `TGSRR` namespace rather than a flat client/shared folder.

## Boundaries

- `shared/TGSRR/Core` contains cross-cutting utilities such as localization and the internal event bus.
- `shared/TGSRR/Challenge` contains tracker/deliverable contracts and presentation-neutral notifications.
- `shared/TGSRR/Milestones` contains milestone definitions, registry policy, and persistent claims.
- `shared/TGSRR/Outposts` contains outpost definitions, normalized persistence, completion calculations, and reusable inspection models.
- `client/TGSRR/Tracker/<feature>` contains player-facing tracker modules and views.
- `client/TGSRR/Outposts` contains live world evaluation that does not belong to tracker presentation.
- `client/TGSRR/Outposts/Checks` contains registered world inspection providers.
- `client/TGSRR/Outposts/Debug` contains developer-only survey and Inspector tooling.
- `client/TGSRR/Notifications` contains client presentation of domain notifications.
- `client/TGSRR/Patches` contains explicit vanilla UI patches.

## Engine-owned locations

The following remain in Project Zomboid's expected locations:

- Challenge entry points under `client/LastStand`.
- Translation JSON under `shared/Translate`.

## Migration rule

Source moves must update require paths without changing runtime behavior. Feature refactors should be separate changes after the reorganized tree has been validated in game.
