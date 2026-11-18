# CrownCAD 特征建模

本文档是实体特征的统一入口：抽壳、拉伸、旋转、放样、扫描及其对应的切除操作，以及筋特征。

草图、截面、路径和旋转轴在特征调用中都作为引用 ID 使用。本文档只规定这些 ID 如何传给特征，不描述它们如何创建或获取。

## 共同规则

- 所有长度、半径和角度按 CrownCAD 接口约定使用；长度和半径单位为 mm。
- 变量只能使用 `var`。
- 特征名必须非空、可读，并且在同一累计脚本中唯一。
- 函数参数、对象和数组末项不写尾随逗号。
- `print(result)` 只用于调试，不是建模必需语句。
- 创建或修改实体后，后续实体操作只能使用真实返回的 `result['entityId']`。
- 特征结果通常同时包含特征 `id` 和实体 `entityId`；后续特征镜像使用 `result['id']`，后续实体操作使用 `result['entityId']`。
- 文档中的数字 ID 只表示示例；实际执行必须替换为当前文档中的真实引用 ID。

参数表中支持类型包含 `Variable` 时，该入参才允许使用 `new Variable(...)`；`Number | Variable` 表示普通数值或变量均可，`Variable` 表示必须传入变量。其他参数类型保持原定义。具体兼容性以本文件的参数表和对应运行时验证记录为准。

## ID 的区别

| ID 类型 | 用途 | 规则 |
|---|---|---|
| 实体 `entityId` | `mergeSolids`、`cutSolids` 和后续实体操作 | 来自前序接口返回值的 `result['entityId']` |
| 特征 `id` | `features` 和后续特征镜像 | 来自前序实体特征返回值的 `result['id']` |
| 线的 `lineId` | `new Axis(lineId)`，也可作为扫描路径 | 使用线的 `id`，不要使用线对应的 `entityId` |
| 草图 ID | `sketch`、`sketchs`、`sweepProfile` 或草图扫描路径 | 使用当前文档中真实的草图引用 ID |
| 路径/曲线 ID | `sweepPath` | 有线或曲线 ID 时优先使用；单条路径也要放进数组 |

旋转轴可以使用已有线：

```javascript
var revolveAxis = new Axis(1506);
```

这里的 `1506` 表示线的真实 `lineId`，不是该线的 `entityId`。

也可以使用两个不同的点：

```javascript
var revolveAxis = new Axis(
    new Point(0, 0, 0),
    new Point(0, 1, 0)
);
```

两个点不能相同。

扫描路径统一使用数组：

```javascript
var sweepPath = [4028];
```

如果路径来自已有实体边，`4028` 应是当前有效的边/线 ID；如果已经拿到了草图内部曲线的真实 `entityId`，直接使用这个曲线 ID；如果只有草图路径 ID，则使用草图 ID。路径来自已有实体边时需要先获取当前拓扑，路径来自草图或曲线时不需要实体拓扑采集。

## 参数如何选择

调研资料中的参数全部保留。生成脚本时按下面的方式选择：

- 必填参数必须传入。
- 可选参数由 LLM 根据用户意图决定是否传入。
- 不要求把所有可选参数全部写入对象。
- 会改变几何含义的参数要明确传值，不依赖不清楚的接口默认值。
- 下面的默认值是 LLM 的判断参考，不是强制模板。

常用默认参考：

| 参数 | 默认参考值 | 说明 |
|---|---:|---|
| `reverse` | `0` | 不反向 |
| `directionType` | `0` | 使用草图法向 |
| `extrudeType2` | `-1` | 不使用第二拉伸方向 |
| `revolveType2` | `-1` | 不使用第二旋转方向 |
| `startConstraint` | `0` | 放样起始端默认约束 |
| `endConstraint` | `0` | 放样终止端默认约束 |
| `selectChain` | `0` | 不自动选择相连路径 |
| `profileDirection` | `0` | 保持轮廓法向 |
| `sweepDirection` | `0` | 沿路径正向 |
| `mergeType` | 按基体/凸台语义决定 | 见下方合并规则 |

## 抽壳约束：`Solid.createShell`

抽壳的参数约束、调用示例和实测组合集中记录在本节：

