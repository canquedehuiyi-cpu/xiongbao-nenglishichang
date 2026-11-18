# 草图建模

## 1. 模块描述

草图建模模块负责把自然语言中的二维轮廓、辅助定位和草图关系转换为已验证的 CrownScript `Sketch` 命令。草图建立在所选平面的局部二维坐标系中，所有 `x/y` 坐标和尺寸单位均为 mm；局部第三轴是平面法向，局部原点是世界原点在该平面的正交投影。

本文件是草图模块命令清单的唯一权威入口。所有已支持命令、基本签名、参数语义和最小用法都必须在此登记；`details/` 只扩展这里已有命令或共性机制的复杂规则，不承担命令发现。

## 2. 能力定位与边界

本模块负责：

- 选择有效草图平面并解析局部坐标系；
- 创建或进入完整的草图会话；
- 创建点、直线、圆、圆弧、矩形、槽、插值样条和参考直线；
- 将实体边、源草图内容或指定源草图线投影转换到当前草图平面；
- 使用本节列明的 `Sketch.addConstraint` 图元组合添加草图几何关系；仅在用户明确要求完全约束草图时考虑完全约束命令；
- 在本地计算复杂几何参数并检查退化、连接、交叠和轮廓关系；
- 返回可供后续拉伸、旋转或扫描特征使用的真实 `sketchId`。

当前边界：

- CrownScript 只可使用本文件列出的已确认 `Sketch` 命令和 `Point` 构造方式；不得臆造草图能力。
- `Sketch.addConstraint` 仅支持 5.17 列出的关系类型、图元组合、XY 平面和 `snapType` 组合；其余枚举与组合在本技能中均视为不支持，不得猜测参数或在普通建模中自行试验。
- `Sketch.createPoint`、`Sketch.createEllipse`、`Sketch.createLine` 和 `Sketch.createCircle` 返回图元 ID；尺寸约束必须引用当前脚本中实际返回的 ID。直线长度约束使用端点 snap 类型 `3/2`。
- 尺寸约束支持直线目标长度、圆目标半径，以及点锚定圆心的水平、竖直目标距离。椭圆半轴和普通点间尺寸可按 5.14 的形式调用，但目标值驱动效果尚未确认；圆直径目标驱动当前不支持。
- `Sketch.createLine(..., 1)` 和 `Sketch.createCircle(..., 1)` 分别用于长度约束和半径约束，没有显式目标值参数。需要指定独立目标尺寸时，创建图元后使用 `Sketch.createDimension` 的 `dimVal` 与 `changeDimVal: 1`。
- `Sketch.addConstraint` 用于草图几何关系，目标长度、半径等数值尺寸仍用 `Sketch.createDimension`。关系类型、拾取参数和实际效果证据见本节 5.17；调用无报错不等同于该关系已正确求解。
- 当前后续实体特征默认接收整个 `sketchId`，没有单独的轮廓或区域 ID 选择机制。
- `Sketch.createIntpCurve` 当前只支持开放样条；没有已验证的端部切向参数或样条约束。
- 本地数值检查、CrownScript 执行成功和 CAD 实际几何有效是三个不同层次的结论。
- `Sketch.convertEdge` 已在编辑草图会话中验证实体边线 ID、源草图 entityId 和单条源草图线 ID 三种输入形式。

- 桥接曲线属于独立 `Curve` 模块，命令和参数见[曲线建模](../curve-modeling/curve-modeling.md)，不需要本文件的草图会话。引用草图曲线或实体边不意味着桥接创建需要进入 `Sketch`。

## 3. 前置约束

### 3.1 草图平面

草图只可建立在 `type == "Plane"` 的 Element 上。实体面的 `faceId` 就是 `elementId`；已确认的基准面 ID 为：前视 XY 基准面 `8`、上视 XZ 基准面 `36`、右视 YZ 基准面 `22`。

实体面候选从当前有效拓扑中自动匹配。优先使用正式 `type`、面积、包围盒、法向和相邻关系理解“顶面、底面、侧面、主平面”等语义。项目默认“上方”为世界坐标 +Y `(0, 1, 0)`，因此“顶面/向上面”优先匹配法向朝 +Y 的 `Plane` 面，绝不可按 +Z 推断。`UnKnow` 不能用作草图平面或几何语义推断。候选无法可靠区分时询问用户，不向用户索要 ID。

选定 Element 后必须先调用 MCP 工具 `resolve_sketch_plane`，验证平面并通过 `setWorkPlane` 获取 `origin`、`xAxis`、`yAxis` 和 `normal`。不得根据法向自行推导局部轴；详细规则见 [平面与局部坐标](details/plane-and-coordinates.md)。

