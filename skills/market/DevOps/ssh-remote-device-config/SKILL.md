---
name: ssh-remote-device-config
description: SSH远程登录网络设备（H3C/华为Comware等）并执行配置脚本。支持单台和批量模式，从Excel读取IP列表自动匹配配置txt文件，支持旧SSH算法(ssh-rsa/ssh-dss)，自动进入system-view、逐行执行命令、检测错误、保存配置。当用户需要远程登录交换机/路由器/防火墙配置设备、批量下发配置脚本、IPv6改造配置时使用。
---

# SSH远程登录网络设备配置

## 适用场景

- H3C / 华为 Comware 系列交换机、路由器、防火墙
- 设备仅支持旧SSH算法（ssh-rsa / ssh-dss），需用 paramiko 2.x
- 批量下发配置脚本（如IPv6改造、ACL更新、VLAN调整等）
- 配置后验证（SSH登录设备执行 display 命令检查配置是否生效）

## 依赖

```bash
pip install "paramiko==2.12.0" openpyxl
```

> paramiko 必须用 2.x 版本，5.x 已移除 ssh-rsa/ssh-dss 支持，无法连接老旧设备。

## 工具一览

| 脚本 | 用途 |
|------|------|
| `scripts/ssh_device_config.py` | 单台设备配置下发 |
| `scripts/batch_device_config.py` | 批量设备配置下发（支持断点续传） |
| `scripts/verify_device_config.py` | 批量验证设备配置是否生效 |

## 配置文件（txt）格式

```
=== 设备名称(10.x.x.x) ===          ← 标题行，自动跳过
system-view                          ← 自动进入，无需手写
vlan 100                             ← 逐行执行
 name IPv6-Users
 quit
interface Vlan-interface 100         ← 空行和 # 分隔符自动跳过
 ipv6 address 2001:db8::1/64
 undo shutdown
return                               ← 自动执行，无需手写
save force                           ← 自动执行，无需手写
```

规则：
- `===` 开头的行 → 跳过
- 空行 / 仅 `#` 的行 → 跳过
- `system-view` / `return` / `save force` → 脚本自动处理，txt 中不要写
- 其余行 → 逐行发送，每行间隔 0.5 秒

## 单台设备配置

```bash
python scripts/ssh_device_config.py \
  --ip 10.0.0.1 \
  --user admin \
  --config /path/to/设备名称(10.0.0.1).txt \
  --passwords "密码1,密码2,密码3" \
  --port 22
```

输出 JSON 格式结果到 stdout，包含：
- `success`: 是否连接成功
- `password_used`: 实际使用的密码
- `save_success`: 配置是否保存成功
- `errors`: 执行过程中遇到的命令错误（如有）

## 批量设备配置

```bash
python -u scripts/batch_device_config.py \
  --excel /path/to/管理信息表.xlsx \
  --config-dir /path/to/configs/ \
  --user admin \
  --passwords "密码1,密码2,密码3" \
  --col 26 \
  --start-row 159 \
  --end-row 382 \
  --log result.json
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--excel` | Excel文件路径 |
| `--config-dir` | 配置文件(txt)所在目录 |
| `--user` | SSH登录用户名 |
| `--passwords` | 密码候选列表，逗号分隔，按顺序逐个尝试 |
| `--col` | Excel中IP所在的列号（默认26即Z列） |
| `--start-row` / `--end-row` | 处理的Excel行范围（含header行，数据从第2行开始） |
| `--log` | 结果日志文件路径（默认 batch_result.json） |
| `--name-col` | 设备名称所在列号（默认1即A列） |
| `--preflight` | 仅检查IP与配置文件匹配关系，不实际连接设备 |

### IP与配置文件匹配规则

配置文件命名格式：`设备名称(IP).txt`
脚本通过 `*(IP).txt` 模式精确匹配，确保IP与配置文件一一对应，杜绝错配。

### 自动跳过规则

