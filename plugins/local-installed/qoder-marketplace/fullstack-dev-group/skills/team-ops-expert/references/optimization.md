# 系统优化（从 SKILL.md §四 展开）

本文件覆盖 Linux 性能调优实战：CPU、内存、IO/文件系统、网络栈、文件描述符与内核参数。
配套 `scripts/kernel_tune.sh`（备份当前值、可回滚）。**铁律：先基准、再调优、留前后证据。**

## 1. 优化通用流程

```
建基准(优化前数据) → 定位瓶颈(USE 信号) → 定向调优(单项变更) → 验证(优化后数据)
→ 对比(确认收益) → 持久化(写入 sysctl.d) → 归档(基准+结果)
```
- 一次只改一个变量，便于归因。
- 每项调优都记录原值与回滚命令（脚本自动备份到 `/etc/sysctl.d/.bak`）。

## 2. CPU 调优
- **调度**：默认 CFS 即可；NUMA 亲和（`numactl --cpunodebind`）对延迟敏感服务有益。
- **中断均衡**：网卡多队列 + `irqbalance` 或手动绑定（`/proc/irq/<n>/smp_affinity`）。
- **上下文切换过高**：查是否过多线程/锁竞争（`pidstat -w`、`cs` in `vmstat`）。
- 基准：`sysbench cpu`、`perf bench`。

## 3. 内存与 swap
```ini
vm.swappiness = 10          # 数据库类调低，减少 swap 颠簸；应用类可 30-60
vm.dirty_ratio = 10         # 脏页占比触发同步刷盘阈值
vm.dirty_background_ratio = 5
vm.overcommit_memory = 0    # 除非明确需要，勿设 1(易 OOM 雪崩)
vm.min_free_kbytes = <物理 1-3%>  # 保留最低内存，避免分配死锁
```
- 关闭透明大页（多数 DB 受益）：`echo never > /sys/kernel/mm/transparent_hugepage/enabled`。
- 基准：`vmstat 1`、`free -h`、`numastat`。

## 4. 文件系统与 IO 调度
- **文件系统**：一般 `ext4` / `xfs`；大文件/高并发倾向 `xfs`。
- **挂载选项**：`noatime`（减少访问时间写）、`data=writeback`(权衡安全)按需。
- **IO 调度器**：SATA/HDD 用 `mq-deadline`；NVMe/SSD 用 `none`(noop) 或 `kyber`。
  - 查看：`cat /sys/block/<dev>/queue/scheduler`；设置：`echo mq-deadline > .../scheduler`。
- **队列深度/readahead**：`/sys/block/<dev>/queue/nr_requests`、`/sys/block/<dev>/queue/read_ahead_kb`。
- 基准：`fio`（randread/randwrite/seq）、`iostat -x 1`。

## 5. 网络栈调优（高并发/网关场景）

```ini
# 连接跟踪(若用 nf_conntrack)
net.netfilter.nf_conntrack_max = 1048576
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 30

# socket 缓冲区
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.netdev_max_backlog = 65536
net.core.somaxconn = 65535

# TCP
net.ipv4.tcp_tw_reuse = 1          # TIME_WAIT 复用(客户端侧安全)
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
```
- **注意**：`tcp_tw_reuse` 仅对出站连接有效；`tcp_tw_recycle` 已废弃（NAT 下会丢包），禁用。
- 基准：`iperf3`、`wrk`/`ab`、连接数压测（`ss -s`）。

## 6. 文件描述符
```ini
fs.file-max = 1000000
```
- 进程级：`/etc/security/limits.conf` + systemd `LimitNOFILE=1048576`。
- 验证：`cat /proc/<pid>/limits | grep "Max open files"`。

## 7. 容量评估方法
- **CPU**：按峰值利用率 ≤70% 留余量；突发用弹性扩容。
- **内存**：常驻 + 峰值 × 安全系数（1.3~1.5）；预留 `min_free_kbytes`。
- **磁盘**：当前增速外推 90 天，预留 30% 水位；IO 看 await/%util 是否触顶。
- **连接**：`ip_local_port_range` 容量 × 单机并发连接上限；conntrack 表余量。
- **带宽**：峰值 × 1.5 冗余；跨 AZ 计费与延迟权衡。

## 8. 验证与证据模板
```
优化前: fio randread  IOPS=xxxx  lat=xxms
优化后: fio randread  IOPS=yyyy  lat=yyms
结论: IOPS +xx%, P99 -xxms  (附命令与输出截图)
```

## 9. 避坑
- 不盲目套用"万能调优"：先测瓶颈在哪一层。
- 不一次改一堆：无法归因且易引入新故障。
- 不忽略持久化：临时 `sysctl -w` 重启失效，必须写 `sysctl.d` 并验证开机生效。
- 内核参数有副作用（如 `overcommit_memory=1` 易 OOM 雪崩），改前读文档。
