# 实体建模

## 1. 模块描述

实体建模模块负责把自然语言中的三维形状、实体关系和后续特征转换为可执行、可验证的 CrownScript。优先使用草图驱动的原生实体特征、镜像和阵列；基础实体和独立布尔运算仅在用户指定该路线，或其他能保持目标几何的已确认方案不可用且记录依据后使用。草图作为实体特征的输入引用，由草图建模模块单独负责。

本文件是实体建模模块的统一入口和命令清单入口。各命令的完整参数、示例和验证状态分别保存在 `details/` 下的参考文档中；详细文档只扩展本文件已经登记的能力，不承担实体命令发现。

## 2. 能力定位与边界

本模块负责：

- 优先按目标形状选择草图驱动的基体、凸台与切除；仅在用户明确指定快捷命令路线或其他已确认方案无法使用时，选择立方体、圆柱体及独立布尔运算，并记录采用依据；
- 使用草图、截面、路径和旋转轴创建拉伸、放样、扫描、旋转及对应切除特征；
- 创建筋特征，并处理其与目标实体及导向草图的关系；
- 根据当前有效拓扑删除实体面，或删除并修补实体面；
- 对实体或同一 Body 中的特征执行镜像；
- 对实体或特征执行线性阵列和圆周阵列；
- 根据当前有效拓扑选择圆角、倒角目标边，并在后续阶段使用新的实体 ID。

当前边界：

- 当前模块只使用参考文档中列出的已确认 CrownCAD 命令和数据结构，不把未验证的参数组合描述为已验证能力；
- 本模块只处理实体，不生成曲面；拉伸、旋转、扫描、放样、填充和缝合曲面使用独立的[曲面建模模块](../surface-modeling/surface-modeling.md)。实体球的球形截面旋转组合尚未登记为已验证能力，不得把曲面结果当作有体积的实体，也不得用其他实体强行近似。用户只要求球面曲面时，按曲面模块的球面旋转路线处理；
- 草图几何、草图约束和草图平面局部坐标系由草图建模模块负责，本模块只消费真实的草图或截面引用 ID；
- 镜像和阵列的实体/特征选择、平面或轴引用必须来自真实 ID，不能根据名称或猜测生成；
- `geometryPattern` 的支持范围以对应阵列或镜像详细文档为准，未验证的组合必须明确标记。

## 3. 前置约束

### 3.1 实体、特征和引用 ID

- 创建、布尔、实体特征、镜像、圆角和倒角返回的实体 ID 使用 `result['entityId']` 读取；
- 特征镜像和特征阵列需要使用前序特征结果中的 `result['id']`；
- 草图、截面、路径和旋转轴必须使用真实引用 ID；已有线作为旋转轴时使用 `new Axis(lineId)`，不能使用该线的 `entityId`；
- `sweepPath` 始终使用数组传递路径 ID；实体边路径必须来自当前拓扑，草图路径或 3D 曲线不需要额外采集实体拓扑；
- `Query.getEntityIdByFeatureName()` 只能作为补充查询，不能代替多实体特征的精确 ID 来源。

### 3.2 坐标、单位和基础实体

- 所有长度、半径、倒角距离和坐标单位均为 mm；
- `Solid.createBox` 和 `Solid.createCylinder` 的 `positionType` 固定为 `2`，`positionPoint` 表示质心；
- 立方体默认按世界坐标轴对齐，`length` 沿 Y 轴、`width` 沿 X 轴、`height` 沿 Z 轴；
- 圆柱体方向的两个点必须不同，不需要归一化；
- 项目默认世界坐标“上方”为 +Y `(0, 1, 0)`，涉及顶面、向上面或实体平面时不得按 +Z 推断。

### 3.3 实体生命周期和拓扑

- 合并、切除、圆角、倒角以及会替换输入实体的镜像或特征操作成功后，后续操作必须使用新返回的 `entityId`；
- 布尔减中 `entityA` 是目标实体，`entityBs` 是工具实体数组；保留原实体时才使用 `keep: 2`；
- 圆角和倒角只能使用该操作前当前拓扑中的边线 ID；任何成功的后续几何执行都会使已采集拓扑失效；
- 需要实体边作为扫描路径、镜像平面或阵列轴时，必须在紧邻操作前重新获取当前拓扑；
- 进行实体特征前，草图、截面、路径、旋转轴和目标实体的依赖关系必须已经明确。

### 3.4 变量参数范围

