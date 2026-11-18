---
name: api-contract
displayName: "接口契约治理"
description: >-
  软硬件交付团队的接口契约治理技能：OpenAPI 设计先行、契约评审、Mock 与桩、前后端联调基线、版本与兼容(破坏性变更管控)、错误码与幂等规范、设备接入协议对齐。
  命中接口、契约、OpenAPI、API 设计、联调、Mock、版本兼容、错误码、幂等等意图时调用。
  触发词：接口、API、契约、OpenAPI、Swagger、联调、Mock、接口设计、版本兼容、破坏性变更、错误码、幂等、接口治理、前后端联调。
descriptionZh: >-
  接口契约治理：OpenAPI 先行、契约评审与 Mock、版本兼容与幂等规范、设备接入协议对齐。
descriptionEn: >-
  API contract governance: OpenAPI-first design, contract review and mocks, version compatibility and idempotency, device-ingestion alignment.
tags:
  - 接口契约
  - OpenAPI
  - 联调
  - 版本兼容
---

# 接口契约治理 (API Contract Governance)

本技能为团队契约侧提供治理方法，与 `agents/` 中的石磐安(后端组长)/颜可见(前端组长)角色卡联动：角色卡定架构与边界，本技能给契约规范与联调基线。

## 适用边界
- OpenAPI 设计先行、契约评审、Mock 与桩、前后端联调基线。
- 版本与兼容（破坏性变更管控）、错误码与幂等规范、设备接入协议对齐。

## 工作流
1. **契约先行**：先出 OpenAPI 草稿（路径/字段/错误码/幂等），再实现；前后端并行用 Mock 开发。
2. **契约评审**：评审关注稳定性、向后兼容、分页/限流/鉴权、错误模型；破坏性变更须版本化并通知。
3. **联调基线**：定义联调环境、数据约定、异常态；用契约测试提前暴露不一致（见 `qa-quality`）。
4. **幂等与错误码**：统一错误码体系与幂等键约定，避免重复提交与状态错乱。
5. **设备接入**：设备↔云端协议与 `hardware-embedded` 对齐字段/时序/重传。

## 产出约定
- OpenAPI 文档（版本化）、错误码表、幂等与限流约定。
- Mock 服务配置与联调清单。
- 版本兼容策略：新增/废弃/破坏性变更的处理与窗口。

## 与内置技能协同
- 契约测试与门禁 → `qa-quality`。
- 设备协议落地 → `hardware-embedded`。
- 联调后的发布编排 → `devops-pipeline` / `team-ops-expert`。
