#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selfcheck_factory.py —— 产出技能包对照本规范的结构机检

定位
----
Skill技能搭建专家的「自检引擎」机械执行工具（细则见 SKILL.md 第七部分 / 第九部分 30 项）。
对照本规范的结构性校验项，对产出的技能目录做机检，
输出 PASS / FAIL 与问题清单。机器判定优先于人工判读：本脚本 FAIL 即 FAIL。

查什么（结构性，不读业务内容）
------
① 核心文件：SKILL.md / _meta.json / LISTING.md 必存在；
② frontmatter：SKILL.md 必须闭合（两枚 ---），且含 name / slug / version / license / security；
③ 一致性：frontmatter 的 name == slug == 目录名；_meta.json 的 slug 与 name 一致；
④ 交互型判定：若 SKILL.md 出现「交互」「路由索引」「兜底」「FAQ」任一信号，
    视为交互式技能，必须存在「路由索引总表」章节、至少一处 FALLBACK 兜底模板、
    以及 FAQ 章节（或独立 FAQ.md）；
⑤ 三档骨架提示：若存在 hooks/ 或 references/ 或 scripts/，提示按标准档；
    若存在 tests/，提示按重型档（需 golden/异常/防呆用例）。

用法
----
    python scripts/selfcheck_factory.py <产出技能目录>
    python scripts/selfcheck_factory.py --self-test