| 参数 | 约束 |
|---|---|
| 第一个参数 `shell` | 必须是非空、可读且在累计脚本中唯一的特征名；项目脚本使用中文语义名。 |
| `removeFaces` | 必填 `Integer[]`。面 ID 必须来自同一文档和版本的当前有效拓扑；`[]` 表示不移除开口面，会生成封闭空腔；单面和多面均已验证。 |
| `thickenSolid` | 必填目标实体 `entityId`，必须取自前序创建/特征调用的实际返回值；不能传特征 `id`、名称或旧实体 ID。 |
| `thickness` | 必填正数，单位 mm，接口类型为 `Float`；可行性取决于几何及偏置方向，不以示例数值限定设计尺寸。零值和负值未验证。 |
| `outward` | 必填整数枚举。生成脚本使用 `0`（向内）或 `1`（向外）；两者已验证。 |
| `multiFaces`、`multiThickness` | 可选自定义厚度参数，按相同顺序一一配对；使用时两者必须同时提供且长度相同。`multiFaces` 使用当前有效拓扑面 ID，`multiThickness` 使用正整数毫米值。单面和多面整数厚度已验证；自定义小数厚度未验证。 |

`removeFaces` 与 `multiFaces` 的面 ID 都依赖当前拓扑。模型有任何后续几何变化时，旧面 ID 失效；需要在抽壳调用前重新获取拓扑。为避免输入语义冲突，生成脚本时不得让同一个面同时出现在 `removeFaces` 和 `multiFaces` 中；该重叠输入的 CAD 行为尚未验证。

### 几何前置条件与失败处理

抽壳目标应为符合设计意图的连续实体，不能包含意外分离的部分。本项目一次支架建模的人工抽壳操作提示目标实体存在其他不相连的部分，无法进行抽壳；将“目标实体含有不相连部分”记录为 CrownCAD 抽壳的已观察失败条件。该记录证明该案例中的目标实体不满足抽壳要求，不据此推断所有多实体场景的接口行为。

遇到明确的不相连部分诊断时，应回查 `thickenSolid` 对应实体及其上游凸台合并、独立实体和切除结果；不要仅通过减小壁厚或更换开口面来重试。按设计意图决定修复连接、分别处理独立零件或重新规划。若返回结果只有空特征且没有明确原因，只能判定抽壳失败、原因未明，不要仅凭空结果归因于实体不连通。现有面边拓扑采集结果不等同于已验证的材料连通性检查；未确认查询语义前，不得将其当作连通性通过证据。

### 抽壳前校验与失败分析

抽壳检查点、删除面覆盖和抽壳后的几何接续，按需读取 [抽壳与后续特征](shell-and-followup.md)。

每次调用前必须核对并记录：目标实体属于当前文档/版本且存在于 `/solids`；壁厚、方向与自定义厚度符合参数约束；移除面来自当前有效拓扑、属于该实体且与目标开口对应。参数或引用错误须先修正。

执行后检查 `errorInfo`、错误行及返回的 `id`、`entityId`；任一 ID 无效均判为失败，不继续构建依赖。无报错但返回空特征时，记录“未生成有效抽壳结果，原因未定”，不能据此判定几何不可行。

失败时先复核参数、引用和选面，再结合实际错误及可用诊断区分几何、工具或文档状态问题；证据不足时保留未定结论。保存抽壳前完整脚本、调用参数、选面依据、原始响应及修正记录。几何风险与路线调整由任务建模流程判断；累计执行、重试和现场恢复遵循执行工作流，不在本节另设规则。

### 抽壳调用示例

用于从实心控制体生成壁厚。`removeFaces`列出移除面，空数组表示不移除开口面；`outward:0`向内，`outward:1`向外。`thickenSolid`指定目标实体，`thickness`指定基础壁厚，成对的`multiFaces`和`multiThickness`指定局部壁厚。

以下为独立模板：目标实体和面ID变量来自前序结果及当前拓扑，不能直接复制到空白文档。数字厚度仅示意用法，不是默认设计尺寸。

```javascript
var cavityResult = Solid.createShell('封闭空腔抽壳', {
    removeFaces: [],
    thickenSolid: controlBodyId,
    thickness: 2,
    outward: 0
});
var cavityBodyId = cavityResult['entityId'];
```

```javascript
var openShellResult = Solid.createShell('单封口面开口抽壳', {
    removeFaces: [openingFaceId],
    thickenSolid: controlBodyId,
    thickness: 2,
    outward: 0
});
var openShellBodyId = openShellResult['entityId'];
```

