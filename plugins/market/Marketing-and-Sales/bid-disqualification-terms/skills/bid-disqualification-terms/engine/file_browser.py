"""
file_browser.py —— 通用目录浏览能力（工作台"文件"标签的数据源）

只暴露固定的、对用户有意义的目录（产物、当前模板、运行状态），
不做成能任意遍历整个电脑文件系统的通用文件管理器——那超出工具
该有的范围，也是不必要的攻击面。

场景包不需要改这个文件；新增可浏览目录时在 BROWSABLE_DIRS 加一行。
open_in_explorer 的路径穿越校验必须保留，任何调用方都不要绕过它。
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

# 允许被浏览的目录，key 是展示给用户看的名字，value 是相对 dist_root 的路径。
BROWSABLE_DIRS = {
    "产物": "output",
    "当前模板": "templates",
    "运行状态": "storage",
}


def list_directory_tree(dist_root: Path) -> dict:
    """返回 BROWSABLE_DIRS 里每个目录的文件列表（不递归子目录，保持简单）。"""
    result: dict = {}
    for label, rel_path in BROWSABLE_DIRS.items():
        dir_path = dist_root / rel_path
        if label == "当前模板" and not dir_path.exists():
            # 本地直跑时模板归场景包资产所有（engine_runtime 的读取顺序就是
            # 「优先场景 assets，包内无场景源码时才回退 dist_root/templates」），
            # 工作台遵循同一口径，避免这个标签页永远显示空列表。前提是标准布局：
            # dist_root 是项目根下的 dist_template/，场景目录在项目根下。
            cands = sorted((dist_root.parent / "scenarios").glob("*/assets/*/templates"))
            # _scaffold 这类下划线开头的脚手架目录不是可执行场景，模板参考价值为零，
            # 会让「当前模板」显示脚手架的半成品而非真实场景的资产
            real = [p for p in cands if not p.parts[-4].startswith("_")]
            dir_path = (real or cands)[0] if cands else dir_path
        entries = []
        if dir_path.exists():
            for item in sorted(dir_path.iterdir()):
                if item.name.startswith("."):
                    continue
                stat = item.stat()
                entries.append(
                    {
                        "name": item.name,
                        "is_dir": item.is_dir(),
                        "size_bytes": stat.st_size if item.is_file() else None,
                        "modified_at": stat.st_mtime,
                    }
                )
        result[label] = {"rel_path": rel_path, "entries": entries}
    return result


def open_in_explorer(dist_root: Path, target_path: str) -> bool:
    """
    在系统文件管理器里定位指定路径：目录 -> 直接打开；文件 -> 打开所在
    目录并选中该文件（工作台结果面板拿到的产物是绝对路径，用户要的是
    "带我去那个文件"，不是"给我看一个文件夹"）。

    target_path 接受相对 dist_root 的路径或绝对路径，但最终必须落在
    dist_root 范围内。非 Windows/macOS 开发环境下跳过实际打开、
    只返回 False，不报错，方便本地测试其它逻辑。
    """
    raw = Path(target_path)
    target = (raw if raw.is_absolute() else dist_root / raw).resolve()
    if not target.exists():
        return False

    # 防止传入 "../../" 或包外绝对路径跳出 dist_root 范围
    try:
        target.relative_to(dist_root.resolve())
    except ValueError:
        return False

    system = platform.system()
    if system == "Windows":
        if target.is_file():
            # /select 定位到具体文件；逗号后不能有空格，否则 explorer 会当成两个参数
            subprocess.Popen(["explorer", f"/select,{target}"])
        else:
            os.startfile(target)  # noqa: S606 —— Windows 专用 API
        return True
    elif system == "Darwin":
        args = ["open"] + (["-R"] if target.is_file() else []) + [str(target)]
        subprocess.Popen(args)
        return True
    else:
        return False
