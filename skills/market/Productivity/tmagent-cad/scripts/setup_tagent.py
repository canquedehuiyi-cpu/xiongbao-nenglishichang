#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# --- output encoding fallback (chinese text garbles under GBK console) ---
# Python may pick GBK(936) for stdout while the terminal decodes as UTF-8 (or vice versa).
def _tmagent_fix_output_encoding():
    import sys as _sys
    for _name in ("stdout", "stderr"):
        _stream = getattr(_sys, _name, None)
        if _stream is None:
            continue
        _enc = (getattr(_stream, "encoding", "") or "").lower().replace("-", "")
        if _enc in ("utf8", "utf8mb4"):
            continue
        _rc = getattr(_stream, "reconfigure", None)
        if callable(_rc):
            try:
                _rc(encoding="utf-8", errors="replace")
                continue
            except Exception:
                pass
        try:
            _stream.errors = "replace"
        except Exception:
            pass


_tmagent_fix_output_encoding()

"""
TmAgent 自动加载脚本
=====================
检查 CAD 运行状态，自动将对应平台的 TmAgent DLL（中望 TmAgent-ZCAD.dll /
AutoCAD TmAgent-ACAD.dll）通过 NETLOAD 加载到 CAD 进程。
随 tmagent-cad 技能分发。技能包不含 DLL（平台会剥离二进制），
setup 会先从本地查找，找不到时自动从 DLL_DOWNLOAD_BASE 在线下载，
或提示用户手动放置。实现一键环境配置。
DLL 获取细节（下载地址、MZ 校验、手动 NETLOAD）见 references/dll-download.md。

用法:
    python setup_tagent.py              # 自动检测并加载（含自动配置 MCP 连接器）
    python setup_tagent.py --check      # 仅检查状态，不加载
    python setup_tagent.py --dll PATH   # 指定 DLL 路径
    python setup_tagent.py --app zwcad|autocad   # 指定目标 CAD 平台
    python setup_tagent.py --json       # 纯 JSON 输出（供智能体解析）
    python setup_tagent.py --launch     # CAD 未运行时自动启动
    python setup_tagent.py --explorer   # 用 explorer 代启 CAD（沙箱环境下必需，隐含 --launch）
    python setup_tagent.py --no-connector  # 跳过 MCP 连接器自动配置
    python setup_tagent.py --force        # 强制重新下载 DLL（忽略本地缓存）

流程:
    1. 检查 TmAgent 是否已在运行（discovery 文件 + HTTP 健康检查）
    2. 若已运行 → 直接返回成功 + 使用指引
    3. 查找 TmAgent.dll（最多每 7 天查一次远端更新，有新版先替换再加载）
    4. 检查 CAD 进程是否运行 → 未运行则尝试启动（--launch）
    5. COM 连接 CAD
    6. 通过 NETLOAD 命令加载 DLL
    7. 轮询等待 TmAgent HTTP 服务启动
    8. 自动在本平台（千问办公）mcp.json（~/.qwenworkcn/mcp.json）中创建/启用 tm-cad MCP 连接器
    9. 输出结果和使用指引（提示用户首次点击 [信任]）
"""

import os
import sys
import json
import time
import socket
import datetime
import subprocess
import importlib
import urllib.request
import urllib.error

# ─── 配置 ────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

# TmAgent DLL 文件名（按 CAD 平台区分版本，随技能打包内置）
DLL_BY_APP = {
    "zwcad":   "TmAgent-ZCAD.dll",   # 中望CAD
    "autocad": "TmAgent-ACAD.dll",   # AutoCAD
}
DLL_GENERIC = "TmAgent.dll"          # 兼容旧版单文件命名

# DLL 在线下载基址（技能包不含 DLL 时，setup 自动据此下载对应版本）
# 留空 "" 表示禁用自动下载，仅提示用户手动放置。
# 脚本会在基址后【自动拼接】平台对应的文件名：
#   中望CAD -> <BASE>/TmAgent-ZCAD.dll
#   AutoCAD -> <BASE>/TmAgent-ACAD.dll
# 因此 BASE 应指向包含这两个 DLL 的目录（如 Gitee raw/master 分支直链）。
# 该分支直链为永久地址，不会过期；若改用带签名/时效的附件链接需自行处理。
DLL_DOWNLOAD_BASE = "https://gitee.com/tmtoolkit/tmagentcadaihui/raw/master"

def get_dll_search_paths(app_key=None):
    """返回 DLL 搜索路径（按优先级排序），按平台选对应版本 DLL。

    平台明确时只搜该平台 DLL + 通用名，【绝不回退到另一平台版本】
    （否则如 autocad 平台会误命中本地已有的 TmAgent-ZCAD.dll，
    把中望 DLL 加载进 AutoCAD）。仅当平台未知(None, 自动探测)时才跨版本兜底。
    """
    names = []
    if app_key and app_key in DLL_BY_APP:
        names.append(DLL_BY_APP[app_key])
        names.append(DLL_GENERIC)          # 仅兼容旧版单文件命名
    else:
        names += list(DLL_BY_APP.values())  # 平台未知：跨版本探测兜底
        names.append(DLL_GENERIC)
    paths = []
    for name in names:
        paths.append(os.path.join(SKILL_DIR, name))          # 技能根目录
        paths.append(os.path.join(SCRIPT_DIR, "lib", name))   # scripts/lib/
        paths.append(os.path.join(SKILL_DIR, "dll", name))    # dll/ 子目录
    # 常见安装目录
    paths += [
        r"C:\Program Files\TmAgent\TmAgent.dll",
        r"D:\TmAgent\TmAgent.dll",
    ]
    return paths

# TmAgent discovery 文件路径
DISCOVERY_PATH = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")),
    "TmAgent", "api_address.json"
)

