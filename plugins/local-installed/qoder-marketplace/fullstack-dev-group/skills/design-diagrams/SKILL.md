---
name: design-diagrams
displayName: "设计图"
description: >-
  软硬件交付团队的设计图技能：系统化产出架构图、时序图、状态图、C4(上下文/容器/组件)、ER 图、部署图、数据流图，统一使用 mermaid(版本≤8.8.3 语法，classDef 配色，禁用 ASCII 图)，并经 validate_mermaid.cjs 校验。
  命中国架构图、时序图、状态机、C4、ER、部署图、拓扑图、流程图等意图时调用。
  触发词：设计图、架构图、时序图、状态图、状态机、C4、ER图、ER、部署图、数据流图、流程图、mermaid、类图、组件图。
descriptionZh: >-
  设计图：架构/时序/状态/C4/ER/部署图，统一 mermaid(≤8.8.3) 并经校验。
descriptionEn: >-
  Design diagrams: architecture/sequence/state/C4/ER/deployment diagrams in mermaid (≤8.8.3), validated.
tags:
  - 设计图
  - mermaid
  - 架构图
  - C4
---

# 设计图 (Design Diagrams)

本技能为团队产出**系统化、可校验的设计图**，与 `agents/` 中的架构/硬件/运维角色卡联动。图示统一 mermaid（≤8.8.3），禁用 ASCII 图，确保可被 pytora 等渲染。

## 适用边界
- 架构图、时序图、状态/状态机图、C4（上下文/容器/组件）、ER 图、部署图、数据流图、组件图、流程图。

## 工作流
1. **选图型**：按意图选正确图型——交互用时序、生命周期用状态、系统边界用 C4、数据关系用 ER、落地用部署图。
2. **口径对齐**：先与对应角色卡对齐边界（如架构图找石磐安、部署图找常守恒、硬件图找路通远）。
3. **mermaid 产出**：用 ≤8.8.3 语法 + `classDef` 配色；节点/连线语义清晰，避免一张图承载过多。
4. **校验**：运行 `team-p8-full-stack` 的 `scripts/validate_mermaid.cjs` 校验语法（或 `team-ops-expert` 同款脚本）。
5. **配套说明**：图下附一句话说明与关键假设，便于评审。

## 产出约定
- 每个图配图型标注 + 一句话说明 + 关键假设。
- 复杂系统分层出多张图（C4 上下文→容器→组件），不堆在一张。
- 图示须与 `api-contract` 的接口、`hardware-embedded` 的协议一致。

## 与内置技能协同
- mermaid 校验脚本 → `team-p8-full-stack/scripts/validate_mermaid.cjs`（或 `team-ops-expert/scripts/validate_mermaid.cjs`）。
- 高保真原型配图 → `high-fidelity-prototype`。
- 网络链路图 → `network-topology`。
