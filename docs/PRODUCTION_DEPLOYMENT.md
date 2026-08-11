# Production Deployment Contract

This document defines the production shape of the Rat Race website. Codex may
provision, release, diagnose, and maintain the host, but the deployed platform
must continue operating independently after a deployment task ends.

## Runtime boundary

Production runs these independently supervised services:

- A reverse proxy providing HTTPS and forwarding to the ASGI application.
- The Django ASGI application using `config.settings_production`.
- One `run_reference_update_worker` process.
- PostgreSQL for durable application data.
- Redis for shared caching, rate limits, and worker health.

A host scheduler may enqueue routine reference updates. It must not replace the
continuously supervised worker.

`compose.production.yml` provides the web, reference worker, PostgreSQL, and
Redis topology decided for the Ubuntu production VM. It binds the web service to
the VM loopback interface only. The selected host HTTPS or tunnel layer must
forward to that listener. WhiteNoise serves versioned static assets from the web
container, so the traffic layer does not need direct access to the static volume.

## Production settings

`config.settings_production` is the only supported production settings module.
It validates the complete environment before Django starts. Missing integrations
are startup failures because production is expected to provide every documented
website capability.

`.env.example` is the non-secret inventory. Real values must be supplied by the
host's secret and configuration mechanism and must never be committed.

## Required host software

- A supported Python release and all packages in `apps/website/requirements.txt`.
- PostgreSQL client tools suitable for backup and restore.
- Redis.
- SteamCMD, including a persistent installation directory and Steam session.
- Java and the pinned Vineflower JAR used by reference decompilation.
- A reverse proxy, service supervisor, and scheduler appropriate to the host.

The container image installs Java and SteamCMD. Place the approved pinned
Vineflower JAR at `deployment/runtime/vineflower.jar` on the host before building
or starting the services. That runtime directory is intentionally excluded from
Git.

## Persistent state

Back up and preserve:

- PostgreSQL.
- Uploaded media.
- The private avatar quarantine directory.
- Project Zomboid reference and decompiled-build directories.
- Deployment configuration and secrets through the host's secure mechanism.
- Operational logs required for diagnosis and audit.

SteamCMD session material is sensitive host state. Preserve it securely when
appropriate, but do not place it in ordinary application backups or the
repository. Collected static files are release output and can be rebuilt.

## Health contract

- `/health/live/` confirms that the application process can answer and reports
  its release identifier.
- `/health/ready/` verifies PostgreSQL, Redis, persistent storage, and a recent
  heartbeat from a reference worker running the same release.

Health responses expose component status only. They must not reveal paths,
credentials, exception details, or participant data.

## Release sequence

1. Fetch the approved commit into a new release directory.
2. Supply `.env.production` through the host's protected deployment storage.
3. Put the pinned Vineflower JAR in `deployment/runtime/` and build the images.
4. Back up durable state.
5. Apply migrations and build static files with one-shot website containers.
6. Run `python manage.py check_production_deployment` in a one-shot website
   container. This also proves that stored provider credentials remain
   decryptable with the supplied Fernet key.
7. Restart the web and worker services onto the same release identifier.
8. Confirm liveness, readiness, and the production acceptance journey.
9. Move traffic only after those checks pass.
10. Retain the previous release and its compatible configuration for rollback.

Database migrations require an explicit rollback assessment. If a schema change
is not backward compatible, restoring the previous application also requires the
documented database restore path.

## Human-controlled actions

Codex must stop for owner authority when work requires new production
credentials, Steam Guard interaction, DNS or TLS ownership, live traffic
switching, destructive data changes, or approval of public policy wording.

## Repository work remaining before launch

- Record host-specific service, scheduler, backup, restore, and rollback commands
  after auditing the host.
- Add a production-shaped acceptance runner.
- Complete retention automation and the final privacy review.
- Exercise the legacy import and claim journey with representative data.
- Remove development-only records before the final production data snapshot.
