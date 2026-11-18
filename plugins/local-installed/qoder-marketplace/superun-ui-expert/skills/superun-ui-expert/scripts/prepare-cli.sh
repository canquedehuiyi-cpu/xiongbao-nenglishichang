#!/bin/sh
# 兼容 Shell 启动器，原生 Windows 可直接执行同目录 mjs。@author xiuyu.yi
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runtime=${SUPERUN_KIT_NODE:-}
if [ -z "$runtime" ]; then runtime=$(command -v node 2>/dev/null || true); fi
if [ -z "$runtime" ] && [ -n "${QODER_NODE_RUNTIME:-}" ] && [ -x "$QODER_NODE_RUNTIME" ]; then
  runtime=$QODER_NODE_RUNTIME
  export ELECTRON_RUN_AS_NODE=1
fi
if [ -n "$runtime" ] && [ -x "$runtime" ]; then
  entry="$script_dir/prepare-cli.mjs"
  if [ "$("$runtime" -p 'process.platform')" = win32 ]; then
    if command -v cygpath >/dev/null 2>&1; then entry=$(cygpath -w "$entry");
    elif command -v wslpath >/dev/null 2>&1; then entry=$(wslpath -w "$entry"); fi
  fi
  exec "$runtime" "$entry" "$@"
fi
case " $* " in
  *' --hook '*) printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"superun CLI 准备失败：NODE_REQUIRED。请宿主准备兼容 Node/npm 后重试原任务。"}}';;
  *) printf '%s\n' '{"schemaVersion":1,"ok":false,"code":"NODE_REQUIRED","results":[]}'; exit 1;;
esac
