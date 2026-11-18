# 装配记录与独立检查：计划是谁，实际是谁

本文约定已有任务资料中的必要字段，不增加自动编译器、绑定系统或阶段调度器。Agent 继续分析、选面、写累计脚本和决定下一步；工具查询实际对象、比较资料并输出报告。

## 1. 先分清计划与实际

| 放在哪里 | 写什么 | 不要混淆 |
| --- | --- | --- |
| `operation_graph.json` | 组件、接口、连接、配合、依据、阶段与检查要求 | 计划编号不是永久 CAD ID；不能按结果反改要求 |
| 已有阶段记录 | 当前实例/元素、创建返回、回查、选择依据和证据 | 重建后重新查询，不拿旧编号继续操作 |
| 独立装配报告 | 每项预期、实际、状态、原因与证据 | 创建有效不等于装配通过 |

图纸理解时一起记录零件和连接信息；来源零件完成后保留关键接口的实际证据。每份文档使用各自固定上下文，源零件局部坐标与装配世界坐标分清。世界上方按项目约定为 +Y。

## 2. 操作图补哪些信息

保留原来的 taskId、fixedContext、parameters、stages、nodes 等字段，在 assemblyPlan 下补：

| 字段 | 每项包含什么 | 白话含义 |
| --- | --- | --- |
| components | id、name、source、parentAssemblyId、fixed、initialPlacement、basis | 每个具体组件；同源重复件也分别编号 |
| interfaces | id、name、sourceComponentId、coordinateFrame、locator、basis | 使用哪个源模型的哪个部位，靠什么找到它 |
| connections | id、name、assemblyId、mechanicalMeaning、expectedMotion、basis、mates | 完整机械连接，不只是一条同轴 |
| openIssues | id、question、affectedRefs、status、answer、basis | 哪个依据没明确、阻塞什么 |

source 记录已知 projectId、documentId、versionId、docName、docType，适用时 configuration。记录要求版本不证明插入接口锁定了版本，实际来源仍需核对。

sourceComponentId 引用一条组件以说明接口描述属于哪个源模型；其他同源组件可以复用描述，但实际使用必须带自己的 componentId，且来源/配置经确认一致。parentAssemblyId 和 assemblyId 引用已有目标装配树，不再复制一份树。

