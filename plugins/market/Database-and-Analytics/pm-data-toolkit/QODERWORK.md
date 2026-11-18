<!--
配置规则（本插件每个 skill 必须遵守）：
1. 读取路径：~/.qoderwork/plugins/config/pm-data-toolkit/QODERWORK.md，不要读这个模板文件。
2. 如果该路径不存在或仍含 [PLACEHOLDER] 标记，停下来。回复用户：
   "这个插件需要先配置一下，运行 /pm-data-toolkit:onboarding 大概 10 分钟，
    本插件所有 skill 都依赖它。否则输出会是通用模板，可能不符合你的实际流程。"
   不要继续。唯一例外是 onboarding skill 本身。
3. Onboarding skill 写入用户配置路径，按需创建父目录。setup 中途用户喊 "pause"，
   在文件顶部写 <!-- SETUP PAUSED AT: {section} --> 注释，下次 setup 从断点继续。
4. 插件升级时，模板会被覆盖，用户配置不动。永远不要把用户填的内容写进模板。
5. 上层共享 profile 在 ~/.qoderwork/plugins/config/team-profile.md，先读它再读本文件。
   共享 profile 缺失时，onboarding 第一步要先创建它。
-->

# 超级产品经理 · 数据武器 —— 团队配置

## 团队/公司

[团队简介——公司类型、产品线、团队规模、负责的业务场景。一段话。]

**最大的痛点：** [PLACEHOLDER —— 例：数据分散在多个ODPS表，口径不统一，每次分析都要重新确认]

**业务设定：** [PLACEHOLDER —— 例：AI 产品 / 搜索产品 / 电商平台 / 其他]

## 已连接的工具

| 工具 | 状态 | 没连接时的 fallback |
|---|---|---|
| ODPS (MaxCompute) | [PLACEHOLDER ✓/✗] | 用户手动提供 CSV/Excel 数据 |
| 钉钉文档 | [PLACEHOLDER ✓/✗] | 产出生成为本地 HTML 文件 |

*重新检测：`/pm-data-toolkit:onboarding --check-integrations`*

## 业务规则

*下面是本团队的数据分析标准做法和红线。每个 skill 在执行前读这一段，按此执行。*

### 标准流程

1. [PLACEHOLDER —— 例：先确认分析目标和口径，再拉数据，最后出报告]
2. [PLACEHOLDER]
3. [PLACEHOLDER]

### 常用 ODPS 表映射

| 业务场景 | 表名 | 项目 | 分区列 | 备注 |
|---|---|---|---|---|
| [PLACEHOLDER —— 例：千问Chat请求明细] | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |
| [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |

### 指标口径定义

| 指标名 | 计算方式 | 备注 |
|---|---|---|
| [PLACEHOLDER —— 例：渗透率] | [PLACEHOLDER —— 例：(相机+相册去重UV)/APPDAU] | [PLACEHOLDER] |
| [PLACEHOLDER —— 例：相机发起率] | [PLACEHOLDER —— 例：发起请求UV÷入口点击UV] | [PLACEHOLDER] |
| [PLACEHOLDER] | [PLACEHOLDER] | [PLACEHOLDER] |

### 红线（绝不能做）

- [PLACEHOLDER —— 例：不准用 SELECT * 不带 LIMIT 查生产表]
- [PLACEHOLDER —— 例：不准在没确认口径的情况下直接给老板发数据]

### 一票否决项

[PLACEHOLDER —— 例：任何对外数据必须标注口径和日期，否则不发]

## 输出风格

**对外报告（给老板/业务方的）：** [PLACEHOLDER —— 例：精炼，一句话直击核心数字和涨幅]

**内部分析（自己/同事看的）：** [PLACEHOLDER —— 例：详细，含多维拆分和方法论说明]

**汇报叙事风格：** [PLACEHOLDER —— 例：三段叙事——绝对pp提升+相对%+稳定平台]

**Stakeholder 摘要长度：** [PLACEHOLDER —— 例：3 段以内，先结论后数据]

**产出格式偏好：** [PLACEHOLDER —— 例：HTML 报告（Chart.js），含 stat cards]

**产出存放位置：** [PLACEHOLDER —— 例：本地工作目录，通过 QoderWork 直接查看]

## 偏好设置

confirm_before_external_send: true
default_output_language: zh
include_meta_note: true
