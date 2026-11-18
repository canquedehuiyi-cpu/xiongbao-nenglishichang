---
name: tmagent-cad
slug: tmagent-cad
version: 4.0.6
display_name: "CAD-TmAgent 绘图助手"
display_name_en: "TmAgent CAD Drawing Assistant"
description_zh: "中望CAD/AutoCAD 的 AI 绘图助手：用自然语言让 CAD 自动画图、改图、查询、统计、标注等。支持内置API-Key或经MCP由外部智能体驱动。触发词：中望CAD、ZWCAD、AutoCAD、CAD、DWG、制图、画图、图层、图框、自动标注。"
description_en: "ZWCAD/AutoCAD AI drawing assistant — use natural language to automatically draw, modify, query, count, and annotate CAD. Supports built-in API-Key or external agents driven via MCP. Keywords — ZWCAD, AutoCAD, CAD, DWG, drafting, drawing, layers, title block, auto-annotation."
displayName: "CAD-TmAgent 绘图助手"
summary: "中望CAD/AutoCAD 的 AI 绘图助手：用自然语言驱动CAD画图、改图、查询、统计、标注等。支持内置API-Key或经MCP由外部智能体驱动。"
description: "中望CAD/AutoCAD 的 AI 绘图助手：用自然语言让 CAD 自动画图、改图、查询、统计、标注等。支持内置API-Key或经MCP由外部智能体驱动。触发词：中望CAD、ZWCAD、AutoCAD、CAD、DWG、制图、画图、图层、图框、自动标注。"
tags: [CAD, 中望CAD, ZWCAD, AutoCAD, TmAgent, DWG, 制图, 画图, 标注, 图层, 图框, 自动标注, AI绘图, MCP]
---

# TmAgent-cad

加载中望CAD / AutoCAD 的 .NET 插件 **TmAgent**，并建好 MCP 连接器 `tm-cad`（所有 CAD 命令 = `mcp__tm-cad__*` 工具，带参数 schema 校验）。

**范围**：只做**环境配置**（NETLOAD 对应平台 DLL ＋ 创建/启用连接器）；**不做**命令用法（连上后工具自带描述，连不上用 `/api/help` 实时查）。缺功能用 `lisp_eval` 或 COM 平替，**别猜不存在的工具名**。

**运行环境**：需附加用户本机**已打开**的中望/AutoCAD 桌面程序（COM/ActiveX ＋ NETLOAD），连接器写入本产品配置 `~/.qwenworkcn/mcp.json`。**仅适用于桌面客户端**——依赖本机 GUI 与 CAD 进程，云端 Agent / 无本机 CAD 的环境无法运行。

## 环境配置（`tm-cad` 不在线时执行）

```bash
python "scripts/setup_tagent.py"
```

流程：检测平台 → 选 DLL（缺/过期自动下载，见 `references/dll-download.md`）→ COM 连接 → NETLOAD → 等 HTTP 起来 → 写连接器到 `~/.qwenworkcn/mcp.json`（`disabled:false`）。
结果 JSON 里 `dll_update.updated:true` 表示换过新版 ⇒ **要告知用户**；强制检查加 `--force`。

| 参数 | 说明 |
|------|------|
| `--check` | 只查状态，不加载 |
| `--app zwcad\|autocad` + `--year <年份>` | **版本感知一条命令**：该版本在跑就附加它；没跑就自动定位并启动，再附加＋NETLOAD。都不给：有在跑的就用它，都没有则启动默认平台最新版 |
| `--exe PATH` | 打开**任意指定**的 CAD（优先级最高；年份从路径推断）|
| `--list-cad` | 列出本机所有 CAD（平台＋年份＋exe 路径）后退出 |
| `--launch` | CAD 没开则自动启动（直起进程，**沙箱下可能会被回收**）|
| `--explorer` | 用 `explorer.exe` 代启（隐含 `--launch`）。**沙箱环境优先用这个** |
| `--dll PATH` | 手动指定 DLL 路径 |
| `--json` | JSON 输出 |
| `--no-connector` | 只加载 DLL，不碰连接器 |

**沙箱环境**：脚本报 success 但 CAD 随即消失（可能被沙箱 Job 回收）⇒ 改用 explorer 代启（等价手动双击，进程落在沙箱外），并把此方法更新入本文件，下次直接用 explorer：

