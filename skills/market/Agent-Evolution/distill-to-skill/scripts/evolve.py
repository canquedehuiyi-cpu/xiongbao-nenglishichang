# -*- coding: utf-8 -*-
"""evolve.py —— 标准件进化三动作落地（追加 / 修正 / 回退·纯标准库·零第三方依赖）

作用：让已产出的标准件可被安全地迭代，且每次迭代都可回退。对齐 SKILL.md A5「进化机制」：
标准件支持用户【追加样本 append】/【修正错误 correction】/【回退旧版 rollback】，
**进化仅在用户授权下发生，不静默改写**。

快照与日志：
  - 任何改动动作执行【前】先对标准件整树打一份快照，存 `.evolve/snapshots/<时间戳-动作>/`；
  - 每次动作向 `.evolve/evolve_log.json` 追加一条记录（动作 / 时间 / 摘要 / 快照 ID）；
  - 回退即从快照恢复，恢复前也会先给「当前状态」打一份快照；
  - 未带 `--approve` 一律拒绝执行——这是「不静默改写」在脚本层的硬保证。

用法：
  python evolve.py append   --target <标准件目录> --add <新材料文件> [--slot 名称] --approve
  python evolve.py append   --target <标准件目录> --add <新材料文件> --slot 名称 --merge --approve
  python evolve.py correct  --target <标准件目录> --file <相对路径> --old "原文" --new "新文" --approve
  python evolve.py rollback --target <标准件目录> [--to <快照ID>] --approve
  python evolve.py log      --target <标准件目录>
  python evolve.py --self-test

追加有两种落位（都不覆盖原文，都先快照）：
  - 默认：每次生成带时间戳的新文件 references/<slot>-appended-<ts>.md（改动可逐条回溯，但长期会碎片化）；
  - `--merge`（须与 `--slot` 合用）：并入既有 references/<slot>.md（无则新建），避免碎片化。
    合并一律「往后接」，绝不覆盖既有内容；旧的独立落位文件不受影响。

零第三方依赖：仅 argparse / json / os / shutil / sys / tempfile / datetime。
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile

EVOLVE_DIR = ".evolve"
SKIP_DIRS = {"__pycache__", ".git", ".svn", EVOLVE_DIR}
SKIP_EXT = {".pyc", ".pyo"}


class EvolveError(Exception):
    pass


def _ts():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _root(target):
    return os.path.join(target, EVOLVE_DIR)


def _snap_dir(target):
    return os.path.join(_root(target), "snapshots")


def _log_path(target):
    return os.path.join(_root(target), "evolve_log.json")


def _read_log(target):
    p = _log_path(target)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _append_log(target, record):
    entries = _read_log(target)
    entries.append(record)
    os.makedirs(_root(target), exist_ok=True)
    with open(_log_path(target), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    return entries


def _ignore(_dir, names):
    return [n for n in names
            if n in SKIP_DIRS or os.path.splitext(n)[1].lower() in SKIP_EXT]


def snapshot(target, label):
    """对标准件整树打快照，返回快照 ID。"""
    sid = "%s-%s" % (_ts(), label)
    base = os.path.join(_snap_dir(target), sid)
    n = 2
    while os.path.exists(base):
        base = os.path.join(_snap_dir(target), "%s-%d" % (sid, n))
        n += 1
    shutil.copytree(target, base, ignore=_ignore)
    return os.path.basename(base)


def _require_approve(approved):
    if not approved:
        raise EvolveError("进化需用户明确授权：请加 --approve 后再执行（本脚本不静默改写）")


def append(target, add_file, slot, approved, merge=False):
    """追加样本：把新材料落进 references/，并在日志留痕。

    默认落位：references/<slot 或 源文件名>-appended-<时间戳>.md（每次新文件，便于逐条回溯）。
    merge=True（须同时给 slot）：并入既有 references/<slot>.md（无则新建），避免长期碎片化。
    两种落位都【只往后接、绝不覆盖既有内容】，且执行前都先打快照。
    """
    _require_approve(approved)
    if not os.path.isdir(target):
        raise EvolveError("标准件目录不存在: %s" % target)
    if not os.path.isfile(add_file):
        raise EvolveError("待追加材料不存在: %s" % add_file)
    if merge and not slot:
        raise EvolveError("合并追加需同时指定 --slot（说明并入哪个 slot 文件）")
    sid = snapshot(target, "before-append")
    refdir = os.path.join(target, "references")
    os.makedirs(refdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(add_file))[0] or "sample"
    with open(add_file, encoding="utf-8", errors="replace") as f:
        body = f.read()

    if merge:
        name = "%s.md" % slot
        p = os.path.join(refdir, name)
        marker = "<!-- evolve:append %s from %s -->\n\n%s\n" % (
            _ts(), os.path.basename(add_file), body)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                prior = f.read()
            if not prior.endswith("\n"):
                prior += "\n"
            with open(p, "w", encoding="utf-8") as f:
                f.write(prior + "\n" + marker)
        else:
            with open(p, "w", encoding="utf-8") as f:
                f.write("# %s（%s 合并归入）\n\n%s" % (slot, _ts(), marker))
        _append_log(target, {"action": "append-merge", "at": _ts(),
                             "added": "references/" + name,
                             "source": os.path.basename(add_file), "snapshot": sid})
        return "references/" + name

    name = "%s-appended-%s.md" % (slot or stem, _ts())
    with open(os.path.join(refdir, name), "w", encoding="utf-8") as f:
        f.write("<!-- evolve:append %s -->\n\n%s" % (_ts(), body))
    _append_log(target, {"action": "append", "at": _ts(), "added": "references/" + name,
                         "source": os.path.basename(add_file), "snapshot": sid})
    return "references/" + name


def correct(target, rel_file, old, new, approved):
    """修正错误：对指定文件做唯一命中的字符串替换；不唯一则拒绝。"""
    _require_approve(approved)
    p = os.path.join(target, rel_file)
    if not os.path.isfile(p):
        raise EvolveError("待修正文件不存在: %s" % rel_file)
    with open(p, encoding="utf-8") as f:
        text = f.read()
    cnt = text.count(old)
    if cnt == 0:
        raise EvolveError("未在 %s 中找到待修正内容" % rel_file)
    if cnt > 1:
        raise EvolveError("待修正内容在 %s 中出现 %d 次，不唯一，拒绝改动" % (rel_file, cnt))
    sid = snapshot(target, "before-correct")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new))
    _append_log(target, {"action": "correct", "at": _ts(), "file": rel_file,
                         "snapshot": sid})
    return rel_file


def rollback(target, to, approved):
    """回退旧版：从快照恢复整树；恢复前先给当前状态打快照。"""
    _require_approve(approved)
    sdir = _snap_dir(target)
    snaps = sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []
    if not snaps:
        raise EvolveError("无可用快照，无法回退")
    sid = to or snaps[-1]
    src = os.path.join(sdir, sid)
    if not os.path.isdir(src):
        raise EvolveError("指定快照不存在: %s" % sid)
    before = snapshot(target, "before-rollback")
    for name in os.listdir(target):
        if name == EVOLVE_DIR:
            continue
        p = os.path.join(target, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for name in os.listdir(src):
        s, d = os.path.join(src, name), os.path.join(target, name)
        shutil.copytree(s, d, ignore=_ignore) if os.path.isdir(s) else shutil.copy2(s, d)
    _append_log(target, {"action": "rollback", "at": _ts(), "to": sid,
                         "safety_snapshot": before})
    return sid


def show_log(target):
    entries = _read_log(target)
    if not entries:
        print("（无进化记录）")
        return entries
    for e in entries:
        print("[%s] %s  %s" % (e.get("at"), e.get("action"),
                               e.get("to") or e.get("added") or e.get("file")))
    return entries


def _selftest():
    td = tempfile.mkdtemp()
    pkg = os.path.join(td, "demo-skill")
    os.makedirs(os.path.join(pkg, "references"))
    open(os.path.join(pkg, "SKILL.md"), "w", encoding="utf-8").write("---\nname: demo\n---\n")
    open(os.path.join(pkg, "references", "a.md"), "w", encoding="utf-8").write("原始内容 A\n")
    sample = os.path.join(td, "sample.md")
    open(sample, "w", encoding="utf-8").write("新样本正文\n")

    # 用例1：未授权一律拒绝
    try:
        append(pkg, sample, None, approved=False)
        raise AssertionError("未授权应被拒绝")
    except EvolveError:
        print("用例1 未授权拒绝: PASS")

    # 用例2：append 成功 + 快照 + 日志
    rel = append(pkg, sample, "book", approved=True)
    assert os.path.isfile(os.path.join(pkg, rel)), rel
    assert len(_read_log(pkg)) == 1, _read_log(pkg)
    assert len(os.listdir(_snap_dir(pkg))) == 1
    print("用例2 append 成功: PASS ->", rel)

    # 用例3：correct 唯一命中成功
    correct(pkg, "references/a.md", "原始内容 A", "修正后内容 A", approved=True)
    assert "修正后内容 A" in open(os.path.join(pkg, "references", "a.md"), encoding="utf-8").read()
    print("用例3 correct 成功: PASS")

    # 用例4：不唯一命中被拒（fail-closed）
    open(os.path.join(pkg, "references", "b.md"), "w", encoding="utf-8").write("X X\n")
    try:
        correct(pkg, "references/b.md", "X", "Y", approved=True)
        raise AssertionError("不唯一应被拒绝")
    except EvolveError:
        print("用例4 不唯一拒绝: PASS")

    # 用例5：rollback 到 append 前 -> appended 文件消失、原文恢复
    sid = _read_log(pkg)[0]["snapshot"]
    rollback(pkg, sid, approved=True)
    left = os.listdir(os.path.join(pkg, "references"))
    assert not any("appended" in x for x in left), left
    assert "原始内容 A" in open(os.path.join(pkg, "references", "a.md"), encoding="utf-8").read()
    print("用例5 rollback 恢复: PASS")

    # 用例6：回退本身也可回退（安全快照存在）+ 日志累积（3 条真实动作；被拒的动作不记日志）
    assert any("before-rollback" in x for x in os.listdir(_snap_dir(pkg)))
    assert len(_read_log(pkg)) == 3, _read_log(pkg)
    print("用例6 安全快照与日志: PASS")

    # 用例7：--merge 合并进既有 slot 文件（治碎片化）——两次 merge 只产一个文件、内容叠加、不覆盖原文
    same = os.path.join(td, "sample2.md")
    open(same, "w", encoding="utf-8").write("第二批样本\n")
    r1 = append(pkg, sample, "kb", approved=True, merge=True)
    r2 = append(pkg, same, "kb", approved=True, merge=True)
    assert r1 == r2 == "references/kb.md", (r1, r2)
    kb = os.path.join(pkg, "references", "kb.md")
    txt = open(kb, encoding="utf-8").read()
    assert "新样本正文" in txt and "第二批样本" in txt, txt
    assert txt.count("evolve:append") == 2, txt.count("evolve:append")
    assert len(_read_log(pkg)) == 5, _read_log(pkg)
    print("用例7 merge 合并归入 slot: PASS")

    print("self-test PASS")


def main():
    ap = argparse.ArgumentParser(description="标准件进化三动作（追加/修正/回退）")
    ap.add_argument("action", nargs="?", choices=["append", "correct", "rollback", "log"])
    ap.add_argument("--target", help="标准件目录")
    ap.add_argument("--add", help="append：待追加的新材料文件")
    ap.add_argument("--slot", help="append：样本归类名（可选）")
    ap.add_argument("--merge", action="store_true",
                    help="append：与 --slot 合用，合并进既有 references/<slot>.md（无则新建），不生成新文件")
    ap.add_argument("--file", help="correct：待修正文件（相对标准件目录）")
    ap.add_argument("--old", help="correct：待替换原文")
    ap.add_argument("--new", help="correct：替换后新文")
    ap.add_argument("--to", help="rollback：目标快照 ID（默认最近一个）")
    ap.add_argument("--approve", action="store_true", help="确认执行（缺省则拒绝）")
    ap.add_argument("--self-test", action="store_true", help="跑内置自测")
    args = ap.parse_args()

    if args.self_test or not args.action:
        _selftest()
        return
    try:
        if args.action == "append":
            print("已追加:", append(args.target, args.add, args.slot, args.approve, merge=args.merge))
        elif args.action == "correct":
            print("已修正:", correct(args.target, args.file, args.old, args.new, args.approve))
        elif args.action == "rollback":
            print("已回退到快照:", rollback(args.target, args.to, args.approve))
        elif args.action == "log":
            show_log(args.target)
    except EvolveError as e:
        print("拒绝执行: %s" % e)
        sys.exit(2)


if __name__ == "__main__":
    main()
