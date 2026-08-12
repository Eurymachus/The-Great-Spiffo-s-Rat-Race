# Native Windows Production Candidate

This is a candidate deployment shape for running the Rat Race website directly
on the existing Windows Server host without changing GSA, Docker, Hyper-V
switches, firewall rules, or physical network adapters. It does not supersede
`PRODUCTION_DEPLOYMENT.md` until its acceptance and recovery tests pass and the
owner approves the production change.

## Boundary

- Cloudflare Tunnel is the outbound-only public traffic layer.
- Uvicorn binds the Django ASGI application to `127.0.0.1:8000` only.
- PostgreSQL binds to loopback only and owns all durable application data.
- The web process and `run_reference_update_worker` are independently
  supervised Windows services.
- PostgreSQL provides shared rate-limit and worker-heartbeat state. Redis is not
  required for this deployment profile.
- SteamCMD, Java, Vineflower, media, quarantine, references, and decompiled
  outputs use Rat Race-owned directories that do not overlap GSA paths.

## Repository support

Use `config.settings_windows_production`. It selects the database runtime-state
backend while retaining all security and integration validation from
`config.settings_production`.

The additive `operations` migration creates:

- atomic, expiring rate-limit buckets; and
- a release-aware reference-worker heartbeat record.

`deployment/windows/Start-RatRaceProcess.ps1` is the common web/worker entry
point. The example WinSW definitions supervise each process separately.
`Test-RatRaceProduction.ps1` runs Django's deployment checks and the Rat Race
production contract check without printing secret values.

WinSW is a proposed free service wrapper, not a bundled binary. Its version,
checksum, installation, service identity, and recovery policy must be approved
and recorded before the example definitions are activated.

## Proposed host layout

```text
C:\ProgramData\RatRace\
  bin\                 service wrapper and launch scripts
  config\              ACL-protected production.env
  current\             pointer or directory for the active release
  releases\            immutable release directories
  venv\                 production Python environment
  logs\                 service and deployment logs

G:\RatRace\
  postgres\
  media\
  private\avatars\
  reference\
  decompiled\
  steam\

D:\RatRaceBackups\     database and file backups
```

Exact locations remain subject to the pre-install host review. The GSA Games
tree must not be reused merely because it is on `G:`.

## Required acceptance gates

Before production installation or traffic:

1. Run the complete test suite with the database runtime-state backend.
2. Prove the atomic rate-limit query against the selected PostgreSQL version.
3. Exercise Windows Steam Guard, SteamCMD update, and Vineflower decompilation.
4. Verify web and worker restart independently and report the same release ID.
5. Verify Cloudflare Tunnel reaches only the loopback ASGI listener.
6. Back up and restore PostgreSQL, media, private avatars, references, and
   decompiled outputs into an isolated test location.
7. Exercise release rollback, including database migration compatibility.
8. Monitor game-server CPU, memory, and disk latency during the heaviest
   reference operation.

## Verification record

On 12 August 2026 the repository candidate was exercised against an isolated,
loopback-only PostgreSQL 18.4 Windows cluster. All migrations applied, the
database-backed signup and resend limits passed end to end, and 16 concurrent
increments against one rate-limit bucket produced every value from 1 through
16 without losing an update. The temporary cluster was then stopped and
removed. This satisfies gate 2; the remaining host and recovery gates still
require explicit approval before production installation.

## Owner-controlled changes

Installing PostgreSQL, Java, SteamCMD, Cloudflare Tunnel, or service wrappers;
creating the service account; registering services; applying production
migrations; configuring DNS; and moving live traffic all require explicit owner
approval. None of those actions are performed by the repository changes.
