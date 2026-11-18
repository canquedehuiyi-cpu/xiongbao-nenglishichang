# references/engine-catalog.md — 可执行引擎清单

> 本文件列出本 skill 附带的全部可执行引擎（scripts/），供宿主按需读取（渐进披露：SKILL.md 只保留入口，完整清单在此，需要时读取）。
> 覆盖能力：L0 安全 → L3 构建 → L4 评分 → L5 版本化 → 进化/画像/评测 → 门禁/一致性/安全自检 → 联网核验。

| 阶段 | 引擎 | 用途 | 用法示例 |
|------|------|------|----------|
| 端到端 | `pipe.mjs` | 完整闭环（安全→构建→评分→版本化）；`--judge <json>` 注入 LLM 判定 | `node scripts/pipe.mjs --request "..." --fp '{}'` |
| L0 安全 | `scan-safety.mjs` | 注入/红线/PII/灰线扫描 | `echo "..." \| node scripts/scan-safety.mjs` |
| L3 构建 | `build-prompt.mjs` | 环境指纹→模板路由→组装（`--learned-file` 可注入学习建议） | `node scripts/build-prompt.mjs <fp.json>` |
| L3 诊断 | `diagnose.mjs` | 提示词诊断（11 类问题 + 模板推荐；`--failure` 失败现象） | `echo "..." \| node scripts/diagnose.mjs` |
| L3 学习 | `golden-learner.mjs` | 好稿结构模式学习 → 学习建议（自进化闭环） | `node scripts/golden-learner.mjs --dir <data>` |
| L3 压缩 | `compress-verify.mjs` | 压缩候选 + 分数对比 + 保留/回退决策 | `echo "..." \| node scripts/compress-verify.mjs` |
| L3 能力 | `capability-digest.mjs` | 从联网文档提取模型能力信号（上下文/工具/推理等） | `node scripts/capability-digest.mjs --cache <fetch缓存>` |
| L3 经济 | `token-count.mjs` | token 估算/预算/冗余/压缩/成本（`--model-family` 按族估算） | `node scripts/token-count.mjs <p.txt> --budget 300` |
| L4 评分 | `score-prompt.mjs` | 结构 4 维评分 | `node scripts/score-prompt.mjs <p.txt>` |
| L4 评分 | `sem-score.mjs` | 语义 4 维评分（规则版） | `node scripts/sem-score.mjs <p.txt> --fp '{}'` |
| L4 评分 | `qscore-full.mjs` | 8 维合成 + LLM 判定覆盖 | `node scripts/qscore-full.mjs <p.txt> --fp '{}'` |
| L4 评分 | `judge-validate.mjs` | LLM 判定校验（失败回退） | `node scripts/judge-validate.mjs <judge.json>` |
| L3 情报 | `search-cache.mjs` | 检索建议缓存（TTL 7 天） | `node scripts/search-cache.mjs put --key K --data '{}'` |
| L3 情报 | `fetch-prompt-practices.mjs` | 官方提示词实践联网核验（缓存+降级） | `node scripts/fetch-prompt-practices.mjs --json` |
| L5 版本 | `version-store.mjs` | 快照/对比/回滚 | `node scripts/version-store.mjs snapshot --prompt "..."` |
| 画像 | `habit-profile.mjs` | 画像读写/清空 | `node scripts/habit-profile.mjs show` |
| 进化 | `evolve.mjs` | 失败入库/提案/确认 | `node scripts/evolve.mjs stats` |
| 评测 | `run-evals.mjs` | 分层 eval/门禁/决策 | `node scripts/run-evals.mjs gate --cases references/evals/scoring.json` |
| 评审 | `expert-panel.mjs` | 双档切换/编排/仲裁 | `node scripts/expert-panel.mjs mode --score 78` |
| 触发 | `trigger-eval.mjs` | 触发评测 | `node scripts/trigger-eval.mjs` |
| 校准 | `calibrate.mjs` | 专家盲评一致性 | `node scripts/calibrate.mjs` |
| 门禁 | `validate.mjs` | 全门禁回归 | `node scripts/validate.mjs` |
| 一致性 | `matrix-check.mjs` | 四方矩阵一致性（含领域路由可达性） | `node scripts/matrix-check.mjs` |
| 攻击 | `attack.mjs` | 安全自检（104 用例，含全角/词库降级/真逃逸/新引擎回归） | `node scripts/attack.mjs` |
| 领域 | `domain-router.mjs` | 领域路由识别（game/visual/ai/ecommerce/content，关键词计分或强制指定） | `node scripts/domain-router.mjs --request "..."` |
| 规范 | `verify-spec.mjs` | 平台规范实时核验（官方源拉取+缓存+diff+降级，需 Node≥18） | `node scripts/verify-spec.mjs --platform wechat-minigame` |
| 发布 | `skill-pack-check.mjs` | Skill 包发布合规检查 + 零依赖打包（--build） | `node scripts/skill-pack-check.mjs --dir <skill> --build --out <zip>` |
| 进化 | `feedback.mjs` | 使用反馈采集（隐式/显式，供 learner 学习） | `node scripts/feedback.mjs record --action build --domain game` |
| 进化 | `learner.mjs` | 自动学习（画像建议 + 规范生命周期提醒；--apply 写入画像） | `node scripts/learner.mjs --apply` |
| 领域 | `wechat-minigame-check.mjs` | 微信小游戏合规自检（离线规则快照，规范日期见文件头） | `node scripts/wechat-minigame-check.mjs --text "..."` |
| 领域 | `national-game-check.mjs` | 国家层游戏合规自检（防沉迷时段阈值/版号/实名/内容安全，全平台统一） | `node scripts/national-game-check.mjs --text "..."` |
| 领域 | `domain-compliance-check.mjs` | 领域合规画像引擎（references/rules 规则快照驱动：schema 校验 + 行业/法域/模态匹配 + warn/remind/pass 三档） | `node scripts/domain-compliance-check.mjs --text "..." --domain finance --jurisdiction cn` |
| 领域 | `safety-compose.mjs` | 四层安全组合器（L1 内容安全→L2 行业合规→L3 平台规范→L4 国家法律；自动识别行业/法域/模态，red 短路） | `node scripts/safety-compose.mjs --text "..." --domain finance --platform oceanengine` |
| 领域 | `wechat-skill-gen.mjs` | 微信 AI 开发模式技能脚手架生成/检查（内测提示内置） | `node scripts/wechat-skill-gen.mjs --name my-skill --desc "..."` |
| L3 技术 | `prompt-contract-check.mjs` | 契约审计：十一要素确定性检查（覆盖/缺失/弱信号 + 判级 + 每要素改进建议） | `node scripts/prompt-contract-check.mjs <p.txt>` |
| L3 技术 | `technique-router.mjs` | 决策树路由：按任务特征选技法（推理/agent/长上下文/格式/多步…）+ 理由 + token 成本 + 不适用项 | `node scripts/technique-router.mjs "任务" --fp '{"model_family":"claude"}'` |
| L3 技术 | `eval-case-gen.mjs` | 评测用例生成：从 prompt 生成可执行 JSON 评测清单（正向/边界/负向 + 通过标准） | `node scripts/eval-case-gen.mjs <p.txt> --json` |
| L3 技术 | `anti-pattern-audit.mjs` | 反模式审计：命中 Don't 清单（模糊/无格式/矛盾/过长/无验证…）+ Do Instead 替代写法 | `node scripts/anti-pattern-audit.mjs <p.txt>` |
| L3 技术 | `prompt-file-manager.mjs` | 提示词资产化：生成 prompts/<name>.md 契约头骨架 + 内联多行提示词规则检查（防目录穿越，默认 dry-run） | `node scripts/prompt-file-manager.mjs --name <slug> --purpose <目的> [--write]` |
| L3 适配 | `model-adapt.mjs` | 模型适配路由：按 model_family 返回技法包（结构/CoT/格式/防幻觉/长上下文/System Prompt，官方来源标注） | `node scripts/model-adapt.mjs --model claude` |
| L3 防御 | `prompt-defense.mjs` | 对抗防御矩阵：注入/越狱/泄露/事实性/偏见分类扫描 + 防御策略建议（与 scan-safety 互补） | `node scripts/prompt-defense.mjs <t.txt>` |
| L3 防御 | `adversarial-test.mjs` | 主动对抗测试：本地对抗用例压力测试 → 绕过风险等级 + 脆弱点定位 + 修复建议 | `node scripts/adversarial-test.mjs <p.txt>` |
| L4 自进化 | `track-outcome.mjs` | 执行反馈追踪：记录 outcome（成功/质量分/耗时/契约缺陷/采纳）→ data/outcomes 按月记录 + 滚动统计 + 数据治理（--purge/--export，保留期 90 天，不采集身份） | `node scripts/track-outcome.mjs --event-file <ev.json>` |
| L4 自进化 | `run-eval.mjs` | 实证评估执行：按评测清单 dry-run 本地规则校验（默认零外部调用）/ API 对比（显式密钥）→ case_results + technique_evidence | `node scripts/run-eval.mjs --cases <eval.json> --output <out.txt>` |
| L4 自进化 | `output-check.mjs` | 输出侧契约验证：实际输出 vs 契约约束（格式/长度/引用/禁止项）→ deviations + fixes（与契约审计互补） | `node scripts/output-check.mjs --contract <p.txt> --output <out.txt>` |
| L4 自进化 | `diagnose-failures.mjs` | 失败模式诊断：outcomes 聚类反复失败（缺 Non-goals/无验证标准/低分/输出未达标）→ 归因 + 置信度（样本 ≥3） | `node scripts/diagnose-failures.mjs` |
| L4 自进化 | `skill-evo.mjs` | 受控进化循环：诊断 + 画像 → 进化提案（改进/新增/废弃模板/版本演进），默认 dry-run，--apply 才写入 proposals/（人工闸门 + validate 门禁） | `node scripts/skill-evo.mjs --diagnosis <diag.json>` |
| L5 平台 | `host-adapt.mjs` | 多宿主适配：生成 Claude Code/Codex/Cursor/ChatGPT/通用部署骨架到 host-out/；frontmatter 校验（name/description/version） | `node scripts/host-adapt.mjs --host all` |
| L5 平台 | `health-report.mjs` | 健康诊断报告：全仓只读扫描（引擎注册/依赖图/版本一致性/JSON/死技能）→ {health, findings[], actions[]} | `node scripts/health-report.mjs [--json]` |
| 公共库 | `lib.mjs` | 共享工具（ROOT/clamp/ts/ensureDir/safePath/safeDir/safeId/escapeRegExp/isMain/makeOpt） | 被各引擎 import |