```javascript
var multipleOpeningsResult = Solid.createShell('多封口面统一抽壳', {
    removeFaces: [firstOpeningFaceId, secondOpeningFaceId],
    thickenSolid: controlBodyId,
    thickness: 2,
    outward: 0,
    multiFaces: [],
    multiThickness: []
});
var multipleOpeningsBodyId = multipleOpeningsResult['entityId'];
```

多面模板只示意数组组织，不规定面数或曲面类型。`multiFaces`和`multiThickness`在均匀壁厚时可省略，也可同时为空数组。目标实体使用前序返回ID。

调用前核对目标实体与面ID是否属于当前状态，参数类型和配对数组是否正确。检查执行错误及返回的有效ID，不把外层成功状态当作特征成功。

### 已确认的用法范围

封闭空腔、单面/多面开口、向内/向外抽壳，以及基础壁厚配合一个或多个面自定义整数厚度，均有有效调用。接口用法得到确认不代表任意实体和尺寸组合都能抽壳；每次仍检查当前几何、选面和实际结果。自定义小数厚度等未验证组合不由这些用法推定支持。

### 已观察到的失败条件

| 情况 | 结果 |
|---|---|
| 支架独立复刻中，目标实体包含其他不相连的部分 | 人工抽壳操作提示无法进行抽壳。该次 UI 参数为 10 mm、四个移除面；脚本尝试记录为 1.5 mm、五个移除面后改为一个，因此仅将“不相连部分”记为本案例观察到的失败条件，不将 UI 参数视为脚本失败请求的参数。 |

### 调用示例

```javascript
var shellResult = Solid.createShell('外壳_001', {
    removeFaces: [openingFaceId],
    thickenSolid: bodyId,
    thickness: 2.5,
    outward: 0,
    multiFaces: [positiveXFaceId, negativeXFaceId],
    multiThickness: [3, 4]
});
var shellEntityId = shellResult['entityId'];
```

必须检查返回对象的 `id` 和 `entityId` 均为非零有效值；外层 API 返回 200 或 `errorInfo: null` 不能单独证明抽壳成功。成功后后续实体操作只使用 `shellResult['entityId']`，不再引用输入实体 ID。

## 基体、凸台和切除

```text
创建基体
→ mergeType: 0
→ 不传 mergeSolids

创建凸台并附着到已有实体
→ mergeType: 1
→ 传 mergeSolids: [已有实体的真实 entityId]

创建凸台但没有目标实体
→ mergeType: 0
→ 不传 mergeSolids

已有实体但用户没有要求附着
→ mergeType: 0
```

`mergeSolids` 和 `cutSolids` 都必须是实体 ID 数组，不能传特征名或实体名称。

`mergeType: 1` 成功后，参与合并的旧实体不再用于后续建模；所有 Cut 方法成功后，`cutSolids` 中的旧实体也不再用于后续建模。后续统一使用新结果：

```javascript
var nextEntityId = featureResult['entityId'];
```

## 1. 拉伸基体/凸台：`Solid.extrude`

```javascript
Solid.extrude(extrudeName, params)
```

必填参数：

- `sketch`
- `extrudeType1`

常用参数：

| 参数 | 含义 |
|---|---|
| `reverse` | 是否反向拉伸，`0` 不反向，`1` 反向 |
| `directionType` | `0` 使用草图法向，`1` 使用 `direction` |
| `direction` | 自定义拉伸方向，`directionType: 1` 时使用 `Direction` |
| `extrudeType1` | `0` 定深，`4` 两侧对称 |
| `height1` | 第一方向高度，`Number \| Variable`，定深或对称拉伸时使用 |
| `draftType1` | 第一方向拔模类型：`-1` 不拔模，`0` 向外拔模，`1` 向内拔模 |
| `angle1` | 第一方向拔模角度，`Number \| Variable`；仅当 `draftType1` 为 `0` 或 `1` 时生效，必须为正值 |
| `extrudeType2` | `-1` 不使用第二方向，`0` 第二方向定深 |
| `height2` | 第二方向高度，`Number \| Variable` |
| `draftType2` | 第二方向拔模类型：`-1` 不拔模，`0` 向外拔模，`1` 向内拔模 |
| `angle2` | 第二方向拔模角度，`Number \| Variable`；仅当 `draftType2` 为 `0` 或 `1` 时生效，必须为正值 |
| `distance` | 偏移距离，`Number \| Variable` |
| `thickness1` | 第一侧厚度，`Number \| Variable` |
| `mergeType` | `0` 独立生成，`1` 与已有实体合并 |
| `mergeSolids` | `mergeType: 1` 时传入实体 ID 数组 |

