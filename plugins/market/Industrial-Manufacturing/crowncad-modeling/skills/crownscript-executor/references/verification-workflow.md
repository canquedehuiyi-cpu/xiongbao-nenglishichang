# 边建模边验证：公共工具使用说明

路径约定：`<skill_dir>` 为本技能 `SKILL.md` 所在目录的实际绝对路径，由代理在执行前替换，不是 Python 或 Shell 自动替换的变量。相对输入、输出及 `generated/` 路径以当前任务工作区为基准，不切换到技能安装目录运行或写入任务资料。


程序负责提取错误、读取实际几何、测量、比较和整理报告；AI 负责理解图纸、确认对象、查看模型、读取结果并决定行动。操作顺序和浏览器访问见[执行流程](execution-workflow.md)，本文件说明如何检查。

## 1. 整理要求和检查时机

建模前在本案例已有操作计划列清每个零件的全部必需要求、首次检查时机、必需特征和后续依赖。尺寸、容差和普通阶段名来自任务，不套固定零件清单。不会测的必需项仍保留，关键参数不明按项目规则澄清。

关键阶段按完整设计部分选择：基体完成查相关外形和厚度，重要孔槽完成查相关尺寸、位置、数量和贯穿，圆角完成查目标及附近结构。关键阶段按要求核查实际数据；仅当判断需要视觉证据时安排 `kind="visual"`、`purpose="stage_model_visual"` 项并实际观察。不为每个阶段固定截图，也不能把必需几何检查全部留到最后。

清单字段：`id`、`title`、`kind`、`stage`、`expected`、`required`；数值项另有 `unit`、`tolerance`、`tolerance_basis`。kind 使用 number 或 visual；stage 表示首次检查阶段，最终使用 final 复查全部要求。位置误差、夹角和数量也可列为数值项。比较容差需说明依据，不能用查询精度冒充制造公差。

执行前复用草图平面、槽及轮廓规则，检查有限坐标、非零方向、槽宽、连接和交叠；端点重合不足以证明复杂轮廓有效。CrownScript 仍遵守 var、真实 ID、唯一特征名、分号及无尾随逗号等项目规则，不增加通用解析器。

## 2. 核对执行返回、取得当前实际数据