# 支持的 CAD 软件
CAD_APPS = {
    "zwcad": {
        "process_names": ["ZWCAD.exe"],
        "com_prog_id": "ZWCAD.Application",
        "display_name": "中望CAD (ZWCAD)",
        "reg_paths": [
            (r"SOFTWARE\ZWCAD\ZWCAD", "Path"),
            (r"SOFTWARE\WOW6432Node\ZWCAD\ZWCAD", "Path"),
        ],
        # ZWCAD 实际注册在版本化键下: SOFTWARE\ZWSOFT\ZWCAD\<年份>\zh-CN\Location
        "reg_enum_roots": [r"SOFTWARE\ZWSOFT\ZWCAD"],
        "reg_value_name": "Location",
        "reg_sub_suffixes": ["", "zh-CN"],
        "common_paths": [
            r"C:\Program Files\ZWSOFT\ZWCAD\ZWCAD.exe",
            r"C:\Program Files\ZWCAD\ZWCAD.exe",
        ],
        "scan_roots": [
            r"C:\Program Files\ZWSOFT",
            r"D:\Program Files\ZWSOFT",
            r"C:\Program Files (x86)\ZWSOFT",
            r"D:\Program Files (x86)\ZWSOFT",
            r"C:\Program Files\ZWCAD",
            r"D:\ZWCAD",
        ],
    },
    "autocad": {
        "process_names": ["acad.exe"],
        "com_prog_id": "AutoCAD.Application",
        "display_name": "AutoCAD",
        "reg_paths": [
            (r"SOFTWARE\Autodesk\AutoCAD", "AcadLocation"),
            (r"SOFTWARE\WOW6432Node\Autodesk\AutoCAD", "AcadLocation"),
        ],
        "reg_enum_roots": [r"SOFTWARE\Autodesk\AutoCAD"],
        "reg_two_level": True,   # AutoCAD 结构: R##.# -> ACAD-xxxx[:locale] -> AcadLocation/Location
        "reg_value_names": ["AcadLocation", "Location"],
        "reg_value_name": "AcadLocation",
        "reg_sub_suffixes": [""],
        # R 版本号 -> 产品年份（实测本机 2026-09: R19.1=2014, R24.1=2022, R24.2=2023）
        "year_map": {
            "R19.0": "2013", "R19.1": "2014",
            "R24.0": "2021", "R24.1": "2022", "R24.2": "2023", "R24.3": "2024",
            "R25.0": "2025", "R25.1": "2026",
            "R26.0": "2026", "R26.1": "2027",
        },
        "common_paths": [
            r"C:\Program Files\Autodesk\AutoCAD\acad.exe",
        ],
        "scan_roots": [
            r"C:\Program Files\Autodesk",
            r"D:\Program Files\Autodesk",
            r"D:\Program Files\Autodesk\AutoCAD",
        ],
    },
}

# HTTP 服务等待超时（秒）
HTTP_WAIT_TIMEOUT = 30
HTTP_POLL_INTERVAL = 1

# DLL 更新检查：最多每 7 天联网查一次（状态文件记录上次检查时间，与是否有更新无关）
DLL_UPDATE_CHECK_DAYS = 7
DLL_CHECK_STATE = os.path.join(SKILL_DIR, ".dll_check.json")
GITEE_API = "https://gitee.com/api/v5/repos/tmtoolkit/tmagentcadaihui/commits"

# ─── MCP 连接器自动配置 ─────────────────────────────────────────────────

# 本平台（千问办公）MCP 连接器名称与端点
MCP_CONNECTOR_NAME = "tm-cad"
MCP_CONNECTOR_URL = "http://localhost:9876/api/mcp"


def get_mcp_config_path():
    """获取本平台（千问办公）mcp.json 路径（跨平台：~/.qwenworkcn/mcp.json）"""
    return os.path.join(os.path.expanduser("~"), ".qwenworkcn", "mcp.json")


def ensure_connector_config():
    """
    在本平台 mcp.json（~/.qwenworkcn/mcp.json）中自动创建 / 启用 tm-cad MCP 连接器。

    返回 (action, detail):
      "created"      — 新建了连接器配置
      "enabled"      — 配置已存在但被禁用，已改为启用 (disabled:false)
      "already_ok"   — 配置已存在且已启用，无需改动
      "skipped"      — 用户用 --no-connector 跳过
      "error"        — 写入失败
    """
    if "--no-connector" in sys.argv:
        return "skipped", "用户指定跳过 (--no-connector)"

    cfg_path = get_mcp_config_path()
    try:
        config = {"mcpServers": {}}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                    if raw:
                        config = json.loads(raw)
            except (json.JSONDecodeError, IOError):
                config = {"mcpServers": {}}
        if not isinstance(config.get("mcpServers"), dict):
            config["mcpServers"] = {}

        servers = config["mcpServers"]
        desired = {
            "type": "streamableHttp",
            "url": MCP_CONNECTOR_URL,
            "disabled": False,
        }
        existing = servers.get(MCP_CONNECTOR_NAME)

        if existing is None:
            servers[MCP_CONNECTOR_NAME] = desired
            changed = True
            action = "created"
        else:
            changed = False
            if existing.get("disabled", True):
                existing["disabled"] = False
                changed = True
            if existing.get("type") != "streamableHttp":
                existing["type"] = "streamableHttp"
                changed = True
            if existing.get("url") != MCP_CONNECTOR_URL:
                existing["url"] = MCP_CONNECTOR_URL
                changed = True
            action = "enabled" if changed else "already_ok"

        if changed:
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return action, cfg_path
        return action, cfg_path
    except Exception as e:
        return "error", str(e)


# ─── 日志输出 ─────────────────────────────────────────────────────────

_json_mode = "--json" in sys.argv

def log(msg, level="INFO"):
    """输出日志（--json 模式下静默）"""
    if _json_mode:
        return
    prefix = {
        "INFO": "  ",
        "OK":   "[OK] ",
        "WARN": "[!]  ",
        "ERR":  "[X]  ",
        "STEP": "->  ",
    }
    print(f"{prefix.get(level, '  ')}{msg}")


def output_result(result):
    """输出 JSON 结果"""
    print(json.dumps(result, ensure_ascii=False, indent=2))


def print_banner():
    """打印横幅"""
    if _json_mode:
        return
    print()
    print("=" * 60)
    print("  TmAgent 自动加载脚本")
    print("=" * 60)
    print()


def print_guide(base_url=None, app_name=None, connector_action=None):
    """打印使用指引"""
    if _json_mode:
        return
    mcp_url = "http://localhost:9876/api/mcp"
    if base_url:
        mcp_url = base_url.rstrip("/") + "/api/mcp"

    print("=" * 60)
    print("  TmAgent 环境配置完成!")
    print("=" * 60)
    print()
    print("  现在可以通过以下两种方式使用:")
    print()
    print("  方式一: TmAgent MCP 连接器 (适配中望CAD / AutoCAD)")
    print("  " + "-" * 40)
    if connector_action in ("created", "enabled"):
        print("  [已自动写入连接器配置] MCP URL:")
    elif connector_action == "already_ok":
        print("  [连接器配置已就绪] MCP URL:")
    else:
        print("  [手动添加] MCP URL:")
    print(f"  {mcp_url}")
    print("  首次使用请在产品的「连接器」管理页面")
    print("  对 tm-cad (TmAgent) 点击 [信任] 启用 (仅此一次)")
    print("  之后即可直接调用 mcp__tm-cad__* 工具")
    print()
    print("  方式二: 直接使用技能绘图")
    print("  " + "-" * 40)
    print('  在对话中直接说:')
    print('  "在CAD中画一个半径50的圆"')
    print('  "查询当前图纸的图层数量"')
    print('  "截图看看当前图纸"')
    print()
    print("=" * 60)

# ─── 依赖管理 ─────────────────────────────────────────────────────────

def ensure_module(module_name, pip_name=None):
    """确保 Python 模块可用，缺失则自动安装"""
    pip_name = pip_name or module_name
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        log(f"{pip_name} 未安装，正在自动安装...", "WARN")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            importlib.import_module(module_name)
            log(f"{pip_name} 安装完成", "OK")
            return True
        except Exception as e:
            log(f"{pip_name} 安装失败: {e}", "ERR")
            return False

