#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""package_zip.py —— 成品包 zip 装配工具（A 场景四条规范的工具化落点）

定位
----
交付闸门第 4 查的装配工具（细则见 references/delivery-gates.md 第五节）。
A 场景打包一律用本脚本，不再手工压包——四条规范由脚本强制落实：
  ① 文件名全部 UTF-8（zipflf 设 0x800 标志），不含特殊字符与控制字符；
  ② mtime 统一：包内所有条目取同一时间戳（默认＝打包时刻；--mtime fixed
     取固定常量，跨次打包字节级一致）；
  ③ 排除非业务文件：__pycache__、.pyc、.DS_Store、Thumbs.db、隐藏文件一律不进包；
  ④ 打包前逐文本文件校验 LF：检出 CRLF 即拒绝打包并列出文件（先修再打）。

用法
----
    python scripts/package_zip.py <成品目录> -o <输出.zip> [--mtime now|fixed] [--top <顶层目录名>]
    python scripts/package_zip.py --self-test

说明
----
- 顶层目录：默认取成品目录名（= name = slug 三者一致的一环）；上架端形态用 --top ""（根目录直放）。
- 文本文件打包前读原始字节校验：含 \r\n 即拒绝（退出码 3），交付闸门第 3 查同口径。
- 退出码：0 = 成功；1 = 装配失败；2 = 参数错误；3 = CRLF 检出拒绝打包；4 = 自测失败；5 = 出厂质检(技能质量标准核验)未通过拦截；6 = 演进痕迹检出拦截（版本沿革标记/构建计数赋值/迭代句式/内部称谓，清扫后重打）。
- 出厂质检前置闸：当 <成品目录>/_meta.json 设 auto_quality_check=true，或显式 --quality-gate，打包前自动跑 技能质量标准五维；未过则拦截出包（退出码 5）。--no-gate 可强制关闭，绕过最低准入红线，慎用。
零外部依赖，纯标准库，不发起任何网络请求。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

FIXED_MTIME = (2026, 1, 1, 0, 0, 0)
TEXT_EXT = {
    ".md", ".txt", ".json", ".py", ".html", ".css", ".js", ".yaml", ".yml",
    ".csv", ".xml", ".ini", ".cfg", ".toml",
}
# 排除名：非业务文件 + 内部私有区（演进痕迹规范：生产日志、维护看板、构建计数器、
# 写防护机件目录永不入包，仅存内部私有存储区域）
EXCLUDE_NAMES = {
    "__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini", "logs",
    "MAINTAINER.md", "_build_seq.json", "hooks", "user_preference.json",
}
EXCLUDE_EXT = {".pyc", ".pyo", ".bak", ".tmp", ".swp"}


def _is_text(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in TEXT_EXT


def _strip_build_no(rel: str, raw: bytes) -> bytes:
    """入包防御性脱敏：SKILL.md frontmatter 与 _meta.json 不携带构建编号字段。"""
    if rel == "SKILL.md":
        text = raw.decode("utf-8")
        m = re.match(r"(---\n.*?\n---\n)", text, re.S)
        if m:
            head = re.sub(r"(?m)^build_no:\s*[\"']?\d+[\"']?\n", "", m.group(1))
            text = head + text[m.end():]
            return text.encode("utf-8")
    elif rel == "_meta.json":
        try:
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict) and data.pop("build_no", None) is not None:
                return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        except Exception:
            pass
    return raw


DESC_KEYS = ("summary", "description", "description_zh", "description_en")


def sync_meta_desc(skill_md_text: str, meta_raw: bytes) -> bytes:
    """观察项2修复（定稿依据 2026-11-04 三方质检报告）：出包时从 SKILL.md frontmatter
    反向同步四段描述到 _meta.json——多数平台读 frontmatter，若某平台改读 _meta.json，
    缺段会导致多语言与预览摘要降级。SKILL.md 缺某段则跳过该段（通用性）。"""
    try:
        data = json.loads(meta_raw.decode("utf-8"))
        if not isinstance(data, dict):
            return meta_raw
        m = re.match(r"(---\n.*?\n---\n)", skill_md_text, re.S)
        if not m:
            return meta_raw
        changed = False
        for k in DESC_KEYS:
            fm = re.search(r'^%s: "(.*)"$' % k, m.group(1), re.M)
            if fm and data.get(k) != fm.group(1):
                data[k] = fm.group(1)
                changed = True
        if not changed:
            return meta_raw
        return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    except Exception:
        return meta_raw


