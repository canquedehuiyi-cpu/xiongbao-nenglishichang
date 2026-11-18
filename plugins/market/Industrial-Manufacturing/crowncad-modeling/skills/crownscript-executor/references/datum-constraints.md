# CrownScript 基准特征与约束参考

## 1. 模块描述

基准模块负责把建模任务中的参考点、参考线和参考面转换为已验证的 CrownScript `Datum` 命令，为草图、实体或其他特征提供可复用的参考对象。

基准特征属于当前文档上下文，可以独立存在，也可以被后续特征引用。它们不是每个建模任务都必须创建的默认步骤。

## 2. 能力定位与边界

### 2.1 能力范围

当前已验证的基准能力包括：

- 通过面和世界坐标点创建投影基准点；
- 通过已有直线或边线创建基准线；
- 通过已有面或基准面偏移创建基准面；
- 通过已有基准面和世界坐标点创建基准面；
- 通过已有基准面和已有边线轴创建带角度的基准面；
- 通过三个世界坐标点创建基准面。

### 2.2 模块边界

- 基准点、基准线和基准面必须按后续建模需要创建，不得默认创建三种基准的完整组合。
- 当前没有独立的通用“添加基准约束”接口；已验证能力是创建基准特征并将其作为后续接口的参考输入。
- 基准线当前只支持通过已有直线或边线创建；通过两个点、圆柱面、圆锥面或两个平面创建基准线的方式不纳入当前可用能力。
- 当前接口不能单独表达基准线与基准面的平行、垂直或相交关系。
- 本模块只负责基准特征的创建和引用规则；草图如何消费有效的 `Plane Element` 由草图模块负责，面、边和点的拓扑查询由拓扑模块负责。

## 3. 前置约束

### 3.1 操作图与依赖

基准特征必须先进入完整建模操作图，再按照依赖顺序生成脚本：

```text
完整建模意图
    -> 确定后续特征需要的参考关系
    -> 解析已有面、边线、点和特征 ID
    -> 创建必要的基准特征
    -> 保存返回的实际 ID
    -> 供后续特征引用
```

不能因为当前存在基准能力，就自动创建基准特征。基准可以引用已有模型元素，也可以引用先前创建的基准特征。

### 3.2 坐标、单位与参数

- `referencePoint`、`paralPnt` 和 `threePnts` 使用世界坐标。
- 长度、偏移距离和坐标单位为 mm；`axisAngle` 单位为度。
- `paralDis` 必须大于或等于 `0`。
- `invertNormal` 用于反转基准面法向。
- `additionalAxis` 使用 `new Axis(edgeId)`，其中 `edgeId` 必须是真实的直线或边线 ID。
- 空字符串坐标在当前运行时中按 `0` 处理；正式脚本应直接展开明确的数值坐标。

### 3.3 ID 类型

不同接口使用的 ID 类型不同，不能混用：

| 用途 | ID 来源 |
| --- | --- |
| `createPlaneByDistance.faceId` | 面元素 ID，可以是普通模型面或已有基准面 |
| `createPlaneByPlanePoint.planeId` | 已有基准面返回值中的 `id` |
| `createPlaneByPlaneAngle.planeId` | 已有基准面返回值中的 `id` |
| `createLine.referenceEntities` | 前序建模结果或拓扑查询得到的真实直线/边线 ID |
| `createPlaneByPlaneAngle.additionalAxis` | `new Axis(edgeId)` 使用的真实直线/边线 ID |

基准点返回的 `entityId` 可能为 `0`。后续引用时必须依据目标接口的参数语义选择 `id`、`entityId` 或面、边元素 ID。

### 3.4 默认基准面

已知默认基准面的面元素 ID 为：

```text
前基准面 -> 8
上基准面 -> 36
右基准面 -> 22
```

这些数值只在接口明确接受基准面或面元素引用的场景中使用。需要 `planeId` 时，仍然必须传入已有基准面返回值中的特征 `id`，不能把默认面元素 ID 当作所有接口的 `planeId`。

## 4. 命令说明

### 4.1 命令总览

| 命令 | 用途 | 主要输入 |
| --- | --- | --- |
| `Datum.createPointByProjectionPoint` | 创建投影基准点 | 面元素 ID、世界坐标点 |
| `Datum.createLine` | 创建基准线 | 直线或边线 ID |
| `Datum.createPlaneByDistance` | 创建偏移基准面 | 面元素 ID、偏移距离 |
| `Datum.createPlaneByPlanePoint` | 创建过点基准面 | 基准面 `id`、世界坐标点 |
| `Datum.createPlaneByPlaneAngle` | 创建旋转基准面 | 基准面 `id`、边线轴、角度 |
| `Datum.createPlaneByThreePoints` | 通过三点创建基准面 | 三个世界坐标点 |

以下命令中的第一个参数是特征名称。正式自动化脚本必须生成唯一、非空、可读的名称；运行时调研中使用的空字符串只适用于测试自动命名。

### 4.2 投影基准点：`Datum.createPointByProjectionPoint`

