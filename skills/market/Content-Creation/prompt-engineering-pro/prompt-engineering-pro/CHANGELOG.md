# 版本日志（CHANGELOG）— 提示词工程系统

> 版本策略：当前版本 1.1.0（2026-09-04 多宿主 + 生命周期平台化版）；版本号按正式迭代递增（1.0.9 → 1.1.0）。后续优化、增强、升级以内容更新形式追加在本日志 1.1.0 段落内（按日期记录），并同步更新相关文档。

---

## 1.1.0（2026-09-04 多宿主 + 生命周期平台化版）

### 定位：平台层收口（+2 引擎，48 → 50）
- 从"单个 SKILL.md 技能"升级为**可部署到任何 skill 兼容宿主 + 自带健康诊断的生命周期管理 + 统一智能路由完成**，为本路线终点版本。
- 灵感来源：agentskills.io（build once, use across any skills-compatible agent、渐进披露三阶段、frontmatter 规范）/ SkillForge 平台层（Health Monitor、Skill Dependency Graph、CLI）/ skill-genesis（跨平台、validation & quality scoring）。

### 新增 2 个可执行引擎（全部确定性、零外部依赖）
- **host-adapt.mjs**：多宿主适配——生成 Claude Code / Codex(AGENTS.md) / Cursor / ChatGPT / 通用 SKILL.md 部署骨架到 host-out/；校验 frontmatter（name/description/version）。仅生成骨架，不执行宿主命令、不写宿主配置目录。
- **health-report.mjs**：健康诊断报告——全仓只读扫描（引擎注册完整性、依赖图一致性、版本一致性、JSON 有效性、死技能/冗余检测）→ {health, findings[], actions[]}（healthy/warning/critical）。只读不修改任何技能文件。

### 升级内容
- **管理 CLI 入口 `scripts/skill.mjs`**（非业务引擎）：统一管理命令集 `skill health / check / adapt / verify / report`，让"管理能力"可被真实使用。
- **`domains/registry.json` → 依赖图（DAG）**：新增 dependency_graph（10 组模板→引擎边 + 19 组引擎→词库/快照边），支持拓扑引用与影响分析（health-report 依赖图一致性校验依据）；registry version 1.1.0。
- **统一智能路由收口**：domain-router.mjs 新增 `routeRequest`——需求判定（合规核验/提示词优化/两者）→ 合规线 + 技法线引擎链，输出单份结构化报告（依赖图版本引用）；CLI `--unified`。
- **渐进披露三层规范（metadata → core → full）**：SKILL.md 摘要 / 核心指令 / references 全量三层组织，不改变语义，验证套件覆盖三层完整性。
- **`references/host-deploy.md`**（新增）：各宿主部署指南 + frontmatter 规范 + 三层加载说明 + 安全边界。
- **`references/health-report.md`**（新增）：健康维度说明 + 等级判定 + 报告结构 + 生命周期关系。
- **validate.mjs P10 门禁**：2 新引擎存在 + engine-catalog 注册 + 依赖图存在 + 统一路由 both 判定 + host-adapt 校验/生成 + health-report 结构（引擎总数 50）。
- **attack.mjs §15（A-96~A-103）**：新引擎健壮性攻击——未知宿主/越界目录/路径防护/管理 CLI，104/104 通过。

### 安全要点
- host-adapt 仅生成部署骨架到 host-out/，不执行宿主侧命令、不写宿主配置目录（safePathOut 校验）。
- health-report 只读扫描，不删除/修改任何技能文件（死技能只标记不删除）。
- 三层加载不改变 SKILL.md 语义，仅重组引用入口；验证套件覆盖三层加载完整性。
- 国际化与 REST/MCP/Web Dashboard 仅作为可选扩展，默认不启用（避免平台膨胀违反 0 冗余原则）。

### 跨平台兼容修复（Coze 等平台部署）
- **根因**：Coze 后端对 SKILL.md 的 `description` 按 **UTF-8 字节数** 校验（业界规范"1024 字符"在 Coze 实现为 1024 字节）；此前 description 字符数 571 < 1024（字符口径通过）但含 296 个中文字符 → UTF-8 字节 1262 > 1024，导致 `copyUploadSkill failed: skill description exceeds maximum length of 1024 characters`。
- **修复**：SKILL.md `description` 压缩至 434 字符 / **900 字节**（≤1024，保留全部触发词与核心能力，且覆盖触发评测对象词 system_prompt/指令），跨平台（Anthropic/Claude Code/扣子/Coze 等）均兼容。
- **防回归**：skill-pack-check.mjs 新增 `description UTF-8 字节 ≤1024` 检查项（跨平台兼容门禁），与字符数检查并行校验。

---

## 1.0.9（2026-09-03 自进化 + 实证评估强化版）

### 定位：引擎层自进化闭环（+5 引擎，43 → 48）
- 补齐"记录 → 评估 → 验证 → 诊断 → 进化"自进化闭环：让系统越用越懂用户、越用越好用，同时严格受控（进化不自动落盘、实证默认离线、数据治理）。
- 灵感来源：AutoSkill（无稳定偏好就不创建）/ SkillForge（Track→Rank→Diagnose→Evolve）/ Anthropic 官方"先定义成功标准+建立评测"。