### 拔模参数联动规则

- `angle1` 不能单独启用第一方向拔模。
- `draftType1: -1` 表示第一方向不拔模，此时 `angle1` 应省略或设置为 `0`。
- `draftType1: 0` 表示第一方向向外拔模，此时 `angle1` 必须为正值。
- `draftType1: 1` 表示第一方向向内拔模，此时 `angle1` 必须为正值。
- `draftType2` 与 `angle2` 使用相同规则。
- `extrudeType2: -1` 时，第二方向未启用，不能单独设置有效的 `draftType2`。

示例：

```javascript
var sketchId = 55;
var bossResult = Solid.extrude('拉伸凸台_001', {
    sketch: sketchId,
    reverse: 0,
    directionType: 0,
    extrudeType1: 0,
    height1: 10,
    draftType1: -1,
    angle1: 0,
    extrudeType2: -1,
    draftType2: -1,
    mergeType: 1,
    mergeSolids: [baseId]
});
var bossId = bossResult['entityId'];
```

向外拔模时，必须同时传入拔模类型和正值角度：

```javascript
var draftResult = Solid.extrude('向外拔模拉伸_001', {
    sketch: sketchId,
    reverse: 0,
    directionType: 0,
    extrudeType1: 0,
    height1: 10,
    draftType1: 0,
    angle1: 60,
    extrudeType2: -1,
    draftType2: -1,
    mergeType: 0
});
var draftEntityId = draftResult['entityId'];
```

禁止只传 `angle1: 60` 而省略 `draftType1`；这种写法不能表达“向外拔模 60 度”。

如果该特征后续需要被镜像，还要保留特征 ID：

```javascript
var bossFeatureId = bossResult['id'];
```

## 2. 拉伸切除：`Solid.extrudeCut`

```javascript
Solid.extrudeCut(extrudeCutName, params)
```

必填参数：

- `sketch`
- `cutSolids`

常用参数：

| 参数 | 含义 |
|---|---|
| `reverse` | 是否反向切除 |
| `directionType` | `0` 使用草图法向，`1` 使用 `direction` |
| `direction` | 自定义切除方向 |
| `extrudeType1` | `0` 定深，`4` 对称，`5` 单向贯穿 |
| `height1` | 第一方向切除深度，`Number \| Variable` |
| `draftType1` | 第一方向拔模类型：`-1` 不拔模，`0` 向外拔模，`1` 向内拔模 |
| `angle1` | 第一方向拔模角度，`Number \| Variable`；仅当 `draftType1` 为 `0` 或 `1` 时生效，必须为正值 |
| `extrudeType2` | `-1` 不使用第二方向，`0` 第二方向定深，`5` 第二方向贯穿 |
| `height2` | 第二方向切除深度，`Number \| Variable` |
| `draftType2` | 第二方向拔模类型：`-1` 不拔模，`0` 向外拔模，`1` 向内拔模 |
| `angle2` | 第二方向切除角度，`Number \| Variable`；仅当 `draftType2` 为 `0` 或 `1` 时生效，必须为正值 |
| `distance` | 偏移距离，`Number \| Variable` |
| `thickness1` | 第一侧厚度，`Number \| Variable` |
| `thickness2` | 第二侧厚度，`Number \| Variable` |
| `reverseToCut` | 是否反侧切除，`0` 否，`1` 是 |
| `cutSolids` | 被切除实体的真实 `entityId` 数组 |

### 拔模切除参数联动规则

拉伸切除使用与拉伸相同的拔模参数规则：

- `angle1` 不能单独启用第一方向拔模。
- `draftType1: -1` 表示第一方向不拔模，此时 `angle1` 应省略或设置为 `0`。
- `draftType1: 0` 表示第一方向向外拔模，此时 `angle1` 必须为正值。
- `draftType1: 1` 表示第一方向向内拔模，此时 `angle1` 必须为正值。
- `draftType2` 与 `angle2` 使用相同规则。
- `extrudeType2: -1` 时，第二方向未启用，不能单独设置有效的 `draftType2`。

