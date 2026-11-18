# 分层命令速查（从 SKILL.md §四 展开）

本文件是按排查层级组织的 Linux 命令速查，便于"看到现象 → 直接取命令"。完整方法论见
`references/troubleshooting.md` 与 `references/optimization.md`。命令默认在目标服务器执行，
生产操作遵循 SKILL.md §六 安全准则。

## 1. 主机与系统信息
```bash
uname -a                      # 内核/架构
hostnamectl                   # 主机名/系统版本
uptime / w                    # 负载/在线用户
timedatectl                   # 时区/时钟同步
cat /etc/os-release           # 发行版
lscpu / lsmem                 # CPU/内存拓扑
```

## 2. CPU
```bash
top -H / htop                 # 实时(线程视角)
mpstat -P ALL 1               # 每核 us/sy/id/wa/irq
pidstat -u 1 -p <pid>         # 进程 CPU
vmstat 1                      # 上下文切换(cs)/等待(wa)
perf top -p <pid>             # 热点函数
sar -u 1 5                    # 历史 CPU
```

## 3. 内存
```bash
free -h                       # 总量/可用
vmstat 1                      # si/so 是否 swap 颠簸
smem -s rss -r -p <pid>       # 进程常驻
cat /proc/<pid>/status | grep Vm  # 进程虚拟/常驻
dmesg | grep -i oom           # OOM 记录
```

## 4. IO 与 磁盘
```bash
iostat -x 1                   # await/%util/rsv 关键
iotop -o                      # 按进程 IO
df -h / df -i                 # 空间/inode
du -sh * | sort -h            # 目录占用
lsblk / fdisk -l              # 块设备
lsof | grep deleted           # 已删仍占用
fio --rw=randread --bs=4k ... # 基准
```

## 5. 网络
```bash
ss -s / ss -lntp / ss -tnp   # 统计/监听/连接
ip -s link / ip addr          # 网卡/流量
ethtool -S <dev>              # 网卡错误/丢包
netstat -s / nstat            # 协议栈统计(重传等)
iptables -L -n / nft list     # 防火墙
tcpdump -i any -n port 80     # 抓包
mtr -n <host>                 # 路由+丢包
iperf3 -c <host>              # 带宽基准
conntrack -S                  # 连接跟踪表
```

## 6. 进程与服务
```bash
ps -eo pid,ppid,stat,rss,comm -p <pid>
systemctl status <svc>        # 服务状态
journalctl -u <svc> -f --since "-10m"
strace -p <pid> -e trace=network,read,write  # 系统调用
lsof -p <pid>                 # 打开的文件/套接字
kill -<sig> <pid>             # 发送信号(谨慎)
```

## 7. 内核参数
```bash
sysctl -a | grep <key>        # 查看
sysctl -w net.ipv4.tcp_tw_reuse=1   # 临时改(重启失效)
sysctl -p /etc/sysctl.d/99-ops.conf # 持久化加载
cat /proc/sys/fs/file-max      # 文件描述符上限
```

## 8. 巡检（一键）
```bash
bash scripts/health_check.sh              # 全量关键指标
bash scripts/trace_diag.sh --out /tmp/diag # 故障信息收集打包
```

## 9. 日志
```bash
journalctl -p err -x --since "-1h"    # 错误日志
tail -f /var/log/messages
grep -i "error\|fail\|timeout" <log>  # 关键词扫描
dmesg -T | tail                      # 内核环缓冲
```

## 10. 安全
```bash
last / lastb                    # 登录/失败登录
faillog -a                      # 失败计数
ss -tnp | grep :22              # SSH 连接
sudo -l -U <user>               # 用户 sudo 权限
ausearch -m avc -ts recent      # SELinux 拒绝
```

> 说明：本表为速查，参数需按环境调整；涉及重启/杀进程/改防火墙务必先确认与备份。
