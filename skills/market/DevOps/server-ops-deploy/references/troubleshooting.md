# Troubleshooting Cheatsheet

Fast, copy-paste diagnostics for common Linux server incidents. Run the
`preflight_check.sh` script first for a broad snapshot, then drill in below.

## High CPU / load
```bash
top -b -n1 | head -20                 # one-shot top
ps -eo pid,user,%cpu,comm --sort=-%cpu | head -10
pidstat 1 5                           # per-process over 5s (sysstat)
uptime                                # load vs nproc
```
Load >> core count = saturation. Identify the top PID, then `strace -p PID` or
check its logs before killing anything.

## Out of memory / OOM kills
```bash
dmesg -T | grep -i -E 'oom|killed process' | tail -20
journalctl -k | grep -i oom | tail -20
free -h; vmstat 1 5                   # si/so columns = swapping
```
If a service was OOM-killed, systemd shows `NRestarts` climbing. Fix the leak
or raise memory limits (`systemctl edit <unit>` → `MemoryMax=`).

## Disk full
```bash
df -h                                 # which mount is full
du -xh --max-depth=1 /var 2>/dev/null | sort -rh | head -15
du -xh --max-depth=1 / 2>/dev/null | sort -rh | head -15
journalctl --disk-usage               # systemd journal often the culprit
```
Safe quick wins: `journalctl --vacuum-time=7d`, clear old app logs, remove
dangling Docker images (`docker image prune -f`). Never blind-delete unfamiliar
files.

## Port already in use / can't bind
```bash
ss -ltnp 'sport = :8080'              # who owns the port
ss -ltnp | grep :8080
lsof -i :8080                         # if available
```

## Service won't start
```bash
systemctl status <unit> -l --no-pager # read the tail first
journalctl -u <unit> -n 100 --no-pager
systemctl cat <unit>                  # see effective unit + drop-ins
sudo -u <svcuser> <ExecStart cmd>     # run manually to see the real error
```
Common causes: bad config syntax, missing env file, port clash, wrong
permissions on data dir, missing dependency ordering.

## Nginx 502 / 504 (reverse proxy)
```bash
nginx -t                              # config syntax
tail -50 /var/log/nginx/error.log
curl -sv http://127.0.0.1:<upstream_port>/   # is the backend actually up?
```
502 = upstream refused/unreachable (backend down or wrong port).
504 = upstream timed out (backend slow; tune `proxy_read_timeout`).

## Network / connectivity
```bash
curl -sv -o /dev/null http://host:port/     # app-level reachability
ss -s                                        # socket summary
ping -c3 <host>; traceroute <host>
getent hosts <name>                          # DNS resolution
ss -tnp state established | head             # active connections
```

## High connections / file descriptors
```bash
ss -s                                 # total sockets
cat /proc/<pid>/limits | grep 'open files'
sysctl fs.file-nr                     # allocated vs max
ulimit -n                             # per-shell limit
```

## Slow disk / IO wait
```bash
vmstat 1 5                            # watch 'wa' (iowait) column
iostat -x 1 5                         # %util per device (sysstat)
iotop -oPa                            # per-process IO (needs root)
```

## Recently changed / what broke
```bash
last -n 20                            # recent logins
journalctl --since "2 hours ago" -p err
find /etc -type f -mtime -1 2>/dev/null   # config touched in last day
```

## Incident response order
1. `preflight_check.sh` — get the snapshot.
2. Confirm blast radius: is it one service or the whole box?
3. Read logs *before* restarting (restart destroys evidence).
4. Mitigate (restart/rollback/scale), then root-cause.
5. Note what changed recently — most incidents follow a change.
