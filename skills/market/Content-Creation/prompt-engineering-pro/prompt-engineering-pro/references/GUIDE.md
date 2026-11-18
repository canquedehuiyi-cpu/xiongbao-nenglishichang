# 提示词工程系统 · 使用指南（GUIDE）

> 版本 1.1.0 · 多宿主 + 生命周期平台化版。本页为 30 秒上手指引，完整能力见各 references 文档。

## 这是什么

面向提示词的工程系统：构建、优化、评估、诊断、压缩、迁移、自省 system prompt 与各类提示词。覆盖所有行业、所有平台、所有模型。安全优先，产出必带证据。

## 首次使用（30 秒自检）

```bash
node scripts/validate.mjs   # 一键完整性检查，全部通过即环境就绪
```

## 三种上手方式

| 场景 | 做法 | 结果 |
|---|---|---|
| 我要写提示词 | `node scripts/pipe.mjs --request "<需求>"` | 安全→构建→8 维评分→版本快照 |
| 我要优化已有提示词 | `node scripts/pipe.mjs --request "<需求>" --prompt "<现有提示词>"` | before/after 对比 + 定向修补 |
| 我的提示词不 work | `node scripts/diagnose.mjs --request "<需求>" --error "<失败现象>"` | 按失败分类定位根因 + 修补建议 |

## 触发词速查

| 你说 | 系统做什么 |
|---|---|
| 写提示词 / 优化 system prompt / improve prompt | 构建或优化提示词 |
| 评估 / 评分 / 好不好 | 8 维 Q-Score 评分（带证据） |
| 不 work / 为什么没效果 / 诊断 | 失败定位与定向修补 |
| 压缩 / 精简 / 太长 | 压缩 + 回归验证 |
| 迁移 / 换个模型 / 换个平台 | 跨模型/平台迁移 |
| 检查技能包 / 打包 / skill 合规 | Skill 包发布合规检查与打包 |
| 微信小游戏合规 | 微信小游戏运营规范自检 |
| 生成微信 AI 技能 | 微信 AI 开发模式技能脚手架生成 |

## 领域选择（我的任务是哪个领域）

| 领域 | 覆盖 | 典型请求 |
|---|---|---|
| game 游戏 | 小游戏/Unity/Cocos/Steam 的开发、NPC、策划案、美术素材、上架物料 | "写个微信小游戏策划案" |
| visual 视觉 | 文生图、角色设计、3D 建模、UI 设计、视频脚本 | "设计角色原画提示词" |
| ai AI 工程 | Agent 系统提示词、Skill 封装、MCP 声明、多智能体 | "封装一个 skill" |
| ecommerce 电商 | 商品标题、详情页、直播脚本、客服话术 | "写电商详情页提示词" |
| content 内容 | 小红书、公众号、短视频、SEO | "写小红书种草笔记" |

不确定领域时，`domain-router` 自动识别；也可 `--domain <领域>` 强制指定。

## 分层路径

- **新手**：用 pipe 走默认闭环，开启引导（默认开）。
- **进阶**：`--no-guide` 关闭引导；按需使用诊断、压缩、迁移、领域模板。
- **专家**：全量 50 引擎 + `--judge` 接入宿主 LLM 语义判定 + `--apply` 让系统学习你的习惯。

## 自进化（越用越懂你）

- 每次使用自动记录行为信号（`feedback`），可主动评分（`feedback rate --stars N`）。
- `learner` 从使用习惯提炼画像建议；`--apply` 确认后生效。
- 画像只影响输出默认值（语言/详略/模板/领域），**不改变任何评分结果**。
- 所有数据仅存本地 `data/`，可用 `feedback clear` / `habit-profile reset` 随时清空。
- 1.0.9 自进化闭环：`track-outcome` 记录执行结果 → `run-eval` 实证评估（默认离线）→ `output-check` 输出侧验证 → `diagnose-failures` 失败诊断 → `skill-evo` 进化提案（默认 dry-run，--apply 才写入 proposals/ 人工评审）；`learner` 输出技能健康度；`--purge`/`--export` 治理 outcomes。

## 平台化（生命周期管理，1.1.0）

- 管理 CLI：`node scripts/skill.mjs health`（健康诊断）/ `check`（发布门禁）/ `adapt --host all`（多宿主部署）/ `verify --domain game`（规范核验）/ `report`（汇总报告）。
- 多宿主部署：`host-adapt` 生成 Claude Code / Codex / Cursor / ChatGPT / 通用 SKILL.md 骨架到 `host-out/`（仅骨架，不写宿主配置）。
- 统一路由收口：`node scripts/domain-router.mjs --request "…" --unified` 输出合规线 + 技法线单份报告。

## 规范核验（引用最新官方规范）

```bash
node scripts/verify-spec.mjs --platform wechat-minigame   # 微信小游戏规范是否更新
node scripts/verify-spec.mjs --domain game                # 游戏领域全部规范源
node scripts/verify-spec.mjs --layer national             # 国家层统一规范源
```

规范核验按需拉取、7 天缓存、失败降级；正式交付前建议先核验再构建。

## 合规检查（内容行业 / 四层安全）

```bash
node scripts/domain-compliance-check.mjs --text "<文案>" --domain finance   # 领域合规画像
node scripts/safety-compose.mjs --text "<文案>"                              # 四层安全（自动识别行业/法域）
node scripts/national-game-check.mjs --text "<游戏方案>"                     # 国家层游戏合规
```

领域规则快照存于 `references/rules/`（11 份，schema 自校验），规则与引擎分离，新增行业只加数据。

## 边界

- 简单单步请求（如"把这句话改顺"）不强制触发，宿主直接处理。
- 红线/注入/PII 输入由安全前置拦截；黄线自动脱敏并提示。
- 评分无把握标注置信度；搜索结果不等于已验证事实。