示例：

```javascript
var cutResult = Solid.extrudeCut('拉伸切除_001', {
    sketch: sketchId,
    reverse: 1,
    directionType: 0,
    extrudeType1: 5,
    draftType1: -1,
    angle1: 0,
    extrudeType2: -1,
    draftType2: -1,
    reverseToCut: 0,
    cutSolids: [baseId]
});
var cutId = cutResult['entityId'];
```

向外拔模切除时，必须同时传入拔模类型和正值角度：

```javascript
var draftCutResult = Solid.extrudeCut('向外拔模切除_001', {
    sketch: sketchId,
    reverse: 1,
    directionType: 0,
    extrudeType1: 0,
    height1: 10,
    draftType1: 0,
    angle1: 30,
    extrudeType2: -1,
    draftType2: -1,
    reverseToCut: 0,
    cutSolids: [baseId]
});
var draftCutEntityId = draftCutResult['entityId'];
```

禁止只传 `angle1` 而省略 `draftType1`；这种写法不能表达拔模切除。

## 3. 旋转基体/凸台：`Solid.revolve`

```javascript
Solid.revolve(revolveName, params)
```

必填参数：

- `sketch`
- `axis`

常用参数：

| 参数 | 含义 |
|---|---|
| `reverse` | 是否反向旋转 |
| `revolveType1` | `0` 定角度，`3` 两侧对称 |
| `angle1` | 第一方向旋转角度，`Number \| Variable` |
| `revolveType2` | `-1` 不使用第二方向，`0` 第二方向定角度 |
| `angle2` | 第二方向旋转角度，`Number \| Variable` |
| `thickness1` | 第一侧厚度，`Number \| Variable` |
| `mergeType` | `0` 独立生成，`1` 与已有实体合并 |
| `mergeSolids` | `mergeType: 1` 时传入实体 ID 数组 |

示例：

```javascript
var revolveAxis = new Axis(revolveLineId);
var revolveResult = Solid.revolve('旋转凸台_001', {
    sketch: sketchId,
    axis: revolveAxis,
    reverse: 0,
    revolveType1: 0,
    angle1: 360,
    mergeType: 0
});
var revolveId = revolveResult['entityId'];
```

## 4. 旋转切除：`Solid.revolveCut`

```javascript
Solid.revolveCut(revolveCutName, params)
```

必填参数：

- `sketch`
- `axis`
- `cutSolids`

常用参数：

| 参数 | 含义 |
|---|---|
| `reverse` | 是否反向旋转切除 |
| `revolveType1` | `0` 定角度，`3` 两侧对称 |
| `angle1` | 第一方向切除角度；变量兼容性当前未单独验证 |
| `revolveType2` | `-1` 不使用第二方向，`0` 第二方向定角度 |
| `angle2` | 第二方向切除角度，`Number \| Variable` |
| `cutSolids` | 被切除实体的真实 `entityId` 数组 |

示例：

```javascript
var revolveCutAxis = new Axis(revolveLineId);
var revolveCutResult = Solid.revolveCut('旋转切除_001', {
    sketch: sketchId,
    axis: revolveCutAxis,
    reverse: 0,
    revolveType1: 0,
    angle1: 360,
    cutSolids: [baseId]
});
var revolveCutId = revolveCutResult['entityId'];
```

## 5. 放样基体/凸台：`Solid.loft`

```javascript
Solid.loft(loftName, params)
```

必填参数：

- `sketchs`，至少两个截面 ID，数组顺序就是放样顺序；
- `startConstraint`；
- `endConstraint`。

常用参数：

| 参数 | 含义 |
|---|---|
| `sketchs` | 两个或更多放样截面 ID |
| `startConstraint` | 起始端约束，`0` 默认，`1` 垂直于草图，`2` 使用方向 |
| `endConstraint` | 终止端约束，`0` 默认，`1` 垂直于草图，`2` 使用方向 |
| `startTangent` | `startConstraint: 2` 时使用的方向 |
| `endTangent` | `endConstraint: 2` 时使用的方向 |
| `mergeType` | `0` 独立生成，`1` 与已有实体合并 |
| `mergeSolids` | `mergeType: 1` 时传入实体 ID 数组 |