### 新增 5 个可执行引擎（全部确定性、零外部依赖；实证评估默认离线）
- **track-outcome.mjs**：执行反馈追踪——记录每次生成/评分/审计 outcome（成功/质量分/耗时/契约缺陷/采纳）到 data/outcomes 按月记录 + 滚动统计 + 数据治理（--purge/--export、保留期 90 天、不采集身份、字段白名单）。
- **run-eval.mjs**：实证评估执行——按评测清单（eval-case-gen 生成）dry-run 本地规则校验（默认零外部调用）/ API 对比（需显式密钥）→ case_results + technique_evidence（effective/pending/no_evidence 不虚构）。
- **output-check.mjs**：输出侧契约验证——实际输出 vs 契约约束（格式/长度/引用/禁止项）→ deviations + fixes；与契约审计互补（一个查 prompt 本身、一个查输出侧）。
- **diagnose-failures.mjs**：失败模式诊断——outcomes 聚类反复失败（缺 Non-goals/无验证标准/低分/输出未达标）→ 归因 + 置信度；实证原则：样本 ≥3 才给归因，无数据诚实返回"样本不足"。
- **skill-evo.mjs**：受控进化循环——从诊断结果（diagnose-failures 输出）生成进化提案（改进/新增/废弃模板/版本演进），默认 dry-run，--apply 才写入 references/proposals/ 供人工评审（validate + 敏感词门禁）。画像层（1.0.8）保持"只记不改"，进化提案由技能层独立承担，两者职责分离。

### 升级内容
- **learner.mjs**：升级为反馈驱动——读取 data/outcomes 输出技能健康度（成功率/使用频次/最近活跃）；新增 --purge/--export 数据治理入口；画像层边界保持"只记不改"。
- **domains/registry.json**：每个领域新增 health 预留字段（success_rate/usage/first_seen/last_seen，由 track-outcome/learner 动态计算）。
- **references/self-evolution.md**（新增）：自进化原则——三层分工（画像层/数据层/技能层）、受控进化五原则、实证评估原则、数据治理规范、闭环图。
- **数据治理 data/outcomes 规范**：仅存工作区 data/、不采集身份、保留期 90 天、--purge/--export；outcomes 不含可执行危险内容；提案写入前过 validate + 敏感词扫描。
- **validate.mjs P9 门禁**：5 新引擎存在 + engine-catalog 注册 + 冒烟回归（空事件报错/统计正确/空清单报错/输出验证结构/诊断聚类/进化提案默认不落盘/数据治理 confirm 保护）。
- **attack.mjs §14（A-86~A-95）**：5 新引擎健壮性攻击——缺参/非法 JSON/空输入/路径穿越/数据治理保护，96/96 通过。

### 安全要点
- 进化不自动落盘（skill-evo 默认 dry-run，--apply 需显式且过 validate 门禁）。
- 实证评估默认离线（run-eval 默认 dry-run 零外部调用；API 模式需显式密钥与目标模型，仅作对比分析）。
- 数据治理（outcomes 仅存工作区/不采集身份/保留期 90 天/--purge/--export；提案写入前过敏感词扫描 + 契约 schema 校验）。

---

## 1.0.8（2026-09-03 系统化整合 + 统一路由雏形版）

### 定位：架构层整合（+3 引擎，40 → 43）
- 补齐模型适配 + 对抗防御系统化 + 自进化边界澄清（画像层）+ 统一智能路由雏形 + 用户引导入口。从"功能多"到"系统成"的关键一跳。

### 新增 3 个可执行引擎（全部确定性、官方有据、零外部依赖）
- **model-adapt.mjs**：模型适配路由——按 model_family 返回技法包（结构语法/CoT 策略/输出格式/防幻觉/长上下文/System Prompt，含官方来源标注）；识别推理模型族（gpt-o 系/gemini-thinking/deepseek-r1/kimi-k2/claude-extended 不给显式 CoT）；与 technique-router 组合"模型 × 任务"双层路由。
- **prompt-defense.mjs**：对抗防御矩阵——按五类对抗（injection/jailbreak/leaking/factuality/bias）结构化扫描 + 分类防御策略；与 scan-safety（被动红线检测）互补，只做防御知识输出。
- **adversarial-test.mjs**：主动对抗测试——内置对抗用例对目标 prompt 做本地静态弱点分析（输入输出隔离/白名单/边界/兜底/泄露口径），输出逐用例风险 + 脆弱点定位 + 风险等级 + 修复建议；三引擎闭环"测试→检测→防御"。

### 统一路由雏形（架构层）
- **domain-router.mjs**：新增 `classifyIntent`——从需求判定意图（compliance_check / prompt_optimization / both / none），作为"合规核验线"与"提示词技法线"的统一入口；routeDomain 输出含 intent 字段。

### 自进化边界澄清（画像层，只记不改）
- **learner.mjs**：新增 `recordRouteLearn` / `routeLearning`——记录"哪些 领域×模型族×技法 组合对用户有效"（data/learning/route-learning.json，与 spec-changes 并列），输出有效/低效组合观察；**不产出模板/技能修改提案**（那是技能层职责）。

### 内容与词库
- **jurisdiction-detect.json**：新增 model_families 检测词（9 模型族关键词）。
- **environment-matrix.md**：新增 §2.5"模型族 × 技法包映射表"（与 model-adapt 同源）。
- **prompt-defense.md**（新增 references）：五类对抗防御策略 + 通用防御 + 流水线用法 + 边界安全。
- **techniques.md**：模型专属技法入口挂接"模型 × 任务"双层路由说明。
- **guide-intro.md**（新增 references）：用户引导入口（我是谁→我能做什么→怎么用→常见任务命令流→FAQ）。