```javascript
var pointResult = Datum.createPointByProjectionPoint('投影基准点_001', {
    referenceFaceId: referenceFaceId,
    referencePoint: new Point(x, y, z)
});
```

- `referenceFaceId` 可以使用普通模型面的 ID，也可以使用基准面的 ID。
- `referencePoint` 使用世界坐标。
- 点位于目标面上时，允许创建重合基准点。
- 已观察到的返回对象包含 `id`、`name`、`entityId` 和 `instanceId`；基准点的 `entityId` 可能为 `0`。

### 4.3 基准线：`Datum.createLine`

```javascript
var lineResult = Datum.createLine('基准线_001', {
    referenceType: 3,
    referenceEntities: [edgeId],
    refInstanceIdList: []
});
```

- 当前只支持 `referenceType: 3`。
- `referenceEntities` 使用真实的直线或边线 ID。
- 线或边 ID 必须来自前序建模结果或查询接口，不能人工猜测。
- 已观察到的返回对象包含 `id`、`name`、`entityId` 和 `instanceId`。

### 4.4 偏移基准面：`Datum.createPlaneByDistance`

```javascript
var offsetPlaneResult = Datum.createPlaneByDistance('偏移基准面_001', {
    faceId: faceId,
    invertNormal: 0,
    paralDis: distance,
    reverse: 0
});
```

- `faceId` 是面元素 ID，可以使用普通模型面或已有基准面。
- `paralDis` 必须大于或等于 `0`，单位为 mm。
- `invertNormal` 控制法向反转。
- `reverse` 用于偏移方向；具体取值效果按已验证运行时处理。
- 当前实际接口不包含 `extensionType`、`extensionWidth`、`extensionHeight` 或 `extensionToObjId`。
- 已观察到的返回对象包含 `id`、`name`、`entityId` 和 `instanceId`。

### 4.5 过点基准面：`Datum.createPlaneByPlanePoint`

```javascript
var pointPlaneResult = Datum.createPlaneByPlanePoint('过点基准面_001', {
    planeId: planeId,
    invertNormal: 0,
    paralPnt: new Point(x, y, z)
});
```

- `planeId` 使用已有基准面返回值中的 `id`，不使用 `entityId`。
- `paralPnt` 使用世界坐标。
- 点可以位于参考平面上，也可以位于参考平面之外。
- 点位于参考平面上时，允许创建重合基准面。
- 当前对象参数只有 `planeId`、`invertNormal` 和 `paralPnt`，不包含 `reverse` 或扩展参数。
- 已观察到的返回对象包含 `id`、`name`、`entityId` 和 `instanceId`。

### 4.6 角度基准面：`Datum.createPlaneByPlaneAngle`

```javascript
var anglePlaneResult = Datum.createPlaneByPlaneAngle('角度基准面_001', {
    planeId: planeId,
    invertNormal: 0,
    additionalAxis: new Axis(edgeId),
    axisAngle: angle,
    reverse: 1
});
```

- `planeId` 使用已有基准面返回值中的 `id`。
- `additionalAxis` 使用 `new Axis(edgeId)`，其中 `edgeId` 是真实的直线或边线 ID。
- `axisAngle` 单位为度。
- 当前运行时默认顺时针旋转，`reverse: 1` 后为逆时针旋转。
- `invertNormal` 用于反转基准面法向。
- 已观察到的返回对象包含 `id`、`name`、`entityId` 和 `instanceId`。

### 4.7 三点基准面：`Datum.createPlaneByThreePoints`

```javascript
var threePointPlaneResult = Datum.createPlaneByThreePoints('三点基准面_001', {
    threePnts: [
        new Point(x1, y1, z1),
        new Point(x2, y2, z2),
        new Point(x3, y3, z3)
    ],
    invertNormal: 0
});
```

- `threePnts` 使用世界坐标点列表。
- 当前对象参数为 `threePnts` 和 `invertNormal`，不包含 `reverse`。
- 已验证案例中三个点共线时接口仍然可以成功，因此不能把“三点不可共线”写成当前运行时已经确认的限制。
- 已观察到的返回对象包含 `id`、`name`、`entityId` 和 `instanceId`。

## 5. 执行注意事项

- 基准特征按依赖加入完整源码；追加创建时本次脚本须具备有效输入，不默认历史变量可用。执行模式遵循[执行流程](execution-workflow.md)。
- 每次成功创建后都要检查返回结果，并保存后续接口真正需要的有效 ID；读取对象字段时使用方括号形式，例如 `result['id']` 或 `result['entityId']`。
- 如果后续操作改变模型拓扑，之前缓存的面、边和点 ID 必须重新查询或确认。
- 基准特征创建成功后，仍需根据后续草图或实体命令的参数要求选择正确的引用类型。
- 正式脚本只能使用 `var`，对象和数组末项不得使用尾随逗号，特征名必须唯一且非空。
- `createPlaneByThreePoints` 的共线案例属于当前运行时观察结果，不代表它能产生几何上有意义的平面；任务需要有效几何时仍应在本地检查点的位置关系。
- 本模块只记录已经确认的 `Datum` 命令和参数。未验证的参数、约束关系或扩展能力不得写入执行脚本。
