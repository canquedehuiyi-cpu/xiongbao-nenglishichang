# 曲面建模

## 1. 模块描述

本模块使用草图、曲线或曲面边界创建拉伸、旋转、扫描、放样和填充曲面，并将已有曲面缝合。草图的创建、平面解析及局部坐标换算由草图模块负责；本模块使用实际取得的源引用 ID。也支持按面 ID 删除曲面中的指定面。

曲面结果不能仅因返回 `entityId` 就被视为有体积的实体，不自动套用实体合并、切除或抽壳规则。

需要保留主体、替换局部实体面并通过补面和缝合恢复实体时，按适用条件读取[局部实体—曲面重构](local-transition-reconstruction.md)。

## 2. 命令清单及共同规则

| 功能 | 命令 | 源引用 |
| --- | --- | --- |
| 拉伸曲面 | `Surface.extrudeSurface` | `curveIds`，整数数组 |
| 旋转曲面 | `Surface.revolveSurface` | `contours`，整数数组 |
| 扫描曲面 | `Surface.sweepSurface` | `sweepProfile`，整数；`sweepPath`，整数数组 |
| 放样曲面 | `Surface.loftSurface` | `profiles`，整数数组 |
| 填充曲面 | `Surface.fillSurface` | `boundaryCurveIds`，整数数组 |
| 缝合曲面 | `Surface.knitSurface` | `surfaces`，曲面 entityId 数组 |
| 删除曲面 | `Surface.deleteSurface` | 第二个位置参数，面 ID 整数数组 |

- 第一个参数是唯一、非空的中文特征名。删除曲面的第二个参数直接传面 ID 数组；其他已登记曲面命令的第二个参数传参数对象。
- 拉伸和旋转的源引用可以使用整个草图的 `entityId` 或单条曲线的 `id`；两种输入和开放曲线均已验证。不把草图创建结果的特征 `id` 当作草图 `entityId`。
- 扫描、放样和填充按各节已验证输入使用，不把一种命令的输入能力推广到所有命令。
- 草图 ID 优先使用 `Sketch.createSketch` 返回对象的 `['entityId']`；单条曲线使用实际取得的曲线 `id`，不能从所属草图 ID 推导。
- 不要求枚举草图中每条线才使用整个草图，也不假定现有实体拓扑采集器能够列出草图曲线。
- 源几何需要创建草图时，先退出草图会话，再调用曲面命令。各阶段使用同一文档，维护完整累计脚本；正常新增默认追加，例外按[执行流程](../execution-workflow.md)处理。
- 长度和坐标单位为 mm，旋转角度为度；变量只用 `var`，每条语句有分号，不写尾随逗号。
- 返回值是特征信息对象，包含 `instanceId`、`entityId`、`id` 和 `name`。曲面结果引用使用 `result['entityId']`，特征引用使用 `result['id']`。
- 检查执行错误和返回的有效非零 `id`、`entityId`；返回成功与实际曲面形状检查分别记录。

## 3. 拉伸曲面：`Surface.extrudeSurface`