### 门禁与文档
- **validate.mjs**：新增 P8 引擎门禁（10.17）——3 新引擎注册 + 模型适配/对抗防御/主动测试/统一路由/路由学习冒烟回归。
- **attack.mjs**：新增第 13 轮（A-76 ~ A-85）覆盖 3 新引擎 + 路由/学习边界（空输入友好报错、未知模型族、双意图判定、无记录不崩溃）。
- **engine-catalog.md**：注册 3 引擎（43 引擎清单 + 1.0.8 编排说明）；SKILL.md version 1.0.8、引擎数 43、L1 统一路由 + L3 工程化入口。

### 攻击审计修复（开发期发现即修复）
- model-adapt 字符串内嵌 ASCII 引号（"think"/"请" 等 6 处）导致语法错误 → 统一改全角引号。
- model-adapt resolveModel/detectModelFamily 对数组用 Object.entries 取键（索引当键）→ 改直接遍历。

### 验证结果
- validate P0-P8 全绿；attack 86/86；43 脚本 node --check 全过；JSON 合法。

---

## 1.0.7（2026-09-03 工程化能力增强版）

### 定位：引擎层工程化（+5 引擎，35 → 40）
- 把 1.0.6 的内容资产固化为可执行引擎：契约审计、技法路由、评测生成、反模式审计、文件资产化；新增 P7 引擎门禁。

### 新增 5 个可执行引擎（全部确定性、证据引用、零外部依赖）
- **prompt-contract-check.mjs**：契约审计——按契约十一要素对 prompt 做确定性检查，输出覆盖/缺失/弱信号 + 判级 + 每要素改进建议。
- **technique-router.mjs**：决策树路由——按任务特征（agent/推理/格式/长上下文/多步/迭代/多跳）选技法，输出推荐 + 理由 + token 成本 + 不适用项；识别推理模型族（不给显式 CoT）。
- **eval-case-gen.mjs**：评测用例生成——从 prompt 生成可执行 JSON 评测清单（正向/边界/负向 + 通过标准），对齐"先建评测再优化"；仅文本级通过标准，不含危险指令。
- **anti-pattern-audit.mjs**：反模式审计——扫描命中 Don't 清单（模糊/无格式/矛盾/过长/无验证/多任务/无边界/无兜底/绝对化/指代不明）+ Do Instead 替代写法。
- **prompt-file-manager.mjs**：提示词资产化——生成 prompts/<name>.md 契约头骨架（purpose/model/token estimate/变量占位）+ 内联多行提示词规则检查；默认 dry-run，safePath 前缀校验防目录穿越。

### 编排关系（1.0.7）
- technique-router 选技术 → 无契约则 prompt-contract-check 补全 → eval-case-gen 生成评测清单 → 顺带 anti-pattern-audit 反模式扫描 → prompt-file-manager 资产化落盘（可选）。

### 门禁与文档
- **validate.mjs**：新增 P7 引擎门禁（10.16）——5 新引擎注册校验（engine-catalog 登记）+ 契约/路由/反模式/评测/资产化冒烟回归（模糊 prompt 报缺失、完整 prompt 低缺失、agent+长上下文路由、规范 prompt 0 反模式命中、评测字段完整、骨架路径正确）。
- **attack.mjs**：新增第 12 轮（A-66 ~ A-75）覆盖 5 新引擎边界——空输入友好报错（无堆栈）、超长输入不崩溃、路径穿越 name 净化、内联多行规则命中。
- **engine-catalog.md**：注册 5 引擎（40 引擎清单 + 编排说明）；SKILL.md L3 补 1.0.7 工程化入口、version 1.0.7、引擎数 35→40。

### 攻击审计修复（开发期发现即修复）
- eval-case-gen 基础用例字段名不一致（pass → pass_criteria），修正后每条用例含 expected/pass_criteria/type。
- 3 个新引擎 CLI 空输入曾泄露 Node 堆栈 → 统一 try/catch 友好报错（对齐既有引擎攻击标准）。
- prompt-file-manager --check 冗余输出（ok 时重复打印建议）已精简。
- prompt-contract-check Task 要素补"任务：/Task:"前缀识别，避免漏判自然语言任务声明。

### 验证结果
- validate P0-P7 全绿；attack 76/76；40 脚本 node --check 全过；JSON 合法。

---

## 1.0.6（2026-09-03 技法与心智模型深化版）

### 定位：内容层深化（0 新引擎，35 引擎不变）
- 补齐技法库与心智模型缺口：模型专属技法、契约心智模型、上下文管理、任务链、工具调用专门化；内容质量门禁防止"无源内容"混入。