# ─── TmAgent 检测 ────────────────────────────────────────────────────

def read_discovery():
    """读取 TmAgent discovery 文件"""
    if not os.path.exists(DISCOVERY_PATH):
        return None
    try:
        with open(DISCOVERY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def check_http_health(base_url, timeout=3):
    """检查 TmAgent HTTP 服务健康状态"""
    try:
        url = base_url.rstrip("/") + "/api/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except Exception:
        return False, None


def is_tagent_running():
    """检查 TmAgent 是否已在运行"""
    # 方式1: 读 discovery 文件
    info = read_discovery()
    if info:
        base_url = info.get("base_url") or info.get("baseUrl", "")
        if base_url:
            ok, data = check_http_health(base_url)
            if ok:
                return True, base_url, info
    # 方式2: 尝试默认端口
    for port in [9876, 9877, 9878]:
        base_url = f"http://127.0.0.1:{port}"
        ok, data = check_http_health(base_url)
        if ok:
            return True, base_url, info
    return False, None, info


def wait_for_http(base_url, timeout=HTTP_WAIT_TIMEOUT):
    """轮询等待 TmAgent HTTP 服务启动"""
    start = time.time()
    while time.time() - start < timeout:
        ok, _ = check_http_health(base_url, timeout=2)
        if ok:
            return True
        time.sleep(HTTP_POLL_INTERVAL)
    return False

# ─── DLL 路径解析 ─────────────────────────────────────────────────────

# 本次运行是否真的下载过 DLL（供 maybe_sync_tools 判断要不要同步工具清单）。
# 覆盖两种触发下载的情形：①check_dll_update 发现远端新版；②本地无 DLL 首次下载（含 --force）。
# 沿用本地（网络失败/内容非 DLL/本地已有）时不置位，避免白跑一次同步。
_DLL_JUST_DOWNLOADED = False


def download_dll(app_key, force=False):
    """从 DLL_DOWNLOAD_BASE 下载对应平台 DLL 到技能根目录，返回本地路径或 None。

    关键修复：在基址后【自动拼接】平台文件名（<BASE>/TmAgent-ZCAD.dll 等），
    因此 Gitee raw 目录直链也能正确下载（旧版请求裸目录导致 HTTP 400）。

    - 本地已存在且未指定 --force：直接返回本地，不联网（不比对版本）。
    - 本地缺失、或指定 --force：联网下载；若网络不可用且本地已有则沿用本地。
    """
    if not DLL_DOWNLOAD_BASE or app_key not in DLL_BY_APP:
        return None
    fname = DLL_BY_APP[app_key]
    dest = os.path.join(SKILL_DIR, fname)
    url = DLL_DOWNLOAD_BASE.rstrip("/") + "/" + fname   # 拼接文件名（修复点）
    # 本地已有且非强制：直接复用，不联网
    if os.path.isfile(dest) and not force:
        return dest
    log(f"从在线地址获取: {url}", "INFO")
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TmAgent-Setup/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        if os.path.isfile(dest):
            log(f"无法连接 Gitee ({e}), 沿用本地 {fname}", "WARN")
            return dest
        log(f"自动下载失败: {e}", "WARN")
        log("通俗说明: 电脑暂时连不上 Gitee (断网/网络拦截/链接失效)。"
            "可用浏览器打开 https://gitee.com/tmtoolkit/tmagentcadaihui 手动下载 DLL 放入本目录, "
            "详见 references/faq.md 的报错对照表", "INFO")
        return None
    # 防错：DLL 文件头两字节必为 'MZ'，否则可能是 Gitee 错误页
    if data[:2] != b"MZ":
        if os.path.isfile(dest):
            log("下载内容非有效 DLL（疑似网页），沿用本地", "WARN")
            return dest
        log("下载到的不是有效 DLL（疑似网页而非二进制），已跳过", "WARN")
        return None
    # 原子写入（先临时文件再替换，避免半截文件）
    tmp = dest + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    if os.path.isfile(dest):
        os.remove(dest)
    os.rename(tmp, dest)
    log(f"已下载到: {dest} ({len(data)} bytes)", "OK")
    global _DLL_JUST_DOWNLOADED
    _DLL_JUST_DOWNLOADED = True
    return dest


def find_dll(app_key=None, custom_path=None, force=False):
    """查找 TmAgent DLL（按平台选版本；本地没有或指定 --force 时自动下载）。"""
    paths = get_dll_search_paths(app_key)
    if custom_path:
        paths.insert(0, custom_path)
    for path in paths:
        if os.path.isfile(path):
            if force:
                continue   # --force: 忽略本地缓存，强制重新下载
            return os.path.abspath(path)
    # 本地未找到（或强制更新）→ 尝试在线下载
    if app_key and DLL_DOWNLOAD_BASE:
        downloaded = download_dll(app_key, force=force)
        if downloaded:
            return downloaded
    return None


def check_dll_update(app_key, dll_path):
    """最多每 7 天查一次 Gitee 提交记录，远端有新版则先替换再加载。

    调用时机在 NETLOAD 之前 —— 此时 DLL 尚未加载进 CAD，文件未被占用，
    替换安全；替换后后续流程直接加载新 DLL，无需重启。
    节流用状态文件 .dll_check.json（上次检查时间），与本地 mtime 无关，
    避免远端无更新时每次运行都重复查 API。
    返回 (dll_path, update_info)；update_info 供 JSON 结果透出给 AI：
      None                  — 本次未检查（节流内 / 不适用）
      {"checked":True, "updated":True/False, "remote_commit": iso} — 查过
    """
    fname = os.path.basename(dll_path)
    if fname not in DLL_BY_APP.values():
        return dll_path, None   # 自定义路径/通用名不参与检查
    try:
        with open(DLL_CHECK_STATE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        state = {}
    now = time.time()
    if now - state.get("last_check", 0) < DLL_UPDATE_CHECK_DAYS * 86400:
        return dll_path, None   # 7 天内查过，不联网
    log(f"距上次更新检查超过 {DLL_UPDATE_CHECK_DAYS} 天，检查远端版本...", "INFO")
    url = f"{GITEE_API}?path={fname}&per_page=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TmAgent-Setup/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            commits = json.loads(resp.read().decode("utf-8"))
        remote_date = datetime.datetime.fromisoformat(
            commits[0]["commit"]["author"]["date"].replace("Z", "+00:00"))
    except Exception as e:
        log(f"更新检查失败 ({e})，沿用本地 DLL（下次运行再试）", "WARN")
        return dll_path, None   # 查询失败不写状态，下次重试
    # 基线：状态文件里上次见过的提交日期，无则退回本地 mtime
    baseline_ts = os.path.getmtime(dll_path)
    if state.get("last_commit"):
        try:
            baseline_ts = datetime.datetime.fromisoformat(
                state["last_commit"].replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    # 查询成功即刷新状态（无论是否有更新）
    new_state = {"last_check": now, "last_commit": remote_date.isoformat()}
    try:
        with open(DLL_CHECK_STATE, "w", encoding="utf-8") as f:
            json.dump(new_state, f)
    except OSError:
        pass
    if remote_date.timestamp() <= baseline_ts:
        log("远端无更新，沿用本地 DLL", "OK")
        return dll_path, {"checked": True, "updated": False,
                          "remote_commit": remote_date.isoformat()}
    log(f"发现新版 DLL (远端提交 {remote_date:%Y-%m-%d})，下载替换...", "INFO")
    try:
        new_path = download_dll(app_key, force=True)
    except PermissionError:
        log("DLL 文件被占用 (CAD 可能已加载它)，沿用本地，请关 CAD 后重试", "WARN")
        return dll_path, {"checked": True, "updated": False,
                          "remote_commit": remote_date.isoformat()}
    return (new_path or dll_path), {"checked": True, "updated": bool(new_path),
                                    "remote_commit": remote_date.isoformat()}

def maybe_sync_tools(base_url, dll_update):
    """DLL 变动后自动同步工具清单（新 DLL 可能新增/删减命令）。

    触发条件（满足其一即可）：
      ① dll_update["updated"] —— check_dll_update 发现远端新版并替换；
      ② _DLL_JUST_DOWNLOADED  —— 本地无 DLL 首次下载 / --force 强制重下。
    沿用本地（网络失败、内容非 DLL、本地已有）时不触发，避免白跑一次。
    仅在 HTTP 已就绪时执行；失败只警告不阻塞。
    返回 True/False/None（None=未触发）。
    """
    if not (bool(dll_update and dll_update.get("updated")) or _DLL_JUST_DOWNLOADED):
        return None
    log("DLL 已变更（更新或新下载），同步工具清单...", "STEP")
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPT_DIR, "sync_tools.py"),
             "--base", base_url.rstrip("/") + "/api/mcp"],
            capture_output=True, text=True, timeout=60)
        ok = r.returncode == 0
        log("工具清单已重新生成" if ok
            else f"工具清单同步失败: {(r.stderr or '').strip()[:120]}", "OK" if ok else "WARN")
        return ok
    except Exception as e:
        log(f"工具清单同步失败: {e}", "WARN")
        return False


