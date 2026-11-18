---
name: prompt-skill
description: "把粗糙 Prompt 诊断修复或按描述新建，认证质量达标后封装为标准 Skill 包（AWP 目录），再做矩阵测试认证、指纹闸门打包交付——当用户要「整理/评估/产品化一个提示词或技能」时使用"
user-invocable: true
metadata:
  openclaw:
    emoji: "🗂️"
    skillKey: "prompt-skill"
    requires:
      bins: [python]
    envVars: []
    # 如实声明权限范围：本技能只调用本工作区的本地 Python 引擎，
    # 不联网、仅依赖 python 解释器——声明越精简越如实，越容易通过宿主审查。
---

# Prompt 修复与 Skill 质检产线

把「Prompt 修复 / 按描述新建 / 质量认证 / 版本管理 / 封装 Skill / 技能质检 / 打包交付 /
飞轮沉淀」收敛为**十一个互相独立**的确定性任务。引擎零模型调用：评分、装配、断言、
指纹全部是本地 Python 引擎里的确定性代码（源码直跑，无需编译产物）；
**Prompt 的语义改写与被测技能的执行回填、LIVE 类材料的联网获取，全部由宿主 Agent（你）完成**
——评分结论只认引擎报告，严禁你自评替代。

## 何时使用

用户拿来粗糙 Prompt 要修/要评级；或只有一句话描述要产出标准 Prompt；或要把达标的
Prompt 产品化成可挂载 WorkBuddy/Trae 的 Skill 目录并交付。

## 使用方法（产线 SOP，按序执行）

| 顺序 | 任务 | 输入 | 产出 |
|---|---|---|---|
| 1a | `fix-prompt` | 旧 Prompt 文件 | 诊断报告 + 逐条修复清单 |
| 1b | *(你)* | 按清单**一次性**改写 | 修复稿文件 |
| 2 | `draft-prompt` | 任务描述一句话 | 标准骨架（含【待填】槽）→ *你补槽* |
| 3 | `score-prompt` | 修复稿 / 填好的骨架 | **体系A 认证**：总分≥80 **且** Risk 轨≥28 **且** Gate M 材料契约通过 **且** Gate S 实质内容（有效行≥10，防关键词堆砌空壳）**、未降级才放行**。同一文本第二次仍不达标会被闸门强制转人工 |
| 3a | `prompt-version` | 候选 ID（`--set candidate=`） | 版本链查询 / 指针回滚（`--set to=vN`）/ 标记不可回滚（`--set exclude=vN`）；快照 append-only |
| 3b | `delta-report` | 候选 ID（`--set candidate=`） | 修复对比（Repair Improvement Delta）：两版总分/双轨/8 维升降 + 缺口**按维度**增减 + 字符量 Δ；缺省对比 次新→最新，`--set from=vX --set to=vY` 可任意对比；纯只读。分数取归档快照（当时认证事实），缺口与字符量按归档正文以当前评分器重算，重算总分与归档不一致会 WARN 报评分器漂移。注：Prompt 缺口模型无 P0 分级（P0/P1/P2 只属于 `harvest-case` 的 Gold Case risk_level） |

**双路线与候选身份（score-prompt 的可选参数）**：

