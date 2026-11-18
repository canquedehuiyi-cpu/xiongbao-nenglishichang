#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_sources.py — 源级完整性门禁（跨材质 uniform·蒸馏前必过）

对齐 text 链的 verify_chunks.py：把所有材质（文字块 / 链接 / 图片 / 音视频）的
「原子单元处理清单(plan)」与「已处理清单(processed)」对账，差集非空→exit≠0，一律不许出包。

用法：
  python verify_sources.py --plan media_plan.json --processed media_processed.json
  python verify_sources.py --self-test

plan.json     : {"units":[{"id":"U001","type":"image","source":"a.png"}, ...]}
processed.json: {"units":[{"id":"U001"}, ...]}   # 仅含成功提取的单元
"""
import sys
import os
import json


def load_ids(path):
    """读取单元 ID 列表。

    ⚠️ 失败信号用 None 表达，绝不用 [] ：空列表会被 check() 算成「无缺失」而让
    「门禁文件压根不存在」的敞口悄悄通过（fail-open）。文件确实缺失/不可读必须让
    调用方硬拦（fail-closed），与 verify_chunks.py 一致。
    仅当文件真实存在、解析成功但确无单元时，才返回 []（合法「无媒体可验」场景）。
    """
    if not path:
        return None
    if not os.path.exists(path):
        return None
    try:
        d = json.load(open(path, encoding="utf-8"))
        return [u.get("id") for u in d.get("units", []) if u.get("id")]
    except Exception:
        return None


def check(plan_ids, processed_ids):
    plan = set(plan_ids)
    proc = set(processed_ids)
    missing = sorted(plan - proc)
    extra = sorted(proc - plan)
    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "extra": extra,
        "total": len(plan),
        "processed": len(proc),
    }


def main():
    # flag 与位置参数严格分离（观察项2工具链建议）：--self-test 不限位置，目录/文件参数永不进自测分支
    if "--self-test" in sys.argv[1:]:
        p = ["U001", "U002", "U003"]
        # 用例1：全处理
        r1 = check(p, ["U001", "U002", "U003"])
        c1 = r1["ok"] and r1["missing"] == []
        # 用例2：漏一个
        r2 = check(p, ["U001", "U003"])
        c2 = (not r2["ok"]) and r2["missing"] == ["U002"]
        # 用例3：含脏数据（多余单元）→ 不影响 missing 判定
        r3 = check(p, ["U001", "U002", "U003", "UX"])
        c3 = r3["ok"] and r3["extra"] == ["UX"]
        # 用例4：fail-closed 护栏——门禁文件缺失/空路径必须返回 None（绝不可返回 [] 误过）
        c4 = (load_ids("") is None) and (load_ids("/nonexistent_verify_src.json") is None)
        ok = c1 and c2 and c3 and c4
        print("self-test:", "PASS" if ok else "FAIL",
              json.dumps({"c1": c1, "c2": c2, "c3": c3, "c4_fail_closed": c4}, ensure_ascii=False))
        sys.exit(0 if ok else 1)

    plan = processed = None
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--plan":
            plan = sys.argv[i + 1]; i += 2
        elif a == "--processed":
            processed = sys.argv[i + 1]; i += 2
        else:
            i += 1
    if not plan or not processed:
        sys.stderr.write("usage: verify_sources.py --plan <plan.json> --processed <processed.json>\n")
        sys.exit(2)
    plan_ids = load_ids(plan)
    proc_ids = load_ids(processed)
    # fail-closed：门禁文件缺失/不可读，一律硬拦，宁可误停不可漏放
    if plan_ids is None or proc_ids is None:
        miss = plan if plan_ids is None else processed
        sys.stderr.write("门禁文件缺失/不可读：%s（fail-closed，不允许出包）\n" % miss)
        sys.exit(2)
    r = check(plan_ids, proc_ids)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