### 新增 7 份技法参考（全部带来源/核验日期/适用范围/实证状态 frontmatter）
- **model-techniques/claude.md**：Claude 专属技法（XML 标签系统、Multishot 3-5 例、CoT 三层次、Extended Thinking min budget 1024 与 think 措辞、Claude 4.x 控制标签、Output format 正向指令）。
- **model-techniques/reasoning-models.md**：推理模型 vs 非推理模型（简单直接提示、内部校验、不强制可见 CoT、明确成功标准）。
- **model-techniques/gpt-gemini.md**：GPT/Gemini 官方 best practices（结构化输出/JSON mode、few-shot 位置、迭代反馈）。
- **techniques/context-management.md**：长上下文（文档置顶、query 末尾提升、引用接地 quote before answer、分块）+ Multi-Context Window 工作流 + 压缩策略（与 compress-verify 联动）。
- **techniques/prompt-chaining.md**：任务链拆分（单步单目标、XML/JSON 交接、隔离调试）+ 并行执行；保留"无锚 chain 禁用"硬约束。
- **references/prompt-contract.md**：Prompt Contract 契约心智模型（Objective/Context/Task/Constraints/Non-goals/Output format/Examples/Process/Verification/Failure handling/Style 十一要素 + 强弱缺失判例 + 与 Q-Score 映射）。
- **techniques/tool-use-prompts.md**：tool-use/MCP/function calling 专门化（工具定义与 schema 优化、工具选择策略、失败恢复、输入输出隔离防工具侧注入）。

### 新增速查与矩阵
- **technique-quickref.md**：技法×场景×token 成本速查表（zero-shot/few-shot/CoT/ReAct/Reflection/Chaining/Self-ask + 按场景选技法）。
- **techniques.md 升级**：补"技术×任务矩阵"（10 类任务 × 推荐技术组合 × 模板）+ 每可靠技术 before/after 示例 + 模型专属技法指针 + 专门技法文件指针；清理"当前版本未包含"占位。

### 模板契约标注
- **templates.md**：39 个模板全部标注"契约要素覆盖"（O/C/T/Cn/NG/Out/Ex/Pr/V/FH/St 图例），提示构建时对未覆盖要素（尤其 NG/V/FH）人工补充。

### 门禁与版本
- **validate.mjs**：新增 P6 内容质量门禁——references/techniques/（含子目录）与 prompt-contract / technique-quickref 强制 frontmatter 四字段（source/verified/scope/evidential），缺即失败；verified 须为日期格式。
- **版本源修复**：单一版本源 references/lexicon/red.json meta.version 由 1.0.4 升至 1.0.6（1.0.5 遗留版本源未同步），3 个引擎标识（build-prompt/qscore-full/score-prompt）同步 1.0.6。

### 文档联动
- SKILL.md：L3 技术选择补矩阵/速查/模型专属技法/契约入口；参考指针补充新文件；version 1.0.6。
- engine-catalog.md / GUIDE.md：内容资产说明与版本同步。

### 攻击审计修复（疯狗模式逐行扫描发现）
- 契约要素数量修正：Prompt Contract 实为 11 要素（Objective→Style 共 11 项），全库"十要素"统一改"十一要素"（prompt-contract / techniques / templates / SKILL / CHANGELOG）。
- prompt-contract 维度映射补 Structure 维（原只列 7 维，现与 scoring-rubric 8 维完整对应）。
- engine-catalog.md 删除 token-count 重复行（1.0.5 遗留冗余，0 冗余要求）。
- environment-matrix.md 清理"当前版本未包含"占位段（怪癖清单已由 model-techniques 覆盖；精确版本矩阵改走情报检索动态核验）。
- claude.md 官方口径修正：Multishot 改为官方"3-5 个多样相关示例"表述；min_budget 改"从最低 1,024 逐步调优"；think 措辞敏感改"官方建议替代词避免弱推理"；控制标签补"随官方版本迭代"说明。
- 内容真实性联网核验：Extended Thinking min budget 1024 / think 词敏感 / query 末尾提升 30% / OpenAI 六策略 / Multishot 3-5 例 / XML 原生偏好 / 控制标签，均对照官方来源核实；query 末尾表述由"检索正确性增益"改"回答质量提升"以贴合官方口径。
- **注入词库误报修复（功能缺陷）**：injection.json 的 `输出.{0,8}(提示词|...)` 特征把"输出：终版提示词"这类**提示词工程本职行为**误判为注入。改为"指向模型自身才判泄露"（`输出(你的|自己的|你最初的?|...).{0,6}(提示词|...)` 或裸"原始/初始指令"），消除了对 expert-personas / llm-judge-prompt 的误报，同时保留 INJ-03 等真实注入变体命中；safety.json 新增 CLN-S11 防回归用例，safety 断言 19/19 通过。injection.json 词库版本 1.0.4→1.0.6。

### 验证结果
- `node scripts/validate.mjs`：P0-P6 全部门禁通过（含新内容质量门禁）
- `node scripts/attack.mjs`：攻击套件全量通过
- `node scripts/matrix-check.mjs`：四方矩阵一致
- 全部 35 个脚本 `node --check` 语法通过；新 references 引用完整；打包解压复验全绿

---

## 1.0.5（2026-09-03 全行业全法域合规版）

### 定位升级：架构全 + 策略全 + 价值全（覆盖全平台、全行业、全领域、全法域）
- **架构全（可插拔）**：新增「领域合规规则快照仓库」（references/rules/，11 份快照 + _schema.json 自校验），新增行业/法域 = 加一份快照，引擎零改动。规则快照带四维字段：法域（jurisdiction）、内容模态（modalities）、法律层级（law_level：行政/民事/刑事/混合）、生命周期（snapshot_checked / effective_date / status / superseded_by）。
- **策略全（三层覆盖模型）**：L-core 深度覆盖（中国核心行业 7 份快照）/ L-extend 快照覆盖（海外法域与平台类 4 份快照）/ L-tail 按需接入（新行业随时加快照）。
- **价值全（高发高风险优先）**：领域选型按"高发违规风险 × 高处罚后果 × 用户高频使用"排序，不追求清单式枚举（任何清单交付当天即过时）。

