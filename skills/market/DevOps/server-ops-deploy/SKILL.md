---
name: server-ops-deploy
description: Operate and deploy applications on general Linux servers over SSH. Use for server health/resource diagnostics (CPU, memory, disk, load, failed services), safe application deployment with automatic backup and rollback, systemd service control and log inspection, and troubleshooting incidents (high load, OOM, disk full, port conflicts, nginx 502/504, service won't start). Triggers on requests about deploying to a server, checking server health, restarting/inspecting services, rolling back a bad release, or diagnosing a production Linux box.
---

# Server Ops & Deploy

## Overview

Toolkit for day-to-day operations on general Linux servers: read-only health
diagnostics, safe deploys with automatic rollback, systemd service control, and
an incident-troubleshooting reference. Scripts are plain bash designed to run
**on the Linux server** — invoke them locally via SSH (`ssh user@host 'bash -s'
-- <args> < scripts/x.sh`).

## Safety rules (always)

- Diagnose **read-only first**. Run `preflight_check.sh` before any change.
- Read logs **before** restarting a service — a restart destroys evidence.
- Never blind-delete unfamiliar files, branches, or data. Investigate first.
- Any destructive or shared-state action (restart prod, prune, rollback, DB
  changes) — confirm with the user unless they pre-authorized it.
- Always pass `--health` on real deploys so a bad release auto-rolls-back.

## Capabilities

### 1. Health / preflight diagnostics — `scripts/preflight_check.sh`
Read-only snapshot: load vs cores, memory, disk & inode usage, failed systemd
units, listening ports, top CPU/MEM processes, zombies, common service states.
Emits `WARN:` / `CRIT:` lines for anything concerning; always exits 0.
```bash
ssh user@host 'bash -s' < scripts/preflight_check.sh
```
Run this first for any "the server is slow / something's wrong" request, then
drill into `references/troubleshooting.md`.

### 2. Safe deployment — `scripts/deploy.sh`
Timestamped immutable releases under `<root>/releases/<ts>` with an atomic
`current` symlink swap. Order: fetch (git or local) → build → swap → restart
service → health check → prune old releases. **On failed restart or health
check it automatically rolls back** to the previous release and deletes the bad
one.
```bash
# git source, with build + health check + auto-rollback
ssh user@host 'bash -s' -- \
  --root /var/www/app --service myapp.service \
  --source git --repo https://github.com/org/app.git --branch main \
  --build "npm ci && npm run build" \
  --health http://127.0.0.1:8080/healthz \
  < scripts/deploy.sh

# local artifact, dry-run to verify staging/build without touching prod
ssh user@host 'bash -s' -- --root /var/www/app --source local \
  --path /tmp/dist --dry-run < scripts/deploy.sh
```
Key options: `--root` (required), `--source git|local` (required),
`--service`, `--repo`/`--branch`, `--path`, `--build`, `--health`,
`--retries` (default 10), `--keep` (default 5), `--dry-run`.
Full layout, systemd unit template, nginx reverse-proxy, TLS, and the deploy
checklist are in `references/deploy-guide.md`.

### 3. Service control — `scripts/service_ctl.sh`
Concise wrapper over `systemctl`/`journalctl` for one unit.
```bash
ssh user@host 'bash -s' -- status  myapp.service < scripts/service_ctl.sh
ssh user@host 'bash -s' -- restart nginx         < scripts/service_ctl.sh
ssh user@host 'bash -s' -- logs    myapp 100     < scripts/service_ctl.sh
ssh user@host 'bash -s' -- health  myapp.service < scripts/service_ctl.sh
```
Actions: `status | start | stop | restart | reload | enable | disable | logs |
health`. `health` reports active state, restart count, and greps recent journal
for errors. Args: `<action> <unit> [lines]` (`.service` suffix optional).

### 4. Incident troubleshooting — `references/troubleshooting.md`
Copy-paste diagnostics for high CPU/load, OOM kills, disk full, port conflicts,
service won't start, nginx 502/504, network, file descriptors, IO wait, and
"what changed recently". Load it when diagnosing a specific incident.

## Typical workflows

**"Deploy the latest main to prod"**
1. `preflight_check.sh` — confirm the box is healthy.
2. `deploy.sh --dry-run` — verify fetch + build succeed.
3. Confirm with the user, then real `deploy.sh` with `--health`.
4. `service_ctl.sh health <unit>` + smoke-test the public URL.

**"The server is slow / a service is down"**
1. `preflight_check.sh` for the snapshot.
2. `service_ctl.sh status <unit>` and `service_ctl.sh logs <unit>`.
3. Match symptoms in `references/troubleshooting.md`; mitigate then root-cause.

**"Roll back the bad release"**
- `deploy.sh` already auto-rolls-back on health failure. For a manual rollback,
  re-point the `current` symlink to a known-good release (see the rollback
  snippet in `references/deploy-guide.md`) and restart the service.

## Resources

- `scripts/preflight_check.sh` — read-only health snapshot.
- `scripts/deploy.sh` — safe deploy with backup + auto-rollback.
- `scripts/service_ctl.sh` — systemd/journal service control.
- `references/deploy-guide.md` — SSH invocation, release layout, systemd unit,
  nginx, TLS, checklist, manual rollback.
- `references/troubleshooting.md` — incident diagnostics cheatsheet.

## Environment notes

- Server prereqs: `bash`, `git` (git source), `curl` (health checks),
  `systemctl`. Passwordless SSH keys recommended.
- These scripts target real Linux. They do not behave correctly under Windows
  git-bash (no real symlink support); always run them on the Linux host.
