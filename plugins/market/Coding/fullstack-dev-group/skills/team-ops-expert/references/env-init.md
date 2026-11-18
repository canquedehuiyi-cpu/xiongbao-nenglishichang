# 基础环境初始化（从 SKILL.md §四 展开）

本文件提供新服务器标准化初始化基线、安全加固项与内核基础参数。配套脚本 `scripts/server_init.sh`
（幂等、含确认与回滚点）。目标：让任意新机"上线即合规、可监控、可回滚"。

## 1. 初始化清单（顺序即执行序）

| 阶段 | 项 | 关键动作 | 验证 |
|------|----|----------|------|
| 1 主机标识 | 主机名、hosts | `hostnamectl set-hostname`、补 `/etc/hosts` | `hostname -f` |
| 2 时间 | 时区、NTP | `timedatectl set-timezone Asia/Shanghai`、装 `chrony` | `timedatectl`、`ntpq -p` |
| 3 系统更新 | 安全补丁 | `yum/apt update` + 安全更新（非全量升级，避免动大版本） | `rpm -qa`/`dpkg -l` |
| 4 用户与权限 | 普通用户、sudo、SSH key | 建运维用户、`sudo` 无密码或精细化、禁用 root 登录 | `sudo -l`、`ssh` 测试 |
| 5 SSH 加固 | 端口、协议、认证 | 禁 root 登录、禁密码、仅 key、改非标端口(可选) | `sshd -t` + 重连 |
| 6 防火墙 | firewalld/iptables/nft | 默认 deny、按需放行业务端口 | `iptables -L`/`nft list` |
| 7 基线工具 | 诊断/监控/编辑 | `vim curl wget net-tools bind-utils htop iotop sysstat dstat lrzsz git` | `which <cmd>` |
| 8 监控 agent | node_exporter / 采集 | 部署并校验指标上报 | Prometheus targets UP |
| 9 日志采集 | rsyslog/filebeat | 统一收集到日志中心 | 日志中心可见 |
| 10 内核基础 | 文件描述符、swap、THP | 见 §3，先备份 | `sysctl -p` 无错 |
| 11 安全基线 | selinux/fail2ban/审计 | 按需开启；fail2ban 防爆破 | `fail2ban-client status` |
| 12 巡检基线 | health_check | 跑 `scripts/health_check.sh` 建基准 | 报告无红 |

## 2. 安全加固要点（含回滚点）

### 2.1 SSH 加固（改前备份 `/etc/ssh/sshd_config`）
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Protocol 2
MaxAuthTries 3
ClientAliveInterval 300
```
- 回滚：保留原 `sshd_config.bak`，改完 `sshd -t` 校验，**另开会话测试登录再断旧连接**。
- 危险点：禁用密码前务必确认 key 已生效，否则会锁死自己。

### 2.2 防火墙（默认拒绝，按白名单放行）
- firewalld：`firewall-cmd --permanent --add-port=<port>/tcp` + `--reload`。
- 回滚：`firewall-cmd --reload` 到上次备份的 `--list-all`；生产机**务必保留当前 SSH 端口放行**。

### 2.3 用户与 sudo
- 建专用运维用户，加入 `wheel`/`sudo`；sudo 精细化（仅需要的命令 NOPASSWD）。
- 禁用不必要的系统账号登录（`/sbin/nologin`）。

### 2.4 fail2ban（防 SSH 爆破）
- 监控 `sshd` 日志，失败 N 次封 IP 一段时间；回滚：`systemctl stop fail2ban`。

## 3. 内核基础参数（先备份，见 `scripts/kernel_tune.sh`）

```ini
# 文件描述符
fs.file-max = 1000000
# swap 倾向（数据库类建议偏低，应用类可调高）
vm.swappiness = 10
# 透明大页（多数数据库建议关闭）
echo never > /sys/kernel/mm/transparent_hugepage/enabled
# 网络基础（高并发见 optimization.md 再细化）
net.ipv4.tcp_tw_reuse = 1
```
- 每项下都有回滚命令；应用用 `sysctl -p` 即时生效并写入 `/etc/sysctl.d/99-ops.conf` 持久化。

## 4. 脚本使用

`scripts/server_init.sh` 设计约定：
- 幂等：重复运行不破坏已配置项（用标记文件/条件判断）。
- 确认：破坏性/加固项运行前 `read` 确认或 `--yes` 显式跳过。
- 备份：改前备份 `sshd_config`、sysctl、sudoers。
- 证据：输出每步结果与最终 `health_check.sh` 摘要。

## 5. 验收标准（初始化完成判据）
- [ ] `timedatectl` 时区正确、NTP 同步中。
- [ ] 普通用户 sudo 正常、root 密码登录已禁、key 登录 OK。
- [ ] 防火墙仅放行必要端口、SSH 可达。
- [ ] 监控 agent 在 Prometheus targets 为 UP。
- [ ] 日志已入中心。
- [ ] `health_check.sh` 无红色项、建立基线报告归档。