### 3.2 参数和计算

- 所有关键尺寸、位置、图元关系和轮廓用途必须明确。
- 需要计算的几何参数须先用适当本地工具求出，再把数值字面量和已知绘制调用展开到 CrownScript。
- 不得把未确认的计算逻辑、循环生成逻辑或几何求解能力带入 CAD 执行环境。
- 不得主动生成零长度、零半径或零面积图元。

### 3.3 草图会话包络规则（强制）

草图会话是原子包络边界。所有草图绘制命令必须严格位于一组类型匹配、完整闭合且不嵌套的会话调用之间。允许的会话组合只有：

| 用途 | 开始调用 | 结束调用 |
| --- | --- | --- |
| 新建草图 | `Sketch.createSketch(featureName, planeElementId)` | `Sketch.exitSketch()` |
| 编辑既有草图 | `Sketch.editSketch(featureName)` | `Sketch.exitEditSketch(featureName)` |

新建草图的合法结构：

```javascript
var sketchResult = Sketch.createSketch('轮廓草图_001', planeElementId);
var sketchId = sketchResult['entityId'];

Sketch.createLine(new Point(0, 0), new Point(20, 0));
Sketch.createLine(new Point(20, 0), new Point(20, 10));
Sketch.createLine(new Point(20, 10), new Point(0, 10));
Sketch.createLine(new Point(0, 10), new Point(0, 0));

Sketch.exitSketch();
```

编辑既有草图的合法结构：

```javascript
Sketch.editSketch('轮廓草图_001');

Sketch.createCircle(new Point(0, 0), new Point(10, 0));

Sketch.exitEditSketch('轮廓草图_001');
```

禁止以下情况：

- 在 `createSketch` 或 `editSketch` 之前执行绘制命令；
- 在 `exitSketch` 或 `exitEditSketch` 之后继续向该会话绘制；
- 新建会话使用 `exitEditSketch` 退出，或编辑会话使用 `exitSketch` 退出；
- 嵌套草图会话，或在同一段绘制命令中混用新建和编辑会话；
- `editSketch` 与 `exitEditSketch` 的 `featureName` 不一致；
- 遗漏退出调用，或在退出前开始另一个草图会话。

### 3.4 草图显示与视角

草图前调用 `resolve_sketch_plane` 解析真实平面及局部坐标系；相机方向不能替代坐标核对。

保持当前合适视角；遮挡妨碍必要判断时，通过 `transform_camera` 调整。