示例：

```javascript
var loftResult = Solid.loft('放样凸台_001', {
    sketchs: [section1Id, section2Id, section3Id],
    startConstraint: 0,
    endConstraint: 0,
    mergeType: 0
});
var loftId = loftResult['entityId'];
```

## 6. 放样切除：`Solid.loftCut`

```javascript
Solid.loftCut(loftCutName, params)
```

必填参数：

- `sketchs`，至少两个截面 ID；
- `startConstraint`；
- `endConstraint`；
- `cutSolids`。

常用参数：

| 参数 | 含义 |
|---|---|
| `sketchs` | 两个或更多放样截面 ID |
| `startConstraint` | 起始端约束 |
| `endConstraint` | 终止端约束 |
| `startTangent` | 起始方向约束参数 |
| `endTangent` | 终止方向约束参数 |
| `cutType` | 切除方式参数，基础写法不强制传入 |
| `cutSolids` | 被切除实体的真实 `entityId` 数组 |

示例：

```javascript
var loftCutResult = Solid.loftCut('放样切除_001', {
    sketchs: [cutSection1Id, cutSection2Id],
    startConstraint: 0,
    endConstraint: 0,
    cutSolids: [loftId]
});
var loftCutId = loftCutResult['entityId'];
```

## 7. 扫描基体/凸台：`Solid.sweep`

```javascript
Solid.sweep(sweepName, params)
```

必填参数：

- `sweepType`；
- `sweepPath`；
- `profileDirection`；
- `sweepDirection`。

常用参数：

| 参数 | 含义 |
|---|---|
| `sweepType` | `0` 草图轮廓，`1` 圆形轮廓 |
| `sweepProfile` | `sweepType: 0` 时使用的轮廓草图 ID |
| `radius` | `sweepType: 1` 时使用的圆形轮廓半径，`Number \| Variable` |
| `sweepPath` | 线、曲线或草图路径 ID 数组 |
| `selectChain` | `0` 不自动选择相连路径，`1` 自动选择 |
| `profileDirection` | `0` 保持法向，`2` 随路径变化 |
| `sweepDirection` | `0` 正向，`1` 双向，`2` 反向 |
| `mergeType` | `0` 独立生成，`1` 与已有实体合并 |
| `mergeSolids` | `mergeType: 1` 时传入实体 ID 数组 |

示例：

```javascript
var sweepResult = Solid.sweep('扫描凸台_001', {
    sweepType: 0,
    sweepProfile: profileSketchId,
    sweepPath: [pathLineId],
    selectChain: 0,
    profileDirection: 2,
    sweepDirection: 0,
    mergeType: 0
});
var sweepId = sweepResult['entityId'];
```

## 8. 扫描切除：`Solid.sweepCut`

```javascript
Solid.sweepCut(sweepCutName, params)
```

轮廓、路径和方向参数的选择规则与 `Solid.sweep` 相同，但扫描切除不使用 `mergeType` 和 `mergeSolids`。另外必须传入：

```javascript
cutSolids: [targetEntityId]
```

扫描轮廓二选一：

- `sweepType: 0` 时必须传 `sweepProfile`，不使用 `radius`；
- `sweepType: 1` 时必须传 `radius`，不使用 `sweepProfile`。

示例：

```javascript
var sweepCutResult = Solid.sweepCut('扫描切除_001', {
    sweepType: 0,
    sweepProfile: cutProfileSketchId,
    sweepPath: [pathLineId],
    selectChain: 0,
    profileDirection: 2,
    sweepDirection: 0,
    cutSolids: [sweepId]
});
var sweepCutId = sweepCutResult['entityId'];
```

## 9. 筋：`Solid.createRib`

```javascript
Solid.createRib(ribName, params)
```

筋特征使用一张导向草图，在已有实体上生成有厚度的筋。`sketch` 和 `body` 必须是当前文档中的真实引用 ID：草图使用草图 ID，基体使用前序特征返回的实体 `entityId`。不能把特征名称、旧实体 ID 或猜测的数字 ID 直接传入。

参数约束：

