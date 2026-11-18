#!/usr/bin/env bash
# Runs the hook scripts shipped inside the ctxdb CLI on behalf of this plugin.
#   ctxdb-hook.sh <session-start|user-prompt-submit|stop>   hook mode; stdin is the hook JSON; always exits 0
#   ctxdb-hook.sh doctor                                     diagnose and refresh the cached runtime paths
set -u

MIN_NODE_MAJOR=20
CACHE_DIR="$HOME/.cache/contextdb-qoder"
CACHE_FILE="$CACHE_DIR/runtime"
PLUGIN_ROOT="${QODER_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# The host home is the directory that owns plugins/ (for example ~/.qoder).
case "$PLUGIN_ROOT" in
  */plugins/*) HOST_HOME="${PLUGIN_ROOT%%/plugins/*}" ;;
  *) HOST_HOME="" ;;
esac
case "${HOST_HOME##*/}" in
  .qoder|.qoder-cn) AGENT=qoder ;;
  .qoderwork|.qoderworkcn) AGENT=qoderwork ;;
  *) HOST_HOME="$HOME/.qoder"; AGENT=qoder ;;
esac
SETTINGS="$HOST_HOME/settings.json"

NODE=""
HOOKS_DIR=""
CTXDB_BIN=""
RESOLVE_ERROR=""

is_true() {
  case "$(printf '%s' "${1:-}" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')" in
    1|true) return 0 ;;
  esac
  return 1
}

# Hooks written by `ctxdb setup --agent=qoder` carry a "_ctxdb..." marker. While they
# exist they already run the same scripts, so the plugin stays out of the way.
global_hooks_present() {
  [ -f "$SETTINGS" ] && grep -q '"_ctxdb' "$SETTINGS" 2>/dev/null
}

