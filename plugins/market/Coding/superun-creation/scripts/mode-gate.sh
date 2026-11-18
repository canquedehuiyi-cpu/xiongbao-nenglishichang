#!/bin/sh
# 兼容 Shell 与 Windows Node 的路径格式。@author xiuyu.yi
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runtime=${SUPERUN_KIT_NODE:-}
if [ -z "$runtime" ]; then runtime=$(command -v node 2>/dev/null || true); fi
if [ -z "$runtime" ] && [ -n "${QODER_NODE_RUNTIME:-}" ] && [ -x "$QODER_NODE_RUNTIME" ]; then
  runtime=$QODER_NODE_RUNTIME
  export ELECTRON_RUN_AS_NODE=1
fi
if [ -n "$runtime" ] && [ -x "$runtime" ]; then
  entry="$script_dir/mode-gate.mjs"
  if [ "$("$runtime" -p 'process.platform')" = win32 ]; then
    if command -v cygpath >/dev/null 2>&1; then entry=$(cygpath -w "$entry");
    elif command -v wslpath >/dev/null 2>&1; then entry=$(wslpath -w "$entry"); fi
  fi
  exec "$runtime" "$entry"
fi
printf '%s\n' 'superun 模式检查缺少 Node；请恢复宿主运行环境后重试。未确认模式前不要提交功能选择。' >&2
exit 2
