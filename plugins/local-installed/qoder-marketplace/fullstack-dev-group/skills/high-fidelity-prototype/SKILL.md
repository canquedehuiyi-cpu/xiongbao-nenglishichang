---
name: high-fidelity-prototype
displayName: "高保真原型"
description: >-
  软硬件交付团队的高保真原型技能：基于设计规范产出可点击的高保真 HTML/CSS 原型与设计令牌(Design Tokens)，覆盖正常/空/错误/加载等状态，还原设计规范(间距/色彩/组件)。
  区别于 product-design 的低保真线框：本技能产出接近真机的视觉与交互雏形。命中高保真、原型、UI 还原、设计令牌、可点击原型等意图时调用。
  触发词：高保真、高保真原型、原型、UI 还原、设计令牌、Design Tokens、可点击原型、视觉稿、交互雏形、组件还原。
descriptionZh: >-
  高保真原型：可点击 HTML/CSS 原型 + 设计令牌，覆盖多状态，还原设计规范。
descriptionEn: >-
  High-fidelity prototype: clickable HTML/CSS prototype and design tokens covering multi-states, faithful to design specs.
tags:
  - 高保真原型
  - 设计令牌
  - UI 还原
  - 交互雏形
---

# 高保真原型 (High-Fidelity Prototype)

本技能为团队产出**接近真机的高保真原型**，与 `agents/` 中的涂悦目(UI)/蓝图画(产品)角色卡及 `product-design` 技能联动：`product-design` 出低保真线框与目标，`high-fidelity-prototype` 出可点击视觉雏形。

## 适用边界
- 基于设计规范的**可点击 HTML/CSS 高保真原型**与**设计令牌（颜色/间距/字号/圆角/阴影）**。
- 覆盖正常 / 空 / 错误 / 加载 / 禁用等状态，还原设计规范。

## 工作流
1. **取规范**：先读 `product-design` 的设计规范与 `product-design`/涂悦目定的间距/色彩/组件要求，提炼设计令牌。
2. **建令牌**：用 CSS 变量定义 Design Tokens（色板、间距阶梯、字号、圆角、阴影、层级）。
3. **出页面**：用语义化 HTML + 组件化 CSS 还原主要页面/流程；多状态用 tab/切换或独立页呈现。
4. **可点击**：关键路径可跳转/可交互（不接真实接口，用 mock 数据）。
5. **对齐还原度**：与涂悦目核对还原度清单，标注与规范的偏差。

## 产出约定
- `tokens.css`（或 `:root` 变量）设计令牌文件。
- 自包含 HTML（单文件或少量文件，离线可开），注明依赖字体/图标。
- 状态清单：正常/空/错误/加载/禁用，每个关键组件均覆盖。
- 还原度说明：与规范的偏差点显式列出。

## 与内置技能协同
- 低保真线框与目标 → `product-design`。
- 设计规范校验图 → `design-diagrams`。
- 真实前端落地（Vue/React）→ `team-p8-full-stack`。