# ─── CAD 进程检测 ─────────────────────────────────────────────────────

def _has_visible_window(pid):
    """进程是否有可见主窗口（过滤 ZWCAD 启动器存根: 1MB 左右、无窗口、不可交互）"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        found = []
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @CB
        def cb(hwnd, _):
            p = ctypes.c_void_p()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value == pid and user32.IsWindowVisible(hwnd):
                if user32.GetWindowTextLengthW(hwnd) > 0:
                    found.append(True)
                    return False
            return True

        user32.EnumWindows(cb, None)
        return bool(found)
    except Exception:
        return True  # 检测失败时保守返回 True

def find_cad_process():
    """查找正在运行的 CAD 进程（只统计有可见主窗口的实例, 忽略存根进程）"""
    def _filtered(app_key, pids):
        for pid in pids:
            if _has_visible_window(pid):
                return True
        return False

    # 方式1: psutil（优先）
    try:
        import psutil
        running = []
        for app_key, config in CAD_APPS.items():
            pids = []
            for proc in psutil.process_iter(["pid", "name"]):
                proc_name = (proc.info["name"] or "").lower()
                if proc_name in [t.lower() for t in config["process_names"]]:
                    pids.append(proc.info["pid"])
            if pids and _filtered(app_key, pids) and app_key not in running:
                running.append(app_key)
        return running
    except ImportError:
        pass

    # 方式2: tasklist（回退）
    #  注意: tasklist 按系统 ANSI 代码页输出(中文 Windows = cp936), 且控制台可能处于
    #  UTF-8 模式 ⇒ 不给 errors 兜底时可能抛 UnicodeDecodeError, 被下面 except 吞掉,
    #  表现为“CAD 明明在运行却报 cad_not_running”。这里用 errors="replace" 保证不炸。
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10, errors="replace"
        )
        running = []
        for app_key, config in CAD_APPS.items():
            pids = []
            for line in result.stdout.splitlines():
                parts = [p.strip('"') for p in line.split('","')]
                if parts and parts[0].lower() in [t.lower() for t in config["process_names"]]:
                    try:
                        pids.append(int(parts[1]))
                    except (IndexError, ValueError):
                        pass
            if pids and _filtered(app_key, pids) and app_key not in running:
                running.append(app_key)
        return running
    except Exception:
        return []


def get_cad_exe_path(app_key, year=None):
    """获取 CAD 可执行文件路径（注册表 + 常见路径 + 目录扫描兜底）

    year: 指定 ZWCAD 版本年份（如 "2024"），只命中该版本的注册表键。
    注意: 启动的 exe 版本不保证等于实际运行版本 —— ZWCAD 试用过期/BETA 版
    可能弹窗退出或由启动器改启其他版本（本机实测 2026 BETA 过期后落到 2024）。
    """
    config = CAD_APPS[app_key]
    exe_name = os.path.basename(config["common_paths"][0])

    # 1) 注册表：固定键 + 版本化键枚举（版本号大的优先）
    try:
        import winreg

        def _enum_keys(hive, path):
            try:
                key = winreg.OpenKey(hive, path)
            except OSError:
                return []
            subs, i = [], 0
            while True:
                try:
                    subs.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
            return subs

        def _verkey(s):
            nums, cur = [], ""
            for ch in s:
                if ch.isdigit():
                    cur += ch
                elif cur:
                    nums.append(int(cur)); cur = ""
            if cur:
                nums.append(int(cur))
            return tuple(nums) if nums else (0,)

        specs = [(h, p, v) for h in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)
                 for p, v in config["reg_paths"]]
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for root in config.get("reg_enum_roots", []):
                subs = _enum_keys(hive, root)
                if config.get("reg_two_level"):
                    # AutoCAD: R##.# -> ACAD-xxxx[:locale] -> AcadLocation/Location
                    year_map = config.get("year_map", {})
                    if year:
                        subs = [s for s in subs if year_map.get(s) == str(year)]
                    subs.sort(key=_verkey, reverse=True)
                    val_names = config.get("reg_value_names", ["AcadLocation", "Location"])
                    for sub in subs:
                        for ch in _enum_keys(hive, root + "\\" + sub):
                            for vn in val_names:
                                specs.append((hive, root + "\\" + sub + "\\" + ch, vn))
                else:
                    if year:
                        subs = [s for s in subs if s == str(year)]
                    subs.sort(key=lambda s: int(s) if s.isdigit() else 0, reverse=True)
                    suffixes = config.get("reg_sub_suffixes", [""])
                    for sub in subs:
                        for suf in suffixes:
                            specs.append((hive, root + "\\" + sub + (("\\" + suf) if suf else ""),
                                          config.get("reg_value_name", "Location")))
        for hive, key_path, val_name in specs:
            try:
                key = winreg.OpenKey(hive, key_path)
                val, _ = winreg.QueryValueEx(key, val_name)
                winreg.CloseKey(key)
            except OSError:
                continue
            for cand in (os.path.join(val, exe_name), val):
                if os.path.isfile(cand):
                    return cand
    except ImportError:
        pass

    # 指定了年份: 只认注册表, 不落兜底（否则可能启动别的版本）
    if year:
        return None

    # 2) 常见路径（C/D 盘）
    for path in config["common_paths"]:
        if os.path.isfile(path):
            return path

    # 3) 兜底：常见安装根下递归扫描（限深 3 层，防慢扫）
    for root in config.get("scan_roots", []):
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath[len(root):].count(os.sep) >= 3:
                dirnames[:] = []
            if exe_name in filenames:
                return os.path.join(dirpath, exe_name)
    return None




# AutoCAD 年份 → R 号（ROT / ProgID 里用的是 R 号，不是年份）
# 已在本机核实：2014=19.1、2022=24.1、2023=24.2；其余为通行对照表（best-effort）
ACAD_RVERSION = {
    "2013": "19.0", "2014": "19.1", "2015": "20.0", "2016": "20.1", "2017": "21.0",
    "2018": "22.0", "2019": "23.0", "2020": "23.1", "2021": "24.0", "2022": "24.1",
    "2023": "24.2", "2024": "24.3", "2025": "25.0", "2026": "25.1",
}
RVERSION_TO_YEAR = {v: k for k, v in ACAD_RVERSION.items()}


def probe_running_versions(app_key):
    """用 ROT 探测该平台正在运行的实例及年份 ⇒ [(year, prog_id)]（年份可能为空字符串）"""
    import win32com.client
    cfg = CAD_APPS[app_key]
    found = []
    for _y in range(2035, 2008, -1):
        _pid = "%s.%s" % (cfg["com_prog_id"], _y)
        try:
            win32com.client.GetActiveObject(_pid)
            found.append((str(_y), _pid))
        except Exception:
            pass
    if app_key == "autocad":
        # AutoCAD 的版本化 ProgID 是 R 号（如 AutoCAD.Application.24.1）⇒ 用 R 号反查年份
        for _rv, _yr in sorted(RVERSION_TO_YEAR.items()):
            _pid = "%s.%s" % (cfg["com_prog_id"], _rv)
            try:
                win32com.client.GetActiveObject(_pid)
                found.append((_yr, _pid))
            except Exception:
                pass
    if not found:
        try:
            win32com.client.GetActiveObject(cfg["com_prog_id"])
            found.append(("", cfg["com_prog_id"]))
        except Exception:
            pass
    return found


def list_all_cad():
    """列出本机检测到的所有可启动 CAD（供 --list-cad 与人工选择用）"""
    rows = []
    for app_key, config in CAD_APPS.items():
        for y in range(2035, 2008, -1):
            p = get_cad_exe_path(app_key, year=str(y))
            if p:
                rows.append((app_key, y, p))
    seen = {}
    for app_key, y, p in sorted(rows, key=lambda r: -r[1]):
        if p.lower() not in seen:
            seen[p.lower()] = (app_key, y, p)
    return [v for v in seen.values()]
def launch_cad(app_key, year=None, exe_override=None, use_explorer=False):
    """启动 CAD（脱离作业对象，父进程退出不连带杀掉）

    exe_override: 直接指定 exe 路径（--exe），用于「打开任意指定 CAD」。
    use_explorer: 强制用 explorer.exe 代启（--explorer）。等价于用户双击，
        进程挂到桌面 shell 下，运行沙箱的 Job 约束不到它 —— 沙箱开启时必需。

    一律带 /Automation：ZWCAD 2026 只有以该参数启动才会把 COM 对象注册进 ROT，
    否则 GetActiveObject 一律 (-2147221021, 操作无法使用) ⇒ 附加必失败（实测 2026-10-11）。
    """
    exe_path = exe_override or get_cad_exe_path(app_key, year=year)
    if not exe_path:
        return False, None

    launch_args = [exe_path, "/Automation"]

    # 0) --explorer：强制 explorer 代启（置于最前；沙箱 Job 内直起的进程会被回收）
    if use_explorer:
        try:
            subprocess.Popen(["explorer.exe", exe_path])
            return True, exe_path
        except Exception:
            pass
    # 1) 直接脱离作业对象启动（agent/任务环境父进程退出不回收 CAD）
    try:
        subprocess.Popen(
            launch_args,
            creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB
                          | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        return True, exe_path
    except Exception:
        pass
    # 2) WMI 代建：父进程是 WmiPrvSE ⇒ 不在当前作业里，且能带 /Automation
    try:
        cmdline = '"%s" /Automation' % exe_path
        ps = ("(Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
              "-Arguments @{CommandLine='%s'}).ProcessId" % cmdline)
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=30)
        return True, exe_path
    except Exception:
        pass
    # 3) explorer 代启（挂在 explorer 下，不受当前作业回收；参数可能不生效）
    try:
        subprocess.Popen(["explorer.exe", exe_path])
        return True, exe_path
    except Exception:
        pass
    # 4) 常规启动兜底
    try:
        subprocess.Popen(launch_args)
        return True, exe_path
    except Exception:
        return False, None
    # 0) --explorer：强制 explorer 代启（置于最前；bash 直起的进程在沙箱 Job 内会被回收）
    if use_explorer:
        try:
            subprocess.Popen(["explorer.exe", exe_path])
            return True, exe_path
        except Exception:
            pass
    # 1) 直接脱离作业对象启动（agent/任务环境父进程退出不回收 CAD）
    try:
        subprocess.Popen(
            [exe_path],
            creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB
                          | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        return True, exe_path
    except Exception:
        pass
    # 2) explorer 代启（进程挂在 explorer 下，同样不受当前作业回收）
    try:
        subprocess.Popen(["explorer.exe", exe_path])
        return True, exe_path
    except Exception:
        pass
    # 3) 常规启动兜底
    try:
        subprocess.Popen([exe_path])
        return True, exe_path
    except Exception:
        return False, None

# ─── COM 连接与 DLL 加载 ──────────────────────────────────────────────

def verify_launched_cad(expected_exe, timeout=60):
    """启动后校验：返回实际运行的 CAD 进程路径（与 expected 不一致 = 被启动器改道）"""
    deadline = time.time() + timeout
    base = os.path.basename(expected_exe).lower()
    while time.time() < deadline:
        actual = None
        try:
            import psutil
            for proc in psutil.process_iter(["name", "exe"]):
                if (proc.info["name"] or "").lower() == base:
                    actual = proc.info.get("exe") or ""
                    break
        except ImportError:
            try:
                _cmd = "wmic process where name='" + base + "' get ExecutablePath"
                _o = subprocess.run(_cmd, shell=True, capture_output=True, text=True,
                                    errors="replace", timeout=10).stdout
                for _line in _o.splitlines():
                    _line = _line.strip()
                    if _line.lower().endswith(".exe"):
                        actual = _line
                        break
            except Exception:
                pass
        if actual:
            return actual
        time.sleep(2)
    return None

def _force_visible(app):
    """COM 新建实例以 -Embedding 服务器模式启动 (Visible=False)，不置真则窗口不显示"""
    try:
        if not app.Visible:
            app.Visible = True
    except Exception:
        pass


def connect_com(app_key, retry=3, delay=2, wait_attach=0, year=None):
    """通过 COM 连接 CAD: 优先附加运行中的可见实例; 附加不到且 CAD 未运行才新建。

    wait_attach: 进程已在跑但 ROT 尚未注册时, 附加轮询等待秒数 (0=不等待)。
    用于 --launch 刚拉起 CAD 的场景 —— ROT 注册可能慢于固定的启动等待。

    实测要点（各宿主注册进 ROT 的名字不一致）:
    - ZWCAD 2026 这类把【带版本号】ProgID 注册进 ROT（如 ZWCAD.Application.2026）；
      而实测 ZWCAD 2025 【裸名 ZWCAD.Application 可用】、带年份反而不可用。
    - 因此统一策略: 先试裸名, 再按年份降序试带版本名, 两种宿主都能兜住。
    - Dispatch = CreateObject, 不看 ROT, 在 CAD 已开时会另起无界面后台实例、
      把 TmAgent 端口挂到用户看不到的实例上 —— 所以必须先 GetActiveObject 附加。
    """
    import win32com.client
    config = CAD_APPS[app_key]

    def try_attach():
        # 版本化优先、裸名最后：裸名 ProgID 的 LocalServer32 指向【最后安装的版本】
        # （本机实测裸名 = ZWCAD 2027），排第一会让 --year 2026 先撞到别的版本。
        # ZWCAD 2025 这类只认裸名的宿主，由最后的裸名兜底命中。
        attach_ids = []
        if year:
            if app_key == "autocad" and str(year) in ACAD_RVERSION:
                attach_ids.append(f"{config['com_prog_id']}.{ACAD_RVERSION[str(year)]}")
            attach_ids.append(f"{config['com_prog_id']}.{year}")
        if app_key == "zwcad":
            for y in range(2035, 2008, -1):
                pid_id = f"{config['com_prog_id']}.{y}"
                if pid_id not in attach_ids:
                    attach_ids.append(pid_id)
        if app_key == "autocad":
            for rv in sorted(ACAD_RVERSION.values(), reverse=True):
                pid_id = f"{config['com_prog_id']}.{rv}"
                if pid_id not in attach_ids:
                    attach_ids.append(pid_id)
        attach_ids.append(config["com_prog_id"])
        for prog_id in attach_ids:
            try:
                return prog_id, win32com.client.GetActiveObject(prog_id)
            except Exception:
                continue
        return None, None

    # 1) 附加已运行的可见实例（GetActiveObject 不新建进程）
    prog_id, app = try_attach()
    deadline = time.time() + max(0, wait_attach)
    while app is None and time.time() < deadline:
        if app_key not in find_cad_process():
            break   # 进程已退出, 不再等
        time.sleep(2)
        prog_id, app = try_attach()
    if app is not None:
        _force_visible(app)
        log(f"已附加运行中的 {config['display_name']} ({prog_id})", "OK")
        return app

    # 2) CAD 进程在跑却附加失败 → 不新建（否则通道挂到后台实例上）
    if app_key in find_cad_process():
        log(f"检测到 {config['display_name']} 已运行, 但附加 COM 实例失败 (ROT 未注册)", "ERR")
        log("请按 references/faq.md 手动 NETLOAD; 或关闭 CAD 后让脚本用 COM 全新启动", "INFO")
        return None

    # 3) CAD 未在运行 → 才允许 Dispatch 新建实例
    for attempt in range(retry):
        try:
            app = win32com.client.Dispatch(config["com_prog_id"])
            _force_visible(app)
            # 确保有活动文档
            try:
                if app.Documents.Count == 0:
                    app.Documents.Add()
                    time.sleep(1)
            except Exception:
                pass
            return app
        except Exception as e:
            if attempt < retry - 1:
                log(f"COM 连接失败 (第 {attempt + 1} 次), {delay}s 后重试...", "WARN")
                time.sleep(delay)
            else:
                return None
    return None


def load_dll_via_com(app, dll_path):
    """通过 COM SendCommand 执行 NETLOAD 加载 DLL"""
    doc = app.ActiveDocument

    # 保存 FILEDIA 设置，设为 0 抑制文件对话框
    old_filedia = None
    try:
        old_filedia = app.GetVariable("FILEDIA")
        app.SetVariable("FILEDIA", 0)
    except Exception:
        pass

    try:
        # 正斜杠路径（LISP 兼容，无需转义）
        lisp_path = dll_path.replace("\\", "/")
        # (command "NETLOAD" "path") — 提供路径参数，绕过文件对话框
        lisp_cmd = f'(command "NETLOAD" "{lisp_path}")\n'
        doc.SendCommand(lisp_cmd)
    finally:
        # 恢复 FILEDIA
        if old_filedia is not None:
            try:
                app.SetVariable("FILEDIA", old_filedia)
            except Exception:
                pass

# ─── 主流程 ───────────────────────────────────────────────────────────

def main():
    check_only = "--check" in sys.argv
    use_explorer = "--explorer" in sys.argv
    auto_launch = "--launch" in sys.argv or use_explorer

    # 解析 --dll / --app 参数
    custom_dll = None
    if "--dll" in sys.argv:
        idx = sys.argv.index("--dll")
        if idx + 1 < len(sys.argv):
            custom_dll = sys.argv[idx + 1]

    force_app = None
    if "--app" in sys.argv:
        idx = sys.argv.index("--app")
        if idx + 1 < len(sys.argv):
            force_app = sys.argv[idx + 1].lower()

    force = "--force" in sys.argv

    # --year 2024: 锁定 ZWCAD 版本年份（--launch 启动时用）
    year = None
    if "--year" in sys.argv:
        idx = sys.argv.index("--year")
        if idx + 1 < len(sys.argv):
            year = sys.argv[idx + 1]

    # --exe "C:\path\CAD.exe": 打开任意指定的 CAD（最高优先）
    exe_override = None
    if "--exe" in sys.argv:
        idx = sys.argv.index("--exe")
        if idx + 1 < len(sys.argv):
            exe_override = sys.argv[idx + 1].strip('"').strip("'")
            if not os.path.isfile(exe_override):
                log(f"--exe 指定的文件不存在: {exe_override}", "WARN")
                exe_override = None
            elif not year:
                for _y in range(2035, 2008, -1):
                    if str(_y) in exe_override:
                        year = str(_y)
                        break

    # --list-cad: 列出本机检测到的 CAD（选好后用 --exe 打开），然后退出
    if "--list-cad" in sys.argv:
        print_banner()
        log("本机检测到的 CAD：", "STEP")
        _cads = []
        for _k, _y, _p in list_all_cad():
            log('  [%s %s] %s' % (CAD_APPS[_k]['display_name'], _y, _p), 'INFO')
            _cads.append({'app': _k, 'year': _y, 'path': _p})
        log('打开指定版本：--exe "<上面的路径>" --launch', 'INFO')
        output_result({'status': 'list_cad', 'cads': _cads})
        return

    print_banner()

    # ── Step 0: 自动创建/启用 tm-cad MCP 连接器（与 TmAgent 是否运行无关）──
    log("配置 tm-cad 连接器...", "STEP")
    conn_action, conn_detail = ensure_connector_config()
    if conn_action == "error":
        log(f"连接器配置写入失败: {conn_detail}", "WARN")
    elif conn_action == "created":
        log("已自动创建 tm-cad 连接器 -> mcp.json", "OK")
    elif conn_action == "enabled":
        log("已启用 tm-cad 连接器 (disabled=false)", "OK")
    elif conn_action == "already_ok":
        log("tm-cad 连接器配置已就绪", "OK")

    # ── Step 1: 检查 TmAgent 是否已在运行 ──
    log("检查 TmAgent 服务状态...", "STEP")
    running, base_url, discovery_info = is_tagent_running()

    # 指定了平台/年份/exe 时：只有"目标版本确实在跑"才允许短路，
    # 否则继续往下走（去启动目标版本），避免被其它版本的既有服务挡住。
    _lv_app = force_app
    if not _lv_app and exe_override:
        _lv_app = "autocad" if os.path.basename(exe_override).lower().startswith("acad") else "zwcad"
    _lv_want = bool(year or force_app or exe_override)
    _lv_ok = True
    if running and _lv_want:
        _lv_running = probe_running_versions(_lv_app or "zwcad")
        if year:
            _lv_ok = any(r[0] == str(year) for r in _lv_running)
        else:
            _lv_ok = bool(_lv_running)
        if not _lv_ok:
            log("已有 TmAgent 服务在跑，但不是指定的目标版本；继续处理指定版本...", "WARN")

    if running and _lv_ok:
        log(f"TmAgent 已在运行 (HTTP: {base_url})", "OK")
        print_guide(base_url, connector_action=conn_action)
        output_result({
            "status": "already_running",
            "base_url": base_url,
            "connector": {
                "name": MCP_CONNECTOR_NAME,
                "action": conn_action,
                "mcp_url": MCP_CONNECTOR_URL,
                "needs_trust": conn_action in ("created", "enabled"),
            },
        })
        return

    if check_only:
        log("TmAgent 未运行 (--check 模式, 不执行加载)", "WARN")
        output_result({
            "status": "not_running",
            "connector": {
                "name": MCP_CONNECTOR_NAME,
                "action": conn_action,
                "mcp_url": MCP_CONNECTOR_URL,
                "needs_trust": conn_action in ("created", "enabled"),
            },
        })
        return

    # ── Step 2: 确定目标 CAD（版本感知，一条命令搞定）──
    #    指定 --app/--year/--exe：该版本已在跑 ⇒ 附加它；没跑 ⇒ 自动定位并启动
    #    未指定：有在跑的任意版本 ⇒ 用它；都没有 ⇒ 启动默认平台的最新版
    target_app = force_app
    if not target_app and exe_override:
        target_app = "autocad" if os.path.basename(exe_override).lower().startswith("acad") else "zwcad"

    _need_launch = False          # 目标版本没在跑 ⇒ 需要启动（与 force_app 无关，故用独立标志）
    _want_version = bool(year or exe_override or force_app)
    if _want_version:
        _app = target_app or "zwcad"
        _running = probe_running_versions(_app)
        if _running:
            if year:
                _hit = [r for r in _running if r[0] == str(year)]
                if _hit:
                    target_app = _app
                    log("检测到已运行的 %s %s" % (CAD_APPS[_app]["display_name"], year), "OK")
                else:
                    _other = ",".join(r[0] or "未知" for r in _running)
                    log("检测到 %s 在运行，但版本不是指定的 %s（在跑：%s）"
                        % (CAD_APPS[_app]["display_name"], year, _other), "WARN")
                    target_app = None
                    _need_launch = True
            else:
                target_app = _app
                log("检测到已运行的 %s" % CAD_APPS[_app]["display_name"], "OK")
        else:
            target_app = None
            _need_launch = True

    if not target_app and not _need_launch:
        # 未指定目标：任选一个在跑的实例
        _any = find_cad_process()
        if _any:
            target_app = _any[0]
            log("检测到运行中的 CAD: %s" % CAD_APPS[target_app]["display_name"], "OK")

    if _need_launch and auto_launch:
        if exe_override:
            launch_key = "autocad" if os.path.basename(exe_override).lower().startswith("acad") else "zwcad"
        else:
            launch_key = force_app or "zwcad"
        exe = exe_override or get_cad_exe_path(launch_key, year=year)
        if not exe and year:
            log("本机没有找到 %s %s 的安装路径" % (CAD_APPS[launch_key]["display_name"], year), "ERR")
        if exe:
            log("尝试启动 %s: %s" % (CAD_APPS[launch_key]["display_name"], exe), "INFO")
            launch_cad(launch_key, year=year, exe_override=exe, use_explorer=use_explorer)
            _actual = verify_launched_cad(exe)
            if _actual and _actual.lower() != exe.lower():
                log("注意：实际启动的是 %s（与指定不符）—— 启动器改道了版本" % _actual, "WARN")
            log("等待 CAD 主窗口出现 (最长 90s)...", "INFO")
            win_deadline = time.time() + 90
            while time.time() < win_deadline:
                if find_cad_process():
                    break
                time.sleep(2)
            target_app = launch_key

    if not target_app:
        running_cads = find_cad_process()
        if running_cads:
            target_app = running_cads[0]
            log("检测到运行中的 CAD: %s" % CAD_APPS[target_app]["display_name"], "OK")
        elif not _want_version:
            # 未指定目标且没有任何实例：落回默认平台，交给 --launch 启动
            target_app = force_app or "zwcad"
            log("未检测到运行中的 CAD，默认目标平台: %s"
                % CAD_APPS[target_app]["display_name"], "INFO")

    if not target_app:
        log("无法确定目标 CAD 平台（未检测到运行实例，且未指定 --app/--year/--exe）", "ERR")
        output_result({
            "status": "cad_not_running",
            "hint": "请指定 --app zwcad|autocad 与 --year，或加 --launch 自动启动默认平台最新版",
        })
        return

    app_key = target_app
    config = CAD_APPS[app_key]
    log(f"目标平台: {config['display_name']}", "OK")

    # ── Step 3: 查找对应版本的 DLL ──
    log(f"查找 {config['display_name']} 对应的 DLL...", "STEP")
    dll_path = find_dll(app_key, custom_dll, force=force)
    if not dll_path:
        log(f"未找到 {DLL_BY_APP.get(app_key, DLL_GENERIC)}", "ERR")
        if DLL_DOWNLOAD_BASE:
            log(f"请检查网络，或手动从以下地址下载对应 DLL 放入技能根目录:", "INFO")
            log(f"  {DLL_DOWNLOAD_BASE.rstrip('/')}/{DLL_BY_APP.get(app_key, DLL_GENERIC)}", "INFO")
        else:
            log(f"请将对应 DLL 放入技能根目录: {SKILL_DIR}", "INFO")
            log("  中望CAD -> TmAgent-ZCAD.dll    AutoCAD -> TmAgent-ACAD.dll", "INFO")
            log("  或参见 references/dll-download.md 获取 DLL 下载地址", "INFO")
        log("也可通过 --dll 参数直接指定 DLL 路径", "INFO")
        output_result({
            "status": "dll_not_found",
            "target_app": app_key,
            "searched_paths": get_dll_search_paths(app_key),
        })
        return
    log(f"找到 DLL: {dll_path}", "OK")

    # ── Step 3.5: 更新检查（最多 7 天查一次远端，有新版先替换再加载）──
    dll_path, dll_update = check_dll_update(app_key, dll_path)
    if dll_update and dll_update["updated"]:
        log(f"DLL 已更新到远端最新版 (提交 {dll_update['remote_commit'][:10]})，"
            "本次加载即为新版", "OK")

    # ── Step 4: 检查依赖 ──
    log("检查依赖 (pywin32)...", "STEP")
    if not ensure_module("win32com", "pywin32"):
        log("pywin32 不可用，无法通过 COM 加载", "ERR")
        log("请手动在 CAD 中执行 NETLOAD 加载 TmAgent.dll", "INFO")
        output_result({
            "status": "dep_error",
            "missing": "pywin32",
            "dll": dll_path,
        })
        return
    log("pywin32 就绪", "OK")

    # ── Step 5: COM 连接（--launch 刚拉起的实例需要轮询等 ROT 注册）──
    log(f"连接 {config['display_name']} COM 接口...", "STEP")
    app = connect_com(app_key, wait_attach=45 if auto_launch else 0, year=year)
    if not app:
        log("COM 连接失败", "ERR")
        log("若 CAD 已打开: 属附加运行实例失败, 见 references/faq.md 手动 NETLOAD", "INFO")
        log("若 CAD 从未开过: 以管理员身份运行一次 CAD 注册 COM, 再重试", "INFO")
        output_result({
            "status": "com_failed",
            "app": app_key,
            "dll": dll_path,
        })
        return
    log("COM 连接成功", "OK")

    # ── Step 6: NETLOAD 加载 DLL ──
    log(f"加载 {os.path.basename(dll_path)} 到 {config['display_name']}...", "STEP")
    try:
        load_dll_via_com(app, dll_path)
    except Exception as e:
        log(f"NETLOAD 执行失败: {e}", "ERR")
        log("手动加载步骤 (任选其一):", "INFO")
        log(f"  方式A: 打开 CAD, 命令行输入 NETLOAD 回车, 在文件对话框中选择:\n"
            f"         {dll_path}", "INFO")
        log(f"  方式B: CAD 命令行输入 APPLOAD (或拖入) 加载技能根目录的 加载dll.lsp", "INFO")
        log("  加载成功的标志: CAD 命令行出现 'TmAgent 加载成功! HTTP: http://127.0.0.1:9876'", "INFO")
        output_result({
            "status": "load_failed",
            "error": str(e),
            "dll": dll_path,
            "hint": "自动 NETLOAD 失败。手动步骤: 在 CAD 命令行输入 NETLOAD, 选择上述 dll 路径; "
                    "或加载技能根目录的 加载dll.lsp。成功标志: CAD 命令行出现 'TmAgent 加载成功'。",
        })
        return

    # ── Step 7: 等待 TmAgent HTTP 服务启动 ──
    log("等待 TmAgent HTTP 服务启动...", "STEP")

    # 先尝试从 discovery 文件获取端口
    time.sleep(2)  # 给 DLL 初始化时间
    _, base_url, _ = is_tagent_running()
    if base_url:
        if wait_for_http(base_url, timeout=HTTP_WAIT_TIMEOUT):
            tools_synced = maybe_sync_tools(base_url, dll_update)
            log(f"TmAgent 加载成功! HTTP: {base_url}", "OK")
            print_guide(base_url, connector_action=conn_action)
            output_result({
                "status": "success",
                "base_url": base_url,
                "app": app_key,
                "dll": dll_path,
                "dll_update": dll_update,
                "tools_synced": tools_synced,
                "connector": {
                    "name": MCP_CONNECTOR_NAME,
                    "action": conn_action,
                    "mcp_url": MCP_CONNECTOR_URL,
                    "needs_trust": conn_action in ("created", "enabled"),
                },
            })
            return

    # discovery 文件未出现, 尝试默认端口
    for port in [9876, 9877, 9878]:
        test_url = f"http://127.0.0.1:{port}"
        if wait_for_http(test_url, timeout=5):
            tools_synced = maybe_sync_tools(test_url, dll_update)
            log(f"TmAgent 加载成功! HTTP: {test_url}", "OK")
            print_guide(test_url, connector_action=conn_action)
            output_result({
                "status": "success",
                "base_url": test_url,
                "app": app_key,
                "dll": dll_path,
                "dll_update": dll_update,
                "tools_synced": tools_synced,
                "connector": {
                    "name": MCP_CONNECTOR_NAME,
                    "action": conn_action,
                    "mcp_url": MCP_CONNECTOR_URL,
                    "needs_trust": conn_action in ("created", "enabled"),
                },
            })
            return

    # 加载了但 HTTP 未响应
    log("TmAgent DLL 已加载, 但 HTTP 服务未响应", "WARN")
    log("可能原因:", "INFO")
    log("  1. DLL 仍在初始化, 请稍后用 --check 检查", "INFO")
    log("  2. 端口被占用, 检查 CAD 命令行输出", "INFO")
    log("  3. DLL 加载失败 (版本不兼容/依赖缺失), 检查 CAD 命令行错误信息", "INFO")
    output_result({
        "status": "loaded_no_http",
        "dll": dll_path,
        "dll_update": dll_update,
        "app": app_key,
        "discovery_exists": os.path.exists(DISCOVERY_PATH),
    })


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("用户中断", "WARN")
        output_result({"status": "interrupted"})
    except Exception as e:
        import traceback as _tb
        _tb.print_exc()
        log(f"未预期的错误: {e!r}", "ERR")
        output_result({"status": "error", "error": str(e), "repr": repr(e)})
