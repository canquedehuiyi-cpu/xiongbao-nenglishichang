---
name: lisp-programming-assistant
slug: lisp-programming-assistant
display_name: lisp编程助手
display_name_en: LISP Programming Assistant
version: 2.0.1
category: cad
platforms: [windows]
description: "AutoLISP 编程开发助手——连接 CAD 自动跑 LISP 完成初步调试。需配合 tmagent-cad 插件。报错先看「分段原文」指认的出错段，需要时加 stack=true 取行号＋调用栈；可按需调用 TmAgent 工具勘察图元、搭测试环境、回读核对。触发词：写 lisp、AutoLISP、lsp、代码。"
description_zh: "AutoLISP 编程开发助手——连接 CAD 自动跑 LISP 完成初步调试。需配合 tmagent-cad 插件。报错先看「分段原文」指认的出错段，需要时加 stack=true 取行号＋调用栈；可按需调用 TmAgent 工具勘察图元、搭测试环境、回读核对。触发词：写 lisp、AutoLISP、lsp、代码。"
description_en: "AutoLISP programming assistant - connects to CAD and runs LISP automatically for initial debugging (requires the tmagent-cad plugin). On error read the segment line to find the failing top-level expression, pass stack=true for line numbers + call stack when needed, and call TmAgent tools to inspect entities, build test environments, and cross-check."
---

# lisp编程助手（CAD-Lisp 双模式开发）

**运行环境**：本技能借助 tmagent-cad 附加用户**本机已打开**的中望/AutoCAD 桌面程序（COM/ActiveX 自动化、DCL 对话框、模拟按键），依赖桌面 GUI，**仅适用于桌面客户端**——云端 Agent / 无本机 CAD 的环境无法运行。

## 1. 连接 CAD

用已装技能 **tmagent-cad** 建立连接：

| 场景 | 动作 |
|------|------|
| 已装、CAD 未开 | `python "<tmagent-cad目录>/scripts/setup_tagent.py" --app zwcad --launch --json` |
| 已开但端口不在线 | 重跑同脚本（不带 `--launch`），附加运行中的可见实例 |
| 未安装 | 提示用户安装，不要裸走 COM |

- **只挂已打开的 CAD，禁止另开进程**（另起的是无界面后台实例）。附加失败报 `com_failed` → 按 tmagent-cad 的 `references/faq.md` 手动 NETLOAD，不反复重跑。
- ZWCAD 的 ProgID 带版本号（如 `ZWCAD.Application.2026`）；AutoCAD 用裸名。
- 端口不写死：读 `%APPDATA%/TmAgent/api_address.json` 的 `baseUrl`；就绪检查 `curl -s --max-time 4 <baseUrl>/api/health`。

## 2. 硬规则：编码与路径

- 开发期源文件 UTF-8；`push_test.py` 加载时自动转 GBK 临时副本（用后即删）；**交付前必须 `python scripts/to_ansi.py <文件.lsp>` 转 ANSI**。
- 改已交付文件：先建副本（§6），优先改 UTF-8 开发版；只有 ANSI 版时先转回 UTF-8，改完重转。

### 2.1 静态检查（可选）

写码后可跑 `python scripts/lint.py <文件.lsp>`：括号/字符串/块注释闭合（带行列）、中文全角标点、变量泄漏与受保护符号、重复 defun/`c:XXX`、交互函数走 lisp_eval 的阻塞风险（交互分支内的不算）、残留调试日志代码。

- **可能误报**：全是启发式规则，不连 CAD。提示可参考着改，**也可以跳过它直接 `push_test.py` 加载实跑**；脚本退出码恒为 0、不拦人，一切以 CAD 实际返回值为准。

### 2.2 函数库（可选）

已验证的可复用辅助函数，**一个函数一个文件、文件名就是函数名**，库在 **`D:/TmLispLib`**（由脚本决定路径）。

