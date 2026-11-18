# 故障排查与解决（从 SKILL.md §四 展开）

本文件提供分层排查方法论、RED/USE 黄金信号、典型故障决策树与止血动作。配套
`scripts/trace_diag.sh`（按层采集诊断数据）。**铁律：止血优先于根因。**

## 1. 分层排查方法论（自顶向下，逐层证伪）

```
应用层(进程/日志/依赖) → 系统层(CPU/内存/IO/文件句柄) → 网络层(连通/延迟/丢包)
→ 存储层(磁盘/挂载/RAID) → 硬件层(温度/内存/ECC/电源)
```
- 每下降一层前，先在该层用证据排除（不要跳层猜）。
- 优先看**黄金信号**快速定位是哪一类（延迟/错误/饱和/利用率）。

## 2. 黄金信号

### 2.1 RED（请求型服务）
- **Rate** 速率：QPS 是否异常变化。
- **Errors** 错误：错误率（4xx/5xx/超时/异常）是否上升。
- **Duration** 耗时：P50/P95/P99 延迟是否劣化。

### 2.2 USE（资源型）
- **Utilization** 利用率：资源忙的百分比（CPU%/磁盘 busy%）。
- **Saturation** 饱和度：队列/等待（run queue、TCP 重传、IO await）。
- **Errors** 错误：设备/资源错误（NIC errors、ECC、ENOMEM）。

## 3. 通用排查工具箱（详见 `references/commands.md`）

| 层 | 先看 | 再深挖 |
|----|------|--------|
| 应用 | 日志、进程状态、端口监听 | `strace`/`perf`/`jstack`、依赖探活 |
| CPU | `top`/`mpstat` us/sy/wa | `pidstat -u`、`perf top`、火焰图 |
| 内存 | `free -h`、`vmstat` | `smem`、泄漏进程、`dmesg\|grep oom` |
| IO | `iostat -x 1`、`iotop` | `blktrace`、文件系统、`df -i` |
| 网络 | `ss -s`、`netstat`、重传 | `tcpdump`、`iperf3`、`mtr`、conntrack |
| 磁盘 | `df -h`、`du`、`lsblk` | `lsof\|grep deleted`、`fstrim` |

## 4. 典型故障决策树

### 4.1 CPU 100% 但 QPS 没涨
```
top 看哪个进程/哪个核 → 
  us 高: 应用热点 → perf top / 火焰图 / 死循环
  sy 高: 系统调用/锁 → pidstat、看是否大量上下文切换(vmstat cs)
  wa 高: IO 瓶颈 → iostat -x 看 await/%util
  si 高: 软中断(网卡) → mpstat -P ALL 看 si，网卡多队列/RPS
止血: 限流 / 摘流量 / 重启实例(确认无状态) / 扩容
```

### 4.2 内存吃满 / OOM
```
free -h 看 used/cache/available → 
  available 仍大: 误判(cache 可回收)，无需处理
  truly 满: dmesg|grep -i oom 看被杀进程 → 
  定位泄漏进程(smem/pmap) → 止血: 重启/扩容/限流
  检查 swap 是否被用尽(颠簸)
```

### 4.3 磁盘满（df 满但 du 对不上）
```
df -h 确认挂载点 → lsof | grep deleted 找被删但仍占用的文件 → 
  重启持有进程或 truncate → df -i 看 inode 是否耗尽 → 
  查挂载覆盖(某目录被挂载掩盖了底层文件)
```

### 4.4 端口不通（ping 通但服务连不上）
```
ss -lntp 看是否监听 0.0.0.0/正确端口 → 
  本地 curl 127.0.0.1:port → 通: 网络/防火墙问题
  不通: 服务未起/应用层拒绝
  网络侧: iptables/firewalld、安全组、selinux、源地址限制
```

### 4.5 连接数暴增 / TIME_WAIT 过多
```
ss -s 看 TCP 各状态 → TIME_WAIT 多: 短连接+高并发 → 
  tcp_tw_reuse=1 / 连接复用 / 改长连接 → 
  ESTABLISHED 多且不释放: 连接池耗尽/下游慢/未设超时
```

### 4.6 DNS 偶发失败/慢
```
dig +trace 域名 → 看哪一级慢/失败 → 
  resolv.conf 配多个 DNS、加 nscd/systemd-resolved 缓存 → 
  查 DNS 服务器健康与限速
```

### 4.7 时间漂移导致证书/Token 失败
```
timedatectl 看 offset → chrony/ntpd 是否同步 → 
  大漂移先手动 ntpdate 再起服务；应用(如 Kerberos/JWT)对时钟敏感
```

## 5. 止血动作库（先恢复业务）

| 现象 | 止血动作 | 注意 |
|------|----------|------|
| 服务假死 | 摘流量(下线节点) + 重启 | 确认无状态/可丢现场再重启 |
| 依赖慢 | 降级/熔断/超时调整/限流 | 保护核心链路 |
| 发布引入 | 立即回滚到上一版本 | 见 `references/deployment.md` |
| 资源打满 | 扩容/临时升配/杀异常进程 | 先备份再杀 |
| 网络攻击 | 封 IP/限流/切高防 | 与网络安全协同 |
| 数据风险 | 先快照/备份再操作 | 不可恢复操作前置 |

## 6. 根因分析（恢复后做）

1. 收集证据：`scripts/trace_diag.sh` 打包当时诊断数据 + 日志 + 监控截图。
2. 时间线对齐：变更、告警、用户反馈的时间点交叉比对（是否紧跟某次发布/配置）。
3. 提出假设 → 用证据证伪/证实 → 定位直接原因与深层原因（流程/架构/监控盲区）。
4. 输出 Postmortem（见 `references/work-planning.md` §5），措施可跟踪。

## 7. 避坑
- 不要"先猜后验"：用数据证伪，而非凭经验拍脑袋。
- 不要为查根因拖延止血：业务恢复优先。
- 不要在生产直接做破坏性实验：先摘流量/灰度/备份。
- 复现很重要：能稳定复现的问题，一半已经解决。
