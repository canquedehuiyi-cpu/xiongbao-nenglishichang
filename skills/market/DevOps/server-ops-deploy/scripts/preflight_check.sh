#!/usr/bin/env bash
# preflight_check.sh — read-only server health snapshot for ops/deploy decisions.
# Safe to run any time. Exits 0 always; signals problems via WARN/CRIT lines.
set -uo pipefail

HOST=$(hostname 2>/dev/null || echo unknown)
echo "===== PREFLIGHT: $HOST ($(date '+%F %T %Z')) ====="

warn() { echo "WARN: $*"; }
crit() { echo "CRIT: $*"; }
ok()   { echo "OK:   $*"; }

# --- Uptime & load ---
if read -r l1 l5 l15 _ < /proc/loadavg; then
  cores=$(nproc 2>/dev/null || echo 1)
  echo "Load: ${l1} ${l5} ${l15} (cores=${cores})"
  awk -v a="$l1" -v c="$cores" 'BEGIN{exit !(a>c)}' && crit "1m load ${l1} exceeds core count ${cores}"
fi
uptime -p 2>/dev/null | sed 's/^/Uptime: /'

# --- Memory ---
if command -v free >/dev/null 2>&1; then
  free -h | awk 'NR==1||/Mem|Swap/{print}'
  mem_total=$(awk '/MemTotal/{print $2}' /proc/meminfo)
  mem_avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  if [ -n "$mem_total" ] && [ "$mem_total" -gt 0 ]; then
    pct_avail=$(( mem_avail * 100 / mem_total ))
    if [ "$pct_avail" -lt 5 ]; then crit "available memory ${pct_avail}% (<5%)"; 
    elif [ "$pct_avail" -lt 15 ]; then warn "available memory ${pct_avail}% (<15%)"; 
    else ok "available memory ${pct_avail}%"; fi
  fi
fi

# --- Disk ---
echo "-- Disk usage (mounted, >0 size) --"
df -hP -x tmpfs -x devtmpfs 2>/dev/null | awk 'NR==1||NR>1{print}'
df -P -x tmpfs -x devtmpfs 2>/dev/null | awk 'NR>1{gsub(/%/,"",$5); if($5+0>=90) print "CRIT: partition "$6" at "$5"%"; else if($5+0>=80) print "WARN: partition "$6" at "$5"%"}'

# --- Inodes ---
df -iP -x tmpfs -x devtmpfs 2>/dev/null | awk 'NR>1{gsub(/%/,"",$5); if($5+0>=90) print "WARN: inodes on "$6" at "$5"%"}'

# --- Failed systemd units ---
if command -v systemctl >/dev/null 2>&1; then
  failed=$(systemctl --failed --no-legend --plain 2>/dev/null | awk '{print $1}')
  if [ -n "$failed" ]; then
    crit "failed systemd units:"; echo "$failed" | sed 's/^/       /'
  else
    ok "no failed systemd units"
  fi
fi

# --- Listening ports ---
echo "-- Listening TCP ports --"
if command -v ss >/dev/null 2>&1; then
  ss -ltnp 2>/dev/null | awk 'NR==1||NR>1{print}' | head -30
elif command -v netstat >/dev/null 2>&1; then
  netstat -ltnp 2>/dev/null | head -30
fi

# --- Top resource consumers ---
echo "-- Top 5 by CPU --"
ps -eo pid,ppid,user,%cpu,%mem,etime,comm --sort=-%cpu 2>/dev/null | head -6
echo "-- Top 5 by MEM --"
ps -eo pid,ppid,user,%cpu,%mem,etime,comm --sort=-%mem 2>/dev/null | head -6

# --- Zombie / defunct processes ---
zombies=$(ps -eo stat 2>/dev/null | grep -c '^Z')
[ "$zombies" -gt 0 ] && warn "${zombies} zombie process(es) detected"

# --- Common service status (best-effort) ---
for svc in sshd nginx docker mysql postgresql redis-server; do
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "^${svc}.service"; then
    state=$(systemctl is-active "$svc" 2>/dev/null)
    echo "service ${svc}: ${state}"
  fi
done

echo "===== PREFLIGHT DONE ====="
exit 0
