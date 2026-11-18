# Skill技能搭建专家 · 5 分钟速览

## 这是什么
Skill全流程工程辅助工具——许多业务涉及商业机密，更适合私有部署；本工具不提供现成技能，基于您提供的业务素材完成代建、答疑、质量分析与迭代；私用或公开、免费或收费版本由您定，全程合规执行。谁都能用——只要手里有想沉淀的谁都能用——只要手里有想沉淀的经验、手艺、标准、流程、规则、制度、技巧、技术、心法、策略、方法、判断、条件、逻辑等；不设行业、岗位与规模限制。

四大闭环：
- **链路1 从零代制作**：你想做技能，协助完成技能Skill（支持免费版本 / 收费版本）。
- **链路2 答疑教学**：怎么做技能、规范、版本与形态选型。
- **链路3 半成品修复**：做到一半卡住、报错、逻辑漂移，协助修正调优。
- **链路4 成品质量分析**：检测技能达不达标、给整改建议。

双版本：免费版本（上架后人人可免费用，也可自用）｜收费版本（使用者付费启用，需创作者开通收款通道）——两个版本均可上架、均可商用，不设使用者类型与规模门槛。

双形态：轻量模式（逻辑全内置，默认）｜API模式（调你自有的外部网关/服务）。

分发访问模式：公开模式（含免费版本/收费版本）｜专用模式‑自用版｜专用模式‑私域版，细则见 `references/REF-DST-034_DistributeMode.md`。

核心改变：**标准不再是一份等你翻的文档，而是每次开发都会被自动触发的动作**——从「每次从 0 到 1 想标准」变成「从 1 到 N 直接复用」，且"做出来能调用、能真正用起来"成为默认结果。

## 你给什么
文档（Word、PDF、PPT、TXT、MD、Excel）、图片、语音、视频、表格、链接都能接，口述零门槛；Word / PDF / PPT / Excel / TXT / MD 等资料也能直接发。想到哪说到哪，不必预先整理。

## 你拿到什么
一份**可独立调用、可跨平台安装**的合规技能Skill（含安装说明与署名编号），以及一份对照统一标准的评审／自检报告。

## 两条不可动摇边界（对外说明）
1. ✅ **我们必做到**：基于你提交的素材，严格执行全部标准，交付标准化、安全、可检验的技能工程产物——这是最低硬性底线，任何模式、任何版本类型都不降。
2. ⚠️ **我们不承诺**：不保证最终业务效果。素材质量、真实业务逻辑、实际运行场景由你掌握，不在工具可控范围；请结合自身业务场景实测验证。

## 怎么开工
回触发词即可：**做技能Skill / 开新技能 / 技能搭建开工 / 帮我把这事做成技能 / 质量分析技能 / 修复技能**。

## 标准原文与标准资料在哪
- `references/REF-SPC-001_AISkillManual_V32.md` —— 评审准则＋构建规范全集
- `references/REF-INT-015_InitForm_V32.md` —— 立项表单
- `references/REF-REV-016_ReviewPrompt_V32.md` —— 评审官模式 Prompt
- `references/REF-SKL-007_SkillSkeleton_v1.md` —— 三档必含文件清单
- `references/REF-NAM-006_NamingDiscovery.md`
- `references/REF-PAY-012_PayStandardFull.md`
- `references/REF-DEP-018_DeploySpec.md`
- `references/REF-HON-017_HonestBoundary.md`
- `references/REF-DST-034_DistributeMode.md` —— 分发访问模式标准
- `references/REF-TER-035_Terminology.md` —— 术语与命名规范（全包唯一口径）
- `references/REF-SCN-036_ScenarioDual.md` —— 双场景标准（对外开源 / 私有内部）

## 机械校验与装配
- `scripts/selfcheck_factory.py` —— 对照标准自检清单机检
- `scripts/skill_quality_check.py` —— 五维质量核验出厂闸（fail-closed）
- `scripts/package_check.py` —— 禁词／CRLF／隐形字符／时间戳
- `scripts/stamp_signature.py` —— 自动盖戳与 `_meta.json`
- `scripts/package_zip.py` —— 合规装配 zip（含出厂质检前置闸）

## 安装
见 `INSTALL.md`。

---

> 本成品由 Skill技能搭建专家 生成 · 业务内容由提供方自主提供并确认合法性