- **一律走脚本：不得以任何理由直接读写该目录的文件**（不要 `type`/`cat`/写文件绕过）—— 脚本负责维护索引、元数据与编码。
- **先读索引**：`Read references/_index.md`（技能内，跟着技能更新一起被删）。**文件不存在就直接 `python scripts/lib.py index` 重建**（全量扫库，一条不少；库真没东西时会直说"库是空的"）。
- **取用**：索引里看到函数名就直接 `show <函数名> [--with-deps]` —— 把**剥掉注释的源码**打到 stdout 再拼进手里的文件（要连带依赖就加 `--with-deps`）。滤掉前缀也认（`show layer-create` 能命中 `tm-layer-create`）。库太大不想读全表时，才用 `get <关键词>` 猜一个（多命中会给候选）。
- `add <文件.lsp> <函数名> --desc "一句话说明" [--tags a,b（最多 5 个）]`（同名覆盖、更新日期写当天）  
  **只有用户说"存起来"才 add**；**最终交付时**列出本轮值得入库的问他，他说哪个存哪个。  
  **值得入库 = 出过 bug、且超过 2 轮才最终修好的辅助函数**（修得快的不值钱）。搜不到就换短词（如 `csv` 而非 `csv行`）。
- 例：`add tools.lsp tm-layer-create --desc "创建图层，同名已存在就直接返回" --tags 图层,创建` —— **标签写具体领域词**（`图层`、`文字样式`），别写"通用/工具/辅助"这种谁都能挂的。
- **取出来的函数原样用，不改名**（不改就与库里那份一致、直接可用）；**一旦改过实现，函数名必须加后缀**（`tm-layer-create2`）—— 老项目里已加载过同名函数，不加后缀会互相覆盖。

## 3. 两条 LISP 通道
判据：`results[0]` **不以 `Lisp求值错误:` 开头 = 成功**（外层 success 恒 true；正常收尾常回 `""`，语法错回 `Lisp求值错误: 输入的列表有缺陷`）。

| 通道 | 用法 | 返回值 | 交互 | 用途 |
|------|------|--------|------|------|
| **lisp** | `{"command":"lisp","code":"(c:XXX)"}` | 无（异步） | 可交互 | **人工验收**：触发命令入口，用户选对象/输参数 |
| **lisp_eval** | `{"command":"lisp_eval","code":"(expr)"}` | 有（同步） | 禁用 | **智能体调试**：参数全预设、零交互，靠返回值对期望 |

lisp_eval 语义：
- 返回值 = 包装 lambda **最后一个表达式**的值；**中间报错整段中断**，后面不再执行。多段代码出错会多一行 `分段原文（N 字符）(…)` 指认出错段；加 `stack=true` 再附一行 `[调试旁听] …`（**中望**：第 N 行 ＋ 函数栈；**ACAD**：仅函数名）。
- 末位 `princ` 的值即回传；defun 返回符号名。大数据落文件，别靠返回值传。
- `/api/execute` 批量路径回传字符串**带引号**（prin1），对话路径不带。
- **单测**（可选）：一次只调一个函数的一种用法，核对返回值。
- 支持 ActiveX/COM：`(vl-load-com)` + `vlax-*`/`vla-*`；`vlax-release-object` 配对释放；交付前在 ZWCAD 实测。

铁律：
- 交互提示（`entsel`/`getfiled`/`getstring` 或缺参）会让 lisp_eval **阻塞 CAD 主线程**：后续请求排队超时（健康检查不受影响）。**解除**：`simulate_keys` 控件直投可在 DCL 上**选择、输入、确认、取消**；命令行提示用 `shortcut_name=ESC`。
- 需要 DCL 时优先动态生成到 `%TEMP%`；非复用的用完 `(vl-file-delete ...)`，删前确认是自家临时产物。
- **技能进化须经用户确认，严禁私自进化**；只修已被证实的技能/脚本错误。

### 3.1 报错定位（从便宜到贵）

| 顺序 | 手段 | 得到什么 |
|------|------|----------|
| 1 | 读返回值 | `Lisp求值错误: <原因>` |
| 2 | **段原文** | 直接指认是哪个**顶层表达式**出错 |
| 3 | **`stack=true`** | `[调试旁听]` 行：中望带行号＋函数栈；ACAD 只有函数名 |
| 4 | **加日志**（兜底） | 只用于**没有报错**的逻辑问题（没进分支 / 选不到对象 / 中间算错） |

