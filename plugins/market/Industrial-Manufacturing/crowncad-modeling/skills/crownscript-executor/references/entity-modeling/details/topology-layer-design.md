# 拓扑分层查询与返回结构

## 选择查询深度和输出

`level` 控制实际查询深度；`output_format` 只控制业务 JSON 文件的结构，不能混为同一开关。

| 目的 | 调用 | 下载的业务文件内容 |
| --- | --- | --- |
| 浏览对象并取得当前拓扑 ID | `collect_topology(level="ids", output_format="compact")`（默认） | 轻量拓扑清单，无几何详情 |
| 测量或判断局部几何 | `query_topology_geometry` 指定 ID | 所选元素实际几何 |
| 取得全量几何 | `collect_topology(level="full", output_format="full")` | 分类图与实际几何，去掉诊断冗余 |

`level="full", output_format="compact"` 仍执行全量详情查询并保存，但下载的业务文件只有拓扑清单。只需 ID 时使用 `ids`，避免无必要的详情请求。

## 零件结构查询

PartDocument 使用一次 `GET /api/topo/d/{documentId}/v/{versionId}/getTopoStruct`，读取对象、面、环、边、顶点及原始类型。不要逐对象、面、边遍历旧接口来重复取得这些关系。

`kinds` 可选 solids、shells、curves，默认仅 solids；`entity_ids` 按所选类别限制对象。接口一次返回文档结构，过滤在本地完成；指定不存在的 ID 报错，不返回成功空集合。保留隐藏对象和 visible 值。

AssemblyDocument 保留旧查询路径，不把它当作新接口已支持；新接口错误不自动降级到旧接口。

## MCP 概况与下载

collect_topology 和 query_topology_geometry 不再内联整份对象、元素或几何数据。MCP 仅返回 operation、execution、document、counts、dataFile、已知覆盖状态和异常计数，以及 artifacts。execution=succeeded 只表示查询执行完成，不代表结构完整或几何正确；issuesReported=false 表示未提供该集合，不等于无问题。异常完整记录在下载文件中，不在概况里展开长数组。

artifacts 包含一个带缩进的业务 JSON 和一个原始证据 ZIP，各有 name、downloadUrl、expiresAt、byteSize、sha256。dataFile 指定优先读取的业务文件名：compact 为 topology-compact.json，full 为 topology-full.json，详情查询为 geometry.json。

按执行流程第5.1节下载校验后，使用本地 Python 按对象 ID、元素 ID、类型或所需字段提取，只输出提取结果或统计。不要直接将整个 JSON 用 read_text/Get-Content 展示到上下文；下载不会自动减少全文读取的 token。需要排错时再下载证据包。临时地址不得写入报告或案例。

## 本地业务数据提取

下载、校验并正式入库后，优先调用执行器的 `scripts/extract_topology.py`，支持 topology-compact.json、topology-full.json 和 geometry.json。直接读取现有 `evidence/topology.json`、`evidence/geometry.json` 或已登记的查询文件，不先复制输入。原始 REST 响应、ZIP 和诊断原图不作为通用输入；不自动解压或执行包内代码。保持当前任务工作区为工作目录；`<skill_dir>` 在执行前替换为执行器技能 `SKILL.md` 所在目录的实际绝对路径，输入路径使用正式业务文件的真实路径：

```text
python "<skill_dir>/scripts/extract_topology.py" "<业务JSON>" --summary
python "<skill_dir>/scripts/extract_topology.py" "<业务JSON>" --kind edge --owner-id 123
python "<skill_dir>/scripts/extract_topology.py" "<业务JSON>" --id 456 --id 789 --fields Geom,Curve
python "<skill_dir>/scripts/extract_topology.py" "<业务JSON>" --scope object --id 123
```

