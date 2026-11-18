#!/usr/bin/env bash
# =============================================================================
# pre_deploy_check.sh — 上线前检查（只读校验 · 发布门禁前置）
# 校验: 磁盘/内存/负载/端口/依赖探活/备份存在性/健康检查端点。
# 任一项失败则非零退出，提示阻断发布。
# 用法:
#   bash pre_deploy_check.sh --disk 85 --mem 90 --ports 8080,9090 \
#        --health http://127.0.0.1:8080/health --backup /backup/app-$(date +%F).tar.gz
# 参数均可选；未给则跳过该项。
# =============================================================================
set -uo pipefail
DISK=85; MEM=90; PORTS=""; HEALTH=""; BACKUP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --disk) DISK="$2";; --mem) MEM="$2";; --ports) PORTS="$2";;
    --health) HEALTH="$2";; --backup) BACKUP="$2";; *) ;;
  esac; shift 2>/dev/null || shift
done

FAIL=0; ok(){ echo "✓ $1"; }; no(){ echo "✗ $1"; FAIL=1; }

echo "== 上线前检查 ($(date)) =="

# 磁盘
while read -r mp pct; do
  pnum=${pct%\%}
  if [ "${pnum:-0}" -ge "$DISK" ]; then no "磁盘 $mp 使用率 $pct ≥ ${DISK}%"; else ok "磁盘 $mp 使用率 $pct"; fi
done < <(df -h -P | awk 'NR>1 && $5 ~ /%/ {print $6, $5}')

# 内存(available 占比)
if command -v free >/dev/null 2>&1; then
  av=$(free | awk '/Mem:/{printf "%.0f", $7/$2*100}' 2>/dev/null)
  if [ "${av:-100}" -lt "$((100-MEM))" ]; then no "可用内存 ${av}% < 预留 ${MEM}%"; else ok "可用内存 ${av}%"; fi
else ok "free 不可用，跳过内存检查"; fi

# 端口监听
if [ -n "$PORTS" ] && command -v ss >/dev/null 2>&1; then
  IFS=',' read -ra PA <<< "$PORTS"
  for p in "${PA[@]}"; do
    if ss -lnt 2>/dev/null | grep -q ":$p "; then ok "端口 $p 监听中"; else no "端口 $p 未监听"; fi
  done
fi

# 依赖探活
if [ -n "$HEALTH" ]; then
  if command -v curl >/dev/null 2>&1; then
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$HEALTH" 2>/dev/null || echo 000)
    [ "$code" = "200" ] && ok "健康检查 $HEALTH -> $code" || no "健康检查 $HEALTH -> $code"
  else no "curl 不可用，无法探活 $HEALTH"; fi
fi

# 备份存在
if [ -n "$BACKUP" ]; then
  [ -e "$BACKUP" ] && ok "备份存在: $BACKUP" || no "备份缺失: $BACKUP"
fi

echo "== 检查结束 =="
if [ "$FAIL" = 1 ]; then echo "存在失败项，建议暂停发布并升级负责人。"; exit 1; fi
echo "全部通过，可进入发布流程(仍须遵循 deployment.md 门禁)。"; exit 0
