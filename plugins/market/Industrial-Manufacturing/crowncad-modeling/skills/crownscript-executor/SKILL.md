---
name: crownscript-executor
description: "CrownCAD 基础操作与 CrownScript 执行技能。用于编写、执行或调整脚本，完成草图与约束、基准、实体与曲面特征、装配操作及实际几何查询；适用于 executeProgram、拉伸、旋转、圆角、倒角、镜像、阵列和配合等明确操作，也可执行已确定的建模步骤。"
---

# CrownScript Executor

本技能是独立的CrownCAD基础操作与执行技能，提供已确认命令、参数组织、引用管理、拓扑查询、累计脚本执行及错误检查。可由用户单独使用，也可接收已经确定的构造目标或操作图；不依赖、不引用或反向调用上层建模流程和专项技能。

将明确目标转换为可验证的CrownScript操作图，依据设计意图选择草图和原生特征。命令能力与基本结果检查在本技能内说明，不猜测接口、实体ID或草图能力，不替调用方重排其已确定的总体建模路线。

## 参考文档路由

| 任务内容 | 必读文档 |
| --- | --- |
| 每项建模任务：案例参考、过程记录和确认保存 | [案例参考与保存](../modeling-case-library/references/case-workflow.md) |
| 基准点、基准线、基准面 | [references/datum-constraints.md](references/datum-constraints.md) |
| 实体建模：原生实体特征、镜像、阵列、拓扑及受限的基础实体/布尔备选路线 | [references/entity-modeling/entity-modeling.md](references/entity-modeling/entity-modeling.md) |
| 草图建模：草图几何、尺寸目标、已确认的几何关系、草图会话和轮廓 | [references/sketch-modeling/sketch-modeling.md](references/sketch-modeling/sketch-modeling.md) |
| 曲线建模：桥接曲线 | [references/curve-modeling/curve-modeling.md](references/curve-modeling/curve-modeling.md) |
| 曲面建模：拉伸、旋转、扫描、放样、填充、缝合、删除 | [references/surface-modeling/surface-modeling.md](references/surface-modeling/surface-modeling.md) |
| 装配建模与验收：实例、固定、移动、旋转、配合、齿轮和槽口 | [references/assembly-modeling/assembly-modeling.md](references/assembly-modeling/assembly-modeling.md)（含第 6 节验收流程） |
| 查询装配实例、配合、transform 或位姿矩阵 | [装配查询第 4.2 节](references/assembly-modeling/assembly-modeling.md#42-查询装配结构getassemblystruct)，含实例配合与全部实例矩阵两个入口 |
| 装配计划与实际对象关联、独立装配检查及报告 | [references/assembly-modeling/assembly-records.md](references/assembly-modeling/assembly-records.md) |
| Common 变量管理、变量表达式和变量依赖 | [references/common-modeling.md](references/common-modeling.md) |
| 新建文档、累计执行、运行资料保存及重试 | [references/execution-workflow.md](references/execution-workflow.md) |
| 按需过程展示与相机方向选择 | [references/execution-workflow.md 第 2.1 节](references/execution-workflow.md#21-建模过程中的视角展示) |

| 要求检查、实际测量、报告及拓扑辅助预览 | [references/verification-workflow.md](references/verification-workflow.md) |

每项新建模任务在确定方法和操作图前，先按 [案例参考与保存](../modeling-case-library/references/case-workflow.md#2-开始任务先看案例再决定方法) 查找并阅读相关案例。运行过程维护任务 README；完成且获得明确授权后，按该文档的归档流程保存。案例不能替代当前参数确认或接口验证。

复合任务读取所有相关文档。实体任务按命令清单继续读取对应 `details/` 文档；草图任务按草图入口读取所需详情。需要创建草图时同时读取草图入口。

下载拓扑业务 JSON 后，优先调用 [scripts/extract_topology.py](scripts/extract_topology.py) 提取所需记录，不重复临时编写通用筛选代码。支持概况、类别、所属对象、元素 ID 和顶层字段选择；调用示例、异常及格式边界见[本地业务数据提取](references/entity-modeling/details/topology-layer-design.md#本地业务数据提取)。复杂测量仍使用对应测量工具。

## 专项约束入口

涉及下列操作时，读取对应约束并执行；详细规则在参考文档中维护。

- 实际建模或装配前：必读 [执行工作流](references/execution-workflow.md)和[验证流程](references/verification-workflow.md)，再按所用命令读取对应接口说明。运行资料使用仓库提供的 `scripts/run_files.py`；适用范围、调用顺序和参数集中见执行工作流，不自行实现文件管理。
- 拓扑优先调用 `collect_topology(level="ids", output_format="compact")` 生成轻量 ID、类型及关系清单文件，不含几何详情。实际测量再用 `query_topology_geometry` 按 ID 查询；需要全量几何时显式使用 `level="full", output_format="full"`。两个参数分别控制查询深度与返回形态；MCP 仅返回概况和 artifacts 下载信息；先下载业务 JSON、校验大小与 SHA-256，再用本地程序按 ID/字段提取，不整份输出到上下文。业务文件使用格式化 JSON。独立曲线 entityId 本身就是元素 ID。字段、分批重试和证据规则见[分层查询](references/entity-modeling/details/topology-layer-design.md)。
- 需要当前模型的 STEP 时，调用 MCP 工具 `export_step_sync`，取得并校验实际文件后再分析。
- 拓扑驱动操作：圆角、倒角、实体边扫描路径、实体平面镜像或选边，按 [拓扑规则](references/entity-modeling/details/topology-and-features.md) 获取当前引用。
- 草图平面：读取 [面类型与空间语义](references/entity-modeling/details/topology-and-features.md#面类型与空间语义)，先解析当前有效平面的局部坐标系，再生成草图命令。
- 过程展示：解析真实工作平面坐标。保持当前合适视角，仅必要时通过 `transform_camera` 调整。文档页面只通过当前任务允许的入口访问；UI 自动化须有覆盖具体动作的明确授权，浏览器 API 形式不构成授权，接口或截图失败不能自动授权切换入口。
- 取证仅在必要时进行，不按阶段固定截图；已有有效证据足够时复用。需要截图时按[视口截图规则](references/verification-workflow.md#41-视口截图与跨环境证据保存)调用 `capture_viewport`，及时下载并查看实际图片，再记录观察和调用端证据路径；下载链接和工具成功不替代视觉检查。
- 抽壳任务必须读取 `references/entity-modeling/details/feature-modeling.md` 的“抽壳前校验与失败分析”，按该节执行。
- 线性阵列和圆周阵列按对应参考文档使用；阵列的实体/特征对象、方向或轴、实例数、间距/角度、跳过实例和 `geometryPattern` 参数必须使用真实且已验证的结构，未经过运行时验证的参数必须标记为未验证。
- 实体建模统一读取 `references/entity-modeling/entity-modeling.md`；特征的草图、截面、路径和旋转轴必须使用真实引用 ID，实体合并和切除必须使用真实的实体 `entityId`。
- 装配交付须执行 [装配参考文档](references/assembly-modeling/assembly-modeling.md) 第 6 节验收流程；命令返回成功不等于验收通过，计划数据不能替代实际结果，必需检查缺少证据时不得宣称装配完成。
- 查实例和配合用 `collect_assembly_state`；查全部实例矩阵用 `collect_assembly_transforms`。两者仅传 document_id、version_id。按实例 ID 关联结果，具体位置检查用法见[装配接口参考第 4.2.2 节](references/assembly-modeling/assembly-modeling.md#422-全部实例矩阵collect_assembly_transforms)。
- 装配静态干涉调用 `check_interference(document_id, version_id, group_ids, distance=0)`。先用 collect_assembly_state 确认当前实例 ID，调用时明确填 distance=0。参数、结果和判定见[装配接口参考第 4.10 节](references/assembly-modeling/assembly-modeling.md#410-静态干涉检查check_interference)。工具直接返回，不保存文件。
- 基体、凸台和切除按 `feature-modeling.md` 的 `mergeType`、`mergeSolids`、`cutSolids` 规则处理；合并或切除后，后续实体操作只使用新返回的 `entityId`。
- `Solid.extrude` 和 `Solid.extrudeCut` 的 `angle1`、`angle2` 不能单独使用。方向1必须根据 `draftType1` 判断是否拔模：`-1` 为不拔模，`0` 为向外拔模，`1` 为向内拔模；启用拔模时对应角度必须为正值。方向2使用 `draftType2` 与 `angle2`，规则相同。
- `Solid.createRib` 使用 `draftType` 和 `angle`；`Solid.extrude` 使用 `draftType1`/`draftType2` 和 `angle1`/`angle2`，两者字段名称不能混用。
- 草图闭合轮廓须按 `references/sketch-modeling/sketch-modeling.md` 及其指向的轮廓验证详情检查连接与交叠；端点重合、接口执行成功均不能单独证明轮廓有效。报告时区分本地几何检查与 CAD 实际结果验证。
- 草图转换边界使用 `Sketch.convertEdge`，命令签名和源 ID 获取规则统一见草图入口第 5.15 节；区分实体边线 id、源草图 entityId 和源草图线 id。后续引用整个目标草图时保留目标 sketchId，不强制获取转换后各图元 ID，不假定命令返回结构。
- 桥接曲线按独立 `Curve` 模块执行，先构造两个桥接点和两组约束，再创建曲线，不建立草图容器或进入 `Sketch` 会话。源引用使用实际曲线或已确认可引用的实体边 ID；通过源引用与方向设置控制切向，不臆造切向向量参数。后续使用实际取得的曲线 ID；返回 `entityId:0` 时不能按实体创建规则直接判失败，应检查错误并通过当前 `/curves` 确认实际结果，不把特征 `id` 当作曲线 ID。
- 曲面建模按曲面模块的接口说明执行。返回的 `entityId` 是曲面对象 ID，`id` 是特征 ID；曲面有对象 ID，也不代表它是有体积的实体。

## 通用强制规则

基础命令介绍按需读取：[圆角调用示例](references/entity-modeling/details/solid-modeling.md#圆角调用示例)、[抽壳调用示例](references/entity-modeling/details/feature-modeling.md#抽壳调用示例)、[填充曲面](references/surface-modeling/surface-modeling.md#7-填充曲面surfacefillsurface)。本技能说明命令含义、参数、调用格式、引用与返回值处理；局部建模策略由本次目标或调用方确定，不在命令说明中另设专项流程。

- 先完成“自然语言目标 → 理解需求和约束 → 查看相关案例 → 确定方法及语义与空间关系 → 基础几何/草图节点 → 特征与布尔节点 → 分阶段操作图”的转换，再生成脚本。历史 CAD ID 不作为本任务有效引用。
- 运行资料写入 `generated/runs/<模型语义>__<8位任务UUID>/`，通过公共入口保存，不手改执行或检查状态，不默认生成 STEP/output。正式案例仅在任务完成且用户明确授权后保存到 models。README 维护、归档工具、索引更新及异常反馈统一遵循 [案例参考与保存](../modeling-case-library/references/case-workflow.md)。
- 根据设计意图和后续修改需求选择原生特征或基础实体；基础实体和独立布尔的参数见实体接口参考。调用方的路线限制持续有效，本技能不授予使用某条路线的额外权限。
- 实体建模命令必须按照对应参考文档使用；未经过运行时验证的参数必须标记为未验证，不得宣称为已验证能力。
- 供后续操作复用的特征尽量只产生一个实体；多实体结果必须按当前实际返回或拓扑精确定位，不能靠特征名猜测。
- 所有变量只用 `var`；实体 ID 只用返回对象的 `['entityId']`；特征名必须唯一、可读、非空。
- 所有尺寸与坐标单位为 mm。`positionType` 固定为 `2`，位置点为质心；立方体默认 `length→Y`、`width→X`、`height→Z`。
- 世界坐标的默认“上方”固定为 +Y `(0, 1, 0)`，不是 +Z；“顶面、上表面、向上、向下”等语义必须据此解释。该约定适用于实体、Topo 语义匹配和草图选面；用户明确指定其他方向时，以用户指定为准。
- 传给 `executeProgram` 的 CrownScript 只能使用已确认的 CrownCAD 命令、数据结构与语法，不得试探未确认能力；坐标计算和重复参数生成在 CAD 执行前用适当本地工具完成，脚本中只保留已知接口调用、数值字面量或已验证的 `Variable` 引用。
- `new Variable(...)` 只能用于对应接口参数表的支持类型中包含 `Variable` 的参数；`Point`、`Direction`、`Axis`、实体/草图/特征 ID 以及未标注支持 `Variable` 的参数不能因为看起来是数值就变量化。
- 实体镜像的 `body` 使用真实实体 `entityId`；特征镜像的 `features` 使用真实特征 `id`；`mirrorPlane` 必须使用真实基准面 ID 或实体平面 ID。
- 装配元素必须使用 `(instanceId, elementId)` 完整引用；`Assembly.moveInstance` 和 `Assembly.rotateInstance` 的 `instanceId` 必须直接写字符串数组字面量。
- 普通配合、齿轮配合和槽口配合的返回值必须检查 `id` 和 `name`；返回不符合要求时，依赖该配合的操作暂停；不依赖它的工作可以继续，修正后重新回查。
- 使用已有线作为旋转轴时传入线的 `lineId`，即 `new Axis(lineId)`，不能把线的 `entityId` 当作旋转轴 ID。
- `sweepPath` 使用数组传递路径 ID；实体边路径必须来自当前拓扑，草图路径或 3D 曲线不需要额外获取实体拓扑。
- 后续操作只使用前一接口实际返回的实体 ID；需要特征镜像时使用前序结果的特征 `id`。圆角或倒角后，输入实体 ID 失效。
- CrownScript 使用保守语法：每一条可执行语句（变量声明、函数调用、赋值、`print` 等）都必须以英文半角分号 `;` 结束；函数、对象和数组末项都不能有尾随逗号。提交前逐行检查，特别是每个 `Sketch.exitSketch();`、`Sketch.exitEditSketch(...);` 与脚本最后一条语句。
- 关键尺寸、位置、实体/草图关系、圆柱方向或执行上下文缺失，且无法由默认约定补足时，先询问用户。
- 根据目标几何选择实体或曲面模块，不得混淆实体与曲面，也不得因一种建模模块的能力限制而忽略另一模块中适用的路线。具体建模方法、能力边界和验证状态以对应参考文档为准。


## 执行与验证

跨机器资料按[文件交付规则](references/execution-workflow.md#51-跨机器文件交付与证据使用)处理：查询和 STEP 工具不接收磁盘路径，返回业务 JSON 与 artifacts；下载并校验后使用调用端本地文件，不能直接引用服务端路径。

CrownCAD 操作默认使用插件已配置且当前已授权的 CrownCAD MCP 工具，身份来自宿主当前连接的 OAuth 授权；代理不查找或读取本地凭据文件，不传入凭据参数。未授权或授权失效时请用户通过宿主完成授权或重新授权，不自动改用本地直连。仅在用户明确要求本地直连时，按明确授权使用对应 Python 执行器；本地计算、几何分析、检查和案例管理仍可使用 Python。

取得目标文档后，使用当前会话浏览器页面接口直接打开并持续参考。关键阶段查看最新实际结构，按要求取得拓扑和几何数据，确认对象后测量、比较；检查结果决定继续、修正或补证据。每个零件完成后独立验收，装配另行验收。操作顺序见[执行流程](references/execution-workflow.md)，工具用法与验收方法见[验证流程](references/verification-workflow.md)。

交付可检查的模型结果时，按 [案例参考与保存](../modeling-case-library/references/case-workflow.md#4-完成任务核对最终版本并询问保存) 邀请用户补充人工经验，记录意见并落实实际调整；涉及模型修改时重新走建模检测流程，用户认可后按授权保存。

本技能不扩展调用方授权；调用方明确要求的工具、范围与交付限制持续有效。

## 执行结果与失败诊断

先检查响应中的 `errorInfo`、错误位置和消息，再按所用接口的已确认返回结构检查必需特征及实体引用。HTTP 成功或错误信息为空不能证明操作有效；需要结果实体的操作若返回 0、空值或缺少实体 ID，不得继续用它构建依赖。执行有效也不证明孔型、厚度、连接或过渡满足原始要求，按用户或调用方提供的几何条件检查并记录证据。

失败时区分语法/参数、引用/拓扑、几何和外部系统问题，记录证据与仍未确认的原因。可能写入的失败先确认现场，对可确定问题局部修正或评估重建，并同步完整累计脚本；每次尝试说明改变了什么及依据，遵守项目和执行工作流的停止条件与重试上限，不随机试尺寸，也不通过切换路线重置次数。瞬时只读GET连接中断先按[执行工作流](references/execution-workflow.md)有限重试并记录脱敏逐请求日志；连续失败后停止反馈。网络重试与几何修正分别计数；建模POST不能盲目重发，业务错误不能当成连接中断。

有具体几何限制或已确认能力边界时，可在允许的修正范围内调整路线，更新操作图并保持原始目标；单次失败不足以证明某条路线不可用。多个因素共同改变后成功，仅能证明该组合有效，不认定未经验证的唯一原因。

任一成功几何执行都会使缓存拓扑失效；后续需要按面、边操作时重新获取当前拓扑，不能仅在圆角或倒角后更新。实体引用使用当前操作的实际结果，查询和累计执行的具体步骤统一遵循 [执行工作流](references/execution-workflow.md)。

交付时区分命令执行结果、实际几何检查与原始目标满足情况。保存实际目标列表及必要依据，不能用固定数量或执行成功替代结果检查。结论与新证据不符时更新状态。查询仅使用已登记能力，不猜测命令或端点；不可取得的参数或几何证据记为未验证。

维护执行经验时，接口约束与停止条件写为规则，诊断判断写为条件性指导，具体响应和修正结果写为案例；保留已验证范围，不把未登记能力或案例参数提升为通用接口保证。