```javascript
Surface.extrudeSurface(extrudeSurfaceName, params);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `extrudeSurfaceName` | 第一个位置参数，中文特征名 |
| `curveIds` | 源草图或曲线实际 ID 数组 |
| `directionType`、`direction` | `0` 和 `new Direction()`，使用源草图法向 |
| `reverse` | `0`，不反向 |
| `extrudeType1`、`height1` | `0`，单深度；基线深度 30 mm |
| `draftType1`、`angle1` | `-1` 和 `0`，不拔模 |
| `offsetType`、`distance`、`reverseOffset` | `-1`、`0`、`0`，不偏置 |
| `capType` | 保留已验证的 `0`，其他取值和封口含义未登记 |
| `extrudeType2` | `-1`，不使用第二方向 |
| `height2`、`draftType2`、`angle2` | `0`、`-1`、`0` |
| `toSurface1`、`toSurface2` | 基线传 `0`，不使用到面终止 |

```javascript
var extrudeSurfaceResult = Surface.extrudeSurface('拉伸曲面_001', {
    curveIds: [sourceSketchId],
    directionType: 0,
    direction: new Direction(),
    extrudeType1: 0,
    height1: 30,
    toSurface1: 0,
    reverse: 0,
    draftType1: -1,
    angle1: 0,
    offsetType: -1,
    distance: 0,
    reverseOffset: 0,
    capType: 0,
    extrudeType2: -1,
    height2: 0,
    toSurface2: 0,
    draftType2: -1,
    angle2: 0
});
var extrudeSurfaceEntityId = extrudeSurfaceResult['entityId'];
var extrudeSurfaceFeatureId = extrudeSurfaceResult['id'];
```

`sourceSketchId` 是前序实际取得的源草图 ID；转换为单曲线输入时使用 `curveIds: [sourceCurveId]`。变量均需在完整累计脚本中由实际引用赋值，不能复制样本 ID 到其他文档。

## 4. 旋转曲面：`Surface.revolveSurface`

```javascript
Surface.revolveSurface(revolveSurfaceName, params);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `revolveSurfaceName` | 第一个位置参数，中文特征名 |
| `contours` | 源草图或曲线实际 ID 数组；开放曲线可用 |
| `axis` | `Axis`，基线用两个世界坐标点定义 Y 轴 |
| `reverse` | `0`，不反向 |
| `revolveType1`、`angle1` | `0` 和 `360`，给定角度旋转一周 |
| `revolveType2`、`angle2` | `-1` 和 `0`，不使用第二方向 |
| `ToSurface1`、`ToSurface2` | 基线传 `0`，不使用到面终止 |

参数字段以已验证调用为准：使用 `axis`，不使用资料中的 `rotAxis`；使用大写 `T` 的 `ToSurface1`、`ToSurface2`。拉伸曲面的 `toSurface1`、`toSurface2` 则是小写 `t`，不能混用。

```javascript
var revolveSurfaceResult = Surface.revolveSurface('旋转曲面_001', {
    contours: [sourceSketchId],
    axis: new Axis(new Point(0, 0, 0), new Point(0, 1, 0)),
    reverse: 0,
    revolveType1: 0,
    angle1: 360,
    ToSurface1: 0,
    revolveType2: -1,
    angle2: 0,
    ToSurface2: 0
});
var revolveSurfaceEntityId = revolveSurfaceResult['entityId'];
var revolveSurfaceFeatureId = revolveSurfaceResult['id'];
```

轴的两个点必须不同，且使用世界坐标。单曲线输入使用 `contours: [sourceCurveId]`。不把 `new Axis(lineId)` 在实体模块中的支持情况当作本曲面接口已运行验证的依据。

### 4.1 球面曲面：半圆弧绕直径旋转

当目标是完整球面曲面且不要求体积时，可将精确的 180° 圆弧绕其直径轴旋转 360°。这是球面曲面路线，不是实体球路线，也不需要用多片曲面近似球面。

- 设球心为 `C`、半径为 `R`。在包含旋转轴的草图平面内创建以 `C` 为圆心、半径为 `R` 的半圆弧；半圆弧的两个端点位于同一直径轴上。使用草图模块已登记的中心圆弧接口，并通过实际草图局部坐标系换算点位。
- 旋转轴通过 `C` 和半圆弧的两个端点。轴用两个不同的世界坐标点定义；球体对旋转轴方向对称，未指定方向时可按项目坐标约定选取可用直径轴。
- 以实际取得的单条圆弧曲线 `id` 作为 `contours: [sourceArcId]`，使用本节已验证的单方向 360° 参数调用 `Surface.revolveSurface`。结果引用读取 `result['entityId']`，并记录其为曲面对象。
- 本构造是从几何关系推导的精确球面路线，不是实体近似。现有运行验证覆盖了单条开放曲线输入和 360° 旋转，但尚未单独验证“半圆弧旋转后得到完整球面”的组合；不得仅凭特征返回 ID 宣称形状已验证。执行后检查曲面类型、完整性和位置，并如实记录组合尚未验证或实际检查结果。
- 完整球面没有设计边可供倒圆角。球面曲面不能用于要求实体体积的布尔、抽壳或实体配合任务；不得把曲面对象当作实体球。

## 5. 扫描曲面：`Surface.sweepSurface`

