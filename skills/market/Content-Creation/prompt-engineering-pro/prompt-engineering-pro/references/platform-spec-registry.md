# 平台规范核验（Platform Spec Verification）

> 版本 1.1.0。由 `verify-spec.mjs` 执行，对应规范核验层：让提示词构建前引用**最新官方规范**，避免用过时约束。

## 为什么需要

平台规范（上架审核、变现规则、技术版本、AI 开发模式、行业监管）会随官方更新而变化。提示词如果引用过时约束，产出可能不合规。本层按需拉取官方源并对比缓存，提示变更，供构建参考。

## 核验范围（需要 / 不需要）

| 需要实时核验 | 不需要实时核验 |
|---|---|
| 平台审核政策（上架/拒审/物料要求） | 通用提示词方法论（CO-STAR 等成熟框架） |
| 变现与广告规则（广告占比/激励频次/第三方 SDK） | 领域基础知识 |
| 技术版本与能力变更（基础库/模型能力/新接口） | 纯技巧与美学偏好 |
| AI 开发模式/技能包规范（SKILL.md/mcp.json 结构） | 平台历史沿革 |
| 行业监管法规（广告/金融/医疗/深度合成/AI 标识） | 法规条文逐字背诵（引用条文编号即可） |

## 规范源注册表

`references/spec-sources.json` 维护各平台官方源（仅收录厂商官方域名，防 SSRF）。每个源带四维字段：**分层 layer**（national 国家法律 / industry 行业监管 / platform 平台规范 / overseas 海外法域）、**法域 jurisdiction**、**内容模态 modalities**、**生命周期**（由规则快照与 learner 跟踪）：

| 平台 | 域名 | 分层/法域 | 说明 |
|---|---|---|---|
| wechat-minigame | developers.weixin.qq.com | platform/cn | 微信小游戏接入/运营/审核 |
| wechat-ai-skill | developers.weixin.qq.com | platform/cn | 微信 AI 开发模式接入/FAQ |
| skillhub | cloud.tencent.com / skillhub.cloud.tencent.com | platform/global | 腾讯 SkillHub 文件规范 |
| openai | platform.openai.com | overseas/global | 提示词工程指南 |
| anthropic | docs.anthropic.com | overseas/global | 提示词工程指南 |
| aliyun | help.aliyun.com | platform/cn | 百炼提示词工程指南 |
| volcengine | volcengine.com | platform/cn | 火山引擎提示词工程指南 |
| douyin-minigame | developer.open-douyin.com / partner.open-douyin.com | platform/cn | 抖音小游戏文档/审核/运营规范 |
| qq-minigame | open.qqgame.qq.com / qqgame.qq.com | platform/cn | QQ 游戏开放平台规范/接入指引 |
| kuaishou-minigame | open.kuaishou.com | platform/cn | 快手小游戏开发流程/开发者工具 |
| alipay-minigame | opendocs.alipay.com / open.alipay.com | platform/cn | 支付宝小游戏文档/开放平台 |
| baidu-minigame | smartprogram.baidu.com | platform/cn | 百度小游戏文档（介绍/API/教程/运营） |
| quickgame-alliance | www.quickapp.cn | platform/cn | 快游戏联盟（vivo/OPPO/小米/荣耀统一标准） |
| huawei-quickgame | developer.huawei.com | platform/cn | 华为快游戏接入 |
| vivo-minigame | minigame.vivo.com.cn | platform/cn | vivo 小游戏开发者文档 |
| national-game | www.nppa.gov.cn / www.gov.cn | national/cn | 国家层游戏合规（防沉迷/版号/实名/内容安全，全平台统一） |
| deepsynthesis-cn | www.cac.gov.cn | industry/cn | 深度合成管理规定（多模态 AI 生成） |
| ai-label-cn | www.gov.cn | national/cn | AI 生成合成内容标识办法（2025-09-01 施行） |
| eu-ai-act | eur-lex.europa.eu / digital-strategy.ec.europa.eu | overseas/eu | 欧盟 AI 法案（Regulation (EU) 2024/1689，2026-08-02 生效） |
| app-store | developer.apple.com | platform/global | App Store 审核指南 |
| google-play | developer.android.com | platform/global | Google Play 开发者政策 |
| oceanengine | support.oceanengine.com | platform/cn | 巨量引擎广告规则中心 + 投放管理规范 |
| finance-cn | www.gov.cn | industry/cn | 金融产品网络营销管理办法（2026-09-30 生效）+ 答记者问 |

> 小游戏全平台闭环：微信/抖音/QQ/快手/支付宝/百度/快游戏联盟/华为/vivo + 国家层统一合规，共 10 个 game 领域规范源。
> v1.0.5 扩展：行业监管（深度合成）、国家层（AI 标识）、海外法域（EU AI Act）、平台类型（应用商店/广告平台）。

## 工作方式

```bash
node scripts/verify-spec.mjs --platform <平台>   # 核验单个平台
node scripts/verify-spec.mjs --domain <领域>     # 核验某领域全部平台
node scripts/verify-spec.mjs --layer <层>        # 按分层核验（national/industry/platform/overseas）
node scripts/verify-spec.mjs --platform <平台> --force  # 强制刷新缓存
```

- **按需拉取**：只核验指定平台/领域/分层，不做全量轮询。
- **缓存复用**：结果缓存 `data/spec-cache/`，7 天内命中缓存不发起网络请求。
- **变更对比**：与上次快照 diff，输出新增/移除片段计数；变更自动写入 learner 学习记录（spec-changes）。
- **失败降级**：网络失败返回最近缓存；无缓存时明确提示手动核对官方规范。
- **诚实边界**：SPA 页面只取响应快照，正文语义解读依赖 AI 联网能力或人工核对，不静默断言。

## 与领域自检引擎的配合

- `verify-spec`：回答"规范有没有变"（实时核验，支持单平台/按领域/按分层批量）。
- `wechat-minigame-check`：回答"这段文案/配置合不合微信小游戏规范"（离线快照，基于 2026-09-03 核验的官方规范）。
- `national-game-check`：回答"这段方案合不合国家层合规"（防沉迷时段阈值/版号/实名/内容安全/健康游戏忠告，一套事实适用全平台）。
- `domain-compliance-check`：回答"这段内容合不合行业监管"（11 份规则快照：广告/生成式AI/深度合成/医疗/金融 + 国家层 + 欧盟/应用商店/广告平台）。
- `safety-compose`：四层组合（内容安全→行业合规→平台规范→国家法律），自动识别行业/法域/模态。
- 建议流程：先 `verify-spec --layer national` 确认国家与行业规范未变 → `domain-compliance-check` 检查内容 → `safety-compose` 四层总检 → 构建提示词。
