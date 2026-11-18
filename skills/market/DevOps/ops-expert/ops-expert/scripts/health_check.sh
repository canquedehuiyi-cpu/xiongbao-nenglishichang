#!/usr/bin/env bash
# =============================================================================
# health_check.sh — Linux 系统健康巡检（只读 · 无副作用）
# 采集: 主机/CPU/内存/磁盘/IO/网络/连接/关键进程/服务，输出可读报告。
# 用法:
#   bash health_check.sh                 # 打印到终端
#   bash health_check.sh --out /tmp/hc.md # 同时写入文件
# 退出码: 0 正常; 2 存在需关注(红)项。
# =============================================================================
set -uo pipefail
OUT=""; for a in "$@"; do case "$a" in --out) OUT="${2:-}";; esac; done
REPORT=""; RED=0

push(){ REPORT+="$1"$'\n'; }

sec(){ push ""; push "## $1"; }
kv(){ push "| $1 | $2 |"; }
tbl_h(){ push "| 项 | 值 |"; push "|----|----|"; }

if [ -f /etc/os-release ]; then . /etc/os-release; OS="$PRETTY_NAME"; else OS="$(uname -s)"; fi

push "# 系统健康巡检报告"; push "_生成时间: $(date '+%F %T %Z')_"
sec "1. 主机信息"; tbl_h
kv "主机名" "$(hostname -f 2>/dev/null || hostname)"
kv "系统" "$OS"
kv "内核" "$(uname -r)"
kv " uptime" "$(uptime -p 2>/dev/null || uptime)"
kv "时间同步" "$(timedatectl 2>/dev/null | grep -i 'synchronized' || echo 'n/a')"

sec "2. CPU 与负载"; tbl_h
LOAD=$(awk '{print $1, $2, $3}' /proc/loadavg); kv "loadavg(1/5/15)" "$LOAD"
CPU_N=$(nproc); kv "逻辑核数" "$CPU_N"
if command -v mpstat >/dev/null 2>&1; then
  IDLE=$(mpstat 1 1 2>/dev/null | awk '/Average/ && $NF ~ /[0-9]/ {print 100-$NF}' | tail -1)
  kv "CPU 空闲%" "${IDLE:-n/a}"
fi

sec "3. 内存"; tbl_h
if command -v free >/dev/null 2>&1; then
  free -h | awk 'NR==1||NR==2' | while read -r l; do push "| $l |"; done
fi

sec "4. 磁盘"; tbl_h
df -h -P | awk 'NR==1 || $5+0 >= 0 {print}' | while read -r fs sz used avail pct mp; do
  pnum=${pct%\%}; if [ "${pnum:-0}" -ge 85 ]; then RED=1; warn="⚠ 关注"; else warn="✓"; fi
  push "| $mp | $used/$sz ($pct) | $warn |"
done

sec "5. IO 等待"; tbl_h
if command -v iostat >/dev/null 2>&1; then
  iostat -x 1 2 2>/dev/null | awk 'NR>1 && $0 ~ /^[a-z]/ {print "| "$1" | util="$NF" |"}' | head -10
else
  kv "iostat" "未安装(sysstat)，跳过"
fi

sec "6. 网络与连接"; tbl_h
if command -v ss >/dev/null 2>&1; then
  ss -s 2>/dev/null | sed 's/^/| /; s/$/ |/'
else
  kv "ss" "未安装，跳过"
fi

sec "7. 关键进程/服务"; tbl_h
for s in sshd cron rsyslog chronyd firewalld; do
  if systemctl is-active --quiet "$s" 2>/dev/null; then kv "$s" "active ✓"; else kv "$s" "inactive"; fi
done

sec "8. 结论"
if [ "$RED" = 0 ]; then push "✓ 未发现红色(≥85%磁盘)项。建议归档本报告作为基线。"; else push "⚠ 存在磁盘使用率≥85%的项，请尽快处理。"; fi

echo "$REPORT"
if [ -n "$OUT" ]; then printf '%s\n' "$REPORT" > "$OUT"; log "报告已写入 $OUT"; fi
[ "$RED" = 0 ] && exit 0 || exit 2