```javascript
Surface.sweepSurface(sweepSurfaceName, params);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `sweepSurfaceName` | 第一个位置参数，中文特征名 |
| `sweepType` | `0`，草图轮廓扫描 |
| `sweepProfile` | 实际轮廓 ID，已验证草图圆曲线 id |
| `sweepPath` | 连续路径 ID 数组，已验证单条样条曲线 id |
| `profileDirection` | `2`，轮廓方向随路径变化 |
| `sweepDirection` | `0`，按文档默认使用正向 |
| `diameter` | 本次草图轮廓模式保留 `0`，不由它定义轮廓直径 |

```javascript
var sweepSurfaceResult = Surface.sweepSurface('扫描曲面_001', {
    sweepType: 0,
    sweepProfile: sourceProfileId,
    sweepPath: [sourcePathId],
    profileDirection: 2,
    sweepDirection: 0,
    diameter: 0
});
var sweepSurfaceEntityId = sweepSurfaceResult['entityId'];
var sweepSurfaceFeatureId = sweepSurfaceResult['id'];
```

`sourceProfileId`、`sourcePathId` 使用实际轮廓和路径引用。字段使用 `diameter`，不是资料中的 `riameter`；模式 `0` 按成功调用提供 `sweepProfile`，不因资料的条件说明省略轮廓。

## 6. 放样曲面：`Surface.loftSurface`

```javascript
Surface.loftSurface(loftSurfaceName, params);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `loftSurfaceName` | 第一个位置参数，中文特征名 |
| `profiles` | 按连接顺序排列的截面 ID 数组；已验证草图区域 id、草图圆曲线 id 的组合 |
| `matchPoints` | 空数组，不指定匹配点 |
| `startConstraint`、`endConstraint` | 基线均为 `0` |
| `startReverse`、`endReverse` | 基线均为 `0` |
| `hasGuideCurve`、`guideCurves` | `0` 和空数组，不使用引导线 |

```javascript
var loftSurfaceResult = Surface.loftSurface('放样曲面_001', {
    profiles: [firstProfileId, secondProfileId],
    matchPoints: [],
    startConstraint: 0,
    startReverse: 0,
    endConstraint: 0,
    endReverse: 0,
    hasGuideCurve: 0,
    guideCurves: []
});
var loftSurfaceEntityId = loftSurfaceResult['entityId'];
var loftSurfaceFeatureId = loftSurfaceResult['id'];
```

`firstProfileId`、`secondProfileId` 使用实际截面引用，并保持用户要求的连接顺序。`profiles` 使用数组，不按资料误写成单个整数；不能为碰运气随意交换截面或增加中间截面。

## 7. 填充曲面：`Surface.fillSurface`

填充用于依据边界曲线生成一片曲面。`boundaryCurveIds`使用实际曲线/边引用，不能传所属对象或面的ID。下方模板依赖已存在的引用，不是空白文档可直接运行的脚本。

```javascript
Surface.fillSurface(fillSurfaceName, params);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `fillSurfaceName` | 第一个位置参数，中文特征名 |
| `boundaryCurveIds` | 实际边界 ID 数组，已验证曲面圆形边界 id 和草图曲线 id |
| `alternateFace` | `0`，不勾选交替面 |
| `reverseSurface` | `0`，不反转曲面 |

```javascript
var fillSurfaceResult = Surface.fillSurface('填充曲面_001', {
    boundaryCurveIds: [boundaryCurveId],
    alternateFace: 0,
    reverseSurface: 0
});
var fillSurfaceEntityId = fillSurfaceResult['entityId'];
var fillSurfaceFeatureId = fillSurfaceResult['id'];
```

`boundaryCurveId` 使用边界自身的实际 ID，不能用所属曲面的 entityId 或面 id 代替。

### 多段闭合边界模板

```javascript
var localPatchResult = Surface.fillSurface('闭合边界局部补面', {
    boundaryCurveIds: [firstBoundaryCurveId, secondBoundaryCurveId, thirdBoundaryCurveId],
    alternateFace: 0,
    reverseSurface: 0
});
var localPatchEntityId = localPatchResult['entityId'];
```

数组只示意多段边界的输入方式，不规定边数。边界必须满足填充所需的闭合引用条件，整个草图ID作为填充输入仍未验证。

`alternateFace:0`、`reverseSurface:0`为已确认基线；其他取值的具体组合未验证。不要添加未登记的面相切/曲率约束字段；桥接曲线的G1约束不代表填充曲面的接缝满足G1。

## 8. 缝合曲面：`Surface.knitSurface`

```javascript
Surface.knitSurface(knitSurfaceName, params);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `knitSurfaceName` | 第一个位置参数，中文特征名 |
| `surfaces` | 待缝合曲面的实际 entityId 数组，不使用特征 id、草图 id 或边线 id |
| `controlGap` | `0` 关闭自定义间隙控制；`1` 开启并使用 `tolerance`。已用同组曲面对比验证，需使用指定缝合间隙时显式传 `1` |
| `tolerance` | 浮点数，文档默认 `0.001` mm；基线保留该值 |