- 提高 2、3 命中率：**步骤拆成多个顶层表达式**，别整段包进一个 `(progn ...)`。
- 第 3 步局限：代码自己接管 `*error*` 或吞错时可能拿不到栈；中望**首次**调用要等通道就绪（几秒）。
- 第 4 步模板（中间 `(princ ...)` 只打命令行、智能体拿不到）：

```lisp
(setq *xx-log* nil                            ; 排错置 T, 交付前复位 nil
      *xx-logfile* "C:/Users/xxx/debug.log")
(defun tm-log (x / lf)
  (if *xx-log*
    (progn (setq lf (open *xx-logfile* "a"))        ; 必须配套 close
           (write-line (vl-princ-to-string x) lf)   ; 先转字符串
           (close lf)))
  x)                                                ; 值透传
```

埋点：分支入口、ssget 过滤前后计数、循环序号/关键坐标、if 走向——**最后一个打出的点之后即错误区间**。流程：先 `(vl-file-delete <日志>)` → 覆盖 `(setq *xx-log* T ...)` 重跑 → `python scripts/read_log.py <日志>`。**读完必须清**：删日志文件、删/复位日志代码，交付版不得往用户磁盘写日志。

### 3.2 按需调用 TmAgent 其他工具

tmagent-cad 的 MCP 工具（`mcp__tm-cad__*`；单条走 MCP、批量走 REST）可全程穿插：

- 用户说不清图元 → 先勘察（图纸摘要/图元列表/属性/图层/选中集）再写码，别照口语猜。
- 临时造测试环境 → 测完按快照/标签精确清理，不碰用户原有图元。
- 核对结果 → 回读图纸与 LISP 返回值**双向一致才算跑通**；不一致先怀疑 LISP（回 3.1），别改期望值。
- **CAD 命令行到底显示了什么看不到时**（提示语/被拒/交互等待/NETLOAD 情况）→ `read_commandline` 带 `tail=N`，返回命令日志尾部 N 行（即完整命令行历史）。
- 工具名/参数不猜：MCP 自带描述，或查 tmagent-cad `references/tool-inventory.md`、`/api/help?command=<名>`。

## 4. 双模式规范（唯一分支点）

一个主函数，交互/调试共用；唯一分支点在主函数开头按全局模式变量取参数，其余逻辑零分支：

```lisp
;; 模式与参数变量 (全局)
(setq *xx-mode* nil)   ; 'i=交互  't=调试
(setq *xx-ent*  nil)   ; 调试模式预设参数(nil=entlast, 兜底写在主函数调试分支)
(setq *xx-csv*  (strcat (getvar "DWGPREFIX") "out.csv"))  ; 默认当前图目录

;; 主函数: 返回结果值, 未选线/取消返回 nil
(defun tm-main (/ pl ...)
  ;; ===== 唯一分支点 =====
  (if (eq *xx-mode* 'i)
    (progn
      (setq pl (car (entsel "\n选择对象: ")))
      (setq csv (if pl (getfiled "保存结果" "C:/" "csv" 1))))  ; 交互类操作只在此分支
    (setq pl (if *xx-ent* *xx-ent* (entlast))                  ; 调试: 读预设变量
          csv *xx-csv*))
  ;; ===== 以下共用, 零分支 =====
  ...)

;; 交互模式: 命令入口 —— 只设模式变量, 启动主函数
(defun c:XXX ()
  (setq *xx-mode* 'i)
  (tm-main)
  (princ))

;; 调试模式: 不写包装, 直接注入两行 (同一条 lisp_eval, 返回值=主函数值):
;;   (setq *xx-mode* 't *xx-ent* nil *xx-csv* "C:/.../out.csv")
;;   (tm-main)
```

- 交互/调试**逐步骤一一对应，只有取参来源不同**（发命令入口 ↔ 注设参；用户选对象 ↔ 读预设变量；弹窗选路径 ↔ 读预设路径）。
- `c:XXX` 只负责"设置交互模式变量"一件事。
- 调试入口默认不写 defun 包装；仅需复用入口或结构化返回时才包装。
- 辅助函数全部共用，**不允许两个平行实现**。
- **命名：辅助/主函数一律连字符**（`tm-main`、`tm-join`），不用冒号；命令入口 `c:XXX` 是 LISP 语法，保留冒号。

