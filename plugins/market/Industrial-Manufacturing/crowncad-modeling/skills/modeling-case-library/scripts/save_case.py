"""保存已完成且获用户授权的 runs 任务，正式转正后重建 models 索引。

真实授权及 CAD 完成检查由调用方负责；本命令只执行文件归档流程。
"""

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    # 兼容直接以脚本路径运行，让公共模块的 scripts 包可以被导入。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_case_library import CaseLibraryError, save_case


def main(argv=None) -> int:
    """解析参数并输出 JSON；业务结果码为 0 成功、1 归档失败、2 索引失败。

    argparse 的缺参等用法错误仍使用其标准退出码 2，结果判定须结合 JSON。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    # 可重复传入最终脚本、响应及其他依赖；README 和操作图由公共模块自动要求。
    parser.add_argument("--required-file", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        result = save_case(args.workspace, args.source, args.required_file)
        # 不能把“案例已保存、索引失败”当作整个归档失败，也不能报告全部成功。
        code = 2 if result["indexStatus"] == "failed" else 0
    except (OSError, ValueError, CaseLibraryError) as error:
        result = {
            "saveStatus": "failed",
            "indexStatus": "unchanged",
            "error": str(error),
        }
        code = 1
    # stdout 保持机器可读 JSON，保留中文，便于代理区分两个阶段的真实状态。
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
