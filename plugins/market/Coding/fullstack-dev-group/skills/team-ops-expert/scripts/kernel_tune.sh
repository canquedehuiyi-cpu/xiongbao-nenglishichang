#!/usr/bin/env bash
# =============================================================================
# kernel_tune.sh — Linux 内核/系统性能调优（备份当前值 · 可回滚 · 需确认）
# 应用一组常见性能参数(文件描述符/内存/网络栈)。每项先记录原值，便于回滚。
# 用法:
#   bash kernel_tune.sh --apply     # 应用(改前备份到 /etc/sysctl.d/.bak)
#   bash kernel_tune.sh --rollback  # 回滚到备份
#   bash kernel_tune.sh --show      # 仅显示将应用的参数
# 警告: 仅在高并发/网关等确有瓶颈场景使用；改前请阅读 references/optimization.md。
# =============================================================================
set -euo pipefail
MODE=""; for a in "$@"; do case "$a" in --apply|--rollback|--show) MODE="${a#--}";; esac; done
[ -z "$MODE" ] && { echo "用法: $0 --apply|--rollback|--show"; exit 1; }

BAK_DIR="/etc/sysctl.d/.bak"; CONF="/etc/sysctl.d/99-ops-perf.conf"
mkdir -p "$BAK_DIR"

# 参数集合: name|value
PARAMS=(
  "fs.file-max|1000000"
  "vm.swappiness|10"
  "vm.dirty_ratio|10"
  "vm.dirty_background_ratio|5"
  "net.core.rmem_max|16777216"
  "net.core.wmem_max|16777216"
  "net.core.netdev_max_backlog|65536"
  "net.core.somaxconn|65535"
  "net.ipv4.tcp_tw_reuse|1"
  "net.ipv4.tcp_fin_timeout|30"
  "net.ipv4.tcp_keepalive_time|600"
  "net.ipv4.tcp_max_syn_backlog|65535"
  "net.ipv4.ip_local_port_range|1024 65535"
  "net.ipv4.tcp_rmem|4096 87380 16777216"
  "net.ipv4.tcp_wmem|4096 65536 16777216"
)

show(){
  for p in "${PARAMS[@]}"; do IFS='|' read -r k v <<< "$p"; printf '  %-40s = %s\n' "$k" "$v"; done
}
rollback(){
  if [ -f "$BAK_DIR/sysctl.bak" ]; then
    cp -a "$BAK_DIR/sysctl.bak" "$CONF"
    sysctl -p "$CONF" && echo "已回滚到备份: $BAK_DIR/sysctl.bak"
  else echo "未找到备份，无法回滚"; exit 1; fi
}
apply(){
  echo "应用前备份当前值 -> $BAK_DIR/sysctl.bak"
  : > "$BAK_DIR/sysctl.bak"
  for p in "${PARAMS[@]}"; do
    IFS='|' read -r k v <<< "$p"
    cur=$(sysctl -n "$k" 2>/dev/null || echo "n/a")
    echo "$k = $cur" >> "$BAK_DIR/sysctl.bak"
    sysctl -w "$k=$v" >/dev/null && echo "  set $k = $v (was $cur)" || echo "  FAIL $k"
  done
  printf '%s\n' "${PARAMS[@]}" | awk -F'|' '{print $1" = "$2}' > "$CONF"
  echo "已持久化到 $CONF ; 重启后生效需确认加载。"
}

case "$MODE" in
  show) echo "将应用的参数:"; show;;
  rollback) rollback;;
  apply)
    read -r -p "确认应用以上内核参数？(已自动备份原值) [y/N] " r
    [[ "$r" =~ ^[Yy]$ ]] && apply || echo "已取消";;
esac
