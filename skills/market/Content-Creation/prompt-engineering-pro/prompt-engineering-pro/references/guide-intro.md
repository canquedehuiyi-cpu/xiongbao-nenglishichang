---
source: 本 skill 能力自述（L0-L5 流水线 + 引擎清单）+ 头部提示词 Skill 的引导实践
verified: 2026-09-03
scope: 新手用户首次使用本提示词工程系统的引导
evidential: 已验证（引导中的命令流与引擎 --help 均来自 engine-catalog 实际可执行项）
---

# 用户引导（Guide-Intro）

> 面向第一次使用本系统的用户：我是谁 → 我能做什么 → 怎么用 → 常见任务命令流 → FAQ。

## 1. 我是谁

提示词工程系统（Prompt-Engineering-Pro）——把"写提示词"变成工程化流程的助手：
构建、评估、诊断、优化、压缩、迁移、合规核验，覆盖全平台、全行业、全模型族。

## 2. 我能做什么

- **构建**：按需求生成结构化提示词（L3，模板 + 技法 + 契约十一要素）
- **评估**：Q-Score 8 维评分（结构 4 维 + 语义 4 维，带证据）
- **诊断**：提示词不 work 时定位原因（失败分类 + 反模式 + 对抗弱点）
- **优化**：压缩、迁移、改写、改进
- **合规**：官方规范实时核验 + 平台合规检查（小游戏全平台/国家层/应用商店/广告平台）
- **自进化**：越用越懂你的偏好，只做画像记录，不擅自改规则

## 3. 怎么用

- 首次：读 `references/GUIDE.md`（30 秒上手）；运行 `node scripts/validate.mjs` 自检环境。
- 流水线（L0-L5）：需求识别 → 环境指纹 → 决策构建 → 自评估 → 输出。
- 想深度使用：参考下节"常见任务命令流"。

## 4. 常见任务命令流

| 我要… | 推荐命令流 |
|--------|------------|
| 写一个提示词 | `node scripts/pipe.mjs --request "<需求>"`（安全→构建→8 维评分→版本快照） |
| 评估已有提示词 | `node scripts/score-prompt.mjs <prompt.txt>` → `sem-score.mjs` |
| 提示词不 work | `diagnose.mjs` → `anti-pattern-audit.mjs` → 按建议修订 → 回归 |
| 优化提示词 | `pipe.mjs` → `compress-verify.mjs`（压缩+分数对比+保留/回退）→ 回归评分 |
| 平台合规核验 | `verify-spec.mjs --layer <层>` → 专项 `wechat-minigame-check.mjs` / `national-game-check.mjs` |
| 选技法 | `technique-router.mjs --request "<任务>"` → `model-adapt.mjs --model <族>`（双层路由） |
| 对抗加固 | `adversarial-test.mjs <prompt.txt>` → `prompt-defense.mjs <prompt.txt>` → `scan-safety.mjs` |
| 看我的画像 | `node scripts/learner.mjs` / `--profile` |

## 5. FAQ

- **会不会乱改我的内容？** 不会。所有引擎只输出建议与报告，写入操作（--apply/--write）默认关闭，需显式开启。
- **评分准吗？** Q-Score 8 维评分带证据引用，无证据记 0；评分无把握会标注置信度。
- **合规信息会不会过时？** 规范核验引擎强制实时联网比对官方文档（缓存 7 天），失败会标注"可能过时"，不静默编造。
- **会不会泄露我的提示词？** 不会。产物默认落在本地工作区；输出不含 token、密钥等敏感信息。
- **新手能直接用吗？** 能。默认引导开启，≤3 轮即可产出可用提示词；老手可 `--no-guide` 关闭。
- **学到的偏好会固化影响结果吗？** 不会。画像只影响体验默认值，不影响评分结果；可 `--reset-profile` 清空。