```javascript
var knitSurfaceResult = Surface.knitSurface('缝合曲面_001', {
    surfaces: [firstSurfaceId, secondSurfaceId],
    controlGap: 1,
    tolerance: 0.001
});
var knitSurfaceEntityId = knitSurfaceResult['entityId'];
var knitSurfaceFeatureId = knitSurfaceResult['id'];
```

`firstSurfaceId`、`secondSurfaceId` 优先使用前序曲面结果的 `['entityId']`，例如 `sweepSurfaceResult['entityId']` 和 `fillSurfaceResult['entityId']`。资料对 surfaces 的“草图或边线Id”描述不符合本次成功输入，本次只登记已验证的曲面对象 entityId 数组。

既有模型可按名称补充查询源引用：

```javascript
var firstSurfaceId = Query.getEntityIdByFeatureName('扫描曲面验证_001');
var secondSurfaceId = Query.getEntityIdByFeatureName('填充曲面8');
```

使用名称查询前须明确每个特征只有一个待引用结果，并检查源 ID 有效且不同；不能用名称查询精确定位多结果特征。以上均为模板片段，提交时包含完整依赖，调试需要时可打印源引用及返回对象。

缝合后的操作使用新返回的 `knitSurfaceEntityId`；源引用在缝合后是否仍有效尚未确认，不依赖旧 ID 继续操作，也不宣称旧对象已删除。后续需要面或边时从新结果取得当前拓扑。

`controlGap`控制是否自定义缝合精度，枚举解释见参数表；设置`tolerance`或获得有效返回，不能证明接缝误差已满足要求。核对边界对应、实际自由边和对象类别后再判断闭合结果，不能用增大精度或切换模式代替几何检查。

2026-10-12 在垂壁与平板四处撕扯边口的同组13个曲面上验证：`controlGap:0` 时将 `tolerance` 从0.001改为0.01及0.1，回查仍为曲面；保持0.1并改为 `controlGap:1` 后回查为1实体、0曲面残留，882条边均关联两侧面。此前将0解释为启用、1解释为不启用的说明已据此纠正。该结果只验证此组合及开关作用，0.1不是其他模型的统一默认精度；仍须确认目标开口未被误合并。

缝合结果可以是实体或曲面，通过当前`/solids`、`/shells`确认实际类别，不能仅根据返回ID认定有体积。`tolerance`的实际效果须结合查询结果确认，参数取值本身不保证闭合。

缝合精度依据真实接缝偏差、允许偏差和局部最小特征选择，记录该值及间隙控制是否启用。回查自由边、非流形边、输入曲面残留，以及应保留的开口内外边界是否仍分离；实体类别、必要闭合条件和目标边口均满足后，才判定实体恢复完成。

## 9. 删除曲面：`Surface.deleteSurface`

```javascript
Surface.deleteSurface(deleteSurfaceName, surfaceIds);
```

| 参数 | 本次使用方式 |
| --- | --- |
| `deleteSurfaceName` | 第一个位置参数，唯一、非空的中文特征名 |
| `surfaceIds` | 第二个位置参数，待删除面的实际 ID 整数数组 |

```javascript
var deleteSurfaceResult = Surface.deleteSurface('删除曲面_001', [targetFaceId]);
var deleteSurfaceEntityId = deleteSurfaceResult['entityId'];
var deleteSurfaceFeatureId = deleteSurfaceResult['id'];
```

