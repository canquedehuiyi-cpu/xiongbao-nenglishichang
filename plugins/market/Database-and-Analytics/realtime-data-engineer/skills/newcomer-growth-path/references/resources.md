# 资料清单（按维度组织）

## P0（必读）

### Flink 官方
- [Flink 官网 Concepts](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/overview/) — 时间、状态、容错三大概念
- [Flink SQL 官方教程](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/table/sql/queries/overview/)

### 阿里云 VVR
- [实时计算 Flink 版文档](https://help.aliyun.com/product/45029.html)
- [VVR Connector 列表](https://help.aliyun.com/zh/flink/developer-reference/connectors)

### 团队内部（动态加载 QODERWORK.md）
- 团队 Wiki 根：`team_wiki_root`
- 内部培训视频：`internal_training_videos`
- onboarding checklist：`onboarding_checklist_path`

## P1（推荐）

### SQL 强化（针对 M1 ≤ 2）
- 《SQL 必知必会》前 8 章
- LeetCode 数据库题 50 道

### 分布式概念（针对 M3 ≤ 2）
- 《数据密集型应用系统设计》（DDIA）第 11 章流处理
- 《Streaming Systems》Tyler Akidau —— watermark 经典书

### Java（针对 M2 ≤ 3 + 有 DataStream 任务）
- 《Effective Java》第 3 章泛型 / 第 7 章 Lambda
- 《Java 并发编程实战》前 5 章

## P2（深入）

- Flink Forward 历年 talks（state backend / checkpoint 优化）
- Apache Kafka 官方文档（不超过 3 篇）
- 《大数据日知录》分布式核心概念

## 业务知识

- **必填**：团队业务结构图、核心指标体系、数据流转图
- **必填**：业务系统的接入点（哪些系统出哪些数）
- **建议**：跟业务方 shadowing 1-2 次

## 不推荐

- ❌ 无差别推 100 篇博客（无人会读）
- ❌ 推大部头书（需要数月，新人不会看完）
- ❌ 视频时长 > 4 小时（学习效率低）