### 新增引擎（33 → 35）
- **domain-compliance-check.mjs 领域合规画像引擎**：加载 rules/ 快照（schema 预校验防规则注入），按 domain + jurisdiction + modality 匹配，三档结论（pass/warn/remind）；规则与引擎分离，新增行业只加数据。
- **safety-compose.mjs 四层安全组合器**：L1 内容安全（scan-safety，red 短路）→ L2 行业合规（domain-compliance）→ L3 平台规范（可选，提示对应平台引擎）→ L4 国家法律（national-* 快照）；未指定领域/法域时自动识别（内容行业词库 + 法域/模态词库）。

### 规范源扩展（spec-sources 16 → 23 平台）
- 新增分层字段（layer: national/industry/platform/overseas）+ 法域字段（jurisdiction）+ 模态字段（modalities）。
- 新增 6 个官方源：深度合成规定（cac.gov.cn）、AI 生成合成内容标识办法（gov.cn，2025-09-01 施行）、欧盟 AI 法案（EUR-Lex 2024/1689，2026-08-02 生效）、App Store 审核指南（developer.apple.com）、Google Play 政策（developer.android.com）、巨量引擎广告规则中心（support.oceanengine.com）；另有金融产品网络营销管理办法（gov.cn，2026-09-30 生效）作为 industry 层核验源。

### 规则快照仓库（references/rules/，11 份）
- 中国核心行业：advertising-cn（广告法/互联网广告管理办法）、ai-aigc-cn（生成式AI暂行办法）、deepsynthesis-cn（深度合成规定 + AI 标识办法，多模态）、medical-cn（医疗广告管理办法 + 认定指南 2025）、finance-cn（金融产品网络营销管理办法，2026-09-30 生效）、national-ai（算法备案/红线）、national-finance（持牌/非法集资/诈骗红线）。
- 海外与平台：eu-ai-act（EU AI Act）、app-store（App Review Guidelines）、google-play（Play 政策）、oceanengine（巨量投放规范）。

### 引擎升级
- **verify-spec.mjs**：新增 --layer 筛选（national/industry/platform/overseas）；输出带分层/法域标签；检测到规范变更自动写入 learner 学习记录（spec-changes）。
- **learner.mjs**：新增规范变更学习（recordSpecChange）与生命周期提醒（specLearning：未生效/已废止/草案状态提醒）；learn() 输出附带生命周期摘要。
- **domain-router.mjs**：新增法域/模态识别（detectJurisdictionModality，基于 references/lexicon/jurisdiction-detect.json），不破坏原领域路由契约。

### 新增词库
- references/lexicon/jurisdiction-detect.json（法域/模态识别）
- references/lexicon/content-domain-detect.json（内容行业识别，供 safety-compose 使用；覆盖 advertising/ai-aigc/deepsynthesis/medical/finance/game 六类内容行业，平台/法域类不在此识别）

### 游戏合规闭环说明
- 内容行业识别含 game（游戏/小游戏/氪金/抽卡等）；四层组合对 game 类内容不重复实现行业规则，诚实指引到专项引擎（wechat-minigame-check / national-game-check，覆盖国家层防沉迷/版号/实名/内容安全），避免空转与"全部通过"误判。
- 规范源另含金融产品网络营销管理办法（industry 层，2026-09-30 生效），可通过 `verify-spec --layer industry` 核验。

### 规范时效承诺
- 每条规则快照标注 snapshot_checked 核验日期；规则引用官方条文编号与来源 URL；正式发布前先运行 verify-spec 核验最新官方规范。已核实的官方源 URL 见 references/spec-sources.json 与各规则快照 sources。

---

## 1.0.4（2026-09-03 领域化与自进化版）

### 定位升级：专业垂直的提示词工程系统（不限于游戏/不限于微信）
- 能力从「微信小游戏场景」升级为 **通用领域化提示词工程系统**：游戏 / 视觉 / AI 工程 / 电商 / 内容五大领域可插拔扩展（domains/registry.json），任何行业可通过注册表新增领域接入，不写死平台。
- 领域 = 模板集 + 规范源 + 词库 + 评分权重 + 引导的完整组合（见 references/domain-architecture.md），而非单一模板叠加。

### 新增引擎（25 → 32）
- **domain-router.mjs 领域路由**：关键词计分识别领域（game/visual/ai/ecommerce/content，未识别走通用），支持 --domain 强制指定；输出领域指纹（模板/规范源/词库/权重/引导）。
- **verify-spec.mjs 规范实时核验**：按官方源（7 平台白名单）拉取最新平台规范 → 与缓存 diff → 提示已变更项；7 天缓存 + 离线降级 + SSRF 白名单 + 2MB 截断。
- **skill-pack-check.mjs 发布合规与打包**：Skill 包结构/命名/大小/路径合规检查 + 零依赖 ZIP 打包（--build，自动排除 data/ 运行时目录），供平台发布前自检。
- **feedback.mjs 反馈采集**：记录使用行为反馈（隐式信号 + 主动评分），data/feedback 持久化，供 learner 学习。
- **learner.mjs 自动学习**：从反馈提炼画像建议（默认 dry-run，--apply 确认后写入 habit-profile），只影响默认值不影响评分，防偏好固化。
- **wechat-minigame-check.mjs 微信小游戏合规自检**：离线规则快照（广告占比/激励视频/适龄/防沉迷/绝对化用语/第三方广告 SDK），规范日期标注在文件头。
- **wechat-skill-gen.mjs 微信 AI 开发模式技能脚手架**：生成 SKILL.md + mcp.json + 原子接口的合规骨架，内置官方内测提示与结构检查。