def _trace_scan_text(rel: str, raw: bytes):
    """入包视图演进痕迹检查：返回命中列表（空 = 通过）。"""
    if not _is_text(rel) or rel.endswith(".py"):
        return []
    sys.path.insert(0, str(Path(__file__).parent))
    import evolution_trace_scan as ets
    text = raw.decode("utf-8", errors="replace")
    # REF-BSE-047 标记区唯一豁免（用户定稿，fail-closed），与 run_scan 同源共用
    text = ets.strip_notice_region(rel, text)
    return ets._scan_text(text)


def collect_files(root: Path, self_use: bool = False):
    """收集 (绝对路径, zip内相对路径)，已排除非业务文件。
    self_use=True（master 自用包）：_build_seq.json（构建序计数器）放行入库——
    公开包排除、自用包需要，差集恒 10 的组成部分。"""
    excl = EXCLUDE_NAMES - {"_build_seq.json"} if self_use else EXCLUDE_NAMES
    items = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in excl if d in dns] and [d for d in dns if d not in excl and not d.startswith(".")] or [d for d in dns if d not in excl and not d.startswith(".")]
        for fn in sorted(fns):
            if fn.startswith(".") or fn in excl:
                continue
            if os.path.splitext(fn)[1].lower() in EXCLUDE_EXT:
                continue
            p = Path(dp) / fn
            items.append((p, p.relative_to(root).as_posix()))
    return items


def content_hash_zip(zip_path):
    """平台内容签名机制公开口径的指纹（依据 REF-SEC-048 第三节，可与其详情页指纹直接核对）：
    遍历 zip 内文件（跳过目录、_meta.json、__MACOSX、.DS_Store、._* 与 Thumbs.db）→
    逐文件 SHA-256 → 相对路径按字典序升序 → 按「路径:哈希\n」拼接 → 对拼接串再算 SHA-256。"""
    entries = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            n = info.filename.replace("\\", "/")
            if (n.endswith("/") or n == "_meta.json" or n.startswith("__MACOSX")
                    or n == ".DS_Store" or os.path.basename(n).startswith("._") or n == "Thumbs.db"):
                continue
            entries.append((n, hashlib.sha256(z.read(info)).hexdigest()))
    blob = "".join("%s:%s\n" % (path, digest) for path, digest in sorted(entries))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_zip(root: Path, out: Path, mtime: tuple, top: str, self_use: bool = False) -> dict:
    items = collect_files(root, self_use=self_use)
    crlf_files = []
    trace_hits = {}
    import re  # noqa: F401  (_strip_build_no 使用)
    for p, rel in items:
        if _is_text(rel):
            raw = p.read_bytes()
            if b"\r\n" in raw:
                crlf_files.append(rel)
            raw = _strip_build_no(rel, raw)
            hits = _trace_scan_text(rel, raw)
            if hits:
                trace_hits[rel] = hits[:10]
    if crlf_files:
        return {"ok": False, "error": "CRLF 检出，拒绝打包（先修为 LF 再打）", "crlf_files": crlf_files}
    if trace_hits and not self_use:
        return {"ok": False, "error": "演进痕迹检出（版本沿革标记/构建计数赋值/迭代句式/内部称谓），"
                                      "清扫完成前禁止打包交付", "trace_hits": trace_hits}
    # self_use=True：自用层包（master）豁免公开层演进痕迹闸——复盘期次编号是自用层功能本体，
    # 公开口径闸只辖公开层（同「平台名只辖公开层」既有惯例，2026-11-11 备案）

    out.parent.mkdir(parents=True, exist_ok=True)
    # 观察项2修复：出包时从 SKILL.md 反向同步四段描述到 _meta.json（内存层，源文件不动）
    sk_text = ""
    sk = root / "SKILL.md"
    if sk.is_file():
        sk_text = sk.read_text(encoding="utf-8")
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p, rel in items:
            raw = p.read_bytes()
            if _is_text(rel):
                raw = _strip_build_no(rel, raw)
            if rel == "_meta.json" and sk_text:
                raw = sync_meta_desc(sk_text, raw)
            arcname = (top + "/" + rel) if top else rel
            zi = zipfile.ZipInfo(arcname, date_time=mtime)
            zi.external_attr = (0o644 | 0o100000) << 16  # rw-r--r-- 常规文件
            zi.compress_type = zipfile.ZIP_DEFLATED
            # 文件名编码：zipfile 对非 ASCII 文件名自动置 UTF-8 标志（0x800）；
            # 纯 ASCII 名无需标志（ASCII 是 UTF-8 的子集）。
            # 注：Python 3.13 写中央目录时会按实际编码重写 flag_bits，
            # 手动置 0x800 会被剥掉——此处不手动设，交给 zipfile。
            zi.create_system = 3
            zf.writestr(zi, raw)
            count += 1
    content_hash = ""
    try:
        content_hash = content_hash_zip(out)
    except Exception:
        pass
    return {"ok": True, "out": str(out), "files": count, "mtime": mtime, "top": top,
            "content_hash": content_hash}