> 管理入口：`skill.mjs`（非业务引擎，管理 CLI）——统一管理命令集 `skill health/check/adapt/verify/report`（生命周期平台化的实体抓手）。
> 引擎数：本 skill 共 50 个可执行引擎（v1.1.0 新增 host-adapt/health-report 2 个，加上 1.0.9 的 48 个）。
> 内容资产（v1.0.6 内容层增强，无新引擎）：模型专属技法（references/techniques/model-techniques/）、上下文管理（context-management.md）、任务链（prompt-chaining.md）、工具调用（tool-use-prompts.md）、契约心智模型（prompt-contract.md）、技法速查（technique-quickref.md）；39 模板已标注契约要素覆盖（templates.md）；新增内容质量门禁（validate.mjs P6）。
> 1.0.7 编排（v1.0.7）：technique-router 选技术 → 无契约则 prompt-contract-check 补全 → eval-case-gen 生成评测清单 → 顺带 anti-pattern-audit 反模式扫描 → prompt-file-manager 资产化落盘（可选）；新增 validate.mjs P7 引擎门禁。
> 1.0.8 编排（v1.0.8）：统一路由雏形 domain-router.classifyIntent 判"合规/优化/两者" → model-adapt 取模型技法包 + technique-router 按任务选技法（模型×任务双层路由）→ 对抗加固 adversarial-test（主动测试）→ prompt-defense（分类防御）→ scan-safety（被动红线闸门）；新增 validate.mjs P8 引擎门禁；自进化画像层新增路由偏好学习（只记不改）。
> 1.0.9 编排（v1.0.9）：自进化 + 实证评估闭环——生成/评分/审计后 track-outcome 记录 outcome → run-eval 实证评估（dry-run 本地，API 需显式密钥）→ output-check 输出侧验证 → diagnose-failures 失败聚类归因（样本 ≥3）→ skill-evo 受控进化提案（默认 dry-run，--apply 才写入 proposals/ 人工评审）；数据治理（data/outcomes 仅存工作区、不采集身份、保留期 90 天、--purge/--export）；learner 反馈驱动输出技能健康度；新增 validate.mjs P9 引擎门禁。
> 1.1.0 编排（v1.1.0）：多宿主 + 生命周期平台化——health-report 全仓健康体检 → validate P0-P10 发布门禁 → host-adapt 跨宿主部署骨架（host-out/）→ verify-spec 规范核验 → skill.mjs 管理 CLI 统一入口（health/check/adapt/verify/report）；统一智能路由收口 domain-router.routeRequest（合规线 + 技法线单份报告）；registry.json 升级依赖图（DAG，模板→引擎、引擎→词库/快照）；渐进披露三层（metadata→core→full）规范；新增 validate.mjs P10 引擎门禁。

## 使用建议

- 需要执行安全扫描时读 `scan-safety.mjs`；需要评分时读 `score-prompt.mjs`/`sem-score.mjs`/`qscore-full.mjs`；需要版本化时读 `version-store.mjs`。
- 全量质量自检一次：`node scripts/validate.mjs`（完整性门禁）+ `node scripts/attack.mjs`（安全自检）+ `node scripts/matrix-check.mjs`（一致性）。
- 联网核验官方提示词实践：`node scripts/fetch-prompt-practices.mjs --json`（缓存+降级，无网络时明确失败或返回快照）。
