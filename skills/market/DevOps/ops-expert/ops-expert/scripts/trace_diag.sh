#!/usr/bin/env bash
# =============================================================================
# trace_diag.sh — 故障排查信息收集（只读 · 打包，便于事后分析）
# 按层采集: 主机/CPU/内存/IO/网络/进程/日志/内核，输出 tar.gz 到指定目录。
# 用法: bash trace_diag.sh [--out /tmp/diag] [--minutes 10]
# 注意: 仅读取与打包，不修改系统；含日志可能含敏感信息，妥善保管。
# =============================================================================
set -uo pipefail
OUT="/tmp/diag"; MINS=10
while [ $# -gt 0 ]; do case "$1" in --out) OUT="$2"; shift 2;; --minutes) MINS="$2"; shift 2;; *) shift;; esac; done
D="$OUT/diag-$(date +%Y%m%d%H%M%S)"; mkdir -p "$D"
c(){ local f="$1"; shift; echo ">> $f"; { eval "$@" 2>&1 || echo "(cmd failed: $*)"; } > "$D/$f" 2>&1; }

echo "采集诊断数据到 $D ..."
c 00_host.txt "uname -a; echo '---'; cat /etc/os-release; echo '---'; uptime; echo '---'; timedatectl 2>/dev/null"
c 01_cpu.txt "top -b -n1 | head -20; echo '--- mpstat ---'; mpstat -P ALL 1 3 2>/dev/null; echo '--- pidstat ---'; pidstat -u 1 3 2>/dev/null"
c 02_mem.txt "free -h; echo '--- vmstat ---'; vmstat 1 3; echo '--- oom ---'; dmesg -T 2>/dev/null | grep -i -E 'oom|kill' | tail -20"
c 03_io.txt "iostat -x 1 3 2>/dev/null; echo '--- iotop ---'; iotop -b -n1 2>/dev/null | head -20; echo '--- df ---'; df -h; echo '--- df-i ---'; df -i; echo '--- deleted ---'; lsof 2>/dev/null | grep deleted | head -20"
c 04_net.txt "ss -s; echo '--- listen ---'; ss -lntp; echo '--- estab top ---'; ss -tn state established 2>/dev/null | wc -l; echo '--- netstat ---'; netstat -s 2>/dev/null | head -40; echo '--- conntrack ---'; conntrack -S 2>/dev/null | head"
c 05_proc.txt "ps -eo pid,ppid,stat,rss,pcpu,comm --sort=-pcpu | head -20; echo '--- top mem ---'; ps -eo pid,ppid,stat,rss,comm --sort=-rss | head -20"
c 06_sysctl.txt "sysctl -a 2>/dev/null | grep -E 'fs.file-max|swappiness|tcp_tw_reuse|somaxconn|rmem|wmem|netdev_max' "
c 07_dmesg.txt "dmesg -T 2>/dev/null | tail -50"
c 08_journal_err.txt "journalctl -p err -x --since '-${MINS}min' 2>/dev/null | tail -60"
c 09_limits.txt "cat /proc/sys/fs/file-nr; echo '---'; ulimit -a"
c 10_meta.txt "echo collection_time=$(date); echo kernel=$(uname -r); echo hostname=$(hostname)"

tar -czf "$D.tar.gz" -C "$OUT" "$(basename "$D")" 2>/dev/null && echo "已生成: $D.tar.gz" && ls -lh "$D.tar.gz"
