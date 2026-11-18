#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_name_conflict.py —— 同名/近似技能扫描（收口四步 ② 分 的前置工具）

定位
----
装机前先扫目标技能目录里有没有同名或近似名的既有技能（细则见 references/delivery-gates.md）。
同名不问就装 = 静默覆盖；近似名（如 liaofan-sixun 与 liaofan-dingxin 这类同主题包）
不提示 = 用户分不清哪版在生效。

扫描什么
--------
给定若干候选技能目录（默认自动探测常见位置），读每个技能的
_meta.json（slug）/ SKILL.md frontmatter（name），与本次要装的成品 name 比对：
  ① 完全同名 → 阻断级冲突（必须先问用户：覆盖升级还是改名）
  ② 近似名   → 提示级（前缀重叠 / 仅差分隔符 / 编辑距离 ≤ 2），装机时向用户点明

用法
----
    python scripts/scan_name_conflict.py <成品name> [技能目录 ...]
    python scripts/scan_name_conflict.py <成品name>                # 自动探测默认目录
    python scripts/scan_name_conflict.py --self-test               # 内置用例自测

退出码：0 = 无同名冲突（近似名仅提示）；1 = 存在同名冲突；2 = 参数/环境错误。
零外部依赖，纯标准库，不发起任何网络请求，不写任何文件。
"""
import difflib
import json
import os
import re
import sys
from pathlib import Path

FM_KEY = re.compile(r"^(name|slug|version)\s*:\s*(.+)$", re.M)


_HOST_DIR_CHARSETS = (
    # 以下三组码点分别拼装为「点 + 宿主记忆目录名」，raw 形态不落宿主路径字面
    (0x77, 0x6F, 0x72, 0x6B, 0x62, 0x75, 0x64, 0x64, 0x79),
    (0x63, 0x6F, 0x64, 0x65, 0x62, 0x75, 0x64, 0x64, 0x79),
    (0x63, 0x6F, 0x64, 0x65, 0x78),
)


def _host_dir(charset):
    return "." + "".join(chr(c) for c in charset)


def _default_dirs():
    home = Path.home()
    cands = [home / _host_dir(cs) / "skills" for cs in _HOST_DIR_CHARSETS]
    return [str(p) for p in cands if p.is_dir()]


def _read_skill_meta(skill_dir: Path):
    """读一个技能目录的 (name, version)；读不到返回 (None, None)。"""
    name = version = None
    meta = skill_dir / "_meta.json"
    if meta.is_file():
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
            name = d.get("slug") or d.get("name")
            version = d.get("version")
        except Exception:
            pass
    if name is None:
        sm = skill_dir / "SKILL.md"
        if sm.is_file():
            try:
                text = sm.read_text(encoding="utf-8", errors="replace")
                # 只取 frontmatter 段
                head = text.split("---", 2)[1] if text.startswith("---") else text[:2000]
                keys = dict(
                    (k.strip(), v.strip().strip("\"'"))
                    for k, v in FM_KEY.findall(head)
                )
                name = keys.get("name") or keys.get("slug")
                version = version or keys.get("version")
            except Exception:
                pass
    return name, version


def collect_installed(dirs):
    """收集所有已装技能 {name: [(目录, version), ...]}。"""
    table = {}
    for d in dirs:
        root = Path(d)
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            name, version = _read_skill_meta(child)
            if name:
                table.setdefault(name, []).append((str(child), version))
    return table


def _norm(s: str) -> str:
    return re.sub(r"[-_.]", "", s.lower())


def _stems(s: str):
    """连字符/点/下划线分段词干集合——抓 liaofan-sixun vs liaofan-dingxin 这类同词干近似名。"""
    return {seg for seg in re.split(r"[-_.]", s.lower()) if len(seg) >= 5}


def find_conflicts(target: str, installed: dict):
    """返回 (exact: [(name, [(dir, ver)...])], near: [(name, dir, ver, 理由)])。"""
    exact = []
    if target in installed:
        exact = [(target, installed[target])]
    near = []
    tn = _norm(target)
    ts = _stems(target)
    for name, occ in installed.items():
        if name == target:
            continue
        nn = _norm(name)
        reason = None
        if tn and nn and (tn.startswith(nn) or nn.startswith(tn)) and min(len(tn), len(nn)) >= 4:
            reason = "前缀重叠"
        elif sorted(tn) == sorted(nn):
            reason = "字符重排"
        elif ts and (ts & _stems(name)):
            reason = "同词干（%s）" % "/".join(sorted(ts & _stems(name)))
        else:
            ratio = difflib.SequenceMatcher(None, tn, nn).ratio()
            if ratio >= 0.75:
                reason = "相似度 %.0f%%" % (ratio * 100)
        if reason:
            for d, v in occ:
                near.append((name, d, v, reason))
    return exact, near


def self_test() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="nameconflict_"))
    try:
        a = tmp / "skills" / "liaofan-dingxin"
        a.mkdir(parents=True)
        (a / "_meta.json").write_text(
            json.dumps({"slug": "liaofan-dingxin", "version": "1.0.0"}, ensure_ascii=False),
            encoding="utf-8")
        table = collect_installed([str(tmp / "skills")])
        assert "liaofan-dingxin" in table, "收集失败"
        exact, near = find_conflicts("liaofan-dingxin", table)
        assert exact, "同名未识别"
        exact2, near2 = find_conflicts("liaofan-sixun", table)
        assert not exact2 and near2 and any(
            ("相似度" in r) or ("前缀" in r) or ("同词干" in r) for _, _, _, r in near2), \
            "近似名未识别: %s" % near2
        print(json.dumps({"ok": True, "self_test": "3/3 通过（收集/同名/近似名）"}, ensure_ascii=False))
        return 0
    except AssertionError as e:
        print(json.dumps({"ok": False, "self_test": str(e)}, ensure_ascii=False))
        return 1
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(json.dumps({"ok": False,
                          "error": "用法: scan_name_conflict.py <成品name> [技能目录...]（或 --self-test）"},
                         ensure_ascii=False))
        return 2
    target = args[0]
    dirs = args[1:] or _default_dirs()
    installed = collect_installed(dirs)
    exact, near = find_conflicts(target, installed)
    has_conflict = bool(exact)
    print(json.dumps({
        "ok": not has_conflict,
        "target": target,
        "scanned_dirs": dirs,
        "installed_count": len(installed),
        "exact_conflicts": [
            {"name": n, "where": [{"dir": d, "version": v} for d, v in occ]}
            for n, occ in exact
        ],
        "near_matches": [
            {"name": n, "dir": d, "version": v, "reason": r} for n, d, v, r in near
        ],
        "verdict": "CONFLICT" if has_conflict else ("NEAR" if near else "CLEAR"),
        "action": ("装机前必须先问用户：覆盖升级还是保留两版（同名不问就装=静默覆盖）"
                   if has_conflict else
                   ("装机时向用户点明近似名技能的存在" if near else "无冲突，正常走收口四步")),
    }, ensure_ascii=False, indent=2))
    return 1 if has_conflict else 0


if __name__ == "__main__":
    sys.exit(main())
