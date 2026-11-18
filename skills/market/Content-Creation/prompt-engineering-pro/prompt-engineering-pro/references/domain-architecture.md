# 领域适配层架构（Domain Adaptation Layer）

> 版本 1.1.0。本层让提示词工程系统覆盖所有行业、所有平台、所有模型、所有法域：领域相关的模式、模板、词库、规范源、评分权重、合规规则快照可插拔注入，核心引擎零改动。

## 设计目标

- **可插拔**：新增行业 = 新增领域目录 + 注册一条 +（可选）新增合规快照，不改任何核心引擎。
- **零侵入**：领域只影响"推荐与约束"，不改变评分/安全门禁的中立性。
- **按需扩展**：领域在注册表中声明自身能力，未注册领域走通用路径。
- **架构全 + 策略全**：覆盖能力来自"任意新行业=加数据不改引擎"的架构，而非清单式枚举（任何清单交付当天即过时）。

## 分层结构

```
核心引擎层（35 个引擎，模型/平台/法域无关）
   ▲
   │ domain-router 根据输入识别领域 → 注入领域指纹（含法域/模态识别）
领域适配层
   ├─ domains/registry.json        领域注册表（领域/平台/模板/词库/规范源/评分权重/合规快照）
   ├─ references/lexicon/domain-detect.json  领域触发词库
   ├─ references/lexicon/jurisdiction-detect.json  法域/模态识别词库（v1.0.5）
   ├─ references/lexicon/content-domain-detect.json  内容行业识别词库（v1.0.5，供 safety-compose）
   ├─ references/domains/<领域>.md  领域模式说明（约束/范式/词表/提示词要点）
   ├─ references/templates/        领域模板（GAME-*/IMAGE-*/AGENT-* 等）
   └─ references/rules/            领域合规规则快照仓库（11 份 + _schema.json，v1.0.5）
```

## 领域指纹

`domain-router` 输出领域指纹，供上层使用：

| 字段 | 含义 |
|---|---|
| domain / label | 领域标识与中文名 |
| platforms | 该领域覆盖的平台（如 wechat-minigame/unity/steam） |
| templates | 可用模板清单 |
| lexicons | 领域词库 |
| spec_sources | 该领域相关的官方规范源（与 references/spec-sources.json 的 domain 字段对应） |
| score_weights | 该领域的评分维度加权（如 game 领域 compliance×1.2） |
| jurisdiction / modality | 从输入识别的法域与内容模态（v1.0.5，未命中为 null） |
| hint | 领域引导语 |

> 合规规则快照不在此登记：`references/rules/*.json`（schema 校验后执行）由 `domain-compliance-check` / `safety-compose` 直接读取，新增行业 = 新增快照即可。

## 新增一个领域（四步）

1. 在 `domains/registry.json` 的 `domains` 增加一条（label/platforms/templates/lexicons/spec_sources/score_weights/hint）。
2. 在 `references/lexicon/domain-detect.json` 的 `domains` 增加触发词（供自动识别）。
3. 视需要新增 `references/domains/<领域>.md` 模式说明与领域模板。
4. 若该领域有监管/平台合规要求：新增 `references/rules/<领域>-<法域>.json` 规则快照（遵循 _schema.json），即可被 `domain-compliance-check` 与 `safety-compose` 自动纳入。

## 领域评分权重

`score_weights` 是**建议性加权**：在 L4 自评估时可参考领域权重调整维度侧重点（如游戏强调合规、视觉强调细节指令）。该加权不改变评分引擎内置的基线逻辑，仅作为领域约束提示。

## 首批领域

| 领域 | 平台 | 核心模板 | 合规机制 |
|---|---|---|---|
| game | wechat-minigame / douyin-minigame / qq-minigame / unity / cocos / steam / taptap | GAME-DEV / GAME-NPC / GAME-DESIGN / GAME-ASSET / GAME-STORE | 专项引擎 wechat-minigame-check / national-game-check（国家层防沉迷/版号/实名/内容安全） |
| visual | image-gen / character-design / 3d-model / ui-design / video | IMAGE-GEN / CHARACTER-DESIGN / UI-DESIGN / VIDEO-SCRIPT | 快照 deepsynthesis-cn / ai-label-cn 规范源 |
| ai | agent / skill-pack / mcp / workflow | AGENT-SYSTEM / SKILL-PACK / MCP-DECL | 快照 ai-aigc-cn / national-ai / eu-ai-act |
| ecommerce | taobao / jd / douyin-shop / pdd / amazon | PRODUCT-TITLE / DETAIL-PAGE / LIVE-SCRIPT / CS-SCRIPT | 快照 advertising-cn / oceanengine / national-finance |
| content | xiaohongshu / wechat-article / short-video / seo | XHS-NOTE / WECHAT-ARTICLE / SEO | 快照 advertising-cn |
