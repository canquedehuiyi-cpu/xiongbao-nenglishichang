# 实体建模

## 自然语言到构造

先识别目标和空间关系，优先选择草图与原生实体特征：底座、平台、主体、台阶和凸台优先通过相应轮廓拉伸或旋转表达；圆孔、矩形槽及其他开口优先通过草图驱动的切除表达。合并和切除优先使用原生特征已支持的 `mergeType`、`mergeSolids`、`cutSolids`，具体见 [feature-modeling.md](feature-modeling.md)。

`Solid.createBox`、`Solid.createCylinder` 及 `booleanUnion`、`booleanSubtract`、`booleanIntersect` 不作为默认首选，也不默认用于临时工具实体。仅在用户明确指定这些命令或基础实体/布尔路线，或其他能保持目标几何的已确认方案无法使用时采用；须记录替代方案、不可用原因和采用依据。用户描述圆孔或矩形槽不等于要求“创建圆柱/立方体工具再相减”。本页的接口表及示例说明满足例外条件后的调用方式，不代表路线优先级。

基础实体部分没有直接的球体原语，支持立方体、圆柱体、布尔加/减/交、圆角和倒角。拉伸、放样、扫描、旋转及其切除特征见 [feature-modeling.md](feature-modeling.md)。实体球的球形截面旋转组合尚未单独运行验证，不得把曲面结果冒充实体，也不得用其他实体强行近似。用户只要求球面曲面时，转到[曲面建模模块](../../surface-modeling/surface-modeling.md)使用其球面旋转路线。任意曲面、旋转立方体或没有已定义接口的操作仍不得强行近似；立方体没有旋转参数，必须按世界坐标轴对齐。关键尺寸、位置、孔类型、圆柱方向或空间关系缺失时，先使用项目默认约定；无法消解的多义性再询问。所有单位为 mm。

## 坐标与特征规则

`Solid.createBox` 的默认映射为：`length` 沿 Y 轴、`width` 沿 X 轴、`height` 沿 Z 轴。位置类型固定为 `2`，位置点为质心。涉及距边缘或四角定位时，基于实际包围范围计算并校验中心在目标内部。

参数表中的支持类型是当前接口的入参类型。只有支持类型中包含 `Variable` 的参数才能传入 `new Variable(...)`：`Number | Variable` 表示普通数值或变量均可，`Variable` 表示必须传入变量；`Integer`、ID、`Point` 和 `Direction` 等不包含 `Variable` 的类型不能变量化。

每个节点使用唯一、可读、非空的中文特征名，例如 `底座_001`、`切除安装孔_001`；变量仍使用英文技术命名。先建立按依赖排序的操作图，后续操作只引用实际返回的实体 ID。所有变量只用 `var`，返回 ID 只用 `result['entityId']`，函数调用、对象和数组末项均不写尾随逗号。

## 立方体与圆柱体

### `Solid.createBox`

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `positionType` | `Integer` | 固定使用 `2` |
| `positionPoint` | `Point` | 表示实体质心 |
| `length` | `Number \| Variable` | 沿 Y 轴，已验证支持变量 |
| `width` | `Number \| Variable` | 沿 X 轴，已验证支持变量 |
| `height` | `Number \| Variable` | 沿 Z 轴，已验证支持变量 |

### `Solid.createCylinder`

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `positionType` | `Integer` | 固定使用 `2` |
| `positionPoint` | `Point` | 表示实体质心 |
| `direction` | `Direction` | 两个方向点必须不同 |
| `radius` | `Number \| Variable` | 已验证支持变量 |
| `height` | `Number \| Variable` | 已验证支持变量 |

```javascript
var boxResult = Solid.createBox('box_001', {
    positionType: 2,
    positionPoint: new Point(cx, cy, cz),
    length: length,
    width: width,
    height: height
});
var boxId = boxResult['entityId'];

var cylinderResult = Solid.createCylinder('cylinder_001', {
    positionType: 2,
    positionPoint: new Point(cx, cy, cz),
    direction: new Direction(new Point(x1, y1, z1), new Point(x2, y2, z2)),
    radius: radius,
    height: height
});
var cylinderId = cylinderResult['entityId'];
```

圆柱方向的两个点必须不同，不需要归一化。

## 布尔运算

### `Solid.booleanUnion`

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `entitys` | `ElementId[]` | 参与合并的实体 ID，不支持变量 |

### `Solid.booleanSubtract`

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `entityA` | `ElementId` | 被切除的目标实体，不支持变量 |
| `entityBs` | `ElementId[]` | 工具实体数组，不支持变量 |
| `keep` | `Integer` | `0` 不保留，`2` 保留，不支持变量 |

### `Solid.booleanIntersect`

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `entitys` | `ElementId[]` | 参与求交的实体 ID，不支持变量 |
| `keep` | `Integer` | `0` 不保留，`2` 保留，不支持变量 |

```javascript
var unionResult = Solid.booleanUnion('union_001', { entitys: [entityIdA, entityIdB] });
var unionId = unionResult['entityId'];
var subtractResult = Solid.booleanSubtract('subtract_001', { entityBs: [toolEntityId], entityA: targetEntityId, keep: 0 });
var subtractId = subtractResult['entityId'];
var intersectResult = Solid.booleanIntersect('intersect_001', { entitys: [entityIdA, entityIdB], keep: 0 });
var intersectId = intersectResult['entityId'];
```