查询返回的 artifacts 按[跨机器文件交付](execution-workflow.md#51-跨机器文件交付与证据使用)下载并校验；下述拓扑文件、原响应和脚本均指下载解压到调用端的证据。工具不接收 task_dir 或 request_log_path，不把服务端文件路径作为本地证据。直接返回的数据可先用于判断，但未取得对应证据时须如实记录限制。

AI 阅读本轮 `execute_program` 原始响应，检查顶层及各命令结果中的 `errorInfo`、错误行号和消息。拓扑工具内部使用 `execution_errors()` 拒绝明确失败的元素查询；空错误列表仅表示未提取到明确报错，不代表返回完整。实体、配合和插入分别按已确认接口核对有效结果，不能对所有命令机械套 entityId 非零。恢复模型后同样检查返回和受影响结构。小响应直接阅读，大响应保留完整文件并按需读取，不省略已发现的错误。

按四层查询规则调用 MCP 工具：`collect_topology(level="ids")` 获取当前 ID，再用 `query_topology_geometry` 按需查询面、边/独立曲线或顶点详情；关系由 `include_edges` 和 `include_vertices` 控制。需要完整兼容图时，使用 `collect_topology(level="full")`。局部 geometry 查询不能当作完整拓扑。工具使用只读 REST GET，并在同一上下文以 `overwrite=false` 追加纯查询脚本；它会保存原始响应、查询脚本与响应、拓扑结果、行号清单和脱敏 GET 日志。具体参数见[分层查询](entity-modeling/details/topology-layer-design.md)和[拓扑说明](entity-modeling/details/topology-and-features.md)。

拓扑回答有哪些实体、面、边及关联；几何详情提供圆心、半径、轴线、法向等；浏览器帮助理解实际结构。它们共同支持对象确认，画面不能证明精确尺寸。公共入口在 prepare 时就将旧的当前模型证据和报告标为过期，失败或未知写入也不沿用旧通过结论；实际修改后下一次需要时重新取得拓扑；受影响旧检查也要复查，不只检查新增项。

下载校验后的拓扑及几何业务文件优先用 [extract_topology.py](../scripts/extract_topology.py) 提取，按[提取说明](entity-modeling/details/topology-layer-design.md#本地业务数据提取)检查缺失、异常和覆盖状态。筛选完成不证明验收通过，也不能从未返回的数据推断目标不存在。

同一模型状态的有效测量和已查看画面可复用，不为进入新阶段或最终报告重复获取。通过公共 save_evidence 保存证据，由程序关联文档、版本、取证前 operation_id、对象、scope、用途及正式文件哈希；README 只导航。保存参数及适用范围见[执行流程 1.1](execution-workflow.md#11-累计源脚本阶段与修订)。同文档同版本不保证几何未变；成功几何执行后旧拓扑引用失效，受影响尺寸及视觉结论重新取得，无法判断是否受影响时补查。最终仍逐项复查所有必需要求，仅引用仍有效且覆盖该项的证据，不能将历史 passed 改名为 final。

### 分层实测中的字段可靠性

不要把原始JSON所有字段严格相等当作几何等价证明。若怀疑字段异常，保持模型不变并重复只读查询，保留原始响应后再分类。2026-10-15支架复刻实测：Curve.SCL在同一边上可返回bool或dict；部分Unknown面的StartAngle/EndAngle在同一状态下变化。这些字段不作为尺寸、闭合或复刻一致性依据，不从Unknown面参数形态推断类型。不得因此忽略真实几何差异：本次历史面积和部分包围盒差异仍单独记录为未解决，未改尺寸强行匹配。

Geom.L不保证满足解析曲线长度公式的高精度容差：本次开口弧报告L与πR相差约0.00103mm。需要解析圆弧时结合已确认R/CP/角度和实际径向点核验，报告长度读回差异，不擅自提高测量精度或统一放宽尺寸容差。原始数据始终保留。该长度偏差仅为单个样本的观测结果，不能推广为通用误差范围。

## 3. 确认对象、测量并比较

AI 根据位置、方向、所在实体、孔口及相关边界确认目标，必要时换浏览器视角或补查询。圆柱面可能属于孔、凸台或槽端，唯一候选也不自动等于目标孔；不能用期望孔径排除做错的孔，也不自动选择排序第一项。

`find_cylinder_candidates()` 用实际轴线位置、方向和实体整理候选，不接收期望孔径。搜索范围来自任务，范围太小可能漏掉位置错误的目标；`collect_cylinders()` 的 unreadable_faces 表示部分数据未读出，不能据此断言缺孔。分不清时列候选并保留未验证；同一个孔不能重复用于多个目标凑数量。只有证据足够证明缺失才能报告缺孔。

| 要检查什么 | 已有工具 | 调用前确认及边界 |
|---|---|---|
| 当前拓扑与详情 | `collect_topology` / `query_topology_geometry` MCP 工具 | 固定上下文、当前模型、所需数据完整，传入当前任务目录 |
| 草图平面局部坐标系 | `resolve_sketch_plane` MCP 工具 | 使用当前有效 Plane ID；按 CrownCAD 返回值读取局部坐标轴，不自行推导 |
| 圆柱候选 | collect_cylinders()、find_cylinder_candidates() | 实体、轴线、边界和结构身份，候选不等于孔 |
| 圆柱直径 | measure_cylinder() | 指定目标孔壁或轴面，半径和单位有效 |
| 轴线位置、夹角 | axis_distance()、axis_angle() | 点到轴线距离不等于孔口中心距离；默认夹角不区分正反，要求方向时 directed=True |
| 厚度或间距 | measure_plane_gap() | 指定两张平行面对应目标尺寸 |
| 简单直槽 | measure_simple_slot() | 已确认四条槽口边，仅支持两半圆加两直线 |
| 圆弧半径 | measure_arc_radius() | 指定实际圆弧，不自动证明整个圆角正确 |
| 实体数量 | measure_entity_count() | 本轮实体集合采集完整，面数不等于孔数 |
| 比较和记录 | compare_number()、check_result()、record_visual() | 当前要求、实测、目标依据及实际观察 |
| 汇总和输出 | build_report()、write_report() | 新增及受影响旧项的本轮结果，AI 随后读取报告 |

测量返回 status=measured/unverified、values、objects、evidence、reason。measured 仅表示取得数值，不表示符合要求；数据不足或结构不支持时说明原因，不猜值。几何一致性 epsilon 与验收容差分开。孔深、贯穿、孔数量、复杂槽和圆角整体不能从半径或面数随意推断，应补实际几何或已确认界面证据，仍查不清则未验证。

数值通过 compare_number() 比较，不预填通过；target_basis 必须来自实际确认，写一段文字不自动证明选对对象。单位先核对及转换，数值必须有限，容差非负且有依据。

## 4. 浏览器观察与阶段结果记录

关键阶段带着本阶段图纸目标查看最新实际模型。根据问题选择整体、局部或已确认可用的剖面，核对方向、位置、连接、漏做或明显穿透；发现异常先排除旧画面和视角误判，再结合实际数据确定原因。精确尺寸靠测量，看见单侧孔口不证明贯穿，没有看见穿透不证明无干涉。

观察时可以旋转视角、缩放、平移或切换观察方向，这些不改变模型的动作不属于建模修改。同一文档正常自动更新后，直接查看并按需重新截图，不例行刷新网页；通过界面执行建模或其他文档修改的授权边界，统一遵循 [执行流程第 2 节](execution-workflow.md#2-浏览器直接访问与持续参考)。

仅在必要时取得并查看 CAD 截图；需要记录视觉取证时，再用 record_visual() 记录：核对什么、实际看到什么、怎样判断及下一步。关键阶段 source="cad_browser"、purpose="stage_model_visual"，不能只写“外观正常”或返回图片路径。拓扑预览不是浏览器前置步骤，也不能代替实际模型检查。

### 4.1 视口截图与跨环境证据保存

仅在必要时调用截图，取图前明确待判断问题。先检查现有证据是否已能回答该问题：尺寸、数量和位置优先用当前实际几何；外形、遮挡、连接局部及最终视觉才按需取图。判断问题沿用操作图或 README 的检查项，不另建截图清单，不固定逐阶段、逐命令或逐相机截图，也不为等待画面更新反复截图。为取证得到的有效截图应查看并保留；纯重复状态不再次下载。以下规定适用于确有取图需要的情形，不构成阶段固定截图要求。优先使用 CrownCAD MCP；Computer Use 限制沿用执行流程，不为截图自动启用。

`capture_viewport` 截取目标文档版本的当前模型视口，由实际前端回传图片，不是浏览器整个页面截图或拓扑渲染图。调用前核对文档、版本、最新执行阶段和页面加载状态，确保前端窗口活跃、相机动画结束且本轮模型渲染稳定。`sentCount>0` 或关闭动画都不能替代这些检查。

1. 调用 MCP 工具 `capture_viewport`，取得目标文档的实际视口图片。
2. 多窗口时，仅在能确认 websocket 会话与目标页面对应关系后，才以 `session_ids=[已确认的单一会话ID]` 定向。相机工具返回多个 `sessionIds` 时不能随意取第一项；省略截图 `session_ids` 会取最先回包页面。返回的 `requestedSessionIds` 仅是请求目标，不证明实际回包来源。无法确认来源时保留相应限制，必要时使用当前已确认浏览器页面的直接截图，不把不明窗口画面用于视觉通过判定。
3. 工具返回 `downloadUrl`、`expiresAt`、图片格式、实际宽高和字节数。通过当前下载能力在有效期内取得内存字节，经 save_evidence 的 view 角色直接按用途写入 `evidence/views/`，不生成中转图片或来源 JSON；必要过程图使用 required_process scope，与当前模型验收图区分。下载链接最长有效10分钟，也可能因服务重启或缓存淘汰提前失效；不要把完整敏感链接或 OAuth 凭据写入 README、报告、公开日志或证据元数据。
4. 下载后核对图片可解码、格式/尺寸及字节数与工具返回一致。前端可能降质或缩图，依据实际尺寸判断是否足以检查局部。实际打开并查看图片，确认它对应当前对象和状态，再填写观察与结论；返回下载地址、保存成功或得到有效图片均不表示内容验收通过。
5. 运行资料记录图片本地路径、文档与版本、对应阶段、采集时间、观察部位、实际图片信息，以及已确认的窗口关联或仍存在的限制。关键阶段仍使用 `source="cad_browser"`、`purpose="stage_model_visual"`；最终复查使用 `purpose="final_model_visual"`。来源由实际 CAD 页面及上下文证据支持，不单凭截图接口返回文档 ID 判定。
6. 链接失效或截图失败时先确认当前模型和页面状态，再决定重新取图或使用已确认页面的直接截图，不盲目重试 POST。模型已变化时新图片属于新状态，不能回填为旧阶段当时已通过的证据。仍无法获得或查看画面时，相关视觉检查保留未验证。

建模过程的选择视角和调用时机统一见[执行流程第 2.1 节](execution-workflow.md#21-建模过程中的视角展示)。仅在必要时截图取证，已有有效证据足够时复用，不为每个关键阶段、图元、命令或视角调整固定截图；图片不能代替精确测量、贯穿关系或装配干涉检查。工具的代码封装、自动化测试和本任务真实前端联调分别判断，未实际观察到的效果不得标记为已验证。

### 4.2 阶段结果记录示例

下面是通过公共入口保存阶段检查的片段。保持当前任务工作区为工作目录；执行前，将执行器技能 `SKILL.md` 所在目录的实际绝对路径加入 Python 模块搜索路径，再导入 `scripts` 下的检查模块。输入、输出及证据路径仍以任务工作区为基准，不切换到技能安装目录。变量由当前任务准备，代码不自动打开浏览器或认定目标，也不要求为每个零件开发专用检查程序。

task_root 为本任务路径；query_context 的 operation_id/input_fingerprint 在实际取证前固定，evidence_hashes 为入库后所用证据相对路径到 SHA-256 的映射。不得在报告保存时重新取得新上下文给旧证据补身份。

```python
import sys

# 执行前将 <skill_dir> 替换为执行器技能的实际绝对路径。
sys.path.insert(0, "<skill_dir>")

from scripts.geometry_measurements import measure_cylinder
from scripts.verification import (
    check_result, compare_number, record_visual, build_report,
)
from scripts.run_files import save_report

# confirmed_candidate：AI 结合本轮画面、拓扑和几何详情确认的对象。
# diameter_requirement：当前任务的孔径要求，包含单位和容差依据。
if confirmed_candidate is None:
    diameter_check = check_result(
        diameter_requirement, stage=current_stage, status="unverified",
        reason=identification_problem, evidence=[topology_path],
    )
else:
    measured = measure_cylinder(confirmed_candidate)
    if measured["status"] != "measured":
        diameter_check = check_result(
            diameter_requirement, stage=current_stage, status="unverified",
            reason=measured["reason"], evidence=[topology_path, f"孔壁面：{confirmed_candidate['face_id']}"],
        )
    else:
        diameter_check = compare_number(
            diameter_requirement, measured["values"]["diameter_mm"],
            stage=current_stage, target_basis=target_basis,
            evidence=[topology_path, f"孔壁面：{confirmed_candidate['face_id']}"],
        )

# 先实际调用浏览器查看最新 CAD，再填写观察、状态和实际截图引用。
# 阶段视觉要求使用 purpose="stage_model_visual"。
visual_check = record_visual(
    stage_visual_requirement, stage=current_stage, status=observed_status,
    observation=actual_observation, evidence=[actual_cad_screenshot],
    source="cad_browser",
)

# other_current_checks 包含孔位、数量等相关要求，以及受影响旧项的本轮结果。
report = build_report(
    requirements, [diameter_check, visual_check, *other_current_checks],
    stage=current_stage, additional_ids=affected_ids,
)
report_source = {
    "operation_id": query_context["operation_id"],
    "input_fingerprint": query_context["input_fingerprint"],
    "evidence": evidence_hashes,
}
save_report(task_root, report=report, source_fingerprint=report_source)
# AI 读取报告中的失败、差异和缺项，再决定行动。
# 公共模块阻止未收尾/资料配错，不自动判断建模语义依赖，也不自动继续 CAD 操作。
```

build_report() 检查本阶段要求及 additional_ids 指定的受影响旧项，这些结果的 stage 都是本轮阶段。AI 选择受影响项，不自动推断依赖。汇总核对 kind、expected、unit、tolerance、tolerance_basis 和 purpose；不一致旧结果保留在 rejected_findings，并记未验证，缺结果也未验证。

所有阶段的数值 passed 记录都会复核：要求值、实际值和容差必须有效，差值不能超容差。矛盾的通过补失败，无效数值补未验证，原始结果保留；已记录 failed 不重新算成 passed。复算仅检查自洽，不证明测量身份或证据真实。

程序检查已安排的 stage_model_visual 项的浏览器来源、非空观察和非空截图引用；不能自动发现清单未安排的阶段视觉检查，也不验证文件存在、真实性、最新状态或 AI 是否看过。AI 负责实际保存、查看和核对证据。record_visual() 的不完整通过降为未验证，已报告失败保留；可选项不阻止必需项通过。

save_report() 固定输出 reports/verification.json 和 verification.md，两份写好后才更新检查状态；调用方不自行写报告或修改状态文件。报告只描述本轮范围。AI 必须读取差异、缺项和必要返回后决定：通过继续；失败确认原因后修正、重查，不继续依赖失败项；未验证补证据或说明阻塞，独立工作可继续。修正规则见执行流程，问题未闭环前保留必要现场；可靠交接后只清受管替代物，不事后补写历史通过。

## 5. 单个零件最终验收

无论是否装配，每个零件完成后均执行：

1. 读取全部必需要求，核对最后构造执行和各命令必需返回。
2. 用当前有效证据确认对象、逐项测量并按当前要求比较。不能只查整体范围、数量或最后特征，不删不会测的要求。
3. 查看最终整体和必要局部，记录具体观察；仅在必要时取得实际 CAD 截图，同一最终状态已有足够有效图片时直接复用，不为报告重复截图；清单必须有 required=True、kind="visual"、purpose="final_model_visual" 项，source="cad_browser"。阶段观察不能代替最终复查。
4. 用已确认查询或最新特征树核对操作图中的必需特征仍存在。名称不证明参数、抑制状态或完整可编辑性，要求这些能力时另取证。
5. 生成 final 要求报告，综合执行、必要返回和路线给出整体结论。

```python
# final_checks 是当前有效证据按当前要求复查的结果。
# 必须包含 required=True、purpose="final_model_visual" 的实际浏览器视觉项。
final_report = build_report(requirements, final_checks, stage="final")
save_report(task_root, report=final_report, source_fingerprint=final_report_source)
# 报告 scope=requirements_check；AI 另核对最终执行、必要返回和特征路线。
# final_report_source 同样使用最终取证前上下文和实际文件哈希。
# 整体范围、限制及人工决定写 README，不默认新增 acceptance.md。
```

最终模型状态下取得、之后未修改的有效数据可以重新按当前要求比较；受影响、失效或无法证明有效的证据重新取得。不能仅把旧 passed 的 stage 改成 final。记录对应累计脚本、执行响应和查询，文档版本相同不证明证据有效。

最终汇总缺少必需 final_model_visual 项或对应观察未通过时写 completion_issues；来源、观察、截图引用缺失不能通过，浏览器受阻仍输出报告，视觉未验证并说明原因。截图检查只核对非空引用，实际真实性及最新状态由 AI 核对。只有一个孔口观察不能替代整体检查。

| 整体情况 | 零件结论 |
|---|---|
| 任一必需项、执行或路线确认失败 | 验收不通过 |
| 无失败但必需检查或执行、路线证据缺失 | 验收未完成 |
| 执行和返回有效、路线符合要求、全部必需项通过 | 验收通过 |

报告 scope=requirements_check，只证明清单要求，不独自代表任务完成。同一次检查失败优先，不能被另一条通过或缺证据抹去；空清单或没有必需项不能通过。修正后只传本轮检查，固定报告在新结果可靠写好后替换；未解决失败和必要过程依据保留，不把旧失败改成通过。JSON 拒绝 NaN/Infinity，不把非有限输入写成正常实测数据。

装配资料比较与报告使用独立的 `scripts/assembly_verification.py`，输入、阶段/最终检查和调用示例见[装配记录与独立检查](assembly-modeling/assembly-records.md)。不向零件 verification.py 增加装配 kind。

装配分别保留零件结论，再按[装配验收](assembly-modeling/assembly-modeling.md#6-装配验收流程)核对真实装配；源几何和计划坐标不能替代实际状态。

## 6. 通用拓扑辅助预览

```powershell
python "<skill_dir>/scripts/render_topology.py" --topology 'generated/runs/<本轮目录>/final.topology.json' --output 'generated/runs/<本轮目录>/preview.png' --views overall front top right --mode wireframe --title '本轮零件'
```

保持当前任务工作区为工作目录运行。默认整体及前、上、右四视角，世界 +Y 朝上，上视来自 +Y、正视来自 -Z、右视来自 +X。--chord-error 默认 0.05 mm，须正数，是圆弧绘图精度，不是验收公差。

- wireframe 画全部支持边，包含遮挡边，不是消隐工程图。
- planar 仅可靠 Plane 闭环填色，嵌套奇偶保留孔口，深度排序是近似展示，非平面不填色。
- 直线核对端点、中点和长度；圆弧依据实际圆心、半径及三维点采样。未知曲线、断环、歧义、自交等明确跳过，不偷偷画成直线或平面。

输出 PNG 和同名 .render.json，记录来源、模式、视图、精度、绘制及跳过项和原因。退出码 0 绘图完成、2 部分预览、1 输入/依赖错误或无可画几何，均不代表模型验收状态。Pillow 延迟加载，只影响绘图工具；需要预览时，Agent 在运行脚本的同一 Python 环境检查 Pillow，缺少时使用本 Skill 实际目录中的依赖文件安装并重试一次：`python -m pip install -r "<skill_dir>/requirements.txt"`。若安装失败或环境不可写，再请用户处理。工具只读已保存拓扑，不访问网络、凭据或修改 CAD。

AI 实际查看生成图并阅读限制后才解释内容。该图不是 CAD 截图，不替代浏览器、尺寸或干涉检查；有展示需要才调用，不强制每个零件生成。
