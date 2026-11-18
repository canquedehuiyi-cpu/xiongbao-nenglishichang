# TmAgent MCP 工具清单（自动生成）

> 由 `scripts/sync_tools.py` 从 MCP 端口 (`http://localhost:9876/api/mcp`) 实时生成。
> 服务：TmAgent-ZWCAD v2.0 · 共 **93** 个工具 / **18** 个类别。
> 调用方式：连接器信任后直接调 `mcp__tm-cad__<工具名>`；未连上时用 REST `GET /api/help?command=<名>` 取参数详情。

## 类别概览

| 类别 | 工具数 |
|------|------:|
| 编辑命令 | 18 |
| 查询命令 | 18 |
| 绘图命令 | 9 |
| 选择与工具 | 8 |
| 空间感知 | 6 |
| 杂项 | 5 |
| 几何计算 | 4 |
| 视图命令 | 4 |
| 布局与视口 | 4 |
| LISP/脚本命令 | 4 |
| 块与组 | 3 |
| 标注命令 | 2 |
| 图层命令 | 2 |
| 样式与符号表命令 | 2 |
| 文字命令 | 1 |
| 填充命令 | 1 |
| 数据导出 | 1 |
| DWG文件管理 | 1 |

## 编辑命令（18）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `transform` | 几何变换(move/copy/rotate/scale/mirror) | `action` |
| `delete` | 删除图元(必须指定目标) | （无必填） |
| `offset` | 偏移图元 | （无必填） |
| `trim` | 修剪图元 | `cutting_handle`、`target_handle` |
| `extend` | 延伸图元 | `boundary_handle`、`target_handle` |
| `fillet` | 倒圆角 | `handle1`、`handle2` |
| `chamfer` | 倒斜角 | `handle1`、`handle2` |
| `break` | 打断图元 | `point1` |
| `stretch` | 拉伸图元 | `minx`、`miny`、`maxx`、`maxy`、`dx`、`dy` |
| `align` | 对齐图元 | `src_handle`、`src1`、`src2`、`dst1`、`dst2` |
| `change_properties` | 批量修改属性(color 传 ACI 0-256 或真彩色 #RRGGBB;256=随层;未识别到任何属性会报错) | （无必填） |
| `erase_by_filter` | 按条件过滤删除(必须至少一个有效过滤条件,否则拒绝执行;单数 layer/type/handle 会自动纠正) | （无必填） |
| `undo` | 撤销(step逐步/begin组/end组) | （无必填） |
| `explode` | 炸开图元（多段线/块引用/尺寸/填充等） | （无必填） |
| `join_entity` | 连接图元（合并共线线段/圆弧为多段线） | `handles` |
| `array` | 阵列（自动分发到array_rect或array_polar） —— ★必填项随 type 变化：type=rect 需 handle(或 index)/rows/cols/row_spacing/col_spacing；type=polar 需 handle/count(center_x、center_y 缺省为0)。也可直接调用 array_rect / array_polar。 | （无必填） |
| `array_rect` | 矩形阵列 | `handle`、`rows`、`cols`、`row_spacing`、`col_spacing` |
| `array_polar` | 环形阵列 | `handle`、`center_x`、`center_y`、`count` |

## 查询命令（18）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `get_drawing_summary` | 图纸摘要统计(类型/图层/密度) | （无必填） |
| `get_drawing_fingerprint` | 图纸指纹(聚类+重复+异常诊断) | （无必填） |
| `query_entities` | 查询图元列表(图层/类型/范围过滤) | （无必填） |
| `get_entity` | 图元详情+端点连接+BFS可达 | （无必填） |
| `entity_info` | 获取图元完整DXF属性（Lisp轮询） | （无必填） |
| `entity_count` | 统计指定类型/标签/颜色的图元数量 | （无必填） |
| `find_text` | 搜索图纸中的文字(DBText+MText) | （无必填） |
| `get_bounds` | 图元包围盒(单/多/标签/全图) | （无必填） |
| `sysvar` | 读写CAD系统变量(action=get查询/set设置) | `action`、`name` |
| `query_relations` | 空间关系(临近/相交/包含) | （无必填） |
| `trace_boundary` | 在指定点追踪封闭边界 | `x`、`y` |
| `verify_result` | 对比图纸修改(快照本地diff:句柄/坐标/文字/图层/颜色) | （无必填） |
| `compare_drawings` | 跨文件对比两张图纸(A vs B:仅A/仅B/共同但不同) | `file_b` |
| `get_selection` | 获取当前选中的图元列表 | — |
| `get_dwg_info` | 获取当前图纸基本信息 | — |
| `read_commandline` | 读取CAD命令行状态(CMDACTIVE/CMDNAMES/LASTPROMPT)；tail=N 时附带命令日志尾部N行(即完整的命令行历史) | （无必填） |
| `layer_query` | 图层查询(count带图元数/detail状态) | （无必填） |
| `list_all` | 列出图元清单(文字/标注) | `kind` |

## 绘图命令（9）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `line` | 绘制两点直线 | `start`、`end` |
| `circle` | 绘制圆 | `cx`、`cy`、`r` |
| `arc` | 绘制圆弧（圆心+半径+角度） | `cx`、`cy`、`r`、`start_angle`、`end_angle` |
| `rectangle` | 绘制矩形 | `x`、`y`、`width`、`height` |
| `polyline` | 绘制多段线 | `points` |
| `ellipse` | 绘制椭圆 | `cx`、`cy`、`rx`、`ry` |
| `spline` | 绘制样条曲线 | `points` |
| `polygon` | 绘制多边形（封闭多段线）。正多边形用lisp:(command "POLYGON" sides center r) | `points` |
| `point` | 绘制点 | `x`、`y` |

## 选择与工具（8）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `selection_state` | 选中集状态(all全选/none取消/erase删除) | `action` |
| `select_region` | 按区域选择(rect/polygon/fence) | `shape` |
| `select_by_name` | 按图层名或块名选择(type=layer/block) | `type`、`name` |
| `select_filter` | 条件选择(combined组合/similar相似) | `mode` |
| `check_inside_frame` | 图元/点是否在图框内 | （无必填） |
| `get_region` | 空间聚焦查询(矩形/圆/多边形 + 相交/跨界/在内/邻近距离；view=true 直接查当前显示范围) | （无必填） |
| `entity_track` | 快照跟踪(start基准/end打标签) —— 绘制前start建基准,绘制后end自动识别新图元打标签。 | `action` |
| `entity_tag` | 标签管理(add/remove/query/select) —— ★仅支持十六进制Handle。标签持久化在DWG的XData中,关闭图纸后不丢失。选中后可用 use_selection=true 批量操作。 | `action` |

## 空间感知（6）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `connected` | 拓扑连接查询(端点重合+连通分支) | （无必填） |
| `inside` | 区域内图元查询 | （无必填） |
| `aligned` | 对齐检测 | （无必填） |
| `detect_clash` | 碰撞/重叠检测(几何求交) | （无必填） |
| `find_vacant` | 查找空地放置指定尺寸矩形 | `width`、`height` |
| `detect_islands` | 空间孤岛/聚类检测(Union-Find) | （无必填） |

## 杂项（5）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `help` | 命令文档查询 | （无必填） |
| `cross_copy` | 跨文件复制 | `source_file` |
| `save_snapshot` | 保存当前DWG快照 | — |
| `simulate_keys` | 键盘模拟 + 界面控件直投(仅兜底;不能用来画图;控件直投不需要前台/焦点，模态框也能用) —— 控件直投: 先 {action:'list'} 看控件清单，再 {control:'edit',action:'set_text',text:'x'} / {control:'text=OK',action:'click'}；关模态框用 action=click_default / click_cancel(比发 ESC 稳)；下拉框用 {control:'combo',action:'get_items'} 读选项、action=select 选中。set_text 会触发字段联动回调(action_tile)。抢前台规则: shortcut_name/key/keys 会抢前台并留在前台；给了 control（或用控件动作）则不抢前台。 | （无必填） |
| `simulate_mouse` | 鼠标模拟(仅兜底;点/拖等界面操作,不能用来画图;会把 CAD 切到前台并留在前台；改平台时用 simulate_keys 的控件直投更稳) | `action` |

## 几何计算（4）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `geo_basic` | 几何量(distance/angle/midpoint) —— 图元模式:distance用几何中心+双向采样最近点;angle/midpoint取几何中心(圆=圆心,线=中点,弧=圆心)。 | `action` |
| `geo_query` | 图元几何量(intersection/nearest/area/length) | `action` |
| `calc_area` | 面积/周长计算(单个或多图元，按真实句柄/序号定位) | （无必填） |
| `divide_curve` | 曲线等分(equal定数/measure定距/native点) | `mode` |

## 视图命令（4）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `zoom` | 缩放视图(无参数=范围缩放/带窗口=窗口缩放;x1/y1/x2/y2 之外的参数会被忽略并提示) | （无必填） |
| `pan` | 平移视图 | `dx`、`dy` |
| `screenshot` | 截取当前视口/指定模型范围/电脑屏幕区域(坐标:模型用 x1,y1,x2,y2;屏幕用 x,y,width,height) | （无必填） |
| `get_viewport` | 视口信息(双空间参数:纸面中心/尺寸/编号/锁定 + 模型视图中心/视图高/可见模型范围/比例)；有handle读该视口，无参读当前空间第一个浮动视口 | （无必填） |

## 布局与视口（4）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `layout` | 布局：列出/切换(切换时若名字不存在则先自动新建再切换；标签名与内部名均可) | （无必填） |
| `create_viewport` | 创建视口 | `layout`、`model_x1`、`model_y1`、`model_x2`、`model_y2`、`vp_x1`、`vp_y1`、`vp_x2`、`vp_y2` |
| `set_viewport` | 修改已有布局视口(view可按模型范围设;scale为CustomScale=图纸/模型,0.2即1:5) | `handle`、`action` |
| `find_frame_bounds` | 查找图框边界 | （无必填） |

## LISP/脚本命令（4）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `lisp_eval` | 同步执行Lisp —— 适用于查询/验证等需要返回值的场景；执行期间阻塞 CAD 线程。 | `code` |
| `lisp` | 异步执行Lisp(要返回值/错误定位请用 lisp_eval) —— 适用于批量操作、修改系统变量等不需要返回值的场景。优先于cad_commands执行。 | `code` |
| `script` | 执行Script(写.scr轮询结果) —— 适用于需要用Script语法的场景。会轮询等待执行完成。 | `code` |
| `python` | 执行Python(复杂计算/数据处理) —— 独立子进程,120秒超时。可用库: numpy/scipy(含KDTree/ConvexHull/Delaunay/Voronoi)/shapely(相交/缓冲/布尔运算)+标准库math/json/csv等。silent=true完全静默。【外部批量】走REST /api/execute。必要时代码内可绕过 api/mcp,经 CAD COM 端口(ZWCAD.Application, win32com 直连)直接操作/查询对象模型(遍历实体、读几何、选择集、坐标转换等端口未暴露的能力)。 | `code` |

## 块与组（3）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `block_manage` | 块管理(建块/插块/改属性/换定义/改名改基点/清理未用) —— 统一返回 JSON —— ★统一返回 JSON：成功 {ok:true,action,...}，失败 {ok:false,error}；未知 action / 未知参数一律明确报错。
★create 回 name/handle(块定义)/entities/attdefs/base/source；source=convert 时另给 ref_handle。
★insert 回 handle(新块参照)，可直接当 attr_set 的 handle 用。
★attr_set 回 targets —— 值是【从实体回读】的，不是回显入参；没匹配上的 TAG 进 attrs_missing。
★attr_set 必须指定范围(handle / index / name)，不再允许"不指定就改全图块引用"。
★replace 回 new_name/replaced/skipped；旧定义仍留着(已无引用)，要清爽再 action=purge。
★modify 改基点 = 改【定义原点 Origin】，不是改参照的插入点(插入点要用 transform action=move)。默认只改原点坐标（定义内几何不动）⇒ 新插入的参照立即按新基点定位；⚠中望实测：已存在的参照是惰性更新，不一定马上跟着变(regen 也不保证)。要"新插入外观与改前一致"传 keep_position=true（同时把定义内几何平移同一向量）。返回 base_before/base_after/affected_refs/mode。
★modify 改名返回 name=新块名 + old_name=旧名。
★purge 回 purged(数量)/names/entities_removed/skipped；name 不传=清理全部未引用块定义。
★删【图上的块参照】不要用它：select_by_name type=block + delete。 | `action`、`name` |
| `block_query` | 块查询(list列出/info详情/attrs提取属性值/attdefs列属性定义) | `action` |
| `group_op` | 组操作(create/add/remove/ungroup) —— ★仅支持十六进制Handle,不支持indices
★组(GROUP)存储位置因平台而异:中望CAD在命名对象字典(用 dictsearch 查询);AutoCAD在GROUP符号表(用 tblsearch "GROUP" 查询)。写LISP时按当前平台选用对应方式。 | `action` |

## 标注命令（2）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `dimension` | 创建标注(只画标注;要数值用geo_basic) —— 必填:aligned\|linear→x1,y1,x2,y2;radial→cx,cy,r;diametric→cx,cy,d;angular→x1,y1(顶点),x2,y2,x3,y3;ordinate→x1,y1,ref_x,ref_y。offset 带符号(负=反侧);要精确落位用 dim_pt_x/dim_pt_y;angular 走托管创建(失败会明确回报未校验) | `dim_type` |
| `leader` | 绘制引线标注 —— 要单独操作引线/文字时，请使用返回的文字句柄（不要用相邻句柄推算）。 | `points`、`text` |

## 图层命令（2）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `set_layer` | 切换到/创建图层 | （无必填） |
| `layer_manage` | 图层操作(freeze/lock/delete + create/set,兼容 set_layer) —— ★freeze/lock/delete 要求图层已存在(不自动建层);create 只建层不切当前层;set/current 等价 set_layer(建层并设为当前层)。其它 action 返回明确错误并列出可用值(不再静默当 freeze)。 | `action`、`name` |

## 样式与符号表命令（2）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `list_symbols` | 符号表清单(图层/文字样式/标注样式/线型) —— ★type 默认 layer（最常用）；多选写 "layer,text"；all=四类全列。列出的是【定义/符号表记录】，不含图元。
★图元清单用 list_all；图层图元数与开关/冻结/锁定详情用 layer_query mode=detail；改变它们用 layer_manage / style_manage。
★type 传其它值返回明确错误并列出可用值（不静默降级）。 | （无必填） |
| `style_manage` | 样式管理(新建/修改/删除/设为当前:文字样式/标注样式) —— ★参数名即 DIM 变量名小写：dimse1/dimtxt/dimclrt… 全套 79 个都能直接用（未列出的如 dimazin/dimfrac 同样有效）。
★颜色参数传 颜色名/中文名/ACI索引/ByLayer；dimtxsty 传样式名、dimblk*/dimltype* 传名字(内部查表转ID)。
★create 已存在：overwrite=false 报错、true 直接改。delete 若样式是当前样式/被图元使用/是 Standard 会被拒绝并说明原因。
★未知参数、未知 action、未知 type 一律明确报错，不静默忽略。 | `action`、`type`、`name` |

## 文字命令（1）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `draw_text` | 放置文字(单行/多行合一) | `mode`、`x`、`y`、`text` |

## 填充命令（1）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `hatch` | 填充封闭区域 | （无必填） |

## 数据导出（1）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `create_table` | 创建表格 | `data`、`insert_x`、`insert_y` |

## DWG文件管理（1）

| 工具 | 说明 | 必填参数 |
|------|------|----------|
| `dwg_op` | DWG操作(open/close/switch/new) | `action` |
