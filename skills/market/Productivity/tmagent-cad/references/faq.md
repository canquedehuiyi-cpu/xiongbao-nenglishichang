# 常见问题答疑（现象 → 动作）

覆盖脚本、连接器、DLL/更新、调用、试用版五类。

## 1 脚本类（status 速查见 SKILL.md）

**`com_failed`（CAD 从未运行过）** ⇒ COM 类未注册：**以管理员身份运行一次 CAD**，再重跑脚本。
**`com_failed`（CAD 已打开）** ⇒ 运行实例附加失败：脚本按「**版本名 → 裸名**」顺序挂可见实例（裸名 ProgID 的 LocalServer32 指向**最后安装的版本**，所以一律先试版本名；只认裸名的老宿主用它兜底），**不会另开后台 CAD**；仍失败就按下方「手动 NETLOAD」，或先关 CAD 让脚本用 COM 全新启动。
**`com_failed`（CAD 明明开着，却报 ROT 未注册）** ⇒ 那个实例**不是带 `/Automation` 启动的**：ZWCAD 2026 只有带该参数启动才会注册 COM ROT，否则 `GetActiveObject` 一律报 `-2147221021 操作无法使用`。脚本启动 CAD 时已自动加该参数；**手动开的实例需要关掉**，让脚本重启一次。
**`loaded_no_http`** ⇒ ①DLL 仍在初始化：稍等后 `setup_tagent.py --check` ②端口被占用：以 `%APPDATA%/TmAgent/api_address.json` 为准 ③看 CAD 命令行报错。
**`load_failed`** ⇒ 手动 NETLOAD（下）。

### 手动 NETLOAD（任选其一）

1. CAD 命令行 `NETLOAD` → 选技能根目录的 `TmAgent-ZCAD.dll`（中望）/ `TmAgent-ACAD.dll`（AutoCAD），路径见脚本输出的 `dll` 字段。
2. 加载技能根目录的 `加载dll.lsp`（命令行 `APPLOAD` 选它，或直接拖进 CAD 窗口）。

成功标志：命令行出现 **`TmAgent 加载成功! HTTP: http://127.0.0.1:9876`**。仍失败 ⇒ 把 CAD 命令行的报错原文反馈给作者。

## 2 连接器类

| 现象 | 动作 |
|---|---|
| 信任后没有 `mcp__tm-cad__*` 工具 | DLL 没加载 ⇒ 跑 `setup_tagent.py`，成功后**重启/重进会话**让工具注入 |
| 信任后仍连不上 | CAD 重启后 DLL 失效（NETLOAD 不跨会话）⇒ 重跑脚本 |
| 改了 `~/.qwenworkcn/mcp.json` 不生效 | 写配置 ≠ 生效 ⇒ 在连接器页**重新点 [信任]**，必要时重启本产品（千问办公） |
| 手动配连接器 | 见 `connector-config.md`（端点是 `/api/mcp`，**不是** `/mcp`）|

## 3 DLL 类

**上架包不含 DLL**（平台会剥离二进制）：`TmAgent-ZCAD.dll` / `TmAgent-ACAD.dll` 由 `setup_tagent.py` 先查本地、缺失时联网从 Gitee 下载（Gitee 仓库里的全量包仍含 DLL，离线场景从那里取）。
**下载失败/拿不到** ⇒ 手动放：浏览器打开 `https://gitee.com/tmtoolkit/tmagentcadaihui` → 下载对应 DLL → 放进技能根目录（含 `SKILL.md` 的目录）→ 重跑脚本。

## 4 调用类

见 SKILL.md「调用通道」（单条 MCP / 批量 REST / 兜底 COM）与 `tool-package.md`（REST 格式 ＋ 实战坑点）。

## 5 试用版启动弹窗（实测 2027/2024）

- 试用版 ZWCAD 启动先弹「中望CAD 试用版」**模态**弹窗：**20~30 秒内主窗口不出、ROT 不注册**，期间 COM 附加必失败——**不是脚本 bug**。对策：附加前轮询等待（`wait_attach` 已内置 45s）；实例始终不出主窗口 = 弹窗卡死，需人工点一下或换正式版。
- **别用 `taskkill /F` 强杀 ZWCAD**：可能留提权僵尸进程（杀不掉、占单实例锁），后续新实例秒退；清理需管理员权限或重启。
- **宿主版本陷阱**：启动的 exe 版本 ≠ 实际运行版本（试用过期会被启动器改道，实测 2026 BETA 落到 2024）。`--year 2024` 可锁定版本探测；确认实际宿主看**进程 exe 路径**，别信窗口标题。