### 领域模板（20 → 39）
- 新增 19 个领域模板：游戏 5（GAME-DEV/NPC/DESIGN/ASSET/STORE）、视觉 4（IMAGE-GEN/CHARACTER-DESIGN/UI-DESIGN/VIDEO-SCRIPT）、AI 工程 3（AGENT-SYSTEM/SKILL-PACK/MCP-DECL）、电商 4（PRODUCT-TITLE/DETAIL-PAGE/LIVE-SCRIPT/CS-SCRIPT）、内容 3（XHS-NOTE/WECHAT-ARTICLE/SEO）。
- build-prompt.mjs 新增领域路由 DOMAIN_ROUTE + DOMAIN_SUB（领域+子类精确选型）；matrix-check 纳入领域路由可达性校验。

### 数据与文档
- 新增：domains/registry.json（5 领域注册表）、references/lexicon/domain-detect.json（领域触发词库）、references/spec-sources.json（7 平台官方规范源）、references/GUIDE.md（30 秒上手）、references/domain-architecture.md、references/platform-spec-registry.md、references/domains/{game,visual,ai,ecommerce,content}.md。
- 新增 6 个评测集：domain-router-cases / wechat-minigame-cases / feedback-cases / verify-spec-cases / wechat-skill-cases / skill-pack-cases。
- validate.mjs 门禁扩展：registry / spec-sources / domain-detect 有效性断言；10.14 新引擎回归段；ZIP 写入器签名断言修复（EOCD 偏移正确读取）。

### 核心流水线增强
- SKILL.md 升级：L1 增加领域识别、L3 增加规范核验节点、新增「引导」「自进化与习惯」段落；五层流水线保持向后兼容。
- pipe.mjs 端到端接入领域识别与反馈采集（待确认时以 --domain/--feedback 显式触发）。

### 真实修复（冒烟测试抓出）
- **feedback**：`opt("stars")` 对 undefined 误判导致隐式记录被标成 explicit 且 score 成 NaN → 数值参数统一经 num() 解析；移除 ESM 下不可用的 require_safe。
- **wechat-minigame-check**：广告占比 30%（合规值）被误报 warn → 合规值返回 null（视为通过）。
- **learner**：删除无意义死代码 suggestions.filter(s => s.key !== "domain" || true)。
- **matrix-check**：模板名含连字符（GAME-DEV 等）不被 `[A-Z]+` 匹配 → 提取正则支持连字符与数组形式。

### 全平台小游戏闭环 + 国家层统一合规（2026-09-03 内容更新）
- **平台规范全量扩展**：spec-sources.json 新增 8 个官方规范源（抖音/QQ/快手/支付宝/百度/快游戏联盟/华为/vivo），全部为 2026-09-03 联网核实的厂商官方域名；连同既有微信小游戏，闭环小游戏全平台提示词规范核验。
- **国家层统一合规**：新增 national-game 规范源（国家新闻出版署防沉迷通知 国新出发〔2021〕14 号 / 网络游戏出版物审批 / 中国政府网政策解读）——防沉迷时段阈值、版号、实名、内容安全一套事实适用全平台。
- **新增引擎（32 → 33）**：`national-game-check.mjs` 国家层游戏合规自检（防沉迷时段/时长、实名注册、版号审批、健康游戏忠告、内容安全、未成年人保护，三档结论 pass/warn/remind）。
- **联动更新**：registry.json 的 game 领域 platforms/spec_sources 全量闭环；platform-spec-registry.md 规范源表与配合流程同步；verify-spec 白名单随 spec-sources.json 自动扩展（不新增硬编码域名）；validate 门禁新增 national-game 存在断言与 10.14.7 国家层回归；attack 新增 A-57/A-58 国家层健壮性用例。

### 验证结果
- `node scripts/validate.mjs`：P0-P5 全部门禁通过（含 7 新引擎回归 + 矩阵一致 + ZIP 断言）
- `node scripts/attack.mjs`：攻击套件 48/48 通过（新引擎健壮性用例）
- `node scripts/matrix-check.mjs`：四方矩阵一致（39 模板 / 39 信号全对齐，含领域路由可达）
- 全部 32 个脚本 `node --check` 语法通过；全新解压副本上 validate / attack / matrix 全绿；data/ 运行时数据不随包分发（skill-pack-check 自动排除）

---

## 1.0.3（2026-08-30 更名与能力升级版）

### 正式更名
- 中文名由「万能提示词系统」正式更名为「提示词工程系统」；英文标识由 `universal-prompt-pro` 更名为 `prompt-engineering-pro`（无空格、连字符分隔、xxx-xxx-pro 格式）。
- 全库同步更正：SKILL.md（frontmatter name/description/title）、references 文档、全部脚本、词库与评测集元信息、引擎内部缩写（`UPP_LEXICON_DIR` → `PEP_LEXICON_DIR`）；包内无旧名残留。
- 版本号统一迭代为 1.0.3：SKILL.md、4 个词库、8 个测试数据集、全部脚本版本标注、规范文档同步；CHANGELOG 历史段落保留原状作为版本记录。