def _pkg_name(root: Path) -> str | None:
    """读包内英文 name（SKILL.md frontmatter，⑪文件名一致性基准）；找不到 SKILL.md 返回 None（非技能包，跳过校验）。"""
    sk = root / "SKILL.md"
    if not sk.is_file():
        for dirpath, _dirs, files in os.walk(root):
            if "SKILL.md" in files:
                sk = Path(dirpath) / "SKILL.md"
                break
        else:
            return None
    try:
        text = sk.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.search(r"^name:\s*(\S+)", text, re.M)
    return m.group(1) if m else None


def self_test() -> int:
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="pkgzip_"))
    try:
        src = tmp / "my-skill"
        src.mkdir()
        (src / "SKILL.md").write_bytes("---\nname: my-skill\n---\n\n# t\n".encode("utf-8"))
        # 注意：测试数据也必须强制 LF——Windows 上 write_text 默认会把 \n 转 CRLF
        (src / "_meta.json").write_bytes(b'{"slug": "my-skill"}\n')
        (src / "__pycache__").mkdir()
        (src / "__pycache__" / "x.pyc").write_bytes(b"\x00")
        sub = src / "使用说明"
        sub.mkdir()
        (sub / "读我.txt").write_bytes(b"\xe4\xb8\xad\xe6\x96\x87\n")  # 中文文件名验证 UTF-8 标志
        r = build_zip(src, tmp / "out.zip", FIXED_MTIME, "my-skill")
        assert r["ok"], "打包失败: %s" % r
        with zipfile.ZipFile(tmp / "out.zip") as zf:
            names = zf.namelist()
            infos = zf.infolist()
            assert len(names) == 3, "非业务文件未排除: %s" % names
            assert all(i.date_time == FIXED_MTIME for i in infos), "mtime 不统一"
            cn = [i for i in infos if "读我" in i.filename]
            assert cn and (cn[0].flag_bits & 0x800), "中文文件名未置 UTF-8 标志"
            assert cn[0].filename == "my-skill/使用说明/读我.txt", "中文文件名乱码: %r" % cn[0].filename
        # CRLF 拒绝
        (src / "bad.txt").write_bytes(b"line1\r\nline2\r\n")
        r2 = build_zip(src, tmp / "out2.zip", FIXED_MTIME, "my-skill")
        assert not r2["ok"] and r2.get("crlf_files") == ["bad.txt"], "CRLF 未拦截: %s" % r2
        # 演进痕迹拦截（入包视图：迭代编号赋值 / 迭代痕迹类字面，词面拼接防自咬）
        src2 = tmp / "trace-skill"
        src2.mkdir()
        head = "---\nname: t\nbuil" + "d_no: 9\n---\n\n正文（v4" + "5 铁规）\n"
        (src2 / "SKILL.md").write_bytes(head.encode("utf-8"))
        r3 = build_zip(src2, tmp / "out3.zip", FIXED_MTIME, "t")
        assert not r3["ok"] and "trace_hits" in r3, "演进痕迹未拦截: %s" % r3
        # _meta.json 构建号字段打包时自动剥离（功能字段保留）
        (src3 := tmp / "strip-skill").mkdir()
        (src3 / "SKILL.md").write_bytes(b"---\nname: t3\n---\n\n# ok\n")
        meta3 = '{"slug": "t3", "version": "1.0.0", "buil' + 'd_no": 12, "auto_quality_check": false}\n'
        (src3 / "_meta.json").write_bytes(meta3.encode("utf-8"))
        r4 = build_zip(src3, tmp / "out4.zip", FIXED_MTIME, "t3")
        assert r4["ok"], "脱敏打包失败: %s" % r4
        import zipfile as _zf
        with _zf.ZipFile(tmp / "out4.zip") as z:
            meta_in = json.loads(z.read("t3/_meta.json").decode("utf-8"))
            assert "buil" + "d_no" not in meta_in and meta_in["version"] == "1.0.0", "构建号未剥离: %s" % meta_in
        print(json.dumps({"ok": True, "self_test": "5/5 通过（装配/排除+CRLF拦截/标志位/演进痕迹拦截/构建号剥离）"},
                         ensure_ascii=False))
        return 0
    except AssertionError as e:
        print(json.dumps({"ok": False, "self_test": str(e)}, ensure_ascii=False))
        return 4
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def quality_gate(root: Path) -> int:
    """出厂质检前置闸（fail-closed）：跑 技能质量标准核验，不过则拦截。返回 0=放行 / 非0=拦截。"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import skill_quality_check
        rc = skill_quality_check.run_trace(root)
    except Exception as e:  # 评测自身异常/未运行 → 同样拦截
        print(json.dumps({"ok": False, "gate": "blocked", "reason": "技能质量标准核验异常: %s" % e}, ensure_ascii=False))
        return 5
    if rc != 0:
        print(json.dumps({"ok": False, "gate": "blocked", "reason": "技能质量标准五维出厂质检未通过，默认拦截出包"}, ensure_ascii=False))
        return 5
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="成品目录")
    ap.add_argument("-o", "--out", help="输出 zip 路径")
    ap.add_argument("--mtime", default="now", choices=["now", "fixed"],
                    help="包内时间戳：now=打包时刻（默认）；fixed=固定常量（跨次打包字节一致）")
    ap.add_argument("--top", default=None,
                    help="zip 内顶层目录名（默认=成品目录名；传空字符串=根目录直放）")
    ap.add_argument("--quality-gate", dest="quality_gate", action="store_true",
                    help="强制开启出厂质检前置闸（技能质量标准核验未过则拦截出包）")
    ap.add_argument("--no-gate", dest="no_gate", action="store_true",
                    help="强制关闭出厂质检前置闸（慎用，绕过最低准入红线）")
    ap.add_argument("--self-use", dest="self_use", action="store_true",
                    help="自用层包（master）：豁免公开层演进痕迹闸（复盘期次编号属自用层功能本体）")
    ap.add_argument("--self-test", dest="self_test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.src or not args.out:
        print(json.dumps({"ok": False, "error": "用法: package_zip.py <成品目录> -o <输出.zip>"}, ensure_ascii=False))
        return 2
    root = Path(args.src).resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "error": "目录不存在: %s" % root}, ensure_ascii=False))
        return 2

    # ⑪文件名一致性（平台要求：压缩包文件名必须与包内英文名一致，否则驳回＋极易与分市场包混淆误传）：
    # 缺省 -o 时自动按包内英文 name 命名；显式 -o 时校验文件名以包内英文 name 开头，违者拒绝出包。
    # 无 SKILL.md 的非技能包（如组件备料件）跳过此查。
    pkg_name = _pkg_name(root)
    if pkg_name:
        if not args.out:
            args.out = "%s.zip" % pkg_name
        if not Path(args.out).name.startswith(pkg_name):
            print(json.dumps({"ok": False, "error": "⑪文件名一致性: 压缩包文件名必须以包内英文 name（%s）开头，当前: %s（文件名与包内英文名不一致会被平台驳回，且易与分市场包混淆误传）" % (pkg_name, Path(args.out).name)}, ensure_ascii=False))
            return 1

    # 出厂质检前置闸（fail-closed）：auto_quality_check 默认开，或显式 --quality-gate
    gate_on = args.quality_gate
    if not args.no_gate and not gate_on:
        meta = root / "_meta.json"
        if meta.is_file():
            try:
                cfg = json.loads(meta.read_text(encoding="utf-8"))
                if cfg.get("auto_quality_check") is True:
                    gate_on = True
            except Exception:
                pass
    if gate_on:
        g = quality_gate(root)
        if g != 0:
            return g

    # 观察项1修复（定稿依据 2026-11-04 三方质检报告，方案A）：出包自动留痕前置到
    # build_zip 之前——质检报告反映本次出包内容，且此刻 _build_seq.json 仍在源目录，
    # 报告可携带真实构建号归档（此前在出包后留痕，报告 build_no 语义错位）。
    # 非阻塞：留痕失败只告警，不影响出包。
    try:
        ext_gate = Path(__file__).resolve().parent / "quality_gate.py"
        subprocess.run([sys.executable, str(ext_gate), str(root), "--quiet"],
                       capture_output=True, timeout=180)
    except Exception:
        pass

    mtime = FIXED_MTIME if args.mtime == "fixed" else time.localtime()[:6]
    top = root.name if args.top is None else args.top
    result = build_zip(root, Path(args.out), mtime, top, self_use=bool(getattr(args, "self_use", False)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else (3 if "crlf_files" in result else (6 if "trace_hits" in result else 1))


if __name__ == "__main__":
    sys.exit(main())
