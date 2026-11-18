# 装配建模

## 1. 模块描述

装配建模模块负责把多个已有零件文档插入 `AssemblyDocument`，再通过实例查询、实例变换和装配配合建立零件之间的空间关系。模块输出可执行、可检查的 CrownScript；实例 ID 和元素 ID 必须来自当前装配文档的真实查询结果。

## 2. 能力定位与边界

### 2.1 能力范围

本模块负责：

- 插入已有零件并查询装配实例；
- 固定或解除固定装配实例；
- 移动和旋转装配实例；
- 创建重合、平行、相切、同心轴、垂直、距离和角度配合；
- 创建齿轮配合和槽口配合；
- 查询最终实例树和配合关系，并判定单条配合命令的返回结果；装配整体验收另按第 6 节执行。

### 2.2 模块边界

- 装配操作使用 `AssemblyDocument`；零件几何仍由实体和草图模块负责；
- MCP 服务负责发送 CrownScript、读取装配结构接口的 JSON，使用当前连接的 OAuth 身份；本地检查脚本负责确定性校验，不负责图片识别或空间关系判断；
- 当前不实现动态干涉检查，也不负责修改或删除已有配合；
- 装配操作只使用本文件列出的已确认命令和数据结构，未确认的参数组合不能直接提交。

## 3. 前置约束

任务操作图中的组件、部位、连接、配合编号与当前实际实例/元素、脚本和返回应相互关联，见[装配记录约定](assembly-records.md)。该约定不自动生成或调度 CrownScript；来源版本、当前引用和能力仍按本文件核对。

### 3.1 文档和实例上下文

- 装配任务必须使用 `AssemblyDocument`；完整的 `documentId + versionId + docType` 一旦确定，后续执行和查询都复用同一上下文；
- `Assembly.insertComponent` 的返回值可能是空特征信息，不能从其中读取有效实例 ID；
- 插入前后都调用 `collect_assembly_state`（底层 getAssemblyStruct），通过 data.Instances 中新增的 ID 判断插入结果；
- 同一个零件文档可以插入多次，实例只能通过 `instanceId` 区分，不能按 `docName` 去重。

### 3.2 实例和元素引用

- 后续装配操作只能使用实例树查询返回的真实 `instanceId`；
- 面、边和顶点属于零件局部拓扑，配合元素必须使用完整的 `(instanceId, elementId)` 引用；
- `moveInstanceId`、`refInstanceId` 使用实例 ID 字符串，`moveElementId`、`refElementId` 使用对应实例内的元素 ID；
- 元素的类型和几何语义需要结合拓扑查询及 `Query.getElementInfoById` 结果确认。

### 3.3 调用形式和参数约束

- `Assembly.fixInstance` 使用两个直接参数，不使用参数对象；
- `Assembly.moveInstance` 和 `Assembly.rotateInstance` 的 `instanceId` 必须直接写字符串数组字面量，不能先放入变量；
- 移动和旋转的角度、位置单位分别按接口定义使用，当前旋转角度单位为度，位置单位为 mm；
- `checkType` 当前统一使用 `0`，不实现动态干涉检查；
- 所有特征名必须唯一、非空且可读，CrownScript 只使用 `var`，函数参数、对象和数组末项不写尾随逗号。

### 3.4 配合命令返回值判定

配合接口可能在失败时返回空特征对象而不返回 `errorInfo`。判定本次配合命令返回成功必须同时满足：返回对象的 `id` 非零且 `name` 非空。有效特征不证明最终配合已持久化、求解有效或实际姿态正确，仍须按第 6 节验收。示例：

```text
{'id': 34, 'name': '同轴心6', 'entityId': 0, 'instanceId': ''}
```

以下结果表示当前配合失败：

```text
{'id': 0, 'name': '', 'entityId': 0, 'instanceId': ''}
```

配合返回对象是配合特征信息，不是零件实体信息，不能从它取得后续零件实体 ID。

## 4. 命令清单