- `targetFaceId` 使用当前有效的面 ID，不使用所属对象 entityId。例如面 `id:1057、entityId:1060`，删除该面传 `[1057]`。
- 第二个参数直接传数组，不写 `{ deleteFaces: [...] }` 或 `{ surfaceIds: [...] }`。
- 已知源曲面 entityId 时，按第 10 节的对象到面查询取得面 ID；按位置选择面时，结合实际几何及按需元素详情识别，不猜 ID。
- 删除结果对象引用使用新返回的 `deleteSurfaceEntityId`；继续选面或选边时重新取得结果的当前拓扑，不依赖删除前的面、边 ID。
- 已验证曲面上的单面删除。多面删除、体积实体删面及删面后的自动修补效果尚未验证，不由命令成功推定这些效果。

## 10. 已知曲面的边界查询

未知曲面对象 ID 时，先用 `/api/topo/d/{documentId}/v/{versionId}/shells` 枚举曲面，返回结构与实体枚举一致。调用拓扑 MCP 工具时传 `kinds=["shells"]`，也可与 `solids`、`curves` 同时查询；对象归属、未知面类型保留及详情追加规则见[统一拓扑采集](../entity-modeling/details/topology-and-features.md#实体曲面与独立曲线的统一采集)。未知面类型不阻断边界和几何详情采集，不据详情轴向推断具体面类型。

已知当前曲面 entityId 时，可以用以下已实测的既有 REST GET 接口先查面，再查边：

```text
/api/topo/d/{documentId}/v/{versionId}/solids/{entityId}/faces
/api/topo/d/{documentId}/v/{versionId}/faces/{faceId}/edges
```

查询必须使用相同文档和版本。边 ID 可去重，但共享边、接缝不一定是待填充的外边界，仍按位置及需求识别；必要时按现有规范追加只含 `Query.getElementInfoById` 的详情查询。任何后续几何变化后重新取得当前拓扑。

## 11. 验证范围与结果检查

- 拉伸和旋转已验证整草图与单曲线输入、开放曲线、法向拉伸30 mm、绕世界Y轴旋转360°；扫描、放样和填充的输入范围见各节。上述六种创建和缝合功能的中文名称、返回ID读取及实际生成结果均已确认。
- 半圆弧绕其直径轴旋转以构造完整球面，是由已验证的开放曲线旋转能力推导出的精确曲面路线；该特定几何组合尚未单独运行验证。执行结果必须单独检查，不得把通用旋转测试等同于球面结果验证。
- 扫描方向 `0` 来自文档默认和用户要求，不把原 `-1` 的运行截图作为该取值已实测的证据。
- 扫描方向 `1`（双向）、`2`（反向）及圆形轮廓扫描模式 `1` 尚未实测，本次不生成这些组合，也不使用或解释方向值 `-1`。
- 放样已验证草图区域与圆曲线组合、两个实体弧边作开放截面并使用独立桥接引导线，以及两条桥接曲线作截面的具体组合。填充已验证曲面圆形边界、草图曲线和三/四段闭环（实体边与独立曲线混合）。这些不保证任意几何组合可用；填充整个草图仍未验证。
- 自定义方向、反向、到面、拔模、偏置、双方向、对称、其他 capType、圆形轮廓扫描、超出已验证组合的引导线放样、匹配点和其他起止约束、填充交替面及反转仍未验证；新组合按项目规则明确状态并检查结果。
- 示例的30 mm、360°不是所有任务的默认尺寸，不给本次参数自行添加 Variable 类型支持。
- 平面区域 `Surface.planeSurface` 不纳入本次功能；加厚和其他未登记曲面命令不扩展。
- 缝合已验证两个曲面 entityId 输入及同组13曲面的间隙控制对照、中文名称和返回 ID 读取；`controlGap:1,tolerance:0.1` 在上述模型形成实体。该具体组合不保证其他模型闭合，源对象生命周期和容差效果仍按实际回查确认。
- 拉伸检查方向、深度和边界；旋转检查轴、角度和形状；扫描检查路径与轮廓方向；放样检查截面连接及扭转；填充检查区域与边界对应。返回有效ID不替代实际结果检查。
- 删除曲面已验证直接传单个面 ID 数组并返回特征信息；不传参数对象，不用所属对象 entityId 替代面 ID。检查指定面是否被删除、剩余面是否符合目标，返回 ID 有效不替代实际结果检查。