## 5. 通用流程

| 步骤 | 动作 | 判据 |
|------|------|------|
| 1 环境 | 无现成环境则先布置（批量 lisp_eval `entmake` 或 3.2 工具）；用户已提供则检查并读关键参数（如句柄）；先手算期望值 | 环境就绪 ＋ 句柄 |
| 2 写码 | 按 §4 写 .lsp（源 UTF-8） | — |
| 3 调试 | `python scripts/push_test.py <文件.lsp> "<§4 的两行>"`；不符期望按序排错：语法先看 lint / 段原文 / `stack=true`（2.1、3.1）→ 可选单测 → 仍定不了才加日志/3.2 回读 → 复跑循环；**必须修到跑通** | results[0] 不以 `Lisp求值错误: ` 开头；返回值与输出文件和期望一致 |
| 4 初步交付 | 转 ANSI 交付；lisp 通道发命令入口请用户验收（期间不发调试请求） | 用户确认 |
| 5 最终交付 | 按 §6 出最终形态并转 ANSI；问备份去向 | 用户可用 |

```bash
curl -s -X POST http://localhost:9876/api/execute -H "Content-Type: application/json" \
  -d '{"commands":[{"command":"lisp_eval","code":"(+ 1 2)"},{"command":"lisp_eval","code":"(load \"C:/x/a.lsp\")"}]}'
curl -s "http://localhost:9876/api/help?command=lisp_eval"
```

## 6. 交付规范

- **形态**：默认**纯净版**（收掉调试入口与调试专用全局变量）；用户要多版本维护才出**双版本**。
- **编码**：每个交付文件转 ANSI，回复里点明已验证。
- **备份**：首次交付不建副本；此后每次修改前先建 `bak/<原名>-bak<N>.lsp`（N 递增不覆盖，全部保留）；改坏了复制回原名重测再交付。
- 本轮最终交付时**问是否删 `bak/`**：同意才删，未表态则保留并列出路径。

## 7. 对话策略

- **新写** → 直接按双模式写，自动走 §5 调试，不用问。
- **改已交付代码** → 先建副本，再问是否改双模：
  > "改成双模后：我能在 CAD 里自动实测确认跑通再交付；你人工验收时经 lisp 通道启动命令，你在 CAD 照常选择输参。不改我只能静态检查语法。要改吗？"

## 8. 示例

`templates/polyint.lsp.txt`——交点统计完整可跑示例（§4 的参照实现，新功能照抄骨架换业务）。包内以 `.lsp.txt` 分发（上传白名单不含 .lsp），本地开发直接用 `.lsp`。

- 交互：lisp 通道发 `(c:POLYINT)` → 用户选多段线 → 选 CSV 路径 → 输出表格
- 调试：lisp_eval 发两行 `(setq *pi-mode* 't *pi-ent* nil *pi-csv* "C:/.../out.csv")` + `(tm-polyint)`
- 模板默认输出当前图目录 `(getvar "DWGPREFIX")`，不硬编码个人路径。

## 9. LISP 坑点汇总

**只登记需联网查询或用户纠正才得知的坑**（实测/推导可得的不记），登记须经用户确认，注明版本与日期；通用坑填 `通用`：

| CAD 版本 | 坑点 | 现象 | 解法 | 发现日期 |
|----------|------|------|------|----------|
| 通用 | 命令行 princ 输出智能体看不见 | lisp_eval 只回末表达式值 | 先看段原文、再 `stack=true` 旁听行（3.1）；仍定不了才走文件日志 | 2026-09-10 |
| 通用 | 中文日志读成乱码 | LISP 按 ANSI(GBK) 落盘 | `python scripts/read_log.py <日志>`（GBK 优先） | 2026-09-10 |
| 通用 | 交付文件编码 | UTF-8 存的 .lsp 用户 load 后乱码 | 交付前必转 ANSI：`python scripts/to_ansi.py <文件.lsp>` | 2026-09-11 |
