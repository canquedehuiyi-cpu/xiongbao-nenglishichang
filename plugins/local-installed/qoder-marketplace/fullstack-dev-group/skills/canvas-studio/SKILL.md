---
name: canvas-studio
displayName: "交互式画布"
description: >-
  软硬件交付团队的交互式画布技能：当需要把团队产物以可交互、可视化方式呈现时，调用 Qoder 内置的 /canvas 能力生成 .canvas.tsx 画布（如团队看板、架构全景、上线作战室、需求泳道、监控大盘、协议联调面板）。
  本技能本身不实现画布运行时，而是编排并委派给内置 canvas 技能，并约定团队的画布模板与数据来源。
  命中国看板、画布、可视化、作战室、全景图、交互式展示等意图时调用。
  触发词：画布、Canvas、交互式、看板、可视化、作战室、全景、大屏、仪表盘、团队视图、需求泳道。
descriptionZh: >-
  交互式画布：委派 Qoder 内置 /canvas 生成可交互画布（看板/架构全景/上线作战室等）。
descriptionEn: >-
  Canvas studio: delegate to Qoder built-in /canvas to render interactive canvases (board/architecture war-room/etc).
tags:
  - 画布
  - Canvas
  - 可视化
  - 看板
---

# 交互式画布 (Canvas Studio)

本技能把团队的**可视化、可交互产物**交给 Qoder 内置的 `/canvas` 能力呈现。编排主技能（delivery-team）在命中「画布/看板/可视化」意图时委派本技能，由本技能调用内置 canvas 技能生成 `.canvas.tsx` 画布。

## 适用边界
- 团队看板、架构全景、上线作战室、需求泳道、监控大盘、协议联调面板、硬件联调视图等**需要交互/持续观察**的制品。
- 一次性静态图（架构图/拓扑）优先用 `design-diagrams`；需要交互才用本技能。

## 工作流
1. **定画布目标**：明确看什么、给谁看、要交互什么（筛选/下钻/刷新）。
2. **委派内置 canvas**：调用 Qoder 内置 `/canvas` 技能（slash 命令）生成 `.canvas.tsx`，遵循其规范。
3. **接数据来源**：声明画布数据来自哪些技能产物（如 `network-topology` 拓扑、`qa-quality` 门禁、`devops-pipeline` 发布状态）。
4. **约定模板**：团队常用画布模板（见下），保持风格一致、不堆装饰。
5. **复核**：确认在活跃工作区可渲染、交互可用、数据可读。

## 团队常用画布模板
- **交付全景**：角色席位 + 当前派单/会诊状态（来自 delivery-team）。
- **上线作战室**：发布阶段 + 回滚路径 + 健康探测（来自 devops-pipeline / team-ops-expert）。
- **架构与拓扑**：逻辑架构 + 网络链路（来自 design-diagrams / network-topology）。
- **质量门禁**：覆盖率/劣化/放行（来自 qa-quality）。

## 与内置技能协同
- 画布运行时 → Qoder 内置 `/canvas` 技能（本插件不自带运行时，按规范委派）。
- 静态图源 → `design-diagrams`、`network-topology`。
- 数据来源 → 各工程技能（ops/qa/devops/api/hardware）。