每条 mate 包含 id、type、moveSide、referenceSide、alignment、parameterRef、dependsOn、reason、basis。双方各是 componentId+interfaceId；同轴选圆柱面，端面定位可用另一对接口。reason 说明该配合实现什么机械要求。type/方向及数值只使用[已确认接口](assembly-modeling.md#4-命令清单)；“轴向定位”须落实为适用命令，不能发明类型。

basis 沿用任务现有依据写法，至少定位图纸文件、页/视图/标注或用户说明。未知关键值写 null 并保留问题，不用零充当未知。参数在 parameters 维护唯一要求值，脚本参数文本是 Agent 编写结果，不另维护第二套尺寸。

节点保留 command、featureName、variable、inputNodes，补稳定 id、componentId 或 connectionId/mateId，以及 requirementIds。脚本行号只对应那份脚本，不把它当长期身份。

### 局部草稿示例（不能直接执行）

```json
{
  "assemblyPlan": {
    "components": [
      {"id": "rod_01", "name": "左拉杆", "source": {"documentId": null, "versionId": null, "docName": null, "docType": "PartDocument"}, "parentAssemblyId": "A_ROOT", "fixed": false, "initialPlacement": null, "basis": []},
      {"id": "body_01", "name": "松紧节", "source": {"documentId": null, "versionId": null, "docName": null, "docType": "PartDocument"}, "parentAssemblyId": "A_ROOT", "fixed": null, "initialPlacement": null, "basis": []}
    ],
    "interfaces": [
      {"id": "I_ROD", "name": "连接轴段", "sourceComponentId": "rod_01", "coordinateFrame": "源零件局部", "locator": {"description": "结合轴段范围与邻接端面确认"}, "basis": []},
      {"id": "I_A", "name": "A端孔", "sourceComponentId": "body_01", "coordinateFrame": "源零件局部", "locator": {"description": "结合A端归属和轴向范围确认"}, "basis": []}
    ],
    "connections": [
      {"id": "R001", "name": "左拉杆连接A端", "assemblyId": "A_ROOT", "mechanicalMeaning": "待核对连接依据", "expectedMotion": {"status": "pending", "description": null}, "basis": [], "mates": [
        {"id": "M001", "type": "concentric", "moveSide": {"componentId": "rod_01", "interfaceId": "I_ROD"}, "referenceSide": {"componentId": "body_01", "interfaceId": "I_A"}, "alignment": null, "parameterRef": null, "dependsOn": [], "reason": "表达同轴；不代表轴向位置已确定", "basis": []}
      ]}
    ],
    "openIssues": [
      {"id": "AXIAL", "question": "轴向定位基准、数值和运动要求是什么？", "affectedRefs": ["R001"], "status": "open", "answer": null, "basis": []}
    ]
  }
}
```

这是片段，已有目标树中的 A_ROOT、来源、方向和依据需补齐后才能执行，不能以此片段宣称计划完整。历史案例保持原样，不自动迁移。

## 3. 重建以后怎样接已有查询

```text
按需查询 before
→ Agent 同步完整脚本，按已确认状态提交本次操作或必要的完整重建脚本；装配追加需单独验证，不能继承零件验证结论
→ collect_assembly_state() 取得当前 data.Instances、data.Matings
→ diff_instances() 按需整理 added/removed/unchanged
→ Agent 根据来源、名称、层级及实际观察确认各组件
→ 需要位置证据时调用 collect_assembly_transforms，按实例 ID 关联矩阵
→ 查询当前拓扑及所需几何，确认部位
→ build_element_ref(instanceId, elementId) 组织完整引用
→ 更新本阶段资料与配合对应
```

查询结果和字段含义见[装配结构查询](assembly-modeling.md#42-查询装配结构getassemblystruct)。diff_instances、check_instances、check_component_source 直接接收 data.Instances，check_mate_readback 接收 data.Matings；计划绑定记录仍保留 componentId 和 instanceId。

来源要求中的 documentId/versionId 在检查函数内部对应 DocID/VersionID；接口原数据不改写。矩阵来自 transform 工具的 data.Instances，按 ID 与组件绑定关联；位置检查方法见[接口参考第 4.2.2 节](assembly-modeling.md#422-全部实例矩阵collect_assembly_transforms)。服务端 Issues 和本地 processingIssues 分开记录。

使用矩阵作为检查证据时，记录目标装配文档、版本、实例 ID、对应阶段及保存的工具返回位置。两份返回中的源信息或身份不一致时，先重查确认，不直接组合验证。后续修改影响位置时，旧矩阵证据失效。查询工具不自动保存文件，由调用方按验收需要保存完整工具返回，不增加固定查询目录或文件名。

整批重建可能全部旧实例移除、全部新实例新增。added 顺序不等于左、右身份；同一局部元素 ID 可以出现在不同实例中。接口行为已确认就沿用，不每次重做实验。

查询得到的是查询时刻的当前编号；若随后又重建，不能把之前编号写进新实例配合。Python 查询不是 CrownScript 内部命令，不能据此假定同次重建引用已自动解决。按现有已确认方法衔接；缺具体能力就说明，不猜命令、不擅改追加建模。

阶段资料增加 componentBindings（componentId、instanceId、reason、evidence）、interfaceBindings（再加 interfaceId、elementId）和 mateResults（mateId、nodeId、variable、featureName、creationResult、evidence）即可，不新增批次系统。

context 记录 documentId、versionId、docType、stage、scriptFile、responseFile。可加 runDir 作为相对资料路径的基目录；省略时相对路径从当前工作目录读取，也可以传明确绝对路径。runDir 不是证据索引或服务器状态标识。

证据用 evidence 路径数组，引用实际文件。新重试保留新脚本/响应，不覆盖旧文件后声称路径没变就是当前；外部编辑是否发生及资料是否仍有效由 Agent 确认。

## 4. 检查要求与结果

每条要求包含 id、title、kind、target、stage、required、expected、basis；数值项加 unit、tolerance、tolerance_basis。stage 表示首次必须检查的阶段。适用视觉项加 purpose=stage_model_visual/final_model_visual。运动机构另列 motion，不能从静态画面推断运动有效。

| kind | 检查什么 |
| --- | --- |
| instances | 当前完整同范围内的数量与实例对应资料 |
| componentSource | 每个组件要求的来源字段 |
| mateCreation | 本条配合的创建返回，沿用 classify_mating_result |
| mateParticipants | 本条配合实际回查的移动方和参考方 |
| mateGeometryRefs / mateParameters | 实际部位引用及适用类型/方向/数值 |
| solver | 实际求解状态 |
| position | 实际装配位置、朝向、间距或几何关系 |
| interference | 真实实体相交范围与允许接触 |
| visual | 已查看的当前 CAD 整体和必要局部 |
| motion | 规定运动与自由度的实际证据 |

干涉 actual 记录 check_interference 的完整返回；用现有 make_check 整理结论，evidence 引用调用方保存的返回文件。Group 非空时按设计依据判断；明确禁止的相交判失败，是否允许不清楚则未验证。Group 和 Issues 均为空且范围完整、证据当前时，可支持本范围未检测到干涉；不代表整体验收通过。服务异常或返回无效记未验证，不能记成空 Group。

instances.expected.componentIds 列具体组件，componentSource.target.componentId 指单个组件，expected.source 只列明确要求的字段。每条配合的四类要求 target.mateId 相同；mateParticipants.expected 记录 moveComponentId/referenceComponentId，实际函数参数由当前确认的绑定取得，不能任意换双方。

make_check 只整理结果，不认证证据。记录包含 requirementId、kind/purpose、target、expected、actual、单位/容差、status、reason、evidence、context；不会复制整份要求做快照。数值或实际观察放 actual，方法、范围和对象依据可一并放在实际记录或阶段说明中。

“重复认领、旧编号、身份未确认”先说明对应资料有问题，相关项未验证；完整同范围的实际查询确认少件、多件或错误来源才判对应模型项失败。

## 5. 工具怎么用

入口位于 `scripts/assembly_verification.py`，这是 Python 函数库，不是 CLI 或 CAD 指令。它不联网、不执行脚本、不选面、不排阶段，零件验证仍使用原模块。

| 函数 | 输入重点 | 输出 |
| --- | --- | --- |
| check_instances | 当前实例、Agent 确认的对应；scope_confirmed=True 才作数量失败判断 | 单项结果 |
| check_component_source | 本组件明确来源要求与当前实例字段 | 单项结果 |
| check_mate_readback | 本轮有效 featureId、实际配合、已确认双方实例 | 单项双方回查结果 |
| compare_value | 实测、要求、容差，调用前确认单位/对象 | error、withinTolerance |
| make_check | 实际比较或 Agent 观察及证据 | 单项记录，不自动判断几何真实性 |
| build_assembly_report | 要求、当前结果、context，按需 final/additional_ids/issues | scope、context、overall、rows、issues |
| write_assembly_report | 报告与新的输出目录 | assembly-verification.json/md，拒绝覆盖已有报告 |

数值 position 的 actual 使用 value、unit、target_basis、coordinateFrame="assembly_world"；要求端有 expected 数值、unit、tolerance、tolerance_basis。报告会复算，不把错误的 passed 原样通过。局部坐标加计划变换不是实际位置证据。

visual 的 actual 使用 method="cad_browser"、observation 非空文字，evidence 指实际截图。程序只核对记录及文件存在，Agent 必须真的看过。solver、motion、干涉、引用和参数的通过也必须有非空实际检查内容，不能以占位字典代替真实检查。

### 最小调用示例（变量由当前任务取得，不是自动装配脚本）

保持当前任务工作区为工作目录；执行前将 `<skill_dir>` 替换为执行器技能 `SKILL.md` 所在目录的实际绝对路径，输入、输出和证据路径仍以任务工作区为基准。

```python
import sys

sys.path.insert(0, "<skill_dir>")

from scripts.assembly_verification import check_instances, build_assembly_report, write_assembly_report

# 当前实例由已有查询取得；bindings 是 Agent 本轮确认的对应，不是历史 ID。
instance_check = check_instances(
    instance_requirement, current_instances, bindings,
    context=context, evidence=["stage02.instances.json"], scope_confirmed=True,
)
# other_checks 包含本阶段/最终所需的配合、实际测量和浏览器观察等记录。
report = build_assembly_report(
    requirements, [instance_check, *other_checks], context=context,
    final=True, issues=unresolved_connection_issues,
)
write_assembly_report(report, output_dir)
# Agent 实际阅读报告、原始资料及模型，决定修正或交付；报告不触发 CAD 修改。
```

无法识别的创建返回为未验证；已确认的空特征为创建失败。直接使用原分类工具的 reason 区分，不把所有格式错误都说成模型失败。

报告 issues 是单一问题数组，每项至少 status、reason，按实际问题加 target/evidence；连接级待定问题、清单外已确认错误都要列入。issues 的明确失败影响整体，缺证据使未验证；不要把可选清单失败偷偷转换为实质问题，除非已有设计依据。

## 6. 检查顺序与完成门槛

先列要求和时机；阶段执行后检查返回并拿当前数据；确认对象再查组件、配合、求解/运动、位置、干涉和视觉；Agent 阅读结果后决定继续、修正或补证据。不是每条调用都查全部，而是按语义完整阶段查适用项及受影响旧项。

报告可用 additional_ids 加本轮受影响旧要求，final=True 复查全部要求。旧 context 或要求不匹配的资料不能直接通过；历史保留，真正修正后只传当前有效记录。基本完整性检查不遍历操作图：每组件来源、每 mate 的四类要求、必要类别及当前/最终视觉应在清单里。Agent 另核对尚未列入清单的缺项、实际树范围、运动要求及未解决连接问题。

当前有效必需失败或实质问题确认失败 → 不通过；无失败但有必需未验证或缺项 → 未完成；全部必需项有有效证据通过且执行、阶段及最终检查满足[装配规范](assembly-modeling.md#6-装配验收流程) → 才可报告装配验收通过。测试通过不等于模型通过，用户同意保存也不替代验收。