| 类别 | 命令或接口 | 用途 |
| --- | --- | --- |
| 插入 | `Assembly.insertComponent` | 插入已有零件文档 |
| 实例查询 | `getAssemblyStruct` | 一次读取实例身份、层级、原型和矩阵 |
| 元素引用 | `(instanceId, elementId)` | 标识实例中的面、边或顶点 |
| 固定 | `Assembly.fixInstance` | 固定或解除固定实例 |
| 移动 | `Assembly.moveInstance` | 移动一个或多个实例 |
| 旋转 | `Assembly.rotateInstance` | 旋转一个或多个实例 |
| 普通配合 | `Assembly.createMating` | 创建基础装配配合 |
| 特殊配合 | `Assembly.createGearMating`、`Assembly.createSlotMating` | 创建齿轮或槽口配合 |
| 配合查询 | 同次 `getAssemblyStruct` 的 `Matings` | 查询当前配合原始记录 |

### 4.1 插入零件：`Assembly.insertComponent`

```javascript
var insertResult = Assembly.insertComponent('零件实例_001', {
  docName: '已有零件文档名',
  position: new Point(0, 0, 0),
  boxCenter: 0
});
print(insertResult);
```

参数说明：

- `insertInstanceName`：插入实例的特征名称，必须唯一、非空、可读；
- `docName`：要插入的已有零件文档名称；
- `position`：插入位置，类型为 `Point`，单位为 mm；
- `boxCenter`：是否按照包围盒中心确定位置，`0` 不使用，`1` 使用；
- `matrix4`：可选的矩阵变换，使用时按接口规则确定位置；
- `projectId`：可选的零件所属项目 ID，默认使用当前项目。

插入完成后必须重新查询实例树，不能使用 `insertResult` 中的 `id`、`entityId` 或 `instanceId` 推断实例。

### 4.2 查询装配结构：`getAssemblyStruct`

