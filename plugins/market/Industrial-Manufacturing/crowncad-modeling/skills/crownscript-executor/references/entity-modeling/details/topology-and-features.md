# 拓扑与特征

## 获取当前拓扑

PartDocument 默认用 `collect_topology(level="ids", output_format="compact")`，一次 `GET /api/topo/d/{documentId}/v/{versionId}/getTopoStruct` 取得结构和原始 T/G。compact 是无几何详情的轻量清单文件，MCP 仅返回概况及业务 JSON/证据包下载信息。先下载校验，再按 ID/字段读取，不直接展示整个文件。实际几何按 ID 查询；需要全量时使用 `level="full", output_format="full"`。AssemblyDocument 保留旧查询路径，不对新接口错误自动回退。

面环类型、环内引用顺序和重复边，以及边顶点原始顺序和重复引用须保留。闭合边不能强制要求两个不同顶点。缺失必需关系和空集合分开处理，保留 issues 与 coverage，不能将执行成功等同于完整或几何正确。

按所需对象和关系选择查询范围：调用 MCP 工具 `collect_topology` 取得当前结构，调用 `query_topology_geometry` 查询所需实际几何；本地提取与覆盖检查见[分层查询](topology-layer-design.md)。

## 面类型与空间语义

零件 getTopoStruct 中的面类型来自原始 G（如 PLANE、CYLINDER），compact 元素只返回 T/G，不含重复 type/typeRaw。完整图保存标准化 type 与原始 typeRaw；按 ID 的 include_face_types 可通过已确认类型接口补查，保留实际响应。Unknown 不阻断采集；不要从 Surface 字段形态推断类型。

`elementInfo` 中实际返回的 `Geometry.Area`、`Geometry.Box`、`Surface.Norm`、`Surface.Axis`、`Surface.Origin` 和 `Surface.Radius` 可辅助自动匹配空间语义，不保证每个元素具有全部字段。项目默认上方为 +Y，顶面候选优先法向朝 +Y；用户明确指定方向时以其指定为准。`Unknown` 不得用于需要类型保证的推断。

## 实体、曲面与独立曲线

- 用 kinds 选择 solids/shells/curves，默认仅 solids；entity_ids 在所选类别中过滤，不存在的对象报错。保留隐藏对象。
- compact 对象 type 为 solid/shell/curve；实体、曲面对象ID与其面/边/顶点ID不得互换。
- 独立曲线 entityId 本身是元素 ID，工具同时标为 elementId，可直接用于 curve_ids。不要求嵌套 TopoData.Curves/Points；存在时保留其真实引用，不伪造顶点。
- 实际曲线 Geom.L、SP、EP、MP、Curve.IsClosed 等由按 ID 查询或 full 返回；compact 不含这些字段。SP/EP 不能作为拓扑顶点证据，未知字段类型按原始响应记录。
- 内部完整图保留 entities/shells/curves/faces/edges/vertices、owners、解析状态和行号证据；compact 用 objects/items 表达对象与元素关系。所有证据绑定当前文档和版本，后续建模使受影响引用失效。

创建草图时，从当前 compact 中 `G == "PLANE"` 或完整图中 `type == "Plane"` 的面选择候选。最终选定的 Plane 才调用 MCP `resolve_sketch_plane`，由它读取 CrownCAD 权威局部矩阵；不要为所有面预先查询矩阵。基准面虽然不在实体拓扑中，但可按相同的面类型与工作平面接口处理。

创建、布尔、实体特征、圆角和倒角接口返回对象中的实体 ID 是后续操作的唯一可靠来源，使用 `result['entityId']` 读取。`Query.getEntityIdByFeatureName('featureName')` 仅可补充查询；多实体特征不能用它精确定位实体。圆角和倒角成功后，输入实体 ID 立即失效，必须改用该特征的新返回 ID。不要猜测实体、面、边或点 ID。

## 特征中的 ID 区别

- `entityId`：实体 ID，用于 `mergeSolids`、`cutSolids` 和后续实体操作。
- `id`：特征 ID，用于特征镜像的 `features`；从实体特征返回对象的 `result['id']` 读取。
- `lineId`：线 ID，用于 `new Axis(lineId)`，不能替换成这条线的 `entityId`。
- 草图 ID：用于 `sketch`、`sketchs` 和 `sweepProfile`。
- 路径或曲线 ID：用于 `sweepPath`，单条路径也必须写成数组。

旋转轴可以使用已有线：

```javascript
var revolveAxis = new Axis(lineId);
```

也可以使用两个不同的点：

```javascript
var revolveAxis = new Axis(
    new Point(0, 0, 0),
    new Point(0, 1, 0)
);
```

扫描路径示例：

```javascript
var sweepPath = [pathId];
```

扫描路径来自已有实体边时，必须先获取当前拓扑。扫描路径来自草图路径或 3D 曲线时，不需要获取实体拓扑。如果已经拿到了草图内部曲线的真实 `entityId`，直接使用这个 ID。

圆角和倒角目标必须是当前拓扑中的边线 ID。一次调用是原子操作；失败响应不提供具体失败边，因此只能根据当前拓扑与明确几何约束修正，不能随机试探边或尺寸。

镜像时：

- `body` 使用真实实体 `entityId`；
- `features` 使用真实特征 `id`，不能使用实体 `entityId`；
- `mirrorPlane` 使用真实的基准面 ID 或实体平面 ID。

如果镜像平面来自实体平面，必须在镜像前确认当前拓扑。任何成功的几何操作都会使旧拓扑失效，下一次使用实体平面时必须重新查询。

圆角的 `elements` 与 `radius` 必须严格一一对应。倒角的 `elementTypes` 每项固定为 `0`，并与 `elements` 等长；统一使用 `type: 2`。对称倒角令 `distance === distance2`；非对称倒角不可指定哪一个相邻面使用哪一个距离。

草图转换边界需要按语义自动识别实体边时，也按需查询同一文档、同一版本的当前拓扑并补充所需元素详情；三种源 ID 的选择和获取统一见[草图转换边界第 5.15 节](../../sketch-modeling/sketch-modeling.md#515-转换边界sketchconvertedge)。

拓扑按需采集，而不是每条命令的固定后置步骤。在阶段、最终要求检查需要实际几何证据，或圆角、倒角需要选取当前面、边或点，扫描路径来自已有实体边，或镜像平面来自实体平面时，使用同一执行上下文先通过 REST GET 采集 ID，再以 `overwrite=false` 追加只含所需 `print(Query.getElementInfoById(realElementId));` 的查询脚本补充元素信息。扫描路径来自草图路径或 3D 曲线、镜像平面来自基准面创建结果时，不需要实体拓扑采集。查询脚本不得包含建模语句；响应行号从 1 对应脚本第一行。保留原始 `message` 字符串，解析失败时标记为原始数据而非使用 `eval`。任一成功几何建模执行都会使已采集拓扑失效；下次需要选边或使用实体平面时必须重新采集，不能依据任意后续建模操作前取得的拓扑。

面法向、面积、包围盒及面—边关系可辅助识别顶面、侧面和孔壁面，并据此定位圆角或倒角目标边。

## 用实际几何检查要求

先确认对象，再测量。对象识别、测量工具、浏览器观察及预览能力统一见[验证流程](../../verification-workflow.md)，本文件只维护拓扑获取、详情解析和有效 ID 规则。