- IP列为空 → 跳过
- IP列包含"不在线"或"离线" → 跳过
- IP格式不合法（非 x.x.x.x） → 跳过
- 找不到对应IP的txt文件 → 跳过
- 已在log中标记为OK的IP → 跳过（断点续传）

### 预检模式（--preflight）

正式批量执行前，务必先用预检模式确认匹配关系：

```bash
python scripts/batch_device_config.py \
  --excel /path/to/管理信息表.xlsx \
  --config-dir /path/to/configs/ \
  --user admin \
  --passwords "密码1" \
  --col 26 \
  --start-row 159 \
  --end-row 382 \
  --preflight
```

输出：
- 总行数、可匹配数、跳过数
- 每个IP对应的配置文件路径
- 未匹配的IP列表
- 匹配成功但无txt文件的IP列表

### 断点续传

如果中途断开（网络问题、手动中断等），重新执行相同命令即可。脚本会读取 `--log` 文件，自动跳过已成功的设备。

### 密码重试

按 `--passwords` 顺序逐个尝试，成功即停止。典型场景：
- 不确定设备密码 → 提供多个候选密码
- 部分设备密码不同 → 按常见程度排序

## 配置验证

配置完成后，批量SSH登录设备执行验证命令，确认配置已生效：

```bash
python -u scripts/verify_device_config.py \
  --log result.json \
  --user admin \
  --command "display ipv6 interface brief" \
  --check-keyword "GE" "Vlan" "::" \
  --verify-log verify_result.json
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--log` | 配置阶段的结果日志（从中读取IP、密码等信息） |
| `--user` | SSH用户名 |
| `--command` | 验证命令（默认 `display ipv6 interface brief`） |
| `--check-keyword` | 输出中包含任一关键词即视为验证通过（可多个） |
| `--verify-log` | 验证结果日志文件 |
| `--export-csv` | 导出IP-密码映射到CSV文件 |

### 验证结果

- `OK` + `check_passed: true` → 配置已生效
- `OK` + `check_passed: false` → SSH成功但配置可能未生效
- `FAILED` → SSH连接失败（超时或密码错误）

## 标准工作流程

### 第一步：准备

1. 确认用户提供了：IP列表(Excel)、用户名、密码候选、配置文件目录
2. 确认配置文件命名格式为 `设备名称(IP).txt`

### 第二步：预检验证

```
必须！在批量执行前确认IP与配置文件的匹配关系
目标：0个错配，所有IP都能找到对应txt
```

### 第三步：单台测试

选一台设备先测试，确认：
- SSH能连上
- 配置命令无报错
- save force 保存成功

### 第四步：批量执行

- 用 `python -u` 确保实时输出
- 用户可实时看到每台设备的进度
- 中途断开可断点续传

### 第五步：验证

- 用 verify 脚本批量检查配置是否生效
- 汇报：成功数、失败数、失败设备列表及原因

### 第六步：更新台账

- 根据结果更新Excel相关列（如AB列标记"已粘贴脚本"）
- 更新密码列（将实际成功的密码写入管理信息表）

## 错误分类

| 错误类型 | 表现 | 处理建议 |
|----------|------|----------|
| 连接超时 | `timed out` | 设备离线或网络不通，标记"设备不在线" |
| 密码错误 | `Authentication failed` | 密码不对，尝试其他密码或人工确认 |
| 命令错误 | 输出含 `Error` | 配置脚本语法问题，检查txt文件 |
| 保存失败 | save输出无 `successfully` | 设备存储问题，手动登录检查 |

## 注意事项

- H3C Comware设备仅支持 ssh-rsa/ssh-dss，必须用 paramiko 2.x（5.x 已移除支持）
- 进入 system-view 后逐行发送命令，每行间隔 0.5 秒
- 配置完成后自动执行 `return` 退出 system-view，再 `save force` 保存
- 连接超时 15 秒自动跳过，不阻塞后续设备
- 批量执行时务必用 `python -u` 关闭输出缓冲，便于实时监控
- 配置文件txt中不要写 `system-view`、`return`、`save force`，脚本会自动处理