实体接口中的变量支持以各 `details/` 参数表为准。只有支持类型中包含 `Variable` 的参数，才可以传入 `new Variable(...)`；`Number | Variable` 表示普通数值或变量均可，`Variable` 表示必须传入变量。未标注的参数不能因为底层使用数值就自行变量化。

镜像没有可用的尺寸参数；`baseType`、`mergeSolids`、实体/特征/平面/轴等枚举和 ID 不能用变量替代。线性阵列和圆周阵列的间距、实例数和角度已做接口层测试，但本次返回的阵列结果 `entityId` 为 `0`，因此暂记为几何结果待验证。筋的厚度和拔模角变量测试与普通数值基线都返回 `id/entityId: 0`，暂不纳入已验证变量参数。

## 4. 标准工作流程

```text
理解自然语言三维目标
  -> 明确实体类型、空间关系和依赖
  -> 优先建立草图/截面/路径引用节点
  -> 建立原生实体特征、镜像或阵列节点
  -> 仅在满足例外条件时建立基础实体/独立布尔节点并记录依据
  -> 按依赖关系排序并检查参数
  -> 按需获取当前拓扑和元素详情
  -> 更新完整累计源码及本次执行片段
  -> 在固定上下文中正常新增默认追加，例外按执行流程处理
  -> 检查 errorInfo、返回 ID 和实体生命周期
  -> 下一阶段沿用有效状态并按需刷新拓扑，继续维护完整源码
```

如果实体特征需要草图，先读取草图建模入口，取得真实草图 ID 后再读取相应的实体特征详细文档。镜像、圆角、倒角或实体边扫描路径依赖当前拓扑时，必须在该操作前重新采集；镜像或阵列成功后，后续实体操作按照返回结果的实体或特征 ID继续。

## 5. 完整命令清单

| 类别 | 命令或能力 | 详细文档 |
| --- | --- | --- |
| 基础实体 | `Solid.createBox`、`Solid.createCylinder` | [基础实体与布尔](details/solid-modeling.md) |
| 壳特征 | `Solid.createShell` | [特征约束与实测](details/feature-modeling.md) |
| 删除面 | `Solid.deleteFaces`：删除、删除并修补 | [删除实体面](details/delete-faces.md) |
| 布尔运算 | `Solid.booleanUnion`、`Solid.booleanSubtract`、`Solid.booleanIntersect` | [基础实体与布尔](details/solid-modeling.md) |
| 边特征 | `Solid.createFillet`、`Solid.createChamfer` | [基础实体与布尔](details/solid-modeling.md)；[拓扑与特征](details/topology-and-features.md) |
| 拉伸 | `Solid.extrude`、`Solid.extrudeCut` | [实体特征](details/feature-modeling.md) |
| 旋转 | `Solid.revolve`、`Solid.revolveCut` | [实体特征](details/feature-modeling.md) |
| 放样 | `Solid.loft`、`Solid.loftCut` | [实体特征](details/feature-modeling.md) |
| 扫描 | `Solid.sweep`、`Solid.sweepCut` | [实体特征](details/feature-modeling.md) |
| 筋 | `Solid.createRib` | [实体特征](details/feature-modeling.md) |
| 镜像 | `Solid.mirrorSolid`：实体镜像、特征镜像 | [镜像](details/mirror-modeling.md) |
| 线性阵列 | `Solid.linearPattern`：实体阵列、特征阵列 | [线性阵列](details/linear-pattern.md) |
| 圆周阵列 | `Solid.circularPattern`：实体阵列、特征阵列 | [圆周阵列](details/circular-pattern.md) |
| 拓扑查询 | 面类型、空间语义、元素详情和当前边 ID | [拓扑与特征](details/topology-and-features.md) |

## 6. 注意事项

- 所有 CrownScript 变量只使用 `var`；函数参数、对象和数组末项不写尾随逗号；
- 特征名必须在同一累计脚本中唯一、非空且可读；
- 只把已确认的命令和数据结构提交给 `executeProgram`，未验证参数必须标记为未验证；
- 基体、凸台和切除的 `mergeType`、`mergeSolids`、`cutSolids` 按实体特征详细文档选择；
- 阵列的实体/特征类型、方向或轴、实例数、间距/角度、跳过实例和 `geometryPattern` 必须按对应详细文档校验；
- 执行失败时先检查 `errorInfo`、错误行号和依赖 ID，在同一文档中修正完整累计脚本并重试，不得随机改变尺寸或位置。