- 路线：`--set route=A`（从 0 新建，重做上限 2 轮）或 `--set route=B`（改已有 Prompt，修复上限 3 轮，默认）。轮次耗尽自动转人工
- 同一候选跨轮修复时**必须带同一个 `--set candidate=<ID>`**（首次送检报告里有 candidate_id）；留空则以本次文本指纹新建候选
- 每轮带一句 `--set change-reason=…` 记入版本快照
- 降级产物（确认无材料依据仍产出）带 `--set degraded=true`：**分数再高也只给 REVIEW，不放行**；补材料后重送即解除
- 分数语义（D-029）：体系A 度量的是**结构契约完备性下限**（必要条件），不是语义质量——100 分只证明「契约齐备」，语义正确性由体系B Gold Case 重放验证；关键词堆砌的空壳会被 Gate S 拦截
- 涉及外部事实（联网/检索/竞品/行业数据等）的 Prompt 必须含第 11 节材料契约（材料来源类型 NONE/PROVIDED/CORPUS/LIVE + 缺口协议 MISSING_MATERIAL），否则 Gate M 拦截；标准骨架已自带该节
- 改差了不用慌：每次送检都留版本快照，降分版本不接管 active 指针，自动回滚到历史最高版继续修（不耗轮次）；也可用 `prompt-version` 手动回滚或把走错的版本踢出回滚候选集
| 4 | `build-skill` | 达标 Prompt + 技能名 + 权限档位 | ``dist_template/output` 下的 `skills`\〈name〉\` AWP 目录（SKILL.md+PERMISSIONS+**按稿生成的领域种子用例**：从正文输出契约/红线/存疑条款自动提炼断言，覆盖 happy/edge/adversarial/refusal/conflict 五类 Gold Case，非通用 nonempty 占位） |
| 5 | *(你)* | 逐条执行包内 `testcases\*.json` 的 `input`，把技能**原样响应**存为 ``dist_template/storage` 下的 `responses`\〈case_id〉.txt` | 响应矩阵 |
| 5a | `plan-responses` | 该目录的 `SKILL.md` | **第 5 步的管道支持**：产出逐条作业单（case_id / 类别 / 风险级 / 断言 / 期望结论 / input 原文 / 目标文件名），并体检已回填的结果——待回填、空文件、孤儿文件名（对不上任何 case_id）、非 `.txt`、用例 JSON 损坏。引擎**不生成也不评判任何响应内容**（B6 严禁模型自评）；此前 `score-skill` 只给一个 `response_count` 计数，填错文件名或漏填都无从发现 |
| 6 | `score-skill` | 该目录的 `SKILL.md` | **体系B 认证**：结构+断言+通过率。响应目录缺失时自动降级为结构自检（DEGRADED，不算可用） |
| 7 | `ship-skill` | 同上 | 认证指纹一致才出 zip+manifest；未认证/认证后改动一律拒绝。另有**回归重放**：同名历史版本的通过用例用旧断言在新响应上重放，任何 PASS→非PASS（含用例被删）强制拒发（D-026） |
| 8 | `harvest-case` | 技能包 SKILL.md + 真实输入 + 类别 + 断言 | **飞轮沉淀**：真实 REVIEW/失败案例写入 testcases/ 为 Gold Case（origin=human_feedback，gold_NNN 递增）。审批规则：至少一条实质断言（nonempty 拒收）、input 去重、adversarial/refusal/conflict 必须显式 verdict。沉淀后认证作废，须重跑 score-skill（D-027） |
| 8a | `import-cases` | 技能包 SKILL.md + `cases-file`（JSON 数组） | **8 的批量版**：一次导入一组真实案例，逐条走与 `harvest-case` **完全相同**的审批规则（共用 `_approve_case`，批量不比单条宽松）——实质断言必填、input 去重（含**批内**去重）、P0 类必须显式 verdict、case_id 须符合 schema pattern 且不覆盖既有。被拒案例逐条给理由且不写入，0 例通过才 FAILED。存在意义是让 `benchmark` 的 Gold Set ≥30 门槛**可达**（靠 8 单条沉淀要跑约 25 次）；**门槛本身是 A.7 反空转的刻意设计，不予调低**。导入即改包指纹，认证作废须重跑 score-skill |
| 9 | `benchmark` | 技能包 `SKILL.md` | **Gold Set 指标引擎**（AP-11）：对包内 testcases/ 做确定性统计——五类覆盖度/实质断言率/可回测性（命中响应）/非法断言率，产出回连 Gate 的达标判定。≥30 例才产结论（A.7 反空转）；未促成可回测 Gold Set 前不晋升基线；FAR/CAR 对「应拒答正例（expected.verdict=REJECT/REVIEW）× 有真实响应」到数计算：FAR=虚假保证率、CAR=正确拒答率（拒答/存疑信号断言命中即判正确）；无应拒答样本/响应时降级只给可回测性判据，不硬造数值 |
| 10 | `sag-fetch` | 技能包 `SKILL.md` + 宿主获取的 LIVE 材料 | **SAG 材料承接**：材料契约 §11 = LIVE 时，宿主把获取到的材料（来源/日期/摘录/正文）交给引擎，引擎做确定性「溯源→落盘→注入」——溯源齐才落盘 `materials/〈topic〉/〈asof〉.md`（append-only，同 topic 不同 as-of 各存一份、不覆盖）并给出注入引用；**缺溯源任一项即 `FAILED`**（`sag_blocked=true`、`sag_missing` 列出缺哪几项），既不落盘也不注入——实测是 fail-closed 硬拒，**不是降级为 REVIEW**，宿主按退出码 1 处理；非 LIVE 早退不落盘，但 WARN 显性标注「未执行」并说明补给线。材料入包已改动技能指纹，交付前须重跑 score-skill 重认证 |

CLI 示例（工作区根目录运行；`--json` 契约见「机器接口」节；skill-file 类任务用 `--set`）：

```
python engine/main.py run --scenario prompt_skill 旧Prompt.md --task fix-prompt
python engine/main.py run --scenario prompt_skill --json --task build-skill 旧Prompt.md --set skill-name=my-skill --set net-policy=无网络·只读工作区
python engine/main.py run --scenario prompt_skill --json --task score-skill --set skill-file=<目录>\SKILL.md
python engine/main.py run --scenario prompt_skill --json --task benchmark --set skill-file=<目录>\SKILL.md
python engine/main.py run --scenario prompt_skill --json --task sag-fetch --set skill-file=<目录>\SKILL.md --set source=WebSearch --set asof=2026-08-31 --set title=竞品A季度份额 --set excerpt=市占率31.2%% --set body=竞品A 2026Q2 市占率31.2%%
```

本地个人版：无需 license、无试用额度，全部任务与特性（批量/证据包/batch_summary）恒开放。

## 不要做什么

- **不要替引擎下结论**：达标与否只以 `dist_template/output/*-cert-*.md` 报告与 JSON `state` 为准；
  报告说「未达标」就必须如实告知，不得美化
- **不要凑词刷分**：体系A 查的是契约实质；为命中词表硬塞关键词会卡在你没写的
  adversarial 用例与人工审查上
- **不要改断言凑通过**：`testcases\*.json` 的 `asserts` 只支持
  `nonempty / contains: / not-contains: / regex:` 四种机器形式。现在 `build-skill` 的
  种子已按稿自动具化（从正文输出契约/红线提炼 `contains:/not-contains:`），不是空壳；
  若正文太薄导致某类仍是 `nonempty`，**体系B 的 B5 硬闸会判它"空转未测"**——
  请补足该领域的具体预期。改断言会改包指纹，认证后任何改动都要重跑 `score-skill`
- **不要绕过 ship 闸门**：手工压 zip 交付 = 放弃质量背书；闸门拒绝时把原因转告用户，
  引导走认证/人审，而不是自行打包


## 机器接口（宿主 Agent 优先用）

调用 `python engine/main.py run --scenario prompt_skill --json --task 〈任务ID〉 〈输入文件〉`：
stdout 输出一份严格 JSON（`state` / `artifacts` / `issues` / `access`），
退出码 0 = 完成（含"待复核"）、1 = 失败、2 = 引擎未绑定（缺 --scenario 或场景名不存在）。
不要靠读人话屏幕输出转述结果。

- 动态探测本产品有哪些任务、怎么调：`python engine/main.py tasks --scenario prompt_skill --json`
  （纯元数据）——宿主不必硬编码本文件的知识
- 批量：`python engine/main.py run --scenario prompt_skill --json --task 〈任务ID〉 --batch <目录>`
  对目录下每个文件各执行一次，stdout 输出一份汇总 JSON
  （含 `batch.processed` 与每个文件的结果）。
  批量产物按源文件隔离在 ``dist_template/output` 下的 `batch`\<序号>-〈文件名〉\`，互不覆盖。
  多表类任务（如对账）批量目录只填第一个 FILE 字段，其余表用 `--set` 固定：
  `--task reconcile-sides --set right-file=<右表> --batch 〈流水目录〉`
- JSON 另有两个特性字段：`evidence_pack`（本次运行的审计证据包 zip 路径）
  与批量结果里的 `batch_summary`（``dist_template/output` 下的 `batch`\_summary-<日期>.md`）。
  本地个人版全部特性恒开放，两者恒产出：zip 内 `manifest.json` 记有输入
  SHA-256 指纹、产物哈希与溯源结论，收包人可脱离本引擎独立复算

## 结果核验铁律

- 答复用户"已生成"之前，必须确认 JSON 的 `artifacts` 中文件真实存在
  （或 ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED）——不得凭记忆宣称成功
- 对结果有疑问时以 ``dist_template/storage` 里的 `last_result.json`` 为准（含输入文件指纹，
  可证明产物确实来自用户的那份输入）

## 异常与降级

| 情况 | 处理 |
|---|---|
| 退出码 1 且 issues 提示输入问题（文件为空/缺字段/格式不对） | 把错误原样转告用户，请用户修正后重跑；不要自行猜测修改输入 |
| score-prompt 返回 REVIEW（未达标） | 把报告 `gaps` 缺口清单如实转告用户，逐条修复后重送；同文本第二次仍不达标，引擎会强制转人工（复检闸门） |
| verdict=ESCALATED（轮次耗尽/闸门转人工） | **停止自动重试**，把认证报告与缺口如实交给用户人工裁决。用户确认问题是「目标写错」而非「写得不好」时：用 `--task prompt-version --set candidate=<ID> --set exclude=〈目标错误的版本〉` 把错误版本踢出回滚集，再用 `--set route=A` 从 0 重做（重做上限 2 轮，D-015/D-016）；问题只是措辞/结构则继续 route=B 修复（新候选文本自然重置轮次判断） |
| 引擎无法运行（Python 缺失/依赖未装/场景名不存在，退出码 2） | 降级为手工整理：按上方"使用方法"的规则逐条整理用户的原始材料，并在结果开头标注「⚠ 降级模式：未经确定性引擎校验，责任人与时间等信息请人工逐条确认」 |
| 连手工整理也不可行（输入不可得） | 如实告知用户失败原因，保留原始输入，不做任何部分产出 |

任何时候都不得：未运行引擎却宣称已运行、编造产物路径、责任归属与旧事项的完成状态一律由用户确认，本技能不代填默认值。

## 宿主结果回贴模板（成功时如何负责任地宣称成功）

向用户汇报时按此结构转述（内容取自 --json / last_result.json，不凭记忆）：

```
已完成：〈任务名〉，产物在 〈artifacts 中的文件路径〉（可在资源管理器中打开）。
本次核验：输入指纹已记录（SHA-256）；溯源自检〈通过 / 有 N 条待人工核对〉；
判定依据见 `dist_template/storage` 里的 `last_result.html`。
〈若有 REVIEW issues〉：以下 N 项需要你确认：逐条列出。
```

降级（异常时的处理见上节）必须显式标注「⚠ 降级模式」，成功也只按上面
的凭证说话——不夸大、不省略 REVIEW 项。