仅在必要时截图，不按草图、图元或阶段固定取图，已有有效证据足够时复用。工具选择和相机边界遵循[执行流程](../execution-workflow.md#21-建模过程中的视角展示)。

## 4. 标准工作流程

```text
理解自然语言草图目标
  -> 确定草图平面语义
  -> 从当前拓扑或基准面取得真实 Plane Element
  -> 解析局部坐标系
  -> 建立草图图元与轮廓操作图
  -> 在本地计算复杂参数
  -> 检查退化、连接、交叠和轮廓关系
  -> 保持当前合适视角；仅必要时调整
  -> 创建完整草图会话
  -> 按依赖顺序创建图元
  -> 退出草图会话
  -> 在累计脚本中执行并检查结果
  -> 查看本轮实际草图和视角，关键阶段按需截图留证
```

修改已有草图仅使用已确认能力；没有可靠编辑路线时更新完整源码后评估覆盖重建，不自动试探编辑会话。几何修改后重取受影响拓扑，执行模式及失败处理见[执行流程](../execution-workflow.md)。

## 5. 完整命令清单

| 类别 | 命令 | 基本用途 | 复杂规则 |
| --- | --- | --- | --- |
| 会话 | `Sketch.createSketch` / `Sketch.exitSketch` | 新建并退出草图 | 本节完整说明 |
| 会话 | `Sketch.editSketch` / `Sketch.exitEditSketch` | 编辑并退出既有草图 | 本节完整说明 |
| 基础几何 | `Sketch.createPoint` | 创建独立草图点 | 本节完整说明 |
| 基础几何 | `Sketch.createLine` | 创建直线段 | [轮廓验证](details/contour-validation.md) |
| 基础几何 | `Sketch.createCircle` | 创建圆形闭合轮廓 | [轮廓验证](details/contour-validation.md) |
| 基础几何 | `Sketch.createEllipse` | 创建椭圆闭合轮廓 | 本节 5.13 |
| 基础几何 | `Sketch.createArcByCenter` | 创建中心圆弧 | [轮廓验证](details/contour-validation.md) |
| 矩形 | `Sketch.createRectangle` | 通过对角点创建矩形 | 本节完整说明 |
| 矩形 | `Sketch.createRectangleByCenter` | 通过中心和顶点创建矩形 | 本节完整说明 |
| 槽 | `Sketch.createStraightSlot` | 创建直口槽闭合轮廓 | [槽命令详解](details/slots.md) |
| 槽 | `Sketch.createCenterArcSlot` | 创建中心点圆弧槽 | [槽命令详解](details/slots.md) |
| 槽 | `Sketch.createThreeArcSlot` | 创建三点圆弧槽 | [槽命令详解](details/slots.md) |
| 曲线 | `Sketch.createIntpCurve` | 创建开放插值样条 | [插值样条详解](details/spline.md) |
| 构造几何 | `Sketch.createReferenceLine` | 创建不参与轮廓识别的参考线 | 本节完整说明 |
| 草图尺寸 | `Sketch.createDimension` | 按已确认的输入形式指定数值尺寸目标 | 本节 5.14；仅使用已记录的图元和拾取组合 |
| 转换边界 | `Sketch.convertEdge` | 将源几何投影转换到当前草图平面 | 本节 5.15 |
| 完全约束草图 | `Sketch.createFullyDefineSketch` | 用户明确要求完全约束时快捷添加约束 | 本节 5.16；不是默认收尾 |
| 草图关系约束 | `Sketch.addConstraint` | 在草图元素间添加几何关系 | 本节 5.17；只按已确认的关系及证据使用 |

### 5.1 草图会话

#### 新建草图

```javascript
var sketchResult = Sketch.createSketch('轮廓草图_001', planeElementId);
var sketchId = sketchResult['entityId'];
// 草图几何
Sketch.exitSketch();
```

- `featureName` 必须是同一脚本中唯一、非空、可读的中文语义名称。
- `planeElementId` 必须来自真实的 `Plane` Element。
- `sketchId` 在退出草图后仍有效，可供后续实体特征使用。
- `createSketch` 与 `exitSketch` 必须成对出现。

#### 编辑既有草图

```javascript
Sketch.editSketch('轮廓草图_001');
// 草图几何
Sketch.exitEditSketch('轮廓草图_001');
```

- 进入和退出使用的 `featureName` 必须完全一致。
- 新建和编辑会话不能混用或嵌套。
- 当前自动建模流程不自动使用编辑会话；它只记录已确认的接口形式。

### 5.2 点：`Sketch.createPoint`

```javascript
Sketch.createPoint(x, y);
```

- `x`、`y` 是草图局部坐标。
- 创建独立草图点，不构成轮廓，也不参与当前轮廓识别。

### 5.3 直线：`Sketch.createLine`

```javascript
Sketch.createLine(new Point(startX, startY), new Point(endX, endY));
```

- 两个 `Point` 分别是起点和终点。
- 两点必须不同；相连图元应复用完全相同的公共端点数值。

### 5.4 圆：`Sketch.createCircle`

```javascript
Sketch.createCircle(new Point(centerX, centerY), new Point(edgeX, edgeY));
```

- 第一个点是圆心，第二个点是圆周上的一点，不是半径数值。
- 半径为两点距离，两点必须不同。
- 圆是独立闭合轮廓，没有可用于连接其他图元的端点。

### 5.5 中心圆弧：`Sketch.createArcByCenter`

```javascript
Sketch.createArcByCenter({
    centerPnt: new Point(centerX, centerY),
    startPnt: new Point(startX, startY),
    endPnt: new Point(endX, endY)
});
```

- 起点和终点到圆心的距离必须一致。
- 圆心不能与起点或终点重合。
- 弧向由局部坐标系右手定则唯一确定：右手拇指指向 `normal`，四指从起点转向终点的正向旋转方向就是圆弧方向。

### 5.6 拐角矩形：`Sketch.createRectangle`

```javascript
Sketch.createRectangle(new Point(startX, startY), new Point(endX, endY));
```

- 两点是矩形的一对对角顶点。
- 矩形边平行于草图局部 X、Y 轴。
- 两点的 X 或 Y 坐标不得相同，否则矩形退化。

### 5.7 中心点矩形：`Sketch.createRectangleByCenter`

```javascript
Sketch.createRectangleByCenter(new Point(centerX, centerY), new Point(vertexX, vertexY));
```

- 第一个点是中心，第二个点是任意顶点。
- 总宽和总高分别为中心到顶点对应坐标差绝对值的两倍。
- 中心与顶点的 X 或 Y 坐标不得相同。

### 5.8 直口槽：`Sketch.createStraightSlot`

```javascript
Sketch.createStraightSlot(
    new Point(startCenterX, startCenterY),
    new Point(endCenterX, endCenterY),
    new Point(radiusX, radiusY)
);
```

- 前两个点是两端半圆的圆心，不是槽的最外端点。
- `radiusPnt` 到中心线的垂直距离是槽半宽 `r`。
- 总宽为 `2r`，总长为两圆心距离加 `2r`。
- 两圆心不能重合，`radiusPnt` 不能落在中心线上。
- 复杂尺寸推导见 [槽命令详解](details/slots.md)。

### 5.9 中心点圆弧槽：`Sketch.createCenterArcSlot`

```javascript
Sketch.createCenterArcSlot(centerPnt, startPnt, endPnt, radiusPnt);
```

- 中心线圆弧由圆心、起点和终点定义。
- 起点和终点到圆心必须等距。
- 半宽必须满足 `0 < r < R`。
- 弧向遵循局部坐标系右手定则。
- 参数计算和预检见 [槽命令详解](details/slots.md)。

### 5.10 三点圆弧槽：`Sketch.createThreeArcSlot`

```javascript
Sketch.createThreeArcSlot(startPnt, endPnt, thirdPnt, radiusPnt);
```

- 参数顺序是起点、终点、弧上点、半宽参考点。
- 起点、弧上点和终点不能共线。
- 半宽必须满足 `0 < r < R`。
- 参数计算和预检见 [槽命令详解](details/slots.md)。

### 5.11 插值样条：`Sketch.createIntpCurve`

```javascript
Sketch.createIntpCurve([
    new Point(x1, y1),
    new Point(x2, y2),
    new Point(x3, y3)
]);
```

- 数组中的点是样条必须经过的点，不是控制点。
- 至少传入两个点。
- 当前只支持开放样条，首尾点不得相同。
- 复杂轮廓使用限制见 [插值样条详解](details/spline.md)。

### 5.12 参考直线：`Sketch.createReferenceLine`

```javascript
Sketch.createReferenceLine(
    new Point(startX, startY),
    new Point(endX, endY)
);
```

- 两个点分别是参考直线起点和终点，且必须不同。
- 参考直线只用于定位，不参与后续特征的轮廓识别。
- 不需要辅助定位时，优先直接通过局部坐标计算普通几何位置。

### 5.13 椭圆：`Sketch.createEllipse`

```javascript
Sketch.createEllipse(centerPnt, minorPnt, majorPnt);
```

- `centerPnt` 是椭圆中心；`minorPnt` 和 `majorPnt` 分别指定两条半径端点，均为局部坐标系中的 `Point`。
- 返回整数类型的 `EllipseId`，后续尺寸约束必须使用此实际返回值，不能猜测图元 ID。
- 支持创建中心和半轴尺寸明确的椭圆，返回图元 ID。
- 当前仅支持主轴沿草图局部 X、短轴沿局部 Y 的椭圆；其他朝向和参数组合不在支持范围内。

### 5.14 尺寸约束：`Sketch.createDimension`

尺寸驱动流程：根据草图平面建立图元并确定位置、方向初值，再引用实际返回的图元 ID，通过尺寸约束指定目标长度或半径。坐标用于定位和拾取，目标大小由尺寸值表达。支持直线目标长度和圆目标半径，无须为命中目标尺寸精算初始坐标。严格精度验收仍应测量求解后的几何；位置、方向及其他自由度需按设计意图另行约束。

#### 椭圆半轴尺寸

用 `Sketch.createPoint` 返回的中心点 ID 和 `Sketch.createEllipse` 返回的椭圆 ID，对齐到局部 X/Y 轴的椭圆半轴添加线性尺寸：

```javascript
var centerPointId = Sketch.createPoint(0, 0);
var ellipseId = Sketch.createEllipse(new Point(0, 0), new Point(0, 5), new Point(10, 0));
var majorAxisDimensionId = Sketch.createDimension({
    firstSnapId: ellipseId,
    firstPickPnt: new Point(10, 0),
    firstSnapType: 7,
    secondSnapId: centerPointId,
    secondPickPnt: new Point(0, 0),
    secondSnapType: 1,
    direction: 0,
    dimPosition: new Point(13, 2, 0),
    dimVal: new Variable(12),
    changeDimVal: 1
});
var minorAxisDimensionId = Sketch.createDimension({
    firstSnapId: ellipseId,
    firstPickPnt: new Point(0, 5),
    firstSnapType: 7,
    secondSnapId: centerPointId,
    secondPickPnt: new Point(0, 0),
    secondSnapType: 1,
    direction: 1,
    dimPosition: new Point(-3, 8, 0),
    dimVal: new Variable(6),
    changeDimVal: 1
});
```

- `firstSnapId`、`secondSnapId` 都必须来自前序草图接口实际返回的 ID。`firstSnapType: 7` 表示椭圆曲线点，`secondSnapType: 1` 表示中心草图点。
- `direction: 0` 表示水平，`direction: 1` 表示竖直；`dimVal` 使用 `Variable`，`changeDimVal: 1` 请求修改尺寸值。
- `Sketch.createDimension` 返回整数类型的尺寸约束 ID；后续读取或修改约束时只能使用该接口实际返回的 ID。
- 支持以下椭圆半轴尺寸调用形式；半轴目标值驱动效果尚未确认，不用于保证目标尺寸。
- 需要按指定半轴尺寸交付模型时，必须再从 CAD 中读回或目视确认实际求解结果；仅有约束 ID 不足以证明半轴达到目标值。

#### 点间水平、竖直和自动方向尺寸

两个当前草图点 ID 可用于点间尺寸，`firstSnapType`、`secondSnapType` 均为 `1`；`direction: 0`、`1`、`3` 分别表示水平、竖直和自动方向。普通点间目标值驱动效果尚未确认；圆心距使用下述点锚定流程。

圆心距不能直接把圆 ID 配合 `snapType: 5` 传给 `createDimension`：API 校验明确拒绝，尺寸接口只接受 `1/2/3/4/7`（第二引用另可为 `0`）。可用已验证的点锚定流程：每个圆心建立一个独立草图点，用 `PointCoincidence` 将圆心 `snapType: 5` 与该点 `snapType: 1` 关联，再对两个点调用 `createDimension`；水平用 `direction: 0`，竖直用 `direction: 1`。支持通过该流程驱动水平、竖直圆心距。

```javascript
var firstPointId = Sketch.createPoint(-7, -5);
var secondPointId = Sketch.createPoint(8, -5);
var distanceDimensionId = Sketch.createDimension({
    firstSnapId: firstPointId,
    firstPickPnt: new Point(-7, -5),
    firstSnapType: 1,
    secondSnapId: secondPointId,
    secondPickPnt: new Point(8, -5),
    secondSnapType: 1,
    direction: 0,
    dimPosition: new Point(0.5, -8, 0),
    dimVal: new Variable(15),
    changeDimVal: 1
});
```

- `firstPointId` 和 `secondPointId` 必须来自当前草图中实际创建或查询到的点；不得根据创建顺序推算 ID。
- `direction: 3` 已在点间尺寸调用中运行通过；更复杂的斜线或其他拾取类型仍未验证。

圆心距用独立中心点锚定到圆心，再约束两中心点。每个圆和点必须使用当前创建返回的 ID；竖直圆心距将尺寸方向改为 `1`：

```javascript
var centerPointA = Sketch.createPoint(-100, 0);
var circleA = Sketch.createCircle(new Point(-100, 0), new Point(-97, 0));
var centerPointB = Sketch.createPoint(-70, 0);
var circleB = Sketch.createCircle(new Point(-70, 0), new Point(-66, 0));
Sketch.addConstraint({
    constraintType: ConstraintType.PointCoincidence,
    firstSnapId: circleA,
    firstSnapType: 5,
    firstPickPnt: [-100, 0, 0],
    firstInstanceId: '',
    secondSnapId: centerPointA,
    secondSnapType: 1,
    secondPickPnt: [-100, 0, 0],
    secondInstanceId: ''
});
Sketch.addConstraint({
    constraintType: ConstraintType.PointCoincidence,
    firstSnapId: circleB,
    firstSnapType: 5,
    firstPickPnt: [-70, 0, 0],
    firstInstanceId: '',
    secondSnapId: centerPointB,
    secondSnapType: 1,
    secondPickPnt: [-70, 0, 0],
    secondInstanceId: ''
});
var centerDistanceId = Sketch.createDimension({
    firstSnapId: centerPointA,
    firstPickPnt: new Point(-100, 0),
    firstSnapType: 1,
    secondSnapId: centerPointB,
    secondPickPnt: new Point(-70, 0),
    secondSnapType: 1,
    direction: 0,
    dimPosition: new Point(-85, -10, 0),
    dimVal: new Variable(40),
    changeDimVal: 1
});
Sketch.exitSketch();
print(Evaluate.getMeasureInfo([circleA], ['']));
print(Evaluate.getMeasureInfo([circleB], ['']));
```

圆心距通过 `Evaluate.getMeasureInfo` 返回的 `Center` 坐标测量。当前 `collect_topology` 不返回这些草图曲线，不能用于核验草图圆心距。

#### 直线长度目标尺寸

引用同一条直线的终点和起点，通过 `dimVal` 指定目标长度。下例初始线长为 12，目标长度为 20：

```javascript
var lineStart = new Point(-8, 8);
var lineEnd = new Point(4, 8);
var lineId = Sketch.createLine(lineStart, lineEnd);
var lineLengthDimensionId = Sketch.createDimension({
    firstSnapId: lineId,
    firstPickPnt: lineEnd,
    firstSnapType: 3,
    secondSnapId: lineId,
    secondPickPnt: lineStart,
    secondSnapType: 2,
    direction: 3,
    dimPosition: new Point(-2, 11, 0),
    dimVal: new Variable(20),
    changeDimVal: 1
});
```

- `firstSnapType: 3` 和 `secondSnapType: 2` 分别引用终点与起点；线 ID 必须取自当前 `createLine` 的返回值。
- 端点坐标可表达起点和方向初值，不必预先精算到目标长度；`dimVal` 指定目标线长。

#### 圆半径和直径尺寸

圆的曲线 ID 与圆心点 ID 可用于圆半径目标尺寸：

```javascript
var centerPointId = Sketch.createPoint(5, -7);
var circleId = Sketch.createCircle(new Point(5, -7), new Point(9, -7));
var circleDimensionId = Sketch.createDimension({
    firstSnapId: circleId,
    firstPickPnt: new Point(9, -7),
    firstSnapType: 7,
    secondSnapId: centerPointId,
    secondPickPnt: new Point(5, -7),
    secondSnapType: 1,
    direction: 3,
    dimPosition: new Point(5, -14, 0),
    dimVal: new Variable(8),
    changeDimVal: 1,
    radiusOrDiameter: 1
});
```

- `radiusOrDiameter: 1` 表示半径尺寸，`0` 表示直径尺寸。
- 支持 `radiusOrDiameter: 1` 的圆半径目标尺寸；`radiusOrDiameter: 0` 的圆直径目标驱动当前不支持。

#### 创建直线或圆时的 `dimensionType`

`Sketch.createLine(startPnt, endPnt, 1)` 在创建直线时增加长度约束，`Sketch.createCircle(centerPnt, circlePnt, 1)` 在创建圆时增加半径约束，约束值取自初始几何。要指定与初始坐标无关的目标值，创建图元后调用 `Sketch.createDimension`，传入目标 `dimVal` 与 `changeDimVal: 1`。


### 5.15 转换边界：`Sketch.convertEdge`

```javascript
Sketch.convertEdge(edgeIds);
```

- `edgeIds` 是必填整数数组，指定待转换源对象的实际 ID。
- 将选中的源几何投影转换到当前草图平面。
- 已验证的输入包括实体边线 `id`、源草图 `entityId` 和源草图内部线 `id`；转换指定边或线时不能使用所属实体或草图的 `entityId` 代替。
- 实体边 ID 从当前有效拓扑或实际选择信息取得；源草图 ID 可使用前序 `Sketch.createSketch` 返回的 `['entityId']`；指定草图线使用实际取得的线 ID，不从草图 ID 推导。
- 源 ID 已明确且有效时可直接使用；需要按位置自动选择实体边时，按现有拓扑规则查询。`Query.getElementInfoById` 仅查询已知 ID 的详情，现有实体拓扑采集器不负责枚举草图内部线。
- `Sketch.convertEdge` 的返回值尚未确认，不依赖其返回值获取转换后的图元 ID。
- 在完整草图会话内调用；组合轮廓按[轮廓验证](details/contour-validation.md)检查，不由转换成功推定闭合有效。

以下三行分别展示三种已验证输入，按目标选择使用，不要求一起执行：

```javascript
Sketch.convertEdge([206, 170, 210]); // 实体边线 id
Sketch.convertEdge([792]); // 整个源草图的 entityId
Sketch.convertEdge([794]); // 源草图中的指定线 id
```

完整编辑会话示例：

```javascript
Sketch.editSketch('草图11');
Sketch.convertEdge([794]);
Sketch.exitEditSketch('草图11');
```

上述数字仅用于说明用户已验证的输入形式，实际任务必须使用当前文档中的真实 ID。

### 5.16 完全约束草图：`Sketch.createFullyDefineSketch`

```javascript
Sketch.createFullyDefineSketch();
```

- 无参数，用于快捷添加草图约束，使当前草图完全约束。
- 不作为每个草图的默认收尾；仅在用户明确要求完全约束状态时考虑。调用前先表达明确尺寸和关系，调用后检查约束状态及要求保留的尺寸和几何关系；不得用批量固定图元或无设计依据的关系来消除自由度、伪造参数化草图。状态无法读取时不能报告完全约束通过。
- 在完整草图会话内、目标图元创建后及退出草图前调用。
- 当前仅支持 XZ 平面矩形草图的调用形式，不支持推广到圆或复杂草图。完全约束状态仍须单独检查；返回值结构未确认，不假定返回约束 ID 或实体 ID。
- 调用成功不能单独证明草图已完全约束；需要此结果时，应检查 CAD 中的实际约束状态，并复核要求保留的尺寸和几何关系。

仅在用户明确要求草图完全约束时使用的完整会话示例（`planeElementId` 为已确认并解析局部坐标系的平面 ID）：

```javascript
var sketchResult = Sketch.createSketch('完全约束矩形草图_001', planeElementId);
var sketchId = sketchResult['entityId'];
Sketch.createRectangle(new Point(0, 0), new Point(20, 10));
Sketch.createFullyDefineSketch();
Sketch.exitSketch();
```

### 5.17 几何关系约束：`Sketch.addConstraint`

`Sketch.addConstraint` 接收对象参数，为一或两个草图元素添加关系约束。本技能只使用下表在 XY 草图中已观察到预期几何效果的组合；其他平面、图元类型或 `snapType` 组合均不在当前支持范围内。

```javascript
Sketch.createSketch('平行关系示例_001', planeElementId);
var lineA = Sketch.createLine(new Point(-120, -80), new Point(120, -80));
var lineB = Sketch.createLine(new Point(-120, 80), new Point(120, 140));
Sketch.addConstraint({
    constraintType: ConstraintType.Parallelism,
    firstSnapId: lineA,
    firstSnapType: 0,
    firstPickPnt: [0, -80, 0],
    firstInstanceId: '',
    secondSnapId: lineB,
    secondSnapType: 0,
    secondPickPnt: [0, 110, 0],
    secondInstanceId: ''
});
Sketch.exitSketch();
```


实际图元的 `firstSnapId`、`secondSnapId` 必须使用当前草图创建或查询取得的 ID；对应拾取点必须落在 XY 草图平面上的该图元。单图元方向约束的第二项使用下表注明的空占位。普通草图元素的 `firstInstanceId`、`secondInstanceId` 使用空字符串；实例化几何未列入当前支持范围。

`firstSnapType` 和 `secondSnapType` 的 API 说明如下：

| 值 | 含义 |
|---:|---|
| 0 | 无 |
| 1 | 点 |
| 2 | 始点 |
| 3 | 终点 |
| 4 | 中点 |
| 5 | 圆心 |

尺寸与关系要分开处理：线长、圆半径等数值目标使用本节 5.14 已确认的 `Sketch.createDimension` 形式；`Sketch.addConstraint` 只使用下表列出的 `ConstraintType` 与图元组合。API 说明 `addConstraint` 返回 `NULL`，不提供可依赖的约束 ID。执行前将设计意图与关系类型、图元和拾取点逐项对照；执行后检查预期几何关系。调用成功或 HTTP 200 不能单独证明约束效果。

用户提供的 UI 补全列表显示 21 个约束类型，详情标注 `filterType`；这只证明界面列出名称，不代表对应组合可用。API 示例对象字段为 `constraintType`，已支持用法按 `constraintType: ConstraintType.<名称>` 传入。

支持以下 XY 平面草图关系组合：

| `ConstraintType` | 图元组合 | `firstSnapType / secondSnapType` | 支持的效果 |
|---|---|---|---|
| `Parallelism` | 直线—直线 | `0 / 0` | 平行 |
| `Collineation` | 直线—直线 | `0 / 0` | 共线 |
| `EqualCurves` | 直线—直线 | `0 / 0` | 曲线尺寸相等 |
| `EqualLength` | 直线—直线 | `0 / 0` | 线长相等 |
| `EqualRadius` | 圆—圆 | `0 / 0` | 半径相等 |
| `FixedHorizontalDirection` | 单条直线；第二项为空占位（ID `0`） | `0 / 0` | 水平方向 |
| `FixedVerticalDirection` | 单条直线；第二项为空占位（ID `0`） | `0 / 0` | 竖直方向 |
| `FixedPoint` | 单个草图点；第二项为空占位（ID `0`） | `1 / 0` | 固定点的位置 |
| `FixedPointXCoordinates` | 单个草图点；第二项为空占位（ID `0`） | `1 / 0` | 固定点的 X 坐标 |
| `FixedPointYCoordinates` | 单个草图点；第二项为空占位（ID `0`） | `1 / 0` | 固定点的 Y 坐标 |
| `PointOnCurve` | 点—直线 | `1 / 0` | 点落在直线上 |
| `PointCoincidence` | 直线终点—直线起点 | `3 / 2` | 端点重合 |
| `PointCoincidence` | 圆心—独立草图点 | `5 / 1` | 圆心与独立点重合，点间尺寸可驱动圆心距 |
| `PointXCoordinatesCoincidence` | 点—点 | `1 / 1` | X 坐标相同，Y 坐标独立 |
| `PointYCoordinatesCoincidence` | 点—点 | `1 / 1` | Y 坐标相同，X 坐标独立 |
| `Tangency` | 直线—圆 | `0 / 0` | 相切 |
| `Tangency` | 圆—圆 | `0 / 0` | 外切 |
| `Tangency` | 圆—圆弧 | `0 / 0` | 外切，切点须位于圆弧范围内 |

图元组合、拾取类型必须与表格一致；实际图元的拾取点取自当前图元并落在 XY 草图平面上，不复用测试脚本中的旧坐标或 ID。单图元方向约束的第二项使用表中 ID `0`、snapType `0` 的空占位，不改成其他图元。`PointCoincidence` 仅支持表中列出的“第一条直线终点 + 第二条直线起点（3 / 2）”和“圆心 + 独立草图点（5 / 1）”组合；其他图元顺序与组合均不支持。所有关系约束仅支持 XY 草图平面。

本技能只支持上表明确列出的 `ConstraintType`、图元组合和 `snapType` 组合；其余枚举和组合一律**不属于本技能支持范围**，包括 `EqualCurvature`、`FixedDirection`、`Mirror`、`Offset`、`Perpendicularity`、`PointOnCurveNonePar`。建模时不得调用未列入支持表的关系、猜参数或自行试验。若设计必须依赖这些关系，说明本技能没有对应实现，并等待用户确认其他建模方案。只有目标为静态几何且不要求保留参数关系时，才可按已知尺寸和位置直接构造图元，并明确这没有建立相应关系约束。

`ConstraintType.Mirror` 和 `ConstraintType.Offset` 当前不支持。参考代码中的 `Sketch.createMirror(...)` 与 `Sketch.createOffsetCurve(...)` 是其他几何创建命令，不能作为这两个关系约束可用的依据。


## 6. 共性强制规则与注意事项

- 所有变量声明只能使用 `var`。
- 返回实体 ID 只能使用 `result['entityId']`。
- 每条可执行语句必须以英文半角分号结束。
- 函数参数、对象字面量和数组末项禁止尾随逗号。
- 每条绘制命令必须位于一个完整且不嵌套的草图会话中。
- 普通草图图元参与轮廓识别；点和参考直线不参与。椭圆是闭合轮廓。
- 有端点的图元通过复用完全相同的端点坐标连接，不使用未确认的连接命令。
- 接口执行成功不能单独证明轮廓有效；组合轮廓必须按 [轮廓验证](details/contour-validation.md) 检查。
- 不得通过猜测图元 ID、区域 ID 或未经验证的约束命令补充能力。

## 7. 详细文档读取规则

命令发现、签名、基本参数和最小用法只查本文件。出现下列情况时，再读取相应详情：

| 条件 | 必读详情 |
| --- | --- |
| 选择实体面、解释顶面/侧面或进行世界坐标换算 | [平面与局部坐标](details/plane-and-coordinates.md) |
| 使用直口槽或圆弧槽 | [槽命令详解](details/slots.md) |
| 使用插值样条组成轮廓 | [插值样条详解](details/spline.md) |
| 组合多个图元形成外轮廓、孔或平滑连接 | [轮廓验证](details/contour-validation.md) |

详情页不得登记本文件未列出的新命令。若详情与本文件的命令签名冲突，以本文件为命令入口，并停止执行直到文档得到一致修正。