默认只显示概况；已知对象直接筛选，不将概况变为固定步骤。`--kind` 可重复，支持 solid/shell/face/edge/vertex/curve；默认 scope=element，实体/曲面对象使用 scope=object，独立曲线可具有对象及元素身份。`--id` 指所选 scope 的身份，`--owner-id` 指所属对象的 entityId。不同条件取交集，同条件多个值取并集。所属关系缺失时报告 unknownOwners，不猜测；对象 scope 的 owner-id 匹配自身。

提取结果默认留在内存或 stdout，不重定向另写 edges-extract.json 等中间文件；也可导入现有 `extract()` 直接交给测量逻辑。报告仍引用实际入库的原证据；本地筛选不冒充新 CAD 查询或伪造 artifact。确需保留的独立实际查询才使用 `evidence/queries/<用途>.json`。

`--fields` 为逗号分隔的顶层字段；完整保留选中嵌套值和 kind、id/entityId 身份，不截断、抽样或降精度。full 格式几何保留在 elementInfo 中，geometry.json 通常直接使用 Geom/Curve/Surface 等原字段，不自动重命名。结果保留源覆盖状态、sourceIssues 及异常记录 recordIssues；missingIds 表示在所选 scope/类别中未找到请求 ID（所属筛选前统计），missingFields 表示匹配记录缺少字段。空结果、部分覆盖、未知关系和明确不存在需分别判断。

退出码 0 只表示提取完成，仍须检查缺失/异常；2 表示文件、格式或参数错误。工具只离线提取，不取得新证据、不判断模型正确性，也不自动选取倒角边。默认不内联整个 JSON，复杂测量仍走测量工具。

## compact：轻量拓扑清单文件

MCP 默认 `output_format="compact"`，适用于 ids 和 full 两种查询深度。业务文件包含 document、requestedKinds、objects、items、coverage，以及实际存在的 requestedEntityIds、missingCollections、issues 等字段；这些数据不直接展开在 MCP 返回中。

- objects 保留 kind、entityId、featureId、entityName、visible 和已有成员 ID 列表。对象 type 使用字符串 solid/shell/curve；原始数字 4/5/8 留在完整证据。
- items 保留 kind、id、原始 T/G、owners 及实际取得的拓扑引用。元素省略重复 type/typeRaw。
- 面 loops 保留 Type、Coedges 的顺序和重复引用；edgeIds 使用原始出现列表。不要将去重索引当作有向环。
- 边 vertexIds 保留 getTopoStruct 返回的顺序和重复；闭合圆边允许单顶点、重复顶点或实际返回的空集合，不强制两个不同顶点。
- 不返回 Geom、Geometry、Surface、Curve、Point、控制点或节点数组，不重复携带对象 TopoData 定义。
- 缺少字段和成功查询为空不同；仅在实际存在时返回集合。issues 原样保留，空 issues 不证明结构完整；缺失必需引用时不得标为完整。

## full 与原始证据

`output_format="full"` 保留 entities/shells/curves/faces/edges/vertices 分类图、元素 elementInfo 实际几何及解析状态。业务文件不含 elementInfoRawMessage、typeResponse、lineManifest、queryBatches；它们留在证据中。

两种查询成功时只返回一份概况文本，不重复返回 structuredContent。业务 JSON 使用换行及两空格缩进，便于本地定位和人工检查；不再以 min.json 方式交付完整业务数据。