| 参数 | 含义和约束 |
|---|---|
| `sketch` | 筋导向草图的真实 ID，必填 |
| `body` | 目标实体的真实 `entityId`，必填 |
| `ribDirection` | 筋方向模式：`0` 平行，`1` 垂直 |
| `direction` | `Direction` 方向对象；不需要自定义方向时使用 `new Direction()` |
| `reverse` | 方向是否反向：`0` 不反向，`1` 反向 |
| `thicknessType` | 厚度位置：`0` 第一侧，`1` 两侧，`2` 第二侧 |
| `thickness` | 筋厚度，单位 mm，应为正值 |
| `draftType` | 拔模方式：`-1` 无拔模，`0` 向外，`1` 向内 |
| `angle` | 拔模角度；`draftType: -1` 时应传 `0` |
| `extendType` | 筋端部延伸方式；当前成功示例使用 `0` |

推荐在同一脚本中先解析草图和基体，再调用筋接口，避免跨阶段缓存失效的 ID：

```javascript
var ribSketchId = Query.getEntityIdByFeatureName('筋验证导向_013');
var ribBodyId = Query.getEntityIdByFeatureName('拉伸凸台/基体1');
var ribResult = Solid.createRib('实体筋_001', {
    sketch: ribSketchId,
    body: ribBodyId,
    ribDirection: 0,
    direction: new Direction(),
    reverse: 0,
    thicknessType: 2,
    thickness: 10,
    draftType: -1,
    angle: 0,
    extendType: 0
});
var ribEntityId = ribResult['entityId'];
print(ribResult);
```

筋创建成功后，后续实体操作使用 `ribResult['entityId']`；不要继续复用已经参与筋特征的旧基体 ID。`Query.getEntityIdByFeatureName()` 只能用于当前文档中的补充解析，不能替代前序接口返回的实体 ID 管理。

筋的导向草图还必须与目标实体建立有效的空间关系。当前测试中，矩形和直线都创建在默认草图平面、实体由该平面单向或双向拉伸、以及使用居中立方体让默认平面穿过实体时，`Solid.createRib` 都返回了 `entityId: 0`。因此不能仅凭“草图创建成功”就判断该草图可以生成筋；空白文档中的无基准面筋测试需要先确认可用的导向平面或已有成功的草图布局。

## 当前验证状态

以下写法已有调研资料或成功示例支持：

- `Solid.extrude`、`Solid.extrudeCut`、`Solid.revolve`、`Solid.revolveCut`、`Solid.loft`、`Solid.loftCut`、`Solid.sweep`、`Solid.sweepCut` 的基本调用形式；
- `Solid.createRib` 的基本调用形式；当前已成功验证 `ribDirection: 0`、`thicknessType: 2`、`draftType: -1`、`extendType: 0` 的组合；
- `loftCut` 基础写法不传 `cutType`；
- `sweepType: 0`；
- `selectChain: 0`；
- 单条路径使用 `sweepPath: [pathId]`；
- `Axis(lineId)` 和两点定义旋转轴。

放样和扫描的基本命令已经验证可用，但验证结果不代表所有几何组合都有效。两个放样截面必须位于满足几何关系的不同平面；扫描必须同时提供合法的轮廓和路径。第一次放样尝试使用不合适的截面平面时返回了空特征，调整为偏移基准面后才生成实体，因此后续执行仍需检查返回对象的 `id` 和 `entityId`。

以下参数写法仍未有完整成功样例，但保留在能力说明中，生成时不能声称已经验证成功：

- `directionType: 1` 配合自定义 `Direction`；
- `startConstraint/endConstraint: 2`；
- 除本次基础组合外的其他 `sweepType: 1`、`radius`、截面方向和路径选择组合；
- `selectChain: 1`；
- `createRib` 的其他 `ribDirection`、`thicknessType`、`draftType` 和 `extendType` 枚举组合；
- 拉伸贯穿、拉伸双向、旋转双向等组合。

### 变量兼容性验证

- 在用户提供的 `PartDocument` 上，`Solid.createRib.thickness` 使用 `new Variable(...)`、`Solid.createRib.angle` 使用 `new Variable(...)` 均未产生 `errorInfo`，但返回 `id: 0`、`entityId: 0`；相同几何布局下的普通数值厚度基线也返回 `id: 0`、`entityId: 0`。
- 因此当前只能确认参数没有触发类型错误，不能确认筋特征已经生成，也不能把 `thickness` 或 `angle` 记为已验证的变量参数。导向草图与目标实体的有效空间关系仍需单独确认。
