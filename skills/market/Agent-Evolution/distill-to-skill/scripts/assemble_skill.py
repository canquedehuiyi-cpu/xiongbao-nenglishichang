# -*- coding: utf-8 -*-
"""assemble_skill.py —— A 模式技能包一键装配器（纯标准库·零第三方依赖）

作用：把 A 模式蒸馏产出的技能包目录（SKILL.md / README.md / references/ / scripts/ /
hooks/）压成「可直接上传 Agent 平台」的标准安装 zip。

—— 出包前强制过门禁（把门禁接在必经之路上）——
本脚本有双重身份，须分流：
  ⓪ 门禁保护对象＝「用户最终拿走的那件东西」：**任何**装配都要过门禁，不看它是不是我们自己的包。
     自举包 → `selfcheck --full`；非自举目录（含用户自己装配的产物包）→ `selfcheck <目录> --product`
     （红线词 / 单字红线 / 构思层残留 / 内部标记残留 / 换行符）。不过即拒绝出包；确需跳过须显式 --gate=off。
  ① 本包自举出包：目标目录里有 scripts/selfcheck.py 与 scripts/verify_render_combos.py
     → 判为自举模式，装配前强制跑 `selfcheck --full`（九扫描/矩阵声明/命名门禁/清单对账/编译/实跑/
     残留复查/组合联测/产物契约/基线），**不通过不出包**；
  ② 用户装配自己的技能包：目标目录没有上述自举脚本 → 只跑安装包硬规校验，照常出包
     （绝不因为用户包没有本包的自检脚本而阻断用户出包）。
门禁模式 --gate=auto|strict|off（默认 auto）：
  auto   = 探测到自举脚本才跑（推荐）
  strict = 无条件跑门禁（CI / 正式发布用；自举脚本缺失也硬失败）
  off    = 不跑门禁（须自行确认；对含自举脚本的包会打印提示）

环境豁免：门禁需要真实渲染环境（中文字体、可起子进程）。环境不具备时判 SKIP 并在
输出中标出，不判失败。

残留清理：验证脚本可能把产物留在 scripts/ 下；装配前后各清一次（限 scripts/ 目录，
避免误删用户文件），确保垃圾不进包。

安装包硬规（对齐 SKILL.md A6#2 / A7）：
  - 无顶层目录：zip 内文件直接位于根，解压不产生嵌套文件夹；
  - UTF-8 无 BOM；mtime 统一；必含 SKILL.md（缺则拒绝出包）；
  - 排除噪音：__pycache__ / *.pyc / .DS_Store / 隐藏项 / 输出 zip 自身 / release/ 元数据目录；
  - 幂等：同一输入重复装配，输出字节一致（MD5 可比对）。

发布清单：自举模式装配成功后，在 release/ 落盘 <版本>-checklist.md 与 <版本>-manifest.json
（文件清单 + 逐文件 MD5，供下版比对变更数）。release/ 属元数据目录，不进安装 zip。

用法：
  python assemble_skill.py <技能包目录> [-o 输出.zip] [--gate auto|strict|off] [--no-release]
  python assemble_skill.py --self-test

零第三方依赖：仅 zipfile / os / sys / json / hashlib / argparse / tempfile / subprocess / datetime。
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from constants import PUBLISH_EXCLUDE   # 出包排除表（按「读者」排除的内部件）·单一事实源

FIXED_DT = (2020, 1, 1, 0, 0, 0)
SKIP_DIRS = {"__pycache__", ".git", ".svn", ".idea", ".vscode", ".pytest_cache", "release"}
SKIP_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_EXT = {".pyc", ".pyo", ".pyd"}
GATE_MODES = ("auto", "strict", "off")
# 验证脚本可能遗留在 scripts/ 下的产物（只在 scripts/ 清，避免误删用户文件）
RESIDUAL_NAMES = {"_dbg.pptx"}
RESIDUAL_PATTERNS = (("t_v_", ".pptx"), ("body_", ".txt"))


class AssembleError(Exception):
    pass


def collect(root, out_zip=None):
    """收集待打包文件，返回 [(绝对路径, zip内相对路径)]，按相对路径排序。"""
    root = os.path.abspath(root)
    out_abs = os.path.abspath(out_zip) if out_zip else None
    items = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns
                        if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            if fn in SKIP_FILES or fn.startswith("."):
                continue
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            full = os.path.join(dp, fn)
            if out_abs and os.path.abspath(full) == out_abs:
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel in PUBLISH_EXCLUDE:
                continue          # 按「读者」排除：给改包的人看的件不进安装包
            if ".bak" in os.path.basename(rel):
                continue          # 备份残件永不进安装包（噪音·2026-10-07 实测混入过一次）
            items.append((full, rel))
    return sorted(items, key=lambda x: x[1])


def excluded_present(root):
    """包内确实存在、但按出包排除表不进安装包的件（用于出厂时如实报告）。"""
    return [rel for rel in PUBLISH_EXCLUDE if os.path.isfile(os.path.join(root, rel))]


def excluded_in_zip(path):
    """安装包内是否混进了出包排除件（出厂前 fail-closed 自校验用）。"""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
    return [rel for rel in PUBLISH_EXCLUDE if rel in names]


def clean_residuals(root):
    """清理验证脚本可能留在包内的产物（限 scripts/ 目录）。返回被清理的文件名。"""
    sd = os.path.join(root, "scripts")
    removed = []
    if not os.path.isdir(sd):
        return removed
    for fn in sorted(os.listdir(sd)):
        hit = fn in RESIDUAL_NAMES or any(
            fn.startswith(a) and fn.endswith(b) for a, b in RESIDUAL_PATTERNS)
        if hit:
            try:
                os.remove(os.path.join(sd, fn))
                removed.append(fn)
            except OSError:
                pass
    return removed


def detect_selfhost(root):
    """目标目录是否为本包（自举）：同时存在 selfcheck.py 与 verify_render_combos.py。"""
    return (os.path.isfile(os.path.join(root, "scripts", "selfcheck.py")) and
            os.path.isfile(os.path.join(root, "scripts", "verify_render_combos.py")))


def run_gate(root):
    """跑自举门禁（selfcheck --full）。返回 (ok, blocked, lines)。
    blocked=True 表示环境不支持起子进程 —— 调用方应判 SKIP 而非失败。"""
    py = sys.executable
    sc = os.path.join(root, "scripts", "selfcheck.py")
    try:
        p = subprocess.run([py, sc, root, "--full"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError as e:
        return True, True, ["[SKIP] 环境不支持子进程，自举门禁未执行（%s）" % e]
    lines = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()]
    return (p.returncode == 0), False, lines


def run_product_gate(target):
    """产物出厂门禁：用本包自带的 selfcheck 扫目标目录（用户最终拿走的那件）。

    与自举门禁（run_gate）的区别：后者验「我们自己的包结构」，
    本函数验「任意交付物里有没有不该有的东西」（selfcheck --product）。
    返回 (ok, blocked, lines)。blocked=True 表示环境不支持 —— 调用方按 SKIP 处理。
    """
    py = sys.executable
    sc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selfcheck.py")
    if not os.path.isfile(sc):
        return True, True, ["[SKIP] 包内未找到 selfcheck.py，产物门禁未执行"]
    try:
        p = subprocess.run([py, sc, target, "--product"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        return True, True, ["[SKIP] 环境不支持子进程，产物门禁未执行（%s）" % e]
    lines = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()]
    return (p.returncode == 0), False, lines


def assemble(root, out_zip=None, gate="auto", info=None):
    """把技能包目录压成标准安装 zip，返回 (zip路径, 文件数)。

    自举模式（或 --gate=strict）下：装配前强制跑门禁，不通过则抛 AssembleError
    （异常消息附门禁输出尾部，便于直接定位）。
    """
    if not os.path.isdir(root):
        raise AssembleError("不是目录: %s" % root)
    if not os.path.isfile(os.path.join(root, "SKILL.md")):
        raise AssembleError("缺 SKILL.md，拒绝出包（这不是一个技能包目录）")
    if gate not in GATE_MODES:
        raise AssembleError("--gate 取值须为 %s" % "/".join(GATE_MODES))
    if not out_zip:
        out_zip = os.path.basename(os.path.abspath(root)) + ".zip"

    selfhost = detect_selfhost(root)
    run_it = (gate == "strict") or (gate == "auto" and selfhost)
    # 非自举目录（用户自己的产物包）同样要过门禁 —— 跑「产物出厂门禁」。
    # 门禁保护的对象是「用户最终拿走的那件东西」，不是只保护我们自己的包。
    run_product = (gate == "auto" and not selfhost)
    gate_lines, gate_ok, gate_blocked, gate_ran = [], True, False, False
    gate_kind = ""

    cleaned_before = clean_residuals(root)
    if gate == "off" and selfhost:
        print("提示: --gate=off —— 已跳过自举门禁；本包含自举脚本，正常应跑门禁。")

    if run_it:
        gate_ran = True
        gate_kind = "selfhost"
        gate_ok, gate_blocked, gate_lines = run_gate(root)
        if not gate_ok and not gate_blocked:
            raise AssembleError(
                "自举门禁未通过，拒绝出包（--gate=%s）。门禁输出尾部：\n%s"
                % (gate, "\n".join(gate_lines[-25:])))
        clean_residuals(root)
    elif run_product:
        gate_ran = True
        gate_kind = "product"
        gate_ok, gate_blocked, gate_lines = run_product_gate(root)
        if not gate_ok and not gate_blocked:
            raise AssembleError(
                "产物出厂门禁未通过，拒绝出包（--gate=%s）。这道门保护的是"
                "「用户最终拿走的那件东西」；确需跳过请显式 --gate=off。\n门禁输出尾部：\n%s"
                % (gate, "\n".join(gate_lines[-25:])))
        clean_residuals(root)

    items = collect(root, out_zip)
    if not items:
        raise AssembleError("目录为空，无可装配文件")
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in items:
            zi = zipfile.ZipInfo(rel, date_time=FIXED_DT)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with open(full, "rb") as f:
                z.writestr(zi, f.read())
    cleaned_after = clean_residuals(root)

    # 出厂前自校验（fail-closed）：安装包内不得含出包排除件。
    # 宁可误停不可漏放 —— 一个自我声明「不参与 Agent 执行」的件混进用户机器，是分类错误，不是小事。
    leaked = excluded_in_zip(out_zip)
    if leaked:
        try:
            os.remove(out_zip)
        except OSError:
            pass
        raise AssembleError(
            "安装包混入内部件（不参与 Agent 执行），已删包拒绝出厂：%s —— 见 constants.PUBLISH_EXCLUDE"
            % "、".join(leaked))

    _kept_out = excluded_present(root)
    if _kept_out:
        print("已按出包排除表排除（留在源码树、不进安装包）: %s" % "、".join(_kept_out))

    if info is not None:
        info.update({
            "selfhost": selfhost,
            "gate_ran": gate_ran,
            "gate_kind": gate_kind,
            "gate_ok": gate_ok,
            "gate_blocked": gate_blocked,
            "gate_lines": gate_lines,
            "gate_reason": ("自举脚本已探测到" if selfhost else
                            "非自举目录：改跑产物出厂门禁（--product）"),
            "cleaned": cleaned_before + cleaned_after,
        })
    return out_zip, len(items)


def verify_zip(path):
    """校验装配结果是否满足安装包硬规，返回问题列表（空 = 通过）。"""
    problems = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "SKILL.md" not in names:
            problems.append("zip 根下无 SKILL.md（有顶层目录或装配错误）")
        for n in names:
            if n.split("/")[0] in SKIP_DIRS or os.path.splitext(n)[1].lower() in SKIP_EXT \
                    or ".bak" in os.path.basename(n):
                problems.append("含噪音条目: %s" % n)
            if n in PUBLISH_EXCLUDE:
                problems.append("含内部件（不参与 Agent 执行）: %s" % n)
            if n.startswith(".") or "/." in n:
                problems.append("含隐藏项: %s" % n)
        for info in z.infolist():
            if info.date_time != FIXED_DT:
                problems.append("mtime 未统一: %s -> %s" % (info.filename, info.date_time))
    return problems


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_version(root):
    p = os.path.join(root, "_meta.json")
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8")).get("version", "")
        except Exception:
            pass
    return ""


def _manifest(root, out_zip=None):
    """{相对路径: md5}，口径与打包一致（不含 release/ 与噪音）。"""
    return {rel: md5(full) for full, rel in collect(root, out_zip)}


def write_release(root, gate_lines, file_count, out_zip=None):
    """落盘 <版本>-checklist.md 与 <版本>-manifest.json 到 release/（不进安装包）。
    返回 (checklist路径, manifest路径, 变更文件列表, 删除文件列表)。"""
    rel = os.path.join(root, "release")
    os.makedirs(rel, exist_ok=True)
    ver = _read_version(root) or "0.0.0"
    cur = _manifest(root, out_zip)

    prev_ver, prev = None, {}
    cands = sorted(fn[:-len("-manifest.json")] for fn in os.listdir(rel)
                   if fn.endswith("-manifest.json") and fn[:-len("-manifest.json")] != ver)
    if cands:
        prev_ver = cands[-1]
        try:
            prev = json.load(open(os.path.join(rel, prev_ver + "-manifest.json"),
                                  encoding="utf-8")).get("files", {}) or {}
        except Exception:
            prev = {}
    changed = sorted(k for k, v in cur.items() if prev.get(k) != v)
    removed = sorted(set(prev) - set(cur))

    mp = os.path.join(rel, "%s-manifest.json" % ver)
    # newline="\n"：显式 LF。Windows 默认 open(...,"w") 会把 \n 翻成 \r\n —— 同一纪律
    # 与 verify_baseline 的 bless 落盘一致，避免「部分文件 CRLF、部分 LF」的隐性不一致。
    with open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"version": ver, "files": cur, "changed_vs": prev_ver,
                   "changed": changed, "removed": removed},
                  f, ensure_ascii=False, indent=2, sort_keys=True)

    now = datetime.datetime.now().isoformat(timespec="seconds")
    who = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
    if prev_ver:
        delta = "与 %s 相比 %d 个文件变更%s" % (
            prev_ver, len(changed), "，%d 个删除" % len(removed) if removed else "")
    else:
        delta = "无上一版清单（首版）"
    body = ["# 发布清单 · v%s" % ver, "",
            "- 生成时间：%s" % now,
            "- 打包人：%s" % who,
            "- 包内文件数：%d" % file_count,
            "- 版本差异：%s" % delta,
            "",
            "## 门禁运行结果", "", "```"]
    body += (gate_lines or ["（未跑门禁：非自举模式或 --gate=off）"])
    body += ["```", "",
             "## 遗留项（占位·发布前人工核对）", "",
             "- [ ] 已确认为本版预期变更（对照上方门禁结果）",
             "- [ ] 无未接线脚本（见 tests/exempt.json 豁免台账）",
             "- [ ] 上传前已过目本清单", ""]
    if changed:
        body += ["## 本版变更文件（%d）" % len(changed), ""]
        body += ["- %s" % c for c in changed[:80]]
        if len(changed) > 80:
            body.append("- …（共 %d 个）" % len(changed))
        body.append("")
    cp = os.path.join(rel, "%s-checklist.md" % ver)
    with open(cp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(body))
    return cp, mp, changed, removed


def _selftest():
    td = tempfile.mkdtemp()
    pkg = os.path.join(td, "demo-skill")
    os.makedirs(os.path.join(pkg, "references"))
    os.makedirs(os.path.join(pkg, "scripts"))
    os.makedirs(os.path.join(pkg, "scripts", "__pycache__"))
    open(os.path.join(pkg, "SKILL.md"), "w", encoding="utf-8").write(
        "---\nname: demo-skill\nversion: \"1.0.0\"\n---\n\n# demo\n")
    open(os.path.join(pkg, "README.md"), "w", encoding="utf-8").write("由 蒸馏成技能Skill 蒸馏产出\n")
    open(os.path.join(pkg, "references", "a.md"), "w", encoding="utf-8").write("# ref\n")
    open(os.path.join(pkg, "scripts", "run.py"), "w", encoding="utf-8").write("print('ok')\n")
    open(os.path.join(pkg, "scripts", "__pycache__", "run.cpython-312.pyc"), "wb").write(b"\x00\x01")
    open(os.path.join(pkg, "_meta.json"), "w", encoding="utf-8").write('{"version": "9.9.9"}\n')

    # 用例1：装配成功且文件数正确（排除 __pycache__ 后应为 5）
    out = os.path.join(td, "demo-skill.zip")
    info = {}
    p, n = assemble(pkg, out, info=info)
    assert n == 5, "文件数应为 5，实得 %d" % n
    print("用例1 装配成功，文件数:", n)

    # 用例2：安装包硬规全过
    probs = verify_zip(p)
    assert not probs, "硬规校验失败: %s" % probs
    print("用例2 安装包硬规: PASS")

    # 用例3：__pycache__ / .pyc 未进包
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
    assert not any("__pycache__" in x or x.endswith(".pyc") for x in names), names
    print("用例3 噪音排除: PASS")

    # 用例4：幂等（重复装配字节一致）
    out2 = os.path.join(td, "demo-skill-2.zip")
    assemble(pkg, out2)
    assert md5(p) == md5(out2), "两次装配字节不一致"
    print("用例4 幂等（MD5 一致）: PASS")

    # 用例5：内容无损（解压读 SKILL.md 一致）
    with zipfile.ZipFile(p) as z:
        got = z.read("SKILL.md").decode("utf-8")
    assert "name: demo-skill" in got, got
    print("用例5 内容无损: PASS")

    # 用例6：缺 SKILL.md 的目录被拒（fail-closed）
    bad = os.path.join(td, "no-skill")
    os.makedirs(bad)
    open(os.path.join(bad, "x.txt"), "w").write("x")
    try:
        assemble(bad, os.path.join(td, "bad.zip"))
        raise AssertionError("缺 SKILL.md 应被拒绝")
    except AssembleError:
        print("用例6 缺 SKILL.md 拒绝出包: PASS")

    # 用例7：用户包（无自举脚本）同样要过门禁 —— 改跑「产物出厂门禁」。
    # 门禁保护的对象是「用户最终拿走的那件东西」，不再对用户产物免检。
    assert info["selfhost"] is False, info
    assert info["gate_ran"] is True and info["gate_kind"] == "product", info
    assert info["gate_ok"] is True, info
    print("用例7 用户包也过产物门禁（内容干净则照常出包）: PASS")

    # 用例8：自举探测 —— 出现 selfcheck.py + verify_render_combos.py 即强制跑门禁
    sh = os.path.join(pkg, "scripts")
    open(os.path.join(sh, "selfcheck.py"), "w").write("import sys\nsys.exit(0)\n")
    open(os.path.join(sh, "verify_render_combos.py"), "w").write("import sys\nsys.exit(0)\n")
    info8 = {}
    assemble(pkg, os.path.join(td, "gate-ok.zip"), gate="auto", info=info8)
    assert info8["selfhost"] is True and info8["gate_ran"] is True and info8["gate_ok"] is True, info8
    print("用例8 自举模式强制过门禁（门禁通过可出包）: PASS")

    # 用例9：门禁失败 -> 拒绝出包（fail-closed）
    open(os.path.join(sh, "selfcheck.py"), "w").write("import sys\nsys.exit(3)\n")
    try:
        assemble(pkg, os.path.join(td, "gate-bad.zip"), gate="auto")
        raise AssertionError("门禁失败应拒绝出包")
    except AssembleError as e:
        assert "拒绝出包" in str(e), str(e)
    print("用例9 门禁失败拒绝出包: PASS")

    # 用例10：release/ 不进安装包 + 清单落盘
    open(os.path.join(sh, "selfcheck.py"), "w").write("import sys\nsys.exit(0)\n")
    os.makedirs(os.path.join(pkg, "release"), exist_ok=True)
    open(os.path.join(pkg, "release", "old.md"), "w").write("# old\n")
    info10 = {}
    p10 = os.path.join(td, "rel.zip")
    _, n10 = assemble(pkg, p10, gate="auto", info=info10)
    with zipfile.ZipFile(p10) as z:
        names10 = z.namelist()
    assert not any(x.startswith("release/") for x in names10), names10
    cp, mp, changed, removed = write_release(pkg, info10.get("gate_lines", []), n10)
    assert os.path.isfile(cp) and os.path.isfile(mp), "发布清单未落盘"
    assert os.path.basename(cp).startswith("9.9.9"), cp
    print("用例10 release/ 不进包 + 发布清单落盘: PASS")

    # 用例11：验证残留被清理（限 scripts/）
    open(os.path.join(sh, "t_v_standard.pptx"), "wb").write(b"x")
    open(os.path.join(sh, "body_a.txt"), "w").write("x")
    info11 = {}
    assemble(pkg, os.path.join(td, "clean.zip"), gate="auto", info=info11)
    assert not os.path.exists(os.path.join(sh, "t_v_standard.pptx")), "残留未清"
    assert "t_v_standard.pptx" in info11["cleaned"], info11["cleaned"]
    print("用例11 验证残留清理: PASS")

    # 用例12：用户包含内部标记 → 产物门禁拦住，拒绝出包（证明这道门真会红）
    dirty = os.path.join(td, "dirty-skill")
    os.makedirs(dirty)
    _mark = "<!-- INTER" + "NAL:BEGIN"
    open(os.path.join(dirty, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(
        "---\nname: dirty\n---\n\n# x\n\n" + _mark + "\n  内部说明\n-->\n")
    open(os.path.join(dirty, "README.md"), "w", encoding="utf-8", newline="\n").write("# 说明\n")
    try:
        assemble(dirty, os.path.join(td, "dirty.zip"))
        raise AssertionError("含内部标记的用户包应被产物门禁拒绝")
    except AssembleError as e:
        assert "产物出厂门禁" in str(e), str(e)
        print("用例12 含内部标记的用户包被拦住（门禁真会红）: PASS")

    # 用例13：出包排除件（给改包的人看的内部件）不进安装包 + 出厂自校验拦得住
    #   判据按「读者」而非「文件类型」：自我声明「不参与 Agent 执行」的件留在源码树、不进包。
    mnt = os.path.join(pkg, "MAINTAINER.md")
    open(mnt, "w", encoding="utf-8", newline="\n").write(
        "# demo 维护者手册\n\n> 本文件不参与 Agent 执行、不被 SKILL.md 加载。\n")
    p13 = os.path.join(td, "excl.zip")
    _, n13 = assemble(pkg, p13, gate="auto")
    with zipfile.ZipFile(p13) as z13:
        assert "MAINTAINER.md" not in z13.namelist(), "内部件混入安装包"
    assert excluded_in_zip(p13) == [], "出厂自校验误报: %s" % excluded_in_zip(p13)
    assert os.path.isfile(mnt), "排除只针对安装包，源码树里的件必须留存"
    bad_zip = os.path.join(td, "leak.zip")
    with zipfile.ZipFile(bad_zip, "w") as zb:
        zb.writestr("SKILL.md", "x")
        zb.writestr("MAINTAINER.md", "y")
    assert excluded_in_zip(bad_zip) == ["MAINTAINER.md"], "应能检出包内内部件"
    assert any("内部件" in x for x in verify_zip(bad_zip)), "verify_zip 未报内部件"
    os.remove(mnt)
    print("用例13 出包排除件不进包 + 出厂自校验: PASS")

    print("self-test PASS")


def main():
    ap = argparse.ArgumentParser(description="A 模式技能包一键装配器")
    ap.add_argument("package_dir", nargs="?", help="技能包目录（须含 SKILL.md）")
    ap.add_argument("-o", "--out", help="输出 zip 路径")
    ap.add_argument("--gate", default="auto", choices=list(GATE_MODES),
                    help="门禁：auto(默认·自举包跑全量、其余跑产物门禁) / strict(无条件跑全量) / off(不跑)")
    ap.add_argument("--no-release", action="store_true", help="不生成 release/ 发布清单")
    ap.add_argument("--self-test", action="store_true", help="跑内置自测")
    args = ap.parse_args()

    if args.self_test or not args.package_dir:
        _selftest()
        return

    info = {}
    try:
        p, n = assemble(args.package_dir, args.out, gate=args.gate, info=info)
    except AssembleError as e:
        print("装配失败：%s" % e)
        sys.exit(2)

    probs = verify_zip(p)
    print("已装配: %s（%d 个文件）" % (p, n))
    if info.get("gate_ran"):
        state = "PASS" if info.get("gate_ok") else ("SKIP(环境不具备)" if info.get("gate_blocked") else "FAIL")
        label = "自举门禁" if info.get("gate_kind") == "selfhost" else "产物出厂门禁"
        print("%s: %s" % (label, state))
    else:
        print("门禁: 未跑 —— %s" % info.get("gate_reason", ""))
    if info.get("cleaned"):
        print("已清理验证残留: %s" % ", ".join(info["cleaned"]))
    print("硬规校验: %s" % ("PASS" if not probs else "FAIL"))
    for x in probs:
        print("  - %s" % x)

    if info.get("selfhost") and not args.no_release and not probs:
        cp, mp, changed, removed = write_release(args.package_dir, info.get("gate_lines", []),
                                                 n, args.out)
        print("发布清单: %s" % cp)
        print("文件指纹清单: %s（%d 个变更%s）"
              % (mp, len(changed), "，%d 个删除" % len(removed) if removed else ""))
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