# GUI-launched hosts on macOS do not inherit the login shell PATH.
augment_path() {
  local d nvm=()
  for d in "$HOME"/.nvm/versions/node/*/bin; do
    [ -d "$d" ] && nvm=("$d" "${nvm[@]+"${nvm[@]}"}")
  done
  for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.npm-global/bin" "${VOLTA_HOME:-$HOME/.volta}/bin" "${nvm[@]+"${nvm[@]}"}"; do
    case ":$PATH:" in
      *":$d:"*) ;;
      *) [ -d "$d" ] && PATH="$PATH:$d" ;;
    esac
  done
  export PATH
}

real_path() {
  local p="$1" dir link
  while [ -L "$p" ]; do
    dir=$(cd -P "$(dirname "$p")" && pwd) || return 1
    link=$(readlink "$p") || return 1
    case "$link" in
      /*) p="$link" ;;
      *) p="$dir/$link" ;;
    esac
  done
  dir=$(cd -P "$(dirname "$p")" && pwd) || return 1
  printf '%s/%s\n' "$dir" "$(basename "$p")"
}

has_hook_scripts() {
  [ -f "$1/session-start.js" ] && [ -f "$1/user-prompt-submit.js" ] && [ -f "$1/stop.js" ]
}

hooks_dir_for() {
  local bin="$1" real candidate volta_bin="${VOLTA_HOME:-$HOME/.volta}/bin"
  if [ "$bin" = "$volta_bin/ctxdb" ]; then
    # Resolve global tools outside the project so local dependencies cannot shadow them.
    real=$(cd / && "$volta_bin/volta" which ctxdb 2>/dev/null) || return 1
    case "$real" in
      /*) ;;
      *) return 1 ;;
    esac
  else
    real="$bin"
  fi
  real=$(real_path "$real") || return 1
  for candidate in \
    "$(dirname "$real")/../hooks" \
    "$(dirname "$bin")/../lib/node_modules/@aliyunrds/ctxdb/dist/hooks" \
    "$(dirname "$bin")/../lib/node_modules/@ali/ctxdb-internal/dist/hooks"; do
    if has_hook_scripts "$candidate"; then
      (cd -P "$candidate" && pwd)
      return 0
    fi
  done
  return 1
}

node_major() {
  local major
  major=$("$1" -p 'process.versions.node.split(".")[0]' 2>/dev/null) || return 1
  case "$major" in
    ''|*[!0-9]*) return 1 ;;
  esac
  printf '%s\n' "$major"
}

volta_node_for() {
  local hooks="$1" package toolchain version node volta="${VOLTA_HOME:-$HOME/.volta}/bin/volta"
  case "$hooks" in
    */node_modules/@aliyunrds/ctxdb/dist/hooks) package=@aliyunrds/ctxdb ;;
    */node_modules/@ali/ctxdb-internal/dist/hooks) package=@ali/ctxdb-internal ;;
    *) return 1 ;;
  esac
  toolchain=$(cd / && "$volta" list --format plain --default "$package" 2>/dev/null) || return 1
  case "$toolchain" in
    *$'\n'*) return 1 ;;
    "package $package@"*" / "*" / node@"*" (default)") ;;
    *) return 1 ;;
  esac
  version=${toolchain##* / node@}
  version=${version%% *}
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  node=$(cd / && "$volta" run --node "$version" --bundled-npm --no-yarn node -p 'process.execPath' 2>/dev/null) || return 1
  case "$node" in
    /*) [ -x "$node" ] || return 1 ;;
    *) return 1 ;;
  esac
  printf '%s\n' "$node"
}

resolve_runtime() {
  local candidate major found_old="" candidates=()
  CTXDB_BIN=$(command -v ctxdb 2>/dev/null) || {
    RESOLVE_ERROR="the ctxdb CLI was not found on PATH"
    return 1
  }
  HOOKS_DIR=$(hooks_dir_for "$CTXDB_BIN") || {
    RESOLVE_ERROR="could not locate the hook scripts of $CTXDB_BIN"
    return 1
  }
  if [ "$CTXDB_BIN" = "${VOLTA_HOME:-$HOME/.volta}/bin/ctxdb" ]; then
    candidate=$(volta_node_for "$HOOKS_DIR") || {
      RESOLVE_ERROR="could not resolve the Node.js engine pinned to $CTXDB_BIN"
      return 1
    }
    candidates=("$candidate")
  else
    candidates=("$(dirname "$CTXDB_BIN")/node" "$(command -v node 2>/dev/null)")
  fi
  for candidate in "${candidates[@]}"; do
    [ -n "$candidate" ] && [ -x "$candidate" ] || continue
    major=$(node_major "$candidate") || continue
    if [ "$major" -ge "$MIN_NODE_MAJOR" ]; then
      NODE="$candidate"
      return 0
    fi
    found_old="v$major at $candidate"
  done
  RESOLVE_ERROR="Node.js >=$MIN_NODE_MAJOR is required${found_old:+, found $found_old}"
  return 1
}

read_cache() {
  local node hooks
  [ -f "$CACHE_FILE" ] || return 1
  { IFS= read -r node && IFS= read -r hooks; } < "$CACHE_FILE" || return 1
  # The Volta node shim follows the current project, not the cached CLI's engine.
  [ "$node" != "${VOLTA_HOME:-$HOME/.volta}/bin/node" ] || return 1
  [ -x "$node" ] && has_hook_scripts "$hooks" || return 1
  NODE="$node"
  HOOKS_DIR="$hooks"
}

write_cache() {
  mkdir -p "$CACHE_DIR" 2>/dev/null || return 1
  printf '%s\n%s\n' "$NODE" "$HOOKS_DIR" > "$CACHE_FILE.$$" 2>/dev/null &&
    mv -f "$CACHE_FILE.$$" "$CACHE_FILE" 2>/dev/null
}

emit_session_context() {
  local msg="$1"
  msg=${msg//\\/\\\\}
  msg=${msg//\"/\\\"}
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
}

run_hook() {
  local event="$1" input output explicit_cli
  is_true "${CTXDB_SKIP_HOOKS:-}" && return 0
  global_hooks_present && return 0
  explicit_cli=$(command -v ctxdb 2>/dev/null)
  augment_path
  if [ -z "$explicit_cli" ] && read_cache; then
    :
  elif resolve_runtime; then
    write_cache
  else
    [ "$event" = session-start ] && emit_session_context "ContextDB plugin is installed but inactive: $RESOLVE_ERROR. Cloud memory and knowledge recall are off in this session. If the user asks about ContextDB, memory, or knowledge bases, suggest running /contextdb:setup."
    return 0
  fi
  if [ "$event" = session-start ]; then
    input=$(cat)
    output=$(printf '%s' "$input" | "$NODE" "$HOOKS_DIR/session-start.js" "--agent=$AGENT")
    if [ -n "$output" ]; then
      printf '%s\n' "$output"
    else
      emit_session_context "ContextDB returned no context for this session; it may not be connected for $AGENT yet. If the user asks about ContextDB, memory, or knowledge bases, suggest running /contextdb:setup."
    fi
  else
    "$NODE" "$HOOKS_DIR/$event.js" "--agent=$AGENT"
  fi
  return 0
}

doctor() {
  local ok=0 skills="" d
  augment_path
  echo "plugin_root: $PLUGIN_ROOT"
  echo "host_home: $HOST_HOME"
  echo "agent: $AGENT"
  if global_hooks_present; then
    echo "hook_owner: global ($SETTINGS has ctxdb hook entries; plugin hooks defer to them)"
  else
    echo "hook_owner: plugin"
  fi
  if resolve_runtime; then
    echo "ctxdb: $CTXDB_BIN"
    echo "ctxdb_version: $("$CTXDB_BIN" --version 2>/dev/null || echo unknown)"
    echo "node: $NODE ($("$NODE" --version 2>/dev/null))"
    echo "hooks_dir: $HOOKS_DIR"
    if write_cache; then echo "runtime_cache: $CACHE_FILE"; else echo "runtime_cache: write failed ($CACHE_FILE)"; fi
  else
    echo "runtime: unavailable ($RESOLVE_ERROR)"
    ok=1
  fi
  for d in "$HOST_HOME"/skills/contextdb-*; do
    [ -f "$d/SKILL.md" ] && skills="$skills ${d##*/}"
  done
  echo "user_level_skills:${skills:- none}"
  return "$ok"
}

case "${1:-}" in
  session-start|user-prompt-submit|stop) run_hook "$1"; exit 0 ;;
  doctor) doctor; exit $? ;;
  *) exit 0 ;;
esac