减法关系为 `entityA - entityBs`。减法和交集的 `keep: 0` 不保留相关原实体/工具，`keep: 2` 保留；仅在后续必须引用原实体时使用 `2`。布尔加不使用 `keep`。

## 圆角与倒角

圆角和倒角只作用于该操作前按需采集的当前拓扑边线 ID；任一后续几何执行后需要重新采集。详细的选边、ID 生命周期和拓扑规则见 [topology-and-features.md](topology-and-features.md)。

### `Solid.createFillet`

对当前实体的棱边构造指定半径的圆滑过渡。工程中的连续过渡常结合切线延伸使用：目标是一条连续相切边链时，先根据实际拓扑确认连接关系和预期范围，再优先评估 `tangentPropagation: 1`，由种子边沿相切连接传播处理；不要默认关闭延伸、将同一连续过渡拆成若干孤立边段。

切线延伸是选边传播方式，不改变目标半径，也不替代圆角阶段的先后依赖。多个不连通边链应分别确认种子与覆盖；只处理指定局部边、需要限制范围或各段半径不同时，可使用 `tangentPropagation: 0` 并明确列出目标边。当前没有单独的传播终点参数，必须限制到指定范围时不能假设延伸会自动停在期望位置。

执行后回查实际处理范围、遗漏、越界及端部交汇。开启延伸、返回有效实体或圆角执行成功，都不能单独证明整条目标边链已处理、曲面接缝达到 G1，或后续抽壳必然可行。

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `elements` | `ElementId[]` | 当前拓扑中的边 ID，不支持变量 |
| `radius` | `Number[]` | 与 `elements` 一一对应；当前不支持 `Variable` |
| `tangentPropagation` | `Integer` | 是否沿相切连接传播选边：`0` 关闭传播，`1` 开启传播 |

`tangentPropagation`的字段与0/1枚举已由用户确认并有有效调用。根据圆角意图显式选择，不推定省略参数的默认值，也不把该参数当作扫描的`selectChain`。实际传播范围及曲面接缝连续性须分别检查，参数为1不是整条边链已处理或曲面G1的证明。

#### 圆角调用示例

用于指定棱边的圆滑处理。`elements`传入边ID数组，`radius`逐项指定半径；命令没有单独的目标实体参数，由所选当前边确定作用对象。`tangentPropagation`为0时不自动传播选边，为1时沿相切连接传播；它不是曲面连续性验收结果。当前未登记单独的传播终点参数。

下面是独立模板，不是连续执行的完整脚本。边ID变量必须先由当前拓扑赋值，示例半径按目标尺寸替换；不能将一组旧边ID用于前一次圆角生成的新实体。

```javascript
var singleRound = Solid.createFillet('局部棱边圆角', {
    elements: [localEdgeId],
    radius: [2],
    tangentPropagation: 0
});
var singleRoundBodyId = singleRound['entityId'];
```

```javascript
var groupedRound = Solid.createFillet('边组不同半径圆角', {
    elements: [firstEdgeId, secondEdgeId],
    radius: [2, 3],
    tangentPropagation: 0
});
var groupedRoundBodyId = groupedRound['entityId'];
```

```javascript
var chainRound = Solid.createFillet('相切边链圆角', {
    elements: [chainSeedEdgeId],
    radius: [2],
    tangentPropagation: 1
});
var chainRoundBodyId = chainRound['entityId'];
```

检查`errorInfo`及非零特征/实体ID。调用成功后更新实体引用，后续操作使用新返回的`['entityId']`；需要再次选边时重新读取当前拓扑。`elements`和`radius`等长且逐项对应，数组不能引用另一状态的边ID。

一次圆角是原子操作，所选边全部成功才生成结果；失败响应不提供具体失败边。变半径及其他未登记参数不由这些示例推定支持。

### `Solid.createChamfer`

| 参数 | 支持类型 | 说明 |
|---|---|---|
| `name` | `String` | 特征名称，必须唯一、非空且可读 |
| `type` | `Integer` | 当前统一使用 `2`，不支持变量 |
| `distance` | `Number \| Variable` | 已验证支持变量 |
| `distance2` | `Number \| Variable` | 已验证支持变量 |
| `elements` | `ElementId[]` | 当前拓扑中的边 ID，不支持变量 |
| `elementTypes` | `Integer[]` | 每项固定为 `0`，不支持变量 |

```javascript
var filletResult = Solid.createFillet('fillet_001', { elements: [edgeIdA, edgeIdB], radius: [5, 10], tangentPropagation: 0 });
var filletId = filletResult['entityId'];
var chamferResult = Solid.createChamfer('chamfer_001', { type: 2, distance: 5, distance2: 5, elements: [edgeIdA, edgeIdB], elementTypes: [0, 0] });
var chamferId = chamferResult['entityId'];
```

圆角的 `elements.length === radius.length`。倒角的 `elementTypes` 每项为 `0`，且与 `elements` 等长；统一使用 `type: 2`，对称倒角令两个距离相等。非对称倒角两距离与相邻面的对应关系不可预测。圆角或倒角成功后，输入实体 ID 失效，后续操作必须使用新返回 ID。
