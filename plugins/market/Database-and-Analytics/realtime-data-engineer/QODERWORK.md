# QODERWORK.md · 实时数据工程师套件团队配置

> 此文件用于在团队/项目层面注入团队规范，让套件 6 个 Skill 在你的实际工作环境下"开箱即用"。
> **首次安装套件后，请按本模板填写并放置在项目根目录或团队 Wiki，套件会自动读取**。
> 任何 `<>` 占位符都需要填写或显式标注 `N/A`。

## 元信息

```yaml
team_name: <你的团队名称>
plugin_owner: <数据 Tech Lead 姓名 / 钉钉 ID>
last_updated: <YYYY-MM-DD>
```

---

## 1. Flink SQL 开发规范（被 Skill 1 + Skill 4 读取）

```yaml
# 命名规范文档路径（团队 Wiki / Git）
flink_sql_naming_convention: <团队 Wiki / Git 链接>

# 团队批准的 connector 版本矩阵
connector_version_matrix:
  vvr_version: <例：vvr-8.0.x>
  kafka_connector: <例：kafka-1.17>
  cdc_connector: <例：mysql-cdc-3.0.x>
  hive_connector: <例：N/A>

# state TTL 默认值（不显式配置时使用）
state_ttl_default: <例：7d>

# checkpoint 配置默认
checkpoint_interval_default: <例：60s>
checkpoint_timeout_default: <例：10min>

# 团队额外红线（除通用 10 条外的团队特有红线）
code_review_extra_rules:
  - <例：禁用 OVER 窗口（性能问题）>
  - <例：所有任务必须配 cancel_with_savepoint 流程>
  - <>
```

---

## 2. 指标口径与数据规范（被 Skill 2 读取）

```yaml
# 团队口径文档模板（如有，否则用 Skill 默认模板）
metric_doc_template_path: <团队 Wiki 链接>

# 文档归档位置
metric_doc_storage:
  platform: <钉钉文档 / Confluence / Wiki>
  root_path: <>

# 业务日切点（影响时间口径）
business_day_cutoff: <例：00:00 UTC+8 / 04:00 UTC+8 / N/A>

# 时区默认
timezone_default: <例：UTC+8>
```

---

## 3. 数据质量监控（被 Skill 3 读取）

```yaml
# DQC 平台
dqc_platform: <DataWorks DQC / 自建>
dqc_platform_url: <>

# 告警通道
alert_channel_p0:
  - <例：短信:on-call-list>
  - <例：电话:on-call-list>
  - <例：钉钉群:1234567>
alert_channel_p1:
  - <例：钉钉群:1234567>
  - <例：邮件:data-team@>
alert_channel_p2:
  - <例：邮件日报:data-team@>

# DQC 规则命名规范
dqc_naming_convention: <例：dqc_<table>_<rule_type>_<field>>

# 团队默认波动基线（按业务节奏）
volume_fluctuation_baseline:
  workday: <例：±10%>
  weekend: <例：±25%>
  big_promotion: <例：单独配置>
```

---

## 4. 团队培训与 onboarding（被 Skill 5 读取）

```yaml
# 内部 Wiki 根（业务知识、规范文档）
team_wiki_root: <Wiki 链接>

# mentor 安排策略
mentor_assignment: <例：每个新人配 1 个 senior + 1 个 同期搭档>

# onboarding checklist
onboarding_checklist_path: <Wiki 链接>

# 内部培训视频
internal_training_videos:
  - <视频 1 标题: 链接>
  - <视频 2 标题: 链接>

# 业务知识入口
business_knowledge_entry: <Wiki 链接>
```

---

## 5. 数据血缘与变更管理（被 Skill 6 读取）

```yaml
# 血缘平台
lineage_platform: <阿里云 DataWorks / 自建>
lineage_platform_url: <>

# 变更通知通道
change_notification_channel:
  business_side: <例：钉钉群:业务对接群>
  tech_side: <例：钉钉群:数据技术群>
  email_list: <例：data-change@>

# 各级变更提前通知 SLA
change_sla_l0: <例：≥ 7 天 + 双 sign off>
change_sla_l1: <例：≥ 3 天>
change_sla_l2: <例：≥ 1 天>

# 核心业务方联系人（L0 sign off 时用）
critical_business_owners:
  finance: <财务负责人 钉钉 ID>
  cfo_dashboard: <CFO 看板 owner>
  external_api: <对外 API owner>
  - <>
```

---

## 6. 协作与工具（被多个 Skill 读取）

```yaml
# 代码仓库
git_repo_root: <例：https://gitlab.example.com/data-team/flink-jobs>

# Flink 平台
flink_platform_url: <例：https://flink.example.com>

# Kafka 集群信息
kafka_cluster: <bootstrap-servers>
kafka_admin_url: <例：Kafka Manager 地址>

# 监控平台
monitoring_platform:
  prometheus: <Prometheus 地址，如有>
  grafana: <Grafana 地址>
```

---

## 使用说明

1. 复制本文件到项目根目录命名为 `QODERWORK.md`
2. 填写所有 `<>` 占位符（或显式标 `N/A`）
3. 提交到团队 Git 仓库
4. 套件会在每次执行 Skill 时自动读取此文件
5. 团队规范变更时更新本文件即可，套件无需重装

## 配置完整性自检

如希望套件提示哪些字段未填，对话中说 "检查 QODERWORK.md 配置完整性"，套件会扫描并标出 N/A 比例和未填写项。