```bash
python "scripts/setup_tagent.py" --app zwcad --year 2026 --explorer
```

**COM 附加**：优先 `GetActiveObject` 挂**运行中的可见实例**（不另开后台 CAD、不挂错实例），顺序＝**先裸名、再按年份/R 号试带版本名**（宿主注册习惯不同：ZWCAD 2025 认裸名、2026 只认带版本名；AutoCAD 用 R 号如 `24.1`）；仅 CAD 未运行时才 `Dispatch` 新建。CAD 开着却报 `com_failed` ⇒ 按 `references/faq.md` 手动 NETLOAD，**别反复重跑 setup**。

**首次配置**：连接器管理页对 `tm-cad` 点 **[信任]**（仅一次），详见 `references/connector-config.md`。

### 脚本 status 速查（排查细节见 `references/faq.md`）

| status | 动作 |
|--------|------|
| `already_running` / `success` | 信任后**重启/重进会话**让工具注入，再优先走 MCP |
| `dll_not_found` | 见 `references/dll-download.md` |
| `cad_not_running` | 起 CAD，或加 `--launch` / `--app` |
| `com_failed` | 从未开过 CAD ⇒ 以管理员跑一次注册 COM；已开仍报 ⇒ 按 faq 手动 NETLOAD |
| `load_failed` | 手动 NETLOAD |
| `dep_error` | `pip install pywin32` |

## 验证就绪

```bash
curl -s --max-time 4 http://localhost:9876/api/health   # {"status":"ok","cadResponding":true,"hasActiveDocument":true}
```

端口被占用则自动递增（9876→9877…），实际地址见 `%APPDATA%/TmAgent/api_address.json`。**中望与 AutoCAD 不能同时挂 TmAgent**，切平台先关另一端。

## 调用通道（单条 MCP，批量 REST）

两条通道**同源**：MCP 连接器（`/api/mcp`，带 schema 校验）与 REST（`/api/execute`，`commands` 数组，`results` 1:1 返回）。

| 场景 | 通道 |
|------|------|
| 单条 / 交互式 | **MCP**（`mcp__tm-cad__<命令>`，需已信任并注入会话）|
| 批量 / 多步（多命令或 python+CAD 并发） | **REST**：`POST /api/execute` |

```bash
curl -s -X POST http://localhost:9876/api/execute -H "Content-Type: application/json" \
  -d '{"commands":[{"command":"circle","cx":50,"cy":50,"r":20}]}'
```

- 命令细节实时查 `curl -s http://localhost:9876/api/help?command=<名>`（别硬编码）。
- **兜底**：MCP 与 REST 都不通但 CAD 已开 ⇒ COM `SendCommand` 走 CAD 原生命令（不经 TmAgent 扩展面）。
- **受信任路径**：AutoCAD 的 `(load ...)` 要求 .lsp 在 DLL 同目录 `projects/`（或其子目录）内，否则弹确认；**中望不受限**。

## 工具清单（按需，不预载）

连上 MCP ⇒ 工具自带描述；连不上但服务在跑 ⇒ `/api/help?command=<名>` 实时查；离线时看 `references/tool-inventory.md`（`sync_tools.py` 生成的快照，以实时接口为准）。
同步：`python "scripts/sync_tools.py"`（`--check` 只打印服务名/工具数）；setup 更新 DLL 后自动跑，失败（`tools_synced:false`）时手动跑。

## 参考文档

| 文件 | 内容 | 何时读 |
|------|------|--------|
| `references/faq.md` | 集中答疑（脚本/连接器/DLL/调用） | **排查任何问题时先看** |
| `references/dll-download.md` | DLL 下载/更新地址与手动兜底 | 仅 DLL 缺失或自动下载失败 |
| `references/connector-config.md` | 连接器配置（mcp.json / 信任 / 启用 / 验证） | 首次信任 / 排查连接 |
| `references/tool-package.md` | REST 格式 ＋ 实战坑点 | 连接器连不上时 |
| `references/tool-inventory.md` | 离线工具快照 | 离线检索 |
| `scripts/sync_tools.py` | 重新生成工具清单 | 自动失败或 TmAgent 升级后 |
