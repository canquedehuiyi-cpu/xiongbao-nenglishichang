#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_chunks.py — 块覆盖完整性机器校验（确定性，仅标准库，零第三方依赖）

用途（对应 SKILL.md A0.3 块覆盖完整性门禁 / A6 汇总门禁联动）：
  逐块提取（A0.1 / A0.2）完成后、汇总架构前，必须实跑本脚本核对——
  「已处理块 ID 集合」是否完整覆盖「分块清单（ingest_chunk.py 产出）的块 ID 集合」。
  差集（分块清单有、processed 无的块）非空 → 说明有整块漏蒸，exit≠0 不许出包。

用法：
  python verify_chunks.py --plan <分块清单.json> --processed <processed_ids.txt>
  python verify_chunks.py --self-test

参数：
  --plan       ingest_chunk.py 产出的 JSON（含 "chunks":[{"id":"C001",...}]）
  --processed  逐块提取时追加写入的状态文件，每行一个已处理块 ID（如 runs/<任务>/.work/processed_ids.txt）

输出（stdout, JSON）：
  {
    "total_plan":     int,      # 分块清单块数
    "processed_count":int,      # processed 文件去重后合法 ID 数
    "missing":        [str],    # 分块清单有、processed 无的块（差集，漏蒸块）
    "extra":          [str],    # processed 有、分块清单无的块（容错提示，非阻塞）
    "ok":             bool      # missing 为空为 True
  }

退出码：ok=True → 0；ok=False（有漏蒸块）→ 1。供 SKILL.md 门禁「exit≠0 不许出包」判定。

--self-test：内置用例，不碰任何文件：
  用例1：plan=C001..C003，processed=C001,C002 → missing=[C003]，expect exit 1 / ok False
  用例2：plan=C001..C003，processed=C001,C002,C003 → missing=[]，expect exit 0 / ok True
"""

import sys
import os
import json


def load_plan_ids(plan_path):
    """从 ingest_chunk.py 产出的 JSON 取块 ID 集合（保序）。"""
    with open(plan_path, encoding="utf-8") as f:
        data = json.load(f)
    chunks = data.get("chunks", [])
    ids = []
    seen = set()
    for c in chunks:
        cid = c.get("id")
        if cid and cid not in seen:
            seen.add(cid)
            ids.append(cid)
    return ids


def load_processed(processed_path):
    """从状态文件取已处理块 ID 集合（每行一 ID，去空、去重、保序）。"""
    ids = []
    seen = set()
    with open(processed_path, encoding="utf-8") as f:
        for line in f:
            tid = line.strip()
            if not tid:
                continue
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)
    return ids


def check(plan_ids, processed_ids):
    """返回完整性校验结果 dict。"""
    plan_set = set(plan_ids)
    proc_set = set(processed_ids)
    missing = [c for c in plan_ids if c not in proc_set]  # 保分块顺序
    extra = [p for p in processed_ids if p not in plan_set]  # 保处理顺序
    return {
        "total_plan": len(plan_ids),
        "processed_count": len(processed_ids),
        "missing": missing,
        "extra": extra,
        "ok": len(missing) == 0,
    }


def main():
    args = sys.argv[1:]
    if args and args[0] == "--self-test":
        return _self_test()

    plan_path = None
    processed_path = None
    i = 0
    while i < len(args):
        if args[i] == "--plan":
            plan_path = args[i + 1]
            i += 2
        elif args[i] == "--processed":
            processed_path = args[i + 1]
            i += 2
        else:
            i += 1

    if not plan_path or not processed_path:
        sys.stderr.write(
            "usage: verify_chunks.py --plan <分块清单.json> --processed <processed_ids.txt>\n"
        )
        sys.exit(2)

    if not os.path.exists(plan_path):
        sys.stderr.write("plan 文件不存在: %s\n" % plan_path)
        sys.exit(2)
    if not os.path.exists(processed_path):
        sys.stderr.write("processed 文件不存在: %s\n" % processed_path)
        sys.exit(2)

    plan_ids = load_plan_ids(plan_path)
    processed_ids = load_processed(processed_path)
    result = check(plan_ids, processed_ids)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


def _self_test():
    import io

    # 构造内存版 plan / processed（不落盘）
    plan_ids = ["C001", "C002", "C003"]

    # 用例1：漏 C003 → 期望 missing=[C003], ok False, exit 1
    proc1 = ["C001", "C002"]
    r1 = check(plan_ids, proc1)
    case1_ok = (r1["missing"] == ["C003"] and r1["ok"] is False)

    # 用例2：全处理 → 期望 missing=[], ok True, exit 0
    proc2 = ["C001", "C002", "C003"]
    r2 = check(plan_ids, proc2)
    case2_ok = (r2["missing"] == [] and r2["ok"] is True)

    # 用例3：processed 含脏数据（重复/多余，模拟文件读取已去空行后场景）→ 不影响 missing 判定
    proc3 = ["C001", "C001", "C002", "C003", "C999"]
    r3 = check(plan_ids, proc3)
    case3_ok = (r3["missing"] == [] and r3["ok"] is True and r3["extra"] == ["C999"])

    all_ok = case1_ok and case2_ok and case3_ok
    print("self-test case1 (漏 C003 -> missing=[C003], ok=False):", case1_ok)
    print("self-test case2 (全处理   -> missing=[],    ok=True ):", case2_ok)
    print("self-test case3 (脏数据容错 -> 不影响 missing)          :", case3_ok)
    print("RESULT:", "PASS" if all_ok else "FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