退出码：0 = PASS；1 = FAIL；2 = 参数/环境错误。
零外部依赖，纯标准库，不发起任何网络请求。
"""
import json
import os
import re
import sys
from pathlib import Path

REQUIRED_CORE = ["SKILL.md", "_meta.json", "LISTING.md"]
FM_KEYS = ("name", "slug", "version", "license", "security")


def _read(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[len(b"\xef\xbb\xbf"):].decode("utf-8"), True
    return raw.decode("utf-8", errors="replace"), False


def split_frontmatter(text: str):
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines(keepends=True)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[:i + 1]), "".join(lines[i + 1:])
    return None, text


def _fm_inner(head: str):
    return head.splitlines()[1:-1]


def check_dir(root: Path, problems: list, hints: list) -> None:
    # ① 核心文件
    for f in REQUIRED_CORE:
        if not (root / f).exists():
            problems.append("[缺失核心文件] %s" % f)

    skill_md = root / "SKILL.md"
    if skill_md.exists():
        text, _ = _read(skill_md)
        head, body = split_frontmatter(text)
        # ② frontmatter 闭合 + 必填字段
        if head is None:
            problems.append("[SKILL.md] frontmatter 未闭合（缺第二个 ---）")
        else:
            inner = _fm_inner(head)
            keys = {ln.split(":", 1)[0].strip() for ln in inner if ":" in ln}
            for k in FM_KEYS:
                if k not in keys:
                    problems.append("[SKILL.md frontmatter] 缺必填字段: %s" % k)
            # ③ 一致性
            name = next((ln.split(":", 1)[1].strip().strip('"\'') for ln in inner
                         if ln.startswith("name:")), None)
            slug = next((ln.split(":", 1)[1].strip().strip('"\'') for ln in inner
                         if ln.startswith("slug:")), None)
            if name and slug and name != slug:
                problems.append("[一致性] frontmatter name(%s) != slug(%s)" % (name, slug))
            if name and name != root.name:
                problems.append("[一致性] name(%s) != 目录名(%s)" % (name, root.name))
            # ④ 交互型信号
            signals = ("交互", "路由索引", "兜底", "FAQ")
            is_interactive = any(s in (head + body) for s in signals)
            if is_interactive:
                if "路由索引" not in (head + body):
                    problems.append("[交互型] 未发现「路由索引总表」章节（V3.2 第3.2章）")
                if not re.search(r"FALLBACK|兜底", head + body):
                    problems.append("[交互型] 未发现兜底(FALLBACK)模板")
                has_faq = ("FAQ" in (head + body)) or (root / "FAQ.md").exists()
                if not has_faq:
                    problems.append("[交互型] 未发现 FAQ 章节或独立 FAQ.md")
        # ⑤ 三档提示（仅提示，不阻断；归入 hints）
        has_hooks = (root / "hooks").is_dir()
        has_refs = (root / "references").is_dir()
        has_scripts = (root / "scripts").is_dir()
        has_tests = (root / "tests").is_dir()
        if has_hooks or has_refs or has_scripts:
            hints.append("[档位提示] 含 hooks/references/scripts → 应按标准档；"
                         "请确认 hooks.json 与 scripts 自测通过")
        if has_tests:
            hints.append("[档位提示] 含 tests/ → 应按重型档；"
                         "请确认 golden/异常/防呆用例齐备")

    # ⑥ 全局可移植铁检（V4.2 0.6 / 第九部分）：禁止写死绝对路径
    # 排除 scripts/ hooks/（专家内部工具机件，非用户交付内容，避免自检误伤）
    for dp, dns, fns in os.walk(root):
        # 跳过构建产物与隐藏目录，避免扫描 quality_gate 自检日志里的绝对路径引发误判
        dns[:] = [d for d in dns if not d.startswith(".") and d != "logs"]
        for fn in fns:
            if fn.startswith("."):
                continue
            rel_dir = Path(dp).relative_to(root).as_posix()
            if rel_dir.startswith("scripts") or rel_dir.startswith("hooks"):
                continue
            if fn.startswith("."):
                continue
            p = Path(dp) / fn
            if p.suffix.lower() in (".md", ".txt", ".json", ".py", ".yaml", ".yml", ".html", ".css", ".js"):
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if re.search(r"[A-Za-z]:\\|/Users/|/root/|/home/[a-z]+/", content):
                    problems.append("[可移植] %s 含写死绝对路径（违反 V4.2 0.6）" % p.relative_to(root).as_posix())

    # _meta.json slug 一致性
    meta_path = root / "_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            skill_md = root / "SKILL.md"
            if skill_md.exists():
                text, _ = _read(skill_md)
                head, _ = split_frontmatter(text)
                if head:
                    name = next((ln.split(":", 1)[1].strip().strip('"\'') for ln in _fm_inner(head)
                                 if ln.startswith("name:")), None)
                    if name and meta.get("slug") != name:
                        problems.append("[_meta.json] slug(%s) != SKILL.md name(%s)"
                                        % (meta.get("slug"), name))
        except Exception as e:
            problems.append("[_meta.json] 不是合法 JSON: %s" % e)


def _self_test() -> int:
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="factory_selfcheck_"))
    try:
        # 用例1：标准合规交互型
        d = tmp / "good-skill"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: good-skill\nslug: good-skill\nversion: \"1.0.0\"\n"
            "license: LicenseRef-Proprietary\nsecurity:\n  external_network: none\n---\n\n"
            "# 标题\n## 路由索引总表\nMAIN-01 FALLBACK-01\n## FAQ\nQ1\n", encoding="utf-8")
        (d / "_meta.json").write_text(
            json.dumps({"slug": "good-skill", "version": "1.0.0"}, ensure_ascii=False) + "\n", encoding="utf-8")
        (d / "LISTING.md").write_text("# L\n", encoding="utf-8")
        p = []
        h = []
        check_dir(d, p, h)
        assert not p, "合规用例不应有问题: %s" % p
        # 用例2：缺 core + frontmatter 坏
        d2 = tmp / "bad-skill"
        d2.mkdir()
        (d2 / "SKILL.md").write_text("# 无 frontmatter\n", encoding="utf-8")
        p2 = []
        h2 = []
        check_dir(d2, p2, h2)
        assert any("缺失核心文件" in x for x in p2), "应报缺失核心文件"
        assert any("frontmatter" in x for x in p2), "应报 frontmatter 问题"
        print(json.dumps({"ok": True, "self_test": "2/2 通过（合规用例零问题 / 坏用例抓到）"}, ensure_ascii=False))
        return 0
    except AssertionError as e:
        print(json.dumps({"ok": False, "self_test": str(e)}, ensure_ascii=False))
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--self-test" in sys.argv:
        return _self_test()
    if not args:
        print(json.dumps({"ok": False, "error": "用法: selfcheck_factory.py <产出技能目录> [--self-test]"}, ensure_ascii=False))
        return 2
    root = Path(args[0]).resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "error": "目录不存在: %s" % root}, ensure_ascii=False))
        return 2
    if not root.name:
        print(json.dumps({"ok": False, "error": "请传技能包目录（目录名须与 name/slug 一致），不要传盘符根目录"}, ensure_ascii=False))
        return 2
    problems = []
    hints = []
    check_dir(root, problems, hints)
    ok = not problems
    print(json.dumps({
        "ok": ok,
        "target": str(root),
        "problems": problems[:60],
        "problem_count": len(problems),
        "hints": hints[:20],
        "verdict": "PASS" if ok else "FAIL",
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