### 新增引擎（21 → 25）
- **diagnose.mjs 诊断引擎**：输入「坏提示词 + 失败现象」→ 按失败分类（含糊/无边界/无格式/防幻觉缺失/冗余/方言不匹配等）定位根因 → 输出定向修补建议 + 受影响评分维度 + 推荐模板路由。补齐 L1「diagnose 诊断」意图的可执行落地。
- **golden-learner.mjs 好稿学习引擎**：从 data/golden 与 data/versions 统计高分提示词的结构模式（角色/目标/格式锚点/防幻觉锚点等），产出带置信度的学习建议（只建议不改评分，防偏好固化）——打通「历史好稿 → 后续构建」的自进化闭环。
- **compress-verify.mjs 压缩回归引擎**：压缩前/后 8 维评分对比 + token 变化 + 保留/回退决策——把「压缩 ≥30% 应回归验证」从建议变成可执行闭环。
- **capability-digest.mjs 能力摘要引擎**：从联网拉取的官方文档/缓存中按关键词提取模型能力信号（上下文窗口/工具调用/推理/多模态等），供 fit 维度标注"可能过时/已更新"——为「跟上最新实践」提供执行端。

### 能力升级
- **token-count**：估算系数按模型族细分（中文/英文系数表），新增按模型族输入/输出单价成本估算（costReport）。
- **version-store**：新增 `promptDiff` 人类可读并排 diff（行级增删），替代仅截断字符串的对比视图。
- **habit-profile**：扩展画像键（output_format / citation / tone 体验默认值），仍不影响评分。
- **build-prompt**：支持可选注入 golden-learner 学习建议（默认不注入，行为不变；pipe 端到端接入后按需附加）。

### 描述与文档去废话（2026-08-30）
- SKILL.md frontmatter `description` 重写为基于真实能力的介绍：删去「不用于：普通写作/翻译/摘要、代码生成」等无信息量负向废话（纯属占用触发描述），改为实际能力陈述（七类意图 / 8 维评分 / 安全扫描 / 25 引擎 / 五层流水线）+ 真实边界「非提示词工程类请求不触发，走宿主常规能力」。
- `references/agent-skills-spec.md` 触发纪律同步去废话（负面触发描述改为真实边界）。
- `scripts/validate.mjs` 门禁同步：移除强制描述含「不用于…」的旧检查（该检查曾逼文档保留废话），改为双向校验——description 须含真实能力锚点（提示词工程动词），且不得出现「不用于普通写作/翻译/摘要/代码生成」废话负向词（防回潮）。

### 复验修复（2026-08-30）
- **version-store**：`listVersions` 此前只跳过损坏 JSON，共享/数据目录混入其他合法 JSON（如 search-cache、evolve 记录）时，CLI 列表渲染 `v.prompt.slice()` 崩溃（Cannot read properties of undefined）；现过滤仅保留真正的版本记录（含 id 与 prompt），渲染侧再加兜底。
- **evolve**：`proposeRules` 早退路径缺 `total` 字段，CLI 打印「共 undefined」；现补全并在返回前读取既有提案数。`add-failure` 的 id 由「时间戳+prompt 哈希」改为追加随机后缀（事件级唯一），修复同秒相同失败互相覆盖、削弱聚类计数的问题。
- **UTF-8 BOM 健壮性**：build-prompt 指纹文件、judge-validate 判定 JSON、capability-digest 缓存 JSON 此前未剥离 BOM，Windows 下用户文件带 BOM 时 JSON.parse 失败；diagnose / score-prompt / qscore-full / sem-score 的提示词文本读取同样可能混入 BOM 前缀字符。现统一在全部用户输入读取处（文件与 stdin）剥离 `^\uFEFF`，与 golden-learner 既有 BOM 处理对齐。
- **词库路径迁移**：安全词库自 `references/data/lexicon` 迁移至 `references/lexicon`（技能包规范将 `data` 目录名视为运行时数据目录、禁止随包分发，平台校验报 invalid package path "references/data/"）。同步更正 scan-safety.mjs 默认词库目录、validate.mjs 目录完整性与版本单一来源路径、SKILL.md、safety-policy.md、safety.json 评测用例路径。
- **attack**：新增 A-45（version-store 混合 JSON 健壮性）、A-46（build-prompt BOM 指纹）、A-47（judge-validate BOM 判定），用例总数 45 → 48。

### 验证结果
- `node scripts/validate.mjs`：P0-P5 全部门禁通过（含新增 4 引擎回归）
- `node scripts/attack.mjs`：攻击套件 48/48 通过（含混合 JSON / BOM 健壮性用例）
- `node scripts/matrix-check.mjs`：四方矩阵一致
- 全部 25 个脚本 `node --check` 语法通过；全新解压副本上 validate / attack / matrix / trigger 全绿；包内无 `references/data` 目录（词库路径已迁移，平台包路径校验通过）

---

## 1.0.2（2026-08-29 安全加固与缺陷修复版）

### 安全修复（高危）
- **路径穿越全面封堵**：`--dir` / `--id` / `--cases` / `--skill` / `--cache-dir` / `--profile-dir` 等参数此前可读写包外任意位置，现统一经 `lib.mjs` 新增的 `safePath` / `safeDir` / `safeId` 安全边界校验，仅允许包内目录或系统临时目录（测试注入用）。
  - 涉及脚本：version-store、search-cache（含 clear 批量删除）、habit-profile、run-evals、evolve、pipe、fetch-prompt-practices、trigger-eval、calibrate、scan-safety
