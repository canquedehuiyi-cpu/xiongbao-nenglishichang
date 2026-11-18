#!/usr/bin/env bash
# service_ctl.sh — friendly wrapper around systemctl + journalctl for one service.
# Prints concise, LLM-readable output. Never leaves you guessing about state.
#
# Usage: service_ctl.sh <action> <unit> [lines]
#   action: status | start | stop | restart | reload | enable | disable | logs | health
#   unit:   service name, e.g. nginx / myapp.service
#   lines:  journal lines for logs (default 50)
set -uo pipefail

ACTION="${1:-}" UNIT="${2:-}" LINES="${3:-50}"
[ -n "$ACTION" ] && [ -n "$UNIT" ] || { echo "usage: service_ctl.sh <action> <unit> [lines]" >&2; exit 2; }
case "$UNIT" in *.service) ;; *) UNIT="${UNIT}.service";; esac

command -v systemctl >/dev/null 2>&1 || { echo "ERROR: systemctl not found (not a systemd host?)" >&2; exit 1; }

need_root_hint() {
  if [ "$(id -u)" -ne 0 ]; then echo "NOTE: not running as root; some actions may need sudo"; fi
}

case "$ACTION" in
  status)
    active=$(systemctl is-active "$UNIT" 2>/dev/null)
    enabled=$(systemctl is-enabled "$UNIT" 2>/dev/null)
    echo "unit:    $UNIT"
    echo "active:  $active"
    echo "enabled: $enabled"
    echo "--"
    systemctl status "$UNIT" --no-pager -l 2>/dev/null | head -12
    [ "$active" = "active" ] && exit 0 || exit 1
    ;;
  start|stop|restart|reload|enable|disable)
    need_root_hint
    echo "[$ACTION] $UNIT ..."
    if systemctl "$ACTION" "$UNIT"; then
      echo "OK: $ACTION succeeded; active=$(systemctl is-active "$UNIT" 2>/dev/null)"
    else
      echo "ERROR: $ACTION failed" >&2
      systemctl status "$UNIT" --no-pager -l 2>/dev/null | head -12
      exit 1
    fi
    ;;
  logs)
    command -v journalctl >/dev/null 2>&1 || { echo "ERROR: journalctl not found" >&2; exit 1; }
    echo "-- last $LINES journal lines for $UNIT --"
    journalctl -u "$UNIT" -n "$LINES" --no-pager 2>/dev/null
    ;;
  health)
    active=$(systemctl is-active "$UNIT" 2>/dev/null)
    failed_since=$(systemctl show "$UNIT" -p NRestarts --value 2>/dev/null)
    echo "unit:      $UNIT"
    echo "active:    $active"
    echo "restarts:  ${failed_since:-unknown}"
    if [ "$active" = "active" ]; then
      # show recent errors/warnings from the journal
      echo "-- recent error/warn log lines --"
      journalctl -u "$UNIT" -n 200 --no-pager 2>/dev/null | grep -iE 'error|fail|warn|fatal|panic|exception' | tail -15
      exit 0
    else
      echo "CRIT: unit is not active ($active)"
      journalctl -u "$UNIT" -n 30 --no-pager 2>/dev/null | tail -20
      exit 1
    fi
    ;;
  *)
    echo "ERROR: unknown action '$ACTION' (status|start|stop|restart|reload|enable|disable|logs|health)" >&2
    exit 2
    ;;
esac
