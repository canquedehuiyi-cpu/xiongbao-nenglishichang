#!/usr/bin/env bash
# deploy.sh — safe release deploy with backup, health check, and auto-rollback.
#
# Pattern: releases live under $DEPLOY_ROOT/releases/<timestamp>; the "current"
# symlink points at the active release. A failed health check rolls back the
# symlink and restarts the service to the previous release.
#
# Usage:
#   deploy.sh --root /var/www/app --service myapp.service \
#             --source git --repo https://github.com/org/app.git --branch main \
#             --health http://127.0.0.1:8080/healthz --build "npm ci && npm run build"
#
#   deploy.sh --root /var/www/app --service myapp.service \
#             --source local --path /tmp/dist --health http://127.0.0.1/healthz
#
# Options:
#   --root DIR        deploy root (required)
#   --service NAME    systemd unit to restart after swap (optional)
#   --source TYPE     git | local (required)
#   --repo URL        git repo (source=git)
#   --branch NAME     git branch/ref, default main (source=git)
#   --path DIR        local directory to copy (source=local)
#   --build CMD       shell command run inside the new release before swap
#   --health URL      HTTP endpoint checked after swap (2xx/3xx = healthy)
#   --retries N       health check attempts, default 10
#   --keep N          old releases to retain, default 5
#   --dry-run         do everything except swap/restart/cleanup
set -uo pipefail

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[deploy $(date '+%T')] $*"; }

ROOT="" SERVICE="" SOURCE="" REPO="" BRANCH="main" LOCAL="" BUILD=""
HEALTH="" RETRIES=10 KEEP=5 DRYRUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --service) SERVICE="$2"; shift 2;;
    --source) SOURCE="$2"; shift 2;;
    --repo) REPO="$2"; shift 2;;
    --branch) BRANCH="$2"; shift 2;;
    --path) LOCAL="$2"; shift 2;;
    --build) BUILD="$2"; shift 2;;
    --health) HEALTH="$2"; shift 2;;
    --retries) RETRIES="$2"; shift 2;;
    --keep) KEEP="$2"; shift 2;;
    --dry-run) DRYRUN=1; shift;;
    *) die "unknown option: $1";;
  esac
done

[ -n "$ROOT" ] || die "--root is required"
[ -n "$SOURCE" ] || die "--source is required (git|local)"
command -v curl >/dev/null 2>&1 || { [ -z "$HEALTH" ] || die "--health needs curl installed"; }

RELEASES="$ROOT/releases"
CURRENT="$ROOT/current"
TS=$(date '+%Y%m%d%H%M%S')
NEW="$RELEASES/$TS"

mkdir -p "$RELEASES" || die "cannot create $RELEASES"

PREV=""
if [ -L "$CURRENT" ]; then PREV=$(readlink -f "$CURRENT"); fi
log "previous release: ${PREV:-<none>}"

# --- Fetch new release ---
case "$SOURCE" in
  git)
    [ -n "$REPO" ] || die "--repo required for source=git"
    log "cloning $REPO@$BRANCH -> $NEW"
    git clone --depth 1 --branch "$BRANCH" "$REPO" "$NEW" >/dev/null 2>&1 \
      || die "git clone failed"
    ;;
  local)
    [ -n "$LOCAL" ] || die "--path required for source=local"
    [ -d "$LOCAL" ] || die "local path not a directory: $LOCAL"
    log "copying $LOCAL -> $NEW"
    mkdir -p "$NEW" && cp -a "$LOCAL/." "$NEW/" || die "copy failed"
    ;;
  *) die "invalid --source: $SOURCE";;
esac

# --- Build ---
if [ -n "$BUILD" ]; then
  log "running build in $NEW"
  ( cd "$NEW" && eval "$BUILD" ) || { rm -rf "$NEW"; die "build failed; aborted before swap"; }
fi

if [ "$DRYRUN" -eq 1 ]; then
  log "DRY-RUN: staged release at $NEW; skipping swap/restart/cleanup"
  exit 0
fi

restart_service() {
  if [ -n "$SERVICE" ] && command -v systemctl >/dev/null 2>&1; then
    log "restarting $SERVICE"
    systemctl restart "$SERVICE" || return 1
  fi
  return 0
}

rollback() {
  log "!!! rolling back"
  if [ -n "$PREV" ] && [ -d "$PREV" ]; then
    local tmpl="${CURRENT}.tmp.$$"
    ln -sfn "$PREV" "$tmpl" && mv -Tf "$tmpl" "$CURRENT"
    restart_service || log "WARN: service restart during rollback failed"
    log "rolled back to $PREV"
  else
    log "no previous release to roll back to; current left as-is"
  fi
  rm -rf "$NEW"
}

# --- Atomic symlink swap (temp link + mv -T avoids partial/deref states) ---
log "swapping current -> $NEW"
TMPLINK="${CURRENT}.tmp.$$"
ln -sfn "$NEW" "$TMPLINK" || { rm -rf "$NEW"; die "failed to stage symlink"; }
mv -Tf "$TMPLINK" "$CURRENT" || { rm -f "$TMPLINK"; rm -rf "$NEW"; die "symlink swap failed"; }
restart_service || { rollback; die "service restart failed after swap"; }

# --- Health check ---
if [ -n "$HEALTH" ]; then
  healthy=0
  for i in $(seq 1 "$RETRIES"); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$HEALTH" 2>/dev/null)
    if [ -n "$code" ] && [ "$code" -lt 400 ] 2>/dev/null; then
      healthy=1; log "health OK (HTTP $code) on attempt $i"; break
    fi
    log "health attempt $i/$RETRIES -> ${code:-no-response}; retrying in 2s"
    sleep 2
  done
  if [ "$healthy" -ne 1 ]; then
    rollback
    die "health check failed against $HEALTH after $RETRIES attempts; rolled back"
  fi
else
  log "no --health provided; skipping health check"
fi

# --- Cleanup old releases ---
log "pruning old releases (keeping $KEEP)"
ls -1dt "$RELEASES"/*/ 2>/dev/null | tail -n +$((KEEP+1)) | while read -r old; do
  old="${old%/}"
  [ "$old" = "$(readlink -f "$CURRENT")" ] && continue
  log "removing $old"; rm -rf "$old"
done

log "DEPLOY SUCCESS: $NEW is now current"
exit 0
