# 超级实时数据工程师套件 · realtime-data-engineer

> 实时数据工程师的完整 AI 工具箱。覆盖需求评审、Flink 任务开发、数据质量、Code Review、新人培养、血缘影响 6 大场景。

## 套件价值主张

不是"再给一份 Flink 入门教程"——而是把**资深实时数仓工程师的判断逻辑**封装成 AI 协作模式：
- 窗口/Watermark/反压不写死阈值，用决策因子引导业务判断
- Code Review 提供具体行号 + 具体改法，不给"建议优化"
- 影响分析按业务关键度分层 + 自动产出业务/技术双版通知
- 全套件统一读取 `QODERWORK.md` 团队配置，安装一次永久受益

## 6 个 Skill

| Skill | 触发示例 | 产出 |
|-------|---------|------|
| `realtime-task-development` | "帮我设计这个实时任务" | Flink SQL 草稿 + 8 步 checklist |
| `realtime-data-requirement-review` | "业务方提了个实时需求" / "评审实时需求" | 评审决议 + 口径文档（含 sign off）|
| `data-quality-monitoring` | "给这张表生成 DQC 规则" | DQC 规则 + 告警阈值 |
| `flink-sql-code-review` | "Review 这段 Flink SQL" | 红/黄/蓝分级 Review 意见 |
| `newcomer-growth-path` | "帮新人定个学习路线" | 4 周阶段化路线 + 资料清单 |
| `data-lineage-impact-analysis` | "XX 字段要改，看下影响" | 影响清单 + 业务/技术双版通知 |

## 工作流协同

```
业务方提需求 → realtime-data-requirement-review（评审：要不要接？拆口径）
             ↓ 决议="做"
             realtime-task-development（设计任务，8 步，引用已有口径）
             ↓
             flink-sql-code-review（提交前自审）
             ↓
             data-quality-monitoring（上线前配 DQC）
             ↓
             上线运行
             ↓ ↓
变更/告警  → data-lineage-impact-analysis（评估变更影响）
新人接入   → newcomer-growth-path（按起点定制路线）
```

## 安装与配置

### 1. 安装套件
```bash
qoder plugin install realtime-data-engineer
```

### 2. 配置团队规范（重要）
复制 `QODERWORK.md` 到项目根目录，填写团队信息：
- Flink SQL 命名规范路径
- DQC 平台与告警通道
- 血缘平台地址
- 团队 Wiki / 业务知识库
- 核心业务方联系人

未配置 `QODERWORK.md` 套件仍可工作，但需要每次重复回答团队规范问题。

### 3. 推荐 MCP

| MCP | 用途 | 必要性 |
|-----|------|-------|
| 阿里云 Flink VVR | 任务部署/反压排查 | 核心 |
| 阿里云 DataWorks | DQC 配置、血缘查询 | 核心 |
| Kafka | 数据源元信息 | 推荐 |
| 钉钉文档 | 文档归档协作 | 推荐 |
| Git/GitLab | PR diff 拉取 | 推荐 |
| Prometheus | 时序 metrics 排查 | 可选 |

## 套件理念（区别于通用 SQL/Flink AI）

1. **决策因子优先于阈值** — 业务场景驱动，不写死数字
2. **红线即时阻断** — 10 条核心红线触发立即标 🔴
3. **分级输出** — 受众不同，输出形态不同（业务版 vs 技术版、L0-L3 分层）
4. **团队规范驱动** — `QODERWORK.md` 一次配置，全套件受益
5. **Skill 间协同** — 形成闭环工作流，不是孤立工具

## 适用人群

- 实时数据/流计算方向数据工程师
- 负责实时任务的数仓工程师
- 数据平台工程师
- 数据团队 Tech Lead（用 Skill 5 培养新人）

## 不适用场景

- 离线批任务为主（推荐使用通用 SQL Skill）
- 数据科学/算法（推荐 ML 类 Skill）
- BI 报表设计（推荐 BI 类 Skill）

## 版本

- v1.0.0 (2026-06-23) · 初版 · 基于资深实时数仓工程师真实工作流共创
