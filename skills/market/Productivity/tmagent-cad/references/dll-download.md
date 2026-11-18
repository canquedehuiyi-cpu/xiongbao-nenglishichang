# DLL 获取与更新（自动流程的兜底说明）

TmAgent 的 DLL 是闭源引擎。技能包**内置**了对应平台的 DLL（`TmAgent-ZCAD.dll` / `TmAgent-ACAD.dll`）；若因平台剥离或分发流程导致缺失，按以下任一方式获取后放入技能根目录（即含 `SKILL.md` 的文件夹），再运行 `setup_tagent.py` 即可自动加载。

> 正常情况无需读本文件：`setup_tagent.py` 会在本地缺失 DLL 或检测到远端有新版时自动下载。仅当**自动下载失败 / 离线 / 脚本返回 `dll_not_found`** 时按本文件处理。

## 两个平台对应文件

| 平台 | 文件名 |
|------|--------|
| 中望CAD | `TmAgent-ZCAD.dll` |
| AutoCAD | `TmAgent-ACAD.dll` |

## 方式一：脚本自动下载（默认，无需手动）

运行 `setup_tagent.py` 时，若本地缺失对应平台 DLL，脚本自动从常量 `DLL_DOWNLOAD_BASE`（`scripts/setup_tagent.py` 顶部）下载并校验：

- 地址拼接规则：`{DLL_DOWNLOAD_BASE}/{文件名}`
- 当前常量值：`https://gitee.com/tmtoolkit/tmagentcadaihui/raw/master`
  - 中望：`https://gitee.com/tmtoolkit/tmagentcadaihui/raw/master/TmAgent-ZCAD.dll`
  - AutoCAD：`https://gitee.com/tmtoolkit/tmagentcadaihui/raw/master/TmAgent-ACAD.dll`
- 支持「单文件直链」与「zip 打包」两种形式，脚本自动识别。
- **防错校验**：写入前校验文件头两字节必须为 `MZ`（Windows PE 标志），否则视为 Gitee 错误页，放弃写入并提示手动处理。

> ⚠ **下载或解压得到的 DLL 可能带 Windows“来自网络”标记**，会让 NETLOAD 直接报“加载失败”（中望只显示“加载失败”；AutoCAD 会提示 `0x80131515` / “尝试从一个网络位置加载程序集 … 请启用 loadFromRemoteSources 开关”）。
> 解决见 `faq.md` §3.1：右键 DLL → 属性 → 勾选「解除锁定」（每次下载/复制后都要重做），或给 CAD 宿主的 `*.exe.config` 加 `<loadFromRemoteSources enabled="true"/>` 后重启 CAD。

## 方式二：手动下载（离线 / 链接失效）

从 Gitee 仓库直接取对应 DLL，放入技能根目录：

- 中望：`https://gitee.com/tmtoolkit/tmagentcadaihui/raw/master/TmAgent-ZCAD.dll`
- AutoCAD：`https://gitee.com/tmtoolkit/tmagentcadaihui/raw/master/TmAgent-ACAD.dll`

放入后二选一：

1. 运行 `setup_tagent.py`（自动 NETLOAD 并创建/启用连接器）；或用 `--dll PATH` 显式指定本地路径。
2. 在 CAD 中手动 **NETLOAD** 对应 DLL（也可借助附带的 `加载dll.lsp` 辅助加载）。

## 更新检查（setup_tagent.py 内置）

- 最多**每 7 天**联网查一次 Gitee 提交记录（`api/v5/.../commits?path=<DLL名>&per_page=1`），比较提交日期与本地版本基线；节流用技能根目录状态文件 **`.dll_check.json`**（记录上次检查时间与提交日期），与是否有更新无关——查过就刷新，不会反复查。
- 远端有新版 → 先下载替换（此时未加载、文件不被占用）再 NETLOAD；无新版或查询失败（失败不写状态，下次重试）→ 沿用本地。
- 结果 JSON 带 `dll_update` 字段：`{"checked":true,"updated":true/false,"remote_commit":...}`，AI 据此在回复中告知用户本次是否换了新版。
- 想立即强制检查/重下：`python scripts/setup_tagent.py --force`。

## 验证 DLL 已就位

```bash
curl -s --max-time 4 http://localhost:9876/api/health
# {"status":"ok","cadResponding":true,"hasActiveDocument":true}  —— 表示 DLL 已 NETLOAD、HTTP 服务已起；cadResponding=false 表示 CAD 卡住（命令行被占用/有模态窗口），此时【不要下发命令】（会挂到客户端超时），先让用户在中望里按 Esc 恢复
```

若 `setup_tagent.py` 返回 `dll_not_found`，即本地缺失且在线无法取得，按本文件「方式二」处理；仍失败则检查 Gitee 链接是否过期或网络是否离线。
