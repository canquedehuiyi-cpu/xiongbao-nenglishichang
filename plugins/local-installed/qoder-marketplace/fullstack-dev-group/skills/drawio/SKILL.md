---
name: drawio
displayName: "Draw.io 可编辑图"
description: >-
  软硬件交付团队的 Draw.io 技能：当需要产出可被人工继续编辑的图（流程图、网络拓扑、架构图、时序图、ER 图、部署图、状态图、组织/职责图等）时，直接产出 .drawio 文件（mxGraph XML）。
  区别于 design-diagrams（mermaid 静态图、用于文档与渲染）：本技能产出可在 draw.io / VS Code Draw.io 插件中二次编辑的工程图源文件，适合需要团队协作、持续演进的架构与拓扑。
  命中意图：画流程图、画拓扑图、画架构图、画部署图、导出 drawio、可编辑图、组件连线、泳道图、机房拓扑、系统框图。
  触发词：drawio、流程图、拓扑图、架构图、部署图、网络拓扑、系统框图、接线图、可编辑图、导出 drawio、画个图、拓扑、框图、泳道、机房图、连线图。
descriptionZh: >-
  Draw.io：产出可在 draw.io 中二次编辑的 .drawio 工程图（流程图/拓扑/架构/部署等），区别于 mermaid 静态图。
descriptionEn: >-
  Draw.io: produce editable .drawio (mxGraph XML) diagrams - flowcharts, network topology, architecture, deployment - vs mermaid static diagrams.
tags:
  - 画图
  - drawio
  - 拓扑
  - 架构图
  - 流程图
---

# Draw.io 可编辑图 (Draw.io Editable Diagrams)

本技能为团队产出**可在 draw.io / VS Code Draw.io 插件中二次编辑**的工程图源文件（`.drawio`，本质是 mxGraph XML）。与 `design-diagrams`（mermaid 静态图，用于文档渲染与 pytora）互补：本技能面向**需要团队协作、持续演进**的架构与拓扑图，产出可编辑的工程源文件而非一次性图。

## 适用边界
- 流程图、泳道图、系统框图、分层架构图。
- 网络拓扑（物理/逻辑）、机房/机柜/链路图。
- 部署图、组件连线图、交互/调用关系图。
- 状态图、ER 图、组织/职责图。
- 任何"之后还要被人改"的图——优先产出 `.drawio` 而非 mermaid。

## 与 design-diagrams 的分工
- **只需要在文档/渲染里展示、不常改**：用 `design-diagrams` 的 mermaid（≤8.8.3 校验）。
- **需要人工继续编辑、协作演进**：用本技能产出 `.drawio`。
- 二者可并存：先 mermaid 快速表达，再 draw.io 沉淀为可编辑源。

## 工作流
1. **定图型与范围**：按意图选图型（流程/拓扑/架构/部署/状态/ER），先与对应角色卡对齐边界（架构找石磐安、运维/网络找常守恒、硬件找路通远）。
2. **落地文件**：在目标工程目录产出 `*.drawio` 文件，内容为合法 mxGraph XML（见下方模板与规范）。
3. **节点与连线语义**：每个节点带 `value`（显示文本）与稳定 `id`；连线用 `edge` 并标注关系（调用/依赖/数据流/部署于/隔离）。
4. **配色与分层**：用 `style` 区分角色/层（前端、后端、基础设施、外部、风险），避免一张图承载过多；复杂系统分层出多张图。
5. **一句话说明**：图旁附一句话说明 + 关键假设，便于评审与后续编辑。

## mxGraph XML 规范（.drawio 文件）
- 根节点 `<mxGraphModel>` → `<root>` 内含一个 `<mxCell id="0"/>` 和一个 `<mxCell id="1" parent="0"/>` 作为画布根。
- 节点：`<mxCell id="n1" value="显示文本" style="rounded=1;..." vertex="1" parent="1"><mxGeometry x="40" y="40" width="160" height="40" as="geometry"/></mxCell>`。
- 连线：`<mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1" source="n1" target="n2"><mxGeometry relative="1" as="geometry"/></mxCell>`。
- 常用 style：圆角框 `rounded=1;whiteSpace=wrap;html=1`；矩形 `whiteSpace=wrap;html=1`；虚线/风险 `strokeColor=#d64545;dashed=1`；填充 `fillColor=#dae8fc`。
- 用 UTF-8 保存，避免裸 `<`/`>` 出现在 value 中（文本用 XML 实体或放在 `value` 属性内）。

## 最小模板
```xml
<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="client" value="客户端" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;" vertex="1" parent="1">
      <mxGeometry x="40" y="40" width="120" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="api" value="API 网关" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;" vertex="1" parent="1">
      <mxGeometry x="220" y="40" width="120" height="40" as="geometry"/>
    </mxCell>
    <mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;" edge="1" parent="1" source="client" target="api">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

## 产出约定
- 文件名语义化（如 `deploy-topology.drawio`、`order-flow.drawio`）。
- 复杂系统分层出多张图（上下文→容器→组件），不堆在一张。
- 图与 `api-contract` 的接口、`hardware-embedded` 的协议、`team-ops-expert` 的部署拓扑保持一致。

## 与内置技能协同
- 文档静态图 → `design-diagrams`（mermaid）。
- 部署/监控/安全闸门 → `team-ops-expert`；网络形态 → `network-topology`；硬件/协议 → `hardware-embedded`。
