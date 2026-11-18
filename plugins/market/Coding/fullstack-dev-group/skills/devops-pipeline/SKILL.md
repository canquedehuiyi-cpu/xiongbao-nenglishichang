---
name: devops-pipeline
displayName: "CI/CD 与发布流水线"
description: >-
  软硬件交付团队的 CI/CD 与发布流水线技能：构建编排、流水线 stages、制品与版本、灰度/蓝绿/滚动发布剧本、回滚剧本、发布验证与门禁、配置与数据库变更流程。
  与 team-ops-expert 互补：team-ops-expert 偏主机/监控/安全闸门，本技能偏流水线/发布编排。
  命中流水线、CI、CD、构建、灰度、蓝绿、滚动、回滚剧本、发布编排、制品、版本等意图时调用。
  触发词：CI、CD、流水线、构建、打包、制品、版本、发布、上线、灰度、蓝绿、滚动、回滚剧本、发布编排、变更流程、配置变更、数据库变更。
descriptionZh: >-
  CI/CD 与发布流水线：构建编排、灰度/蓝绿/滚动发布与回滚剧本、发布验证门禁。
descriptionEn: >-
  CI/CD and release pipeline: build orchestration, canary/blue-green/rolling release and rollback playbooks, release verification gates.
tags:
  - CI/CD
  - 发布流水线
  - 回滚
  - 灰度
---

# CI/CD 与发布流水线 (CI/CD & Release Pipeline)

本技能为团队发布侧提供编排方法，与 `agents/` 中的常守恒(运维)角色卡联动，并与 `team-ops-expert` 互补：team-ops-expert 负责主机/监控/安全闸门，本技能负责流水线/发布编排。

## 适用边界
- 构建编排、流水线 stages、制品与版本策略。
- 灰度/蓝绿/滚动发布剧本、回滚剧本、发布验证与门禁。
- 配置与数据库变更流程（与 `team-ops-expert` 的生产安全闸门一致：方案+回滚+授权）。

## 工作流
1. **流水线分层**：lint → build → unit/contract test → 镜像/制品 → 预发验证 → 生产发布。
2. **发布策略**：按风险选灰度/蓝绿/滚动；先小流量再全量，每步带自动健康探测。
3. **回滚剧本**：每个发布必须有回滚路径（版本回退/开关/流量切回），与 team-ops-expert 共定。
4. **变更门禁**：配置/DB 变更走审批与窗口；生产变更须方案+回滚+授权。
5. **发布验证**：与测试查无漏共定验收清单，发布后监控指标达标方可结束。

## 产出约定
- 流水线定义：stages、触发、并发与缓存、制品命名。
- 发布剧本：步骤、健康检查、回滚触发点、值守与通讯。
- 变更单：范围、回滚、授权、窗口。

## 与内置技能协同
- 主机/监控/安全闸门 → `team-ops-expert`。
- 接口契约测试门禁 → `api-contract` / `qa-quality`。
- 设备批量烧录/上线 → `hardware-embedded`。
