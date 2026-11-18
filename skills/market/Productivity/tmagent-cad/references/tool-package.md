# TmAgent 工具包（REST 批量主路径 ＋ 实操坑点）

> **`/api/execute` 是批量主路径**：一次 `commands` 数组发多条命令（python 与 CAD 命令并发），`results` 与 `commands` **1:1 对应**。MCP（`mcp__tm-cad__*`）每条工具只发单条；**批量 / 多步走 REST**，连不连 MCP 都推荐。

## 1 服务与命令清单

- 健康检查：`curl -s --max-time 4 http://localhost:9876/api/health`（端口回退时以 `%APPDATA%/TmAgent/api_address.json` 为准）。
- 命令细节**实时查**：`/api/help?command=<名>`（多命令 `/api/help?commands=a,b`；无参只给用法示例，不返回全量）。
- 对话式入口：`POST /api/chat`。

## 2 执行命令（REST）

```
POST /api/execute
单条: {"command":"circle","cx":50,"cy":50,"r":20}
批量: {"commands":[{"command":"set_layer","name":"dim"},{"command":"circle","cx":50,"cy":50,"r":20}]}
响应: {"success":true,"results":[...]}        # results 与 commands 1:1
```
一个用户意图的命令**合并成一次调用**。

> **绘图/插入/表格类返回统一为「类型 句柄=XX」**（如 `直线 句柄=2A1`、`多行文字 句柄=2A7`、`块 "BR" 句柄=2A8 属性2`、`表格 句柄=2A9 3x4`）⇒ **拿到句柄直接用于 trim/chamfer/transform/change_properties，不必再查**；多对象命令返回数量（如 `已镜像 3 个图元`）。

## 3 必记坑点（`/api/help` 不会说）

1. **`handle` 必须传字符串** `"29E"`，传数字会被当 `"29"`→0x29 匹配错图元；只有 index 时先查出句柄。
2. **`polyline`/`spline` 的 `points` 必须是扁平数组** `[x1,y1,x2,y2,…]`，不能 `[[x,y],…]`（报 JArray 转换错误）。
3. **HTTP 通道是 UTF-8**（响应头 `application/json; charset=utf-8`）：中文按 UTF-8 解码（旧文档写的 GB18030 有误，按 GBK 解会乱码）。
4. **编辑命令（`move`/`delete` 除外）必须显式给 `handle` 或 `index`**，无默认值。
5. **图层线宽用 lisp ActiveX 才稳**：
   `(vla-put-Lineweight (vla-Item (vla-get-Layers (vla-get-ActiveDocument (vlax-get-acad-object))) "层名") 30)`（30 = 0.30mm）。
6. **颜色：CECOLOR 生效、真彩可用**：
    - 绘制命令**读 CECOLOR**：`sysvar set CECOLOR 1` 后画线，图元组码 `62=1`；CECOLOR=BYLAYER 时无 62 组码。
    - `sysvar set` 现在是**锁外直调 API ＋ 同步真回读**：成功回 `已设置系统变量 X = Y（已回读校验）`；宿主拒绝时明确回 `设置被宿主拒绝：X 仍为 …`，并给出 `lisp_eval` 取因写法。`mode=lisp` 可强制旧的异步下发路径（此时返回「已下发…未能回读确认」）。写入前会拒绝**含换行、超长（>255 字符）、数字型变量传非数字**的取值。
    - 上色两条路都可行：创建类命令自带 `color`（ACI / 色名 / `ByLayer` / `ByBlock` / `#RRGGBB`），或画完再 `change_properties{handles:[…],color:…}` 分组改。**真彩色实测落地**：`#EE1C25` → 组码 `420=15604773`；`#00FF00` → `420=65280`。
    - **读回颜色别信 `get_entity`**：它给的是解析后的 ACI 近似值（`#00FF00`→3、`#EE1C25`→240），无法区分真彩与索引色。判真彩必须看组码 420：`lisp_eval (assoc 420 (entget (handent "句柄")))`。
    - 真彩色**图层**仍走 COM/ActiveX（见第 7 条，图层表 `entmod` 写 420 会静默失败）；图元侧不需要绕。
    - `sysvar` 的 value 现在**会**自动补引号：`BYLAYER` 可直接传，不必再写 `"256"`；但字符串型变量（DIMDSEP/CECOLOR）**不接受整数**，DIMDSEP 只收单个分隔符字符（如 `.` 或 `,`）。
7. **真彩色只能走 COM/ActiveX（实测 ZWCAD 2026 通过）**：图层表 `entmod` 写 `(420 . val)` **静默失败**（写后 `entget (tblobjname "LAYER" …)` 里没有 420 组码、`lisp_eval` 也不报错，但颜色没变）。可行路径：
    ```python
    import win32com.client as w
    app = w.GetActiveObject("ZWCAD.Application.2026")     # 两平台都须带版本号 ProgID
    col = app.GetInterfaceObject("ZWCAD.AcCmColor.2026")  # AutoCAD 用 "AutoCAD.AcCmColor.24"
    col.SetRGB(238, 28, 37)                               # 例：#EE1C25
    app.ActiveDocument.Layers("国旗红").TrueColor = col
    app.ActiveDocument.Regen(0)                           # 改完必须 Regen 才刷新
    ```
    读回校验 `L.TrueColor.Red/Green/Blue`；图元侧可 `screenshot` 存图后取像素众数，验证到「落图即 #EE1C25」。图元颜色随层时，只改图层即可覆盖其下全部填充/轮廓。

8. **读「特性面板」能读到什么（2026-10-15 实测 ZWCAD 2026）**：
    - 能读：面板标题与分类（`基本`/`几何图形`/`其他`）、对象类型（如 `多段线`）、**属性名**（颜色/图层/线型/线型比例/打印样式/线宽/透明度/厚度/顶点 X 坐标/全局宽度/面积/长度/闭合…）。途径：Win32 `EnumChildWindows` + `GetWindowText`（属性名各自是独立子窗），或 UIA 元素的 `Name`。
    - 读不到**值**：值是自绘的 —— 网格里那个 `ListBox` 样式为 `LBS_OWNERDRAWVARIABLE`（`LB_GETTEXT`/`get_items` 只返回分类标题，属性行全空），UIA 的 `ValuePattern`/`TextPattern`/`LegacyIAccessible.Value`/`ItemStatus` 也全空。
    - ⇒ 校验数据用 `entity_info`（原始 DXF：8 图层/62 ACI/420 真彩/6 线型/1 文字）。确实要看面板上的值时，只能**截图 + OCR**，且只 OCR **名字列右边界之后的那条窄带**（需自行取控件矩形）。

## 4 高频速查（免调 help）
`get_drawing_summary{minx,miny,maxx,maxy}` `query_entities{mode,…}` `get_entity{handle|index}` `get_bounds{handles}`
`line{start,end}` `circle{cx,cy,r}` `rectangle{x,y,width,height}` `polyline{points,closed}` `draw_text{mode,x,y,text,height}`
`transform{action,…}` `delete{handle|index|all}` `change_properties{handles,color|layer}` `layer_query{mode}` `sysvar{action,name,value}`
`verify_result{action}` `lisp_eval{code}` `python{code}`
其余一律 `GET /api/help?command=<名>` 定向查后再调（别拉全量）。

