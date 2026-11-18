---
name: effect-image
displayName: "效果图生成"
description: >-
  软硬件交付团队的效果图生成技能：直接产出高保真图片素材（非 HTML 截图），用于头像、产品渲染图、UI 视觉稿、硬件外观、场景效果图、营销配图等。
  通过 ImageGen 工具直接生成图片并落到项目资产目录，区别于 high-fidelity-prototype 的 HTML/CSS 可点击原型。
  命中国生成头像、效果图、渲染图、视觉稿、配图、产品图、硬件外观等意图时调用。
  触发词：生成图片、效果图、头像、渲染图、视觉稿、配图、产品图、硬件外观、场景图、插画、封面图。
descriptionZh: >-
  效果图生成：用 ImageGen 直接生成图片素材（头像/渲染/视觉稿/配图），不走 HTML 截图。
descriptionEn: >-
  Effect image: generate high-fidelity image assets via ImageGen (avatar/render/visual/illustration), not HTML screenshots.
tags:
  - 效果图
  - 图片生成
  - 头像
  - 渲染图
---

# 效果图生成 (Effect Image)

本技能为团队产出**直接生成的高保真图片素材**，与 `high-fidelity-prototype`（HTML/CSS 可点击原型）互补：当需求是「一张图」而非「可点击页面」时使用本技能，通过 ImageGen 直接生成并落盘。

## 适用边界
- 头像、产品渲染图、UI 视觉稿/氛围图、硬件外观图、场景效果图、营销/封面配图、插画。
- 任何「给我生成一张图」而非「做一个可交互原型」的诉求。

## 工作流
1. **定意图与尺寸**：确认用途（头像/方图/横幅/竖图）、风格、比例（如 1:1 / 16:9 / 3:2 / 4:3）、是否需要文字。
2. **写提示词**：用结构化中文提示词——主体 + 风格 + 构图 + 光照 + 配色 + 背景 + 画质词；避免矛盾描述。
3. **生成**：调用 ImageGen 生成；人物/品牌类先确认是否需真实感或插画风。
4. **落盘**：保存到合适资产目录（如 `public/images/` 或 `src/assets/uploads/`），文件名语义化、不写占位名。
5. **复核**：检查分辨率/比例/主体一致性；如需微调改提示词重生成，不裁剪失真。

## 产出约定
- 生成图片文件 + 一行说明（用途/风格/提示词要点）。
- 多方案时给 2–3 版供选，标注各自适合场景。
- 不生成含真实敏感信息（人脸实名、密钥、内部拓扑）的图片。

## 与内置技能协同
- 可点击原型（非图片） → `high-fidelity-prototype`。
- 设计令牌/规范 → `product-design`。
- 需要交互式画布呈现 → Canvas（`/canvas`，见编排主技能说明）。
