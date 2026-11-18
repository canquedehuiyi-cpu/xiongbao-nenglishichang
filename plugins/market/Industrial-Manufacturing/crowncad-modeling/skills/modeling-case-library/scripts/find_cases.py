"""案例库命令入口：search 只读查找，rebuild-index 显式重建 models 索引。"""

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    # 直接运行本文件时补齐包搜索路径，不要求调用方安装 Python 包。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_case_library import CaseLibraryError, find_cases, rebuild_case_index


def main(argv=None) -> int:
    """分发子命令并输出 JSON；无匹配是成功的空列表，读取错误返回失败。"""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search")
    search.add_argument("--workspace", type=Path, required=True)
    # 一个 --term 对应一个关键词；多个关键词默认任一匹配。
    search.add_argument("--term", action="append", required=True)
    rebuild = commands.add_parser("rebuild-index")
    rebuild.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # 普通 search 即使发现索引过期也不写文件，重建必须显式选择子命令。
        result = (
            find_cases(args.workspace, args.term)
            if args.command == "search"
            else rebuild_case_index(args.workspace)
        )
    except (OSError, ValueError, CaseLibraryError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