两个 MCP 工具共用以下只读接口，每次独立向内核读取当前状态，不走缓存，不互相调用。分别通过 `collect_assembly_state(document_id, version_id)` 和 `collect_assembly_transforms(document_id, version_id)` 获取实例/配合与矩阵数据；不传本地路径，返回的 artifacts 证据包按[文件交付规则](../execution-workflow.md#51-跨机器文件交付与证据使用)下载、校验并保存到调用端：

```text
GET /api/topo/d/{documentId}/v/{versionId}/getAssemblyStruct
```

两个工具只传目标装配 document_id、version_id，不传 task_dir、request_log_path 或实例筛选参数。服务端分别返回精简业务数据和临时证据包下载地址；验收所需证据下载到调用端后保存。查询失败仍作为错误报告，不返回空成功。

#### 4.2.1 实例与配合：`collect_assembly_state`

```python
# 读取实例和配合；这里表示 MCP 调用参数。
collect_assembly_state(document_id="装配ID", version_id="版本ID")
```

返回 documentId、versionId、data、processingIssues 和 artifacts，不返回 schemaVersion。data 包含 Instances、Matings，以及服务端实际存在的 Issues；artifacts 提供本次查询证据包的临时下载地址。

| 实例原字段 | 用途 |
| --- | --- |
| ID / Name | 确认实例身份与名称；同源重复实例分别识别 |
| DocID / VersionID / ProtoID | 确认源文档、源版本及原型；与顶层目标装配上下文区分 |
| ParentID / Level / Path | 保留父级和层级线索 |
| Visible / IsVirtual / IsFolder | 可见性、虚拟和组织节点标记 |

Instances 保留其他原字段，但移除 Matrix、Matrix4Rows；Matings 原字段完整保留。不返回两棵树、Protos 或其他大集合；原型仅供内部来源检查。processingIssues 为本地来源、字段、引用问题，与服务端 Issues 区分。

业务检查直接接收 data.Instances、data.Matings；计划绑定仍用 componentId、instanceId，这些是计划记录字段。组织文件夹不计组件；隐藏、虚拟和无效实例不能静默丢弃，子装配统计范围须先确认。docName 等没有已确认来源的要求仍记缺少证据，不能用实例名补造；有效来源字段与要求不符才判来源失败。

```text
查询插入前 state.data.Instances
→ Assembly.insertComponent
→ 重新查询插入后 state.data.Instances
→ diff_instances 按原始 ID 比较新增、移除和保留对象
→ 根据来源、名称与实际观察确认组件
```

#### 4.2.2 全部实例矩阵：`collect_assembly_transforms`

**功能：读取指定装配当前全部实例的位置和朝向数据，供装配位置验证使用。** 同一个零件插入多次，各实例分别返回自己的 ID 和矩阵，能区分“这是哪个零件实例、属于哪个父级、具有怎样的平移和旋转”。它是只读查询，不移动零件、不创建配合；查询时会把接口的 12 项矩阵补成便于计算的 4×4 矩阵。

在插入、移动、旋转或创建配合之后，需要核对实际位置时调用。例如检查两个孔是否同轴、两个安装面是否贴合、零件朝向是否正确、关键间距是否符合要求。工具提供矩阵数据，具体关系还需结合对应的局部几何进行计算和比较，不直接返回“位置正确”。

```python
# 查询全部实例，不按名称筛选或合并重复零件。
collect_assembly_transforms(document_id="装配ID", version_id="版本ID")
```

返回 documentId、versionId、data、processingIssues 和 artifacts。data 只包含 Instances，以及服务端实际存在的 Issues。每个实例仅复制实际存在的 ID、Name、DocID、VersionID、ProtoID、ParentID、Level、Path、Visible、IsVirtual、IsFolder、Matrix，并新增 Matrix4Rows；不补造缺失字段，不返回配合或原型。artifacts 提供原响应、整理结果和脱敏 GET 日志的临时下载包。

使用返回时按以下顺序：

1. 在 `data.Instances` 中按 `ID` 找到目标实例，用来源和层级核对对象。
2. 读取同一对象的 `Matrix4Rows`；为 null 时，查看 `processingIssues` 中对应 ID 的原因，不能继续用默认矩阵验证。
3. 按下述坐标说明，将孔中心、轴线或安装面等必要局部几何转换到可比较的装配坐标，再与设计要求和容差比较。数量、来源和配合回查仍使用 `collect_assembly_state`。

Matrix 为接口原始 12 项，Matrix4Rows 为本地补全的四行：[0,3,6,9]、[1,4,7,10]、[2,5,8,11]、[0,0,0,1]（前三行数字表示原数组下标）。缺失或非法矩阵时保留原实例及原字段，Matrix4Rows=null，原因按实例 ID 写入 processingIssues；不替换成单位矩阵。返回保留全部实例和原顺序，包括隐藏、虚拟、文件夹节点。无效或重复 ID 整体报错；Matrix4Rows 固定从 Matrix 生成。

合理推断：Matrix 表示零件自身坐标到装配坐标的实例变换。接口每次向内核读取当前矩阵，已查真实单层样本的 5 个实例均为 ParentID=""、Level=0，可按“零件自身坐标 → 当前装配坐标”理解。这是单层样本支持的解释，不代表所有嵌套场景已验证。

```text
装配中的点 = Matrix4Rows × [零件自身坐标x, y, z, 1]
```

最后三项是平移分量；按上述解释，它表示零件自身原点的位置，不一定是几何中心。孔轴、接触面等检查须转换对应局部几何后比较，不能仅看平移三个数。

嵌套子装配尚需一次实际对照：内部矩阵相对父装配，还是已累计到总装。用带可核对旋转、平移和几何点的现有嵌套样本，比较直接应用实例矩阵与“父矩阵 × 子矩阵”哪种符合实际几何，再记录结论。当前单层样本无法区分；工具不自动递归累乘，依赖嵌套世界位置的检查在确认前保留未验证，也不自动填 assembly_world 标记。其他柔性或特殊实例范围仍待实际确认。

结构和矩阵两份返回按实例 ID 关联，不按名称或数组位置关联。两个查询独立执行，之间发生装配修改则重新取得受影响的数据。矩阵读取、补全仅提供位置检查数据，不直接产生验收通过结论。

### 4.3 元素完整引用：`(instanceId, elementId)`

同一个零件的不同实例可以拥有相同的局部元素 ID，因此不能只保存元素 ID。创建配合时，实例和元素必须成对传入：

```javascript
var matingResult = Assembly.createMating('同心配合_001', {
  moveInstanceId: '67',
  moveElementId: 100,
  refInstanceId: '63',
  refElementId: 5909,
  matingType: 3,
  alignType: 0,
  offsetValue: 0
});
print(matingResult);
```

### 4.4 固定实例：`Assembly.fixInstance`

固定实例：

```javascript
var fixResult = Assembly.fixInstance('62', 1);
print(fixResult);
```

解除固定：

```javascript
var activeResult = Assembly.fixInstance('62', 0);
print(activeResult);
```

第一个参数是实例 ID 字符串，第二个参数中 `1` 表示固定，`0` 表示活动。

### 4.5 移动实例：`Assembly.moveInstance`

```javascript
var moveResult = Assembly.moveInstance({
  instanceId: ['76'],
  startPos: new Point(10, 0, 0),
  endPos: new Point(30, 10, 20),
  moveType: 0,
  checkType: 0
});
print(moveResult);
```

| `moveType` | 含义 | 主要参数 |
| ---: | --- | --- |
| `0` | 自由移动 | `startPos`、`endPos` |
| `1` | 沿装配体 XYZ 移动 | `startPos`、`endPos`、`moveDir` |
| `2` | 沿实体移动 | `startPos`、`endPos`、`moveDir` |
| `3` | 使用 XYZ 变量移动 | `moveDir`、`varX`、`varY`、`varZ`、`checkRange` |
| `4` | 移动到 XYZ 位置 | `moveDir`、`varX`、`varY`、`varZ`、`checkRange` |

默认使用装配体全局坐标系；如果要沿零件自身方向移动，应使用沿实体方式，或先将零件方向转换到装配体坐标系。

### 4.6 旋转实例：`Assembly.rotateInstance`

自由旋转示例：

```javascript
var axialDir = new Point(0, 0, 1);
var rotateAxisStart = new Point(0, 0, 0);
var rotateAxisEnd = new Point(0, 0, 1);
var rotateAxis = new Axis(rotateAxisStart, rotateAxisEnd);

var rotateResult = Assembly.rotateInstance({
  instanceId: ['76'],
  rotateType: 0,
  checkType: 0,
  axialDir: axialDir,
  rotateAxis: rotateAxis,
  angleVal: 45
});
print(rotateResult);
```

| `rotateType` | 含义 | 主要参数 |
| ---: | --- | --- |
| `0` | 自由旋转 | `axialDir`、`rotateAxis`、`angleVal` |
| `1` | 沿实体旋转 | `axialDir`、`rotateAxis`、`angleVal` |
| `2` | XYZ 变量旋转 | `angleValX`、`angleValY`、`angleValZ` |

XYZ 旋转示例：

```javascript
var rotateResult = Assembly.rotateInstance({
  instanceId: ['76'],
  rotateType: 2,
  checkType: 0,
  angleValX: 10,
  angleValY: 20,
  angleValZ: 30
});
print(rotateResult);
```

角度单位为度；`angleVal: 45` 表示旋转 45°。

### 4.7 普通配合：`Assembly.createMating`

调用形式：

```javascript
Assembly.createMating(insertInstanceName, params)
```

已确认的 `matingType`：

| `matingType` | 配合 |
| ---: | --- |
| `0` | 重合 |
| `1` | 平行 |
| `2` | 相切 |
| `3` | 同心轴 |
| `7` | 垂直 |
| `11` | 距离 |
| `12` | 角度 |

`alignType` 的取值：

- `0`：同向对齐；
- `1`：反向对齐；
- `2`：无对齐方式，相切和垂直使用。

配合会立即移动 `moveInstanceId` 对应的实例，并影响后续配合。距离和角度配合都使用 `offsetValue`：`matingType: 11` 表示距离，`matingType: 12` 表示角度。

### 4.8 齿轮和槽口配合

齿轮配合：

```javascript
var gearResult = Assembly.createGearMating('', {
  moveInstanceId: '56',
  moveElementId: 1808,
  refInstanceId: '130',
  refElementId: 1808,
  gearValue1: 20,
  gearValue2: 20,
  reverse: 0
});
print(gearResult);
```

`gearValue1:gearValue2` 表示传动比；`reverse: 0` 为正常方向，`reverse: 1` 为反向。

槽口配合：

```javascript
var slotResult = Assembly.createSlotMating('', {
  moveInstanceId: '62',
  moveElementId: 100,
  refInstanceId: '59',
  refElementId: 855,
  constraintType: 2,
  offsetValue: 50,
  reverse: 0,
  alignType: 0
});
print(slotResult);
```

槽口约束：

- `constraintType: 0`：自由；
- `constraintType: 1`：槽口中心；
- `constraintType: 2`：槽口百分比，按 `0` 到 `100` 处理；
- `constraintType: 3`：槽口距离，单位为 mm；
- `reverse: 0`：不反转，`1`：反转；
- `alignType: 0`：同向，`1`：反向。

### 4.9 回查配合：`data.Matings`

使用同次结构结果的 Matings 原始记录：ID、Name、MoveInstance、RefInstance 标识配合和双方实例；MoveElement、RefElement、Offset 等按实际返回检查。check_mate_readback 直接读取这些原字段，不需要调用方先转换一套小写字段。

Status、ReferenceStatus、MatingErrInfo 按原值保留；枚举语义未确认时不能以 Status=0 或空错误文本判求解成功。

### 4.10 静态干涉检查：`check_interference`

```python
# 以下表示 MCP 调用。ID 必须来自本轮实际查询，不照抄示例编号。
check_interference(
    document_id="装配文档ID",
    version_id="版本ID",
    group_ids=["52", "54", "56", "58", "60"],
    distance=0,
)
```

底层为 `POST /api/topo/d/{documentId}/v/{versionId}/checkInterference`，JSON 正文为 `groupIds` 和 `distance`。group_ids 至少包含两个不同的非空字符串，使用当前 collect_assembly_state 的 data.Instances[].ID，确认检查对象后转为字符串；不使用源零件实体 ID 或历史编号。文件夹不参与检查；子装配、隐藏或虚拟实例等不能静默遗漏，应先确认应检范围与接口覆盖能力。

distance 为有限非负距离阈值，默认 0，调用时明确填 0；非零值尚未实际验证，不能宣称已验证其行为。工具使用当前 OAuth 会话，只发送一次 POST，不自动重试、不缓存、不保存文件。

返回 documentId、versionId、groupIds、distance、data。data.Group 的 CheckObjectId1/CheckObjectId2 是检测到干涉的双方实例 ID；data.Issues 和其他 data 扩展字段原样保留。不返回实例位置、干涉体积或预览几何，也不能证明运动全行程无碰撞。

Group 非空时对应具体组件并结合设计要求判断；明确禁止的相交判失败，是否允许不清楚则未验证。Group 与 Issues 均为空且范围完整、证据当前时，仅支持本次范围和阈值下未检测到干涉；Issues 含义不明、请求失败或返回无效时不能判无干涉。需要证据时由调用方保存完整工具返回到现有任务记录，模型修改后重新查询和检测。

## 5. 注意事项

- 插入零件后，必须通过插入前后的实例树差异得到真实 `instanceId`；不能依赖插入返回对象中的空实例信息；
- 同一个零件文档的多个实例必须分别保留各自的 `instanceId`；
- 配合元素必须同时记录 `instanceId` 和 `elementId`，不能只记录局部元素 ID；
- 配合按顺序创建。返回不符合已确认接口要求时，记录名称、原始返回和失败原因。依赖该配合的操作暂停，不依赖它的工作可以继续；修正后回查并重查，不能用其他配合成功覆盖该项失败；
- 结构响应中的配合回查不替代配合创建返回值的即时判定；
- Python 不根据图片选择配合元素，元素选择必须基于图片、拓扑和元素详情完成；
- 装配运行资料写入 `generated/runs/<装配语义>__<任务UUID>/`；用户确认后的归档按 [案例参考与保存](../../../modeling-case-library/references/case-workflow.md) 执行；
- 任一装配操作失败时，先检查 `errorInfo`、实例 ID、元素 ID 和配合返回字段，不得随机更换零件或元素。

## 6. 装配验收流程

独立检查函数及输入、输出示例见[装配记录与独立检查](assembly-records.md#5-工具怎么用)。assembly_verification.py 与零件 verification.py 分开：程序比较明确数据并整理结果，Agent 确认对象、实际观察并决定下一步。先列清单和时机，再按阶段核对返回、当前对象、组件、配合、求解/运动、实际位置、干涉和画面，修改后查受影响旧项，最终按最新状态查全。缺取证能力仍未验证，新工具不扩大本节接口能力。

### 过程检查

浏览器访问及阶段循环沿用[执行流程](../execution-workflow.md)。插入一组零件或完成关键连接后，查看最新实际画面，结合真实实例、配合回查及必要实际位置核对方向和连接；记录目标、现象、依据和下一步。失败连接的依赖操作暂停，修正后重查；独立工作可继续，不能事后补写阶段通过。不按每颗重复螺钉截图，过程检查不代替以下最终验收。

关键插入、移动、旋转或配合阶段前，按[视角展示规则](../execution-workflow.md#21-建模过程中的视角展示)使用 `transform_camera` 选择能观察连接双方和相关接触区域的方向，当前视角已清楚时保持。方向依据实际装配状态，不能将源零件局部法向或计划变换当作已读取的世界位姿。阶段完成后查看最新连接；仅在必要时截图；已有有效画面证据足够时复用，不按插入、移动、旋转或配合阶段固定截图。需要取图时按[视口截图规则](../verification-workflow.md#41-视口截图与跨环境证据保存)下载并实际查看。相机下发和截图成功不证明配合求解、真实位置或无干涉，也不借展示绕过本节验收。

本节定义装配取证与完成门槛：实例、配合求解、实际位姿、真实几何干涉及视觉均须有最新证据。每项记录通过、失败或未验证；任一失败则不通过，无失败但有必需项未验证则未完成，全部通过才可报告装配完成。不新增或假定未确认的 CAD 接口能力。

### 6.1 能力前提

- 实例矩阵通过 collect_assembly_transforms 读取，配合通过 collect_assembly_state 读取。矩阵用法见第 4.2.2 节，配合状态说明见第 4.9 节。
- 第 4.9 节保留原始求解相关字段，但枚举语义未确认；配合回查成功、Status=0 或空 Issues 不能代替求解和干涉检查。
- `checkType: 0` 不执行动态干涉检查，移动或旋转成功不能作为无干涉的证据。
- 实例矩阵已有读取入口，嵌套矩阵是否累计到总装仍需按第 4.2.2 节对照。求解状态和实体干涉检查使用已确认能力；能力、权限或证据不足时记未验证，不改用计划值冒充结果。

### 6.2 检查顺序

1. 在执行前从用户要求确定预期零件及数量、配合清单、关键空间关系和允许误差。将这些预期与实际证据分开保存，禁止根据执行结果反向修改验收目标。
2. 在最后一次装配操作后，通过 collect_assembly_state 重新查询同一装配文档和版本的 getAssemblyStruct，逐项核对源文档、实例 ID 和数量；只统计实际实例，不把根节点计入零件数量。
3. 使用同次响应的 data.Matings 回查配合，将配合名称、移动实例、参考实例及特征 ID 与预期清单和命令返回结果逐项对应；检查缺失、重复及引用不符，不能只比较总数。预期存在配合但回查为空时，不得通过配合验收。
4. 单独核实最终配合求解状态。记录实际错误、冲突以及不符合设计要求的自由度；保留设计允许的运动自由度，不能一律要求机构完全固定。读取不到状态时，不能用有效特征 ID 代替。
5. 调用 collect_assembly_transforms 读取当前全部实例矩阵，按第 4.2.2 节结合所需实际几何核对同轴、端面贴合、朝向和关键间距。若使用源零件局部几何，必须确认它与装配引用的版本一致，并应用真实读取的实例变换；不能应用预设旋转和平移来证明装配正确。
6. 根据当前实例确认应检范围，调用 check_interference，明确填 distance=0。将返回 Group 对应到具体组件，结合设计要求判断干涉是否允许。最终覆盖全部应检组件，阶段检查覆盖受影响组件及其与其他组件的关系。保存完整工具返回到现有任务记录；修改后重新查询和检测。包围盒、名义尺寸和截图不能代替检测。
7. 在 CAD 页面确认当前文档和版本，查看并保存整体、关键连接局部及必要剖面截图。检查错位、穿透、反向和漏件；无法打开模型或截图未覆盖关键部位时，视觉检查仍未完成。

### 6.3 证据与报告

- 由调用方将所用查询工具的完整返回、实际测量或检测结果、截图和验收报告保存到本任务运行目录；每项记录文档 ID、版本 ID、对应执行阶段、检查对象、预期值、实际结果、判定依据、状态及证据路径。验收与用户保存决定分别记录，用户同意保存不能代替必需验收检查。
- 未取得实际结果时保留为空并记录原因，状态为未验证；不得把 `false`、零误差或空异常列表作为“无问题”的默认结果。没有异常记录不等于已检查且无异常。
- 分开报告命令执行结果、配合关系回查、求解状态、实际位置、实体干涉及视觉检查；不得把“命令成功数”写成“配合验收通过数”。
- 汇总时先检查已确认的失败，再检查缺失证据；任何必需检查未验证都不能输出整体验收通过。构建成功但证据不足时，报告“装配已构建，验收未完成”及具体阻塞项，而不是“已完成，待用户确认”。
- 配合、实例变换或所引用源零件发生后续修改时，重新取得受影响的证据并重新汇总；即使文档和版本 ID 没变，也不能复用修改前的验收结论。