- **version-store `--id` 穿越向量**：用户可控 id 现经 `safeId` 清洗（剥离路径分隔符与 `..`）。
- **fetch-prompt-practices 攻击面收紧**：`--allow-any-domain` 使用时向 stderr 打印醒目警告；`--allow-domains` 追加项须含域名点号（拒绝顶级域通配）；`--cache-dir` 纳入安全边界；响应体超 2MB 截断。
- **scan-safety 词库健壮性**：词库条目正则损坏时跳过该条并记录警告，不再整体崩溃；`UPP_LEXICON_DIR` 经安全边界校验。

### 逻辑 Bug 修复
- **build-prompt**：删除 CoT 推理分支中两分支均为空字符串的死代码三元表达式。
- **run-evals**：pass 判定由"或"改为"且"——同时声明 expected_band 与 expected_score_min 时两者均须满足（原实现 band 匹配但分数不达标也误判通过）；报告文件名追加短哈希防同秒碰撞覆盖。
- **expert-panel**：arbitrate 自定义权重时加权平均公式统一（逐项乘权重再除权重总和）。
- **qscore-full**：LLM 覆盖分数保留一位小数（消除 ±0.5 舍入偏差）；weightSum 为 0 时降级返回而非除零产出 NaN。
- **trigger-eval**：空用例集除零防护（比率置 0 并标注警告）；frontmatter 解析支持跨行 description。
- **calibrate**：Spearman 相关在样本数 <2 时返回明确降级而非除零。
- **search-cache**：TTL 时间格式读写不一致修复（兼容 ISO 与紧凑两种历史格式；无法解析按过期处理）。
- **version-store**：排序比较器补全相等分支；防重循环加上界；rollback 不再忽略 currentPrompt 参数（返回新旧对比）。
- **habit-profile**：补齐 string 类型画像键的长度与内容校验（剥离控制字符、限长 120）；get 子命令缺 `--key` 时明确报错。

### 健壮性与工程增强
- **lib.mjs 公共库升级**：新增 `safePath` / `safeDir` / `safeId` / `escapeRegExp` / `isMain` 五个安全与工程工具函数。
- **主入口判定统一**：20 个 CLI 引擎的入口判定改用 `lib.isMain`（pathToFileURL 实现），修复 Windows 含空格/中文/特殊字符路径下 CLI 静默不执行的问题（`validate.mjs` 为门禁脚本，按主执行结构直接运行，无需守卫）。
- **动态 import 统一**：全部 `import(\`file://...\`)` 拼接改为 `pathToFileURL(...)` 写法（30 处），消除含空格/中文安装路径下的加载失败。
- **matrix-check**：task 名拼正则前经 `escapeRegExp` 转义（正则注入防护）；依赖文件缺失时预检降级而非崩溃。
- **judge-validate**：无文件参数且 stdin 为 TTY 时提示并退出，不再静默挂起；证据引用截断时标记 `truncated: true`。
- **token-count**：去除无异步操作的多余 async 关键字；重复句定位改为报告第二次出现位置。
- **sem-score**：方言信号正则由 `(?=.*)` 前瞻写法改为语义等价的无回溯版本（消除超长输入下 O(n²) 回溯风险）；去除同步函数的冗余 Promise 包装；输入文件加存在性检查。
- **score-prompt / build-prompt 等 CLI**：输入文件不存在或 JSON 非法时给出友好错误信息，不再抛出原始堆栈。
- **attack 测试套件**：临时目录清理移入 try/finally（异常路径不泄漏）；新增真正的路径逃逸用例并断言被安全边界拦截。
- **validate**：readdirSync 改为顶部静态导入。

### 版本统一
- 全部 17 处版本号（SKILL.md、4 个词库、8 个测试数据集、3 个引擎标识、规范文档）统一为 1.0.2。

### 验证结果
- `node scripts/validate.mjs`：P0–P5 全部门禁通过
- `node scripts/attack.mjs`：攻击套件 35/35 通过（含 A-03b 真逃逸拦截用例）
- 全部 21 个脚本 `node --check` 语法通过

### 深度核验记录（2026-08-30）
- 全库逐项复核：发现此前部分修复未落盘（23 项缺失），全部手动补齐并逐一验证
- 追加修复：pipe.mjs `--dir`/`--profile-dir` CLI 安全边界、`--fp` 缺值提示、budget 缓存、缓存错误日志含堆栈首行；version-store API 层 `safePath` 纵深防护；fetch-prompt-practices 主入口守卫（防导入时意外触发网络请求）；attack.mjs 四轮临时目录全部改为 try/finally 清理
- 最终状态：30 处旧式动态导入归零、旧式 isMain 归零、重复代码清零（ts 去重 + opt 统一 makeOpt）

---

## 1.0.1（2026-08-24 初始发布）
- 五层流水线（L0 安全前置 → L1 意图路由 → L2 环境指纹 → L3 决策构建 → L4 自评估 → L5 输出）
- 21 个可执行引擎、20 个提示词模板、4 类安全词库、8 组测试数据集
- 零外部依赖，Node ≥14.18

---

## 后续更新记录（追加到当前版本段落）
<!-- 后续内容优化/增强/升级请按以下格式追加：
### 1.0.3（YYYY-MM-DD）更新
- 变更条目
-->