`topology.json` 保存完整原图；compact 模式另存 `topology-compact.json`。原始 REST 响应为 `rest-responses.json`，GET 日志为 `requests.jsonl`。选定的业务 JSON 可直接下载，完整原始图和诊断文件另由 artifacts ZIP 交付，按[跨机器文件交付](../../execution-workflow.md#51-跨机器文件交付与证据使用)下载、校验后引用本地证据，不代表跨模型状态仍有效。

## 独立曲线

已由用户确认：独立曲线的 entityId 本身就是可查询的元素 ID。工具以 elementId 明确表达同一身份；`items` 中 curve 的 id 也是该 ID，可直接用于 curve_ids 或 `Query.getElementInfoById`。

独立曲线不要求具有 TopoData 或嵌套 Curves/Points；缺少这些可选集合不标 partial。如果接口实际提供嵌套引用，保留真实 curveIds/pointIds，不将其替换为对象 ID，也不替换曲线本身的 elementId。端点 SP/EP 是几何坐标，不能据此伪造拓扑顶点或顶点 ID。独立曲线不等于实体边，也不扩展为草图曲线自动发现。

## 按 ID 查询几何

`query_topology_geometry` 至少提供 face_ids、edge_ids、vertex_ids、curve_ids 中一组。使用当前有效 ID，仅查询需要的数据。

- face_ids：取得实际面几何；include_face_types 按需查询类型。include_edges=true 另取面边关系，保留重复边，不展开边几何。
- edge_ids：取得实际边几何；include_vertices=true 另取顶点 ID，不查询坐标。该选择性旧关系接口当前对 ID 去重，不能据此推断端点顺序或原始重复次数；需原始关系时用 getTopoStruct。
- vertex_ids：取得真实拓扑顶点 Point，不从边端点补造坐标。
- curve_ids：使用独立曲线元素 ID，返回实际 Geom/Curve。include_vertices 不适用于 curve_ids，含曲线或未提供边时会在请求前报错。

此工具下载的 geometry.json 与 collect_topology 的轻量 compact 不同：items 保留实际几何的原字段、精度、空数组及未知类型，不裁剪控制点数组；未解析项进入 issues，详情 ID 不匹配报错。没有 Curve 不代表已确认直线，Surface 为空也不推测类型。

geometry.json 可直接下载；geometry-full.json、line-manifest.json、批次脚本及响应在 geometry-evidence.zip 中交付。按需关系 GET 的原始响应另存。未请求的关系字段省略，查询成功为空保留空数组，失败不伪装成功空结果。

## 分批、节流与有限重试

全量和按 ID 的只读元素详情查询均按每批最多 200 条顺序执行。每批响应行号从 1 开始；累计 lineManifest 和 queryBatches 保存局部行号与累计行号关系，不能直接用后一批行号覆盖前一批。

正常批间默认等待 1 秒，首批不等待。环境变量 CROWNCAD_DETAIL_BATCH_INTERVAL_SECONDS 可设置有限正数；无效值在详情请求前报错。间隔不保证满足未知服务端限流窗口。

仅生成的 `print(Query.getElementInfoById(...));` 查询可进行有限重试，每批最多 3 次（首次加 2 次），失败后分别等待 5 秒、10 秒：

- HTTP 429/500/502/503/504；
- 业务 429/502/503/504；
- 已观察到的业务 501 且消息恰为“模型数据解析异常null”。

认证、参数、脚本错误、不确定网络中断不自动重发。成功批次不重新查询；重试耗尽或不适用时停止，不返回完整成功结果。该规则只适用于只读详情，不授权建模 POST 重试。只读 GET 的瞬时错误重试仍按执行工作流。

每批证据在 batch-0001 等目录，每次尝试在 attempt-01 等子目录保存响应或脱敏 HTTP 状态和异常类型。根目录 element-query.crownscript.js/element-response.json 是最近已保存脚本/响应的兼容副本，失败时可能不属于同一次尝试；诊断应查看批次及尝试目录。HTTP 异常文件当前不保证包含原始响应正文，不将缺失证据写成已保存。

## 有效性与完成判断

同一 documentId/versionId 不保证模型未变。任何成功几何建模操作后重新取得受影响拓扑；不能复用历史 ID，也没有自动跨调用缓存或外部状态变化检测。

区分接口执行成功、结构完整、实际几何正确。coverage=queried 只说明对应查询覆盖状态；issues=[] 也不能证明尺寸、连接或无干涉。测量和浏览器观察按[验证流程](../../verification-workflow.md)执行。
