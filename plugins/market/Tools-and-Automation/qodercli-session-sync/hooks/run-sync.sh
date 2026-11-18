#!/bin/sh
# macOS/Linux hook entry, called by run-sync.cmd or directly.
# Usage: run-sync.sh [check]
#   sync (default): register the current session in the app database.
#   check: only verify that a supported Python exists and explain how to install it.

set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 0
SYNC_SCRIPT="${SCRIPT_DIR}/../scripts/qodercli_sync.py"
MODE="${1:-sync}"

python_ok() {
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1
}

PYTHON=""
if command -v python3 >/dev/null 2>&1 && python_ok python3; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1 && python_ok python; then
  PYTHON=python
elif command -v py >/dev/null 2>&1 && python_ok py -3; then
  PYTHON="py -3"
fi

if [ -z "$PYTHON" ]; then
  if [ "$MODE" = "check" ]; then
    cat >&2 <<'EOF'
[qodercli-session-sync] Python 3.8+ not found, automatic sync is disabled.
  macOS:  xcode-select --install   or   brew install python
  Linux:  sudo apt install python3   (Fedora: sudo dnf install python3)
  Restart Qoder after installing, or sync manually:
          python3 scripts/qodercli_sync.py --cwd <project>
  See the plugin README section "Dependencies".
EOF
  fi
  exit 0
fi

[ "$MODE" = "check" ] && exit 0

case "$PYTHON" in
  "py -3") py -3 "$SYNC_SCRIPT" --hook --quiet ;;
  *) "$PYTHON" "$SYNC_SCRIPT" --hook --quiet ;;
esac
exit 0
