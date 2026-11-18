# 曲线建模

## 1. 模块描述

本模块使用独立的 `Curve` 命令创建曲线。本次登记桥接曲线：用两个桥接点及其约束生成连接曲线。用户明确该模块与 `Sketch` 无直接会话依赖；不要为了创建桥接曲线建立草图容器、进入编辑草图或退出草图。原有历史样例中的草图包络不表示必要条件。

## 2. 命令清单及共同规则

| 功能 | 命令 | 用途 |
| --- | --- | --- |
| 桥接点 | `Curve.bridgeCurvePoint` | 构造起点或终点的引用和定位参数 |
| 桥接约束 | `Curve.bridgeCurveConstraint` | 构造定位及连续方式 |
| 桥接曲线 | `Curve.createBridgeCurve` | 使用两点和两组约束创建曲线 |

- 使用当前有效的源引用，不用所属草图 ID 代替曲线 ID。
- 桥接创建独立执行；使用同一文档并维护完整累计脚本，正常新增默认追加，例外按[执行流程](../execution-workflow.md)处理，源引用须在该次执行中有效。历史草图包络下的运行证据与用户确认的独立调用方式分开记录，不宣称已完成独立调用的额外运行时测试。
- 变量只用 `var`，语句有分号，不写尾随逗号；特征名使用唯一、非空的中文名称。
- 检查执行错误，并按目标检查连接位置、形状和所需连续性；调用成功不等于完成连续性的几何检测。

## 3. 桥接曲线：`Curve.createBridgeCurve`

先构造两个桥接点和两组约束，再创建曲线。

### 3.1 桥接点

```javascript
Curve.bridgeCurvePoint(params);
```

| 参数 | 含义 | 已验证用法 |
| --- | --- | --- |
| `pointType` | 点类型 | `0`，线上点 |
| `referenceId` | 源引用 ID | 实际源曲线 ID |
| `point` | 点参数 | 按已确认目标传实际世界坐标；历史原点样例不是默认要求。本次支架使用实际连接点复现了目标曲线，仍需读回端点确认 |
| `reverse` | 点反向，仅线上点有效 | `0`，不反向 |

### 3.2 桥接约束

```javascript
Curve.bridgeCurveConstraint(params);
```

| 参数 | 含义 | 已验证用法 |
| --- | --- | --- |
| `contType` | 连续方式 | `1`，G1 相切 |
| `pointPositionType` | 桥接点定位方式 | `2`，弧长百分比 |
| `curArcLength` | 弧长或弧长百分比 | `new Variable(30)`，本例为 30% |
| `tanDirReverse` | 切线方向选择 | 示例 `0`；与点的 `reverse` 分开设置，取值不能直接映射为固定世界方向，实际结果须读回确认 |
| `weights` | 权重 | `new Variable(1)` |
| `faceAng` | 面上点的截面角度 | 本例传 `new Variable(0)` |
| `UFaceLength`、`VFaceLength` | 面上点的 U、V 百分比 | 本例均传 `new Variable(0)` |

面上点参数在本例中保留零值，不用于线上点定位。

### 3.3 创建桥接曲线

```javascript
Curve.createBridgeCurve(featureName, params);
```

| 参数 | 含义 | 已验证用法 |
| --- | --- | --- |
| `featureName` | 第一个位置参数，特征名 | 唯一、非空的中文名称 |
| `startBridgePoint`、`endBridgePoint` | 起点、终点桥接点 | 前面构造的两个桥接点 |
| `startBridgeConstraint`、`endBridgeConstraint` | 起点、终点约束 | 前面构造的两组约束 |
| `defaultEndPoint` | 是否选择默认端点 | `0`，不选择 |

独立调用模板（源引用、点坐标变量须由前序有效查询或明确几何构造取得，非完整可直接执行的脚本；历史运行样例曾含草图包络，独立性由用户确认，不因此声称本模板已经另行实测）：

```javascript
var startBridgePoint = Curve.bridgeCurvePoint({
  pointType: 0,
  referenceId: startSourceCurveId,
  point: startTargetPoint,
  reverse: 0
});
var endBridgePoint = Curve.bridgeCurvePoint({
  pointType: 0,
  referenceId: endSourceCurveId,
  point: endTargetPoint,
  reverse: 0
});

var startBridgeConstraint = Curve.bridgeCurveConstraint({
  contType: 1,
  pointPositionType: 2,
  tanDirReverse: 0,
  weights: new Variable(1),
  curArcLength: new Variable(30),
  faceAng: new Variable(0),
  UFaceLength: new Variable(0),
  VFaceLength: new Variable(0)
});
var endBridgeConstraint = Curve.bridgeCurveConstraint({
  contType: 1,
  pointPositionType: 2,
  tanDirReverse: 0,
  weights: new Variable(1),
  curArcLength: new Variable(30),
  faceAng: new Variable(0),
  UFaceLength: new Variable(0),
  VFaceLength: new Variable(0)
});

var bridgeCurveResult = Curve.createBridgeCurve('桥接曲线验证_001', {
  startBridgePoint: startBridgePoint,
  endBridgePoint: endBridgePoint,
  startBridgeConstraint: startBridgeConstraint,
  endBridgeConstraint: endBridgeConstraint,
  defaultEndPoint: 0
});

```

- 已有线上点、定位及 G1 约束生成桥接曲线的运行证据；其中历史草图包络应去除，不提升为必要依赖。G1 参数接受不等于实际连接方向与连续性验收通过。
- 示例数字 ID 仅说明结构，不能用于其他任务。当前已验证实体边作为源引用的支架组合；位置、方向、权重仍须依据具体几何和实际结果确定。
- 后续使用实际取得的 `bridgeCurveId`。2026-10-10 支架案例中创建结果返回特征 `id` 非零、`entityId:0`，但 REST `/curves` 返回独立曲线真实 `entityId`，详情查询成功。不能将零值直接当成创建失败，也不能假定特征 `id` 为曲线 ID。通过同文档当前 `/curves` 和新增特征归属确认结果；多曲线结果不要只取列表第一项。见[统一拓扑采集](../entity-modeling/details/topology-and-features.md#实体曲面与独立曲线的统一采集)。该入口不处理草图内部曲线。
- 没有创建前求值接口时，先创建再读取 `Geom.SP/EP`、控制点及可用曲线数据。端点错误先处理定位，方向错误再处理方向，形状问题再分析权重；方向编辑后重新核对端点，避免把多个因素的作用混为一谈。
- 只对已确认的三次 Bézier 表示使用首末控制段计算端部切向；一般 B 样条须考虑节点、权重、阶次和参数范围。接口采用源引用和方向设置，不需要自行添加切向向量参数。
- 面上点、其他连续方式和其他定位方式尚未验证。不以用户手动调整作为以后自动构造的前置条件。
