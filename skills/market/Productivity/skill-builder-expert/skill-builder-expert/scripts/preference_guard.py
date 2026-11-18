#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preference_guard.py — 本地偏好守卫（REF-ADT-037 专用机检，fail-closed）

四查（P1–P4）：
  P1 规则册存在且含清除条款（用户可随时清除偏好，必须有落点）
  P2 首屏透明告知语在交互模板文本中（不隐蔽采集，必须事先告知）
  P3 偏好路径仅限本地相对文件名；网络字样与绝对路径零容忍
  P4 偏好文件名不入对外交付视图（打包排除清单与排除扫描双保险）

指向式纪律：违例字面一律运行时拼接，本文件不复述完整违例词。
退出码：0 = 全过；1 = 检出违例；2 = 用法错误。
"""

import argparse
import re
import sys
from pathlib import Path

RULE_BOOK = "references/REF-ADT-037_AdaptivePreference.md"
MENU_BOOK = "references/REF-TMP-003_MenuInteraction.md"

# P2 首屏告知语关键句（须逐字存在于交互模板）
_NOTICE_KEY_PHRASES = [
    "可在你当前设备本地留存你的使用偏好",
    "不会向外上传",
    "随时可以回复 **【清除偏好】** 一键清除记忆、重置全部配置",
]

# P3 网络与绝对路径特征（运行时拼接，防自咬）
_NET_PARTS = ["ht", "tp" + "://", "ft" + "p", "u" + "pl" + "oad", "do" + "wnl" + "oad",
              "sync", "cl" + "oud", "re" + "mote", "api." + "com"]
_ABS_WIN = re.compile(r"[A-Za-z]:\\\\")
_ABS_POSIX = re.compile(r"(?<![\w.])/[\w\-]+/[\w\-]+\.json")

PREF_NAME = "user_preference.json"


def _scan_text(text: str, label: str, fails: list, idx_label: str) -> None:
    """对一份文本执行 P3 网络字样与绝对路径扫描。"""
    low = text.lower()
    for parts in _NET_PARTS:
        if parts in low:
            fails.append(f"{idx_label} {label}: 检出网络字样特征（偏好必须仅存本地）")
    if _ABS_WIN.search(text):
        fails.append(f"{idx_label} {label}: 检出 Windows 绝对路径（偏好必须为工作区相对路径）")
    if _ABS_POSIX.search(text):
        fails.append(f"{idx_label} {label}: 检出 POSIX 绝对路径（偏好必须为工作区相对路径）")


# P5 快照档案白名单/黑名单声明（须存在于规则册——五类白名单＋黑名单严禁存入）
P5_KEY_PHRASES = [
    "白名单，仅下面这些，禁止扩列",
    "黑名单严禁存入",
    "不和 Agent 平台原生会话记忆、平台记忆并行",
]

def run_checks(root: Path) -> list:
    fails = []
    rule = root / RULE_BOOK
    menu = root / MENU_BOOK

    # P1 规则册存在 + 清除条款
    if not rule.exists():
        fails.append(f"P1 规则册缺失: {RULE_BOOK}")
    else:
        t = rule.read_text(encoding="utf-8")
        if "清除偏好" not in t or "立即删除" not in t:
            fails.append("P1 规则册缺清除条款（清除口令→删文件→回执，三要素须齐）")
        for banned in ("回传", "跨用户学习", "隐蔽采集"):
            if ("禁止" not in t and "不得" not in t and "永不" not in t) or banned not in t:
                fails.append(f"P1 规则册缺边界红线条款: {banned}")
        _scan_text(t, RULE_BOOK, fails, "P3")

    # P2 首屏告知语
    if not menu.exists():
        fails.append(f"P2 交互模板缺失: {MENU_BOOK}")
    else:
        t = menu.read_text(encoding="utf-8")
        for phrase in _NOTICE_KEY_PHRASES:
            if phrase not in t:
                fails.append(f"P2 首屏告知语缺失关键句: 「{phrase[:14]}…」")
        _scan_text(t, MENU_BOOK, fails, "P3")

    # P4 偏好文件名不入包：打包排除 + 包体视图无实体文件
    pkg = root / "scripts" / "package_zip.py"
    if pkg.exists():
        pt = pkg.read_text(encoding="utf-8")
        if PREF_NAME not in pt:
            fails.append("P4 打包排除清单未登记偏好文件名（偏好文件不得入对外交付包）")
    for p in root.rglob(PREF_NAME):
        fails.append(f"P4 包体视图检出实体偏好文件（不得随包分发）: {p.relative_to(root)}")

    # P5 快照档案白名单/黑名单声明
    snp = root / "references" / "REF-SNP-051_UserSnapshotProfile.md"
    if snp.exists():
        _snp_t = snp.read_text(encoding="utf-8", errors="replace")
        for _k in P5_KEY_PHRASES:
            if _k not in _snp_t:
                fails.append(f"P5 快照档案声明缺失: 规则册缺『{_k}』（REF-SNP-051，fail-closed）")
    else:
        fails.append("P5 快照档案规则册缺失: references/REF-SNP-051_UserSnapshotProfile.md")
    return fails




def self_test() -> int:
    """阳/阴用例自测：阳性必须拦，阴性必须放行。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src = Path(td)
        (src / "references").mkdir()
        (src / "scripts").mkdir()
        # 组装一份合规定册与模板
        rule_text = (
            "# 偏好规则\n\n"
            "用户说「清除偏好」→ 立即删除 user_preference.json 并回执。\n\n"
            "边界红线：禁止回传；禁止跨用户学习；禁止隐蔽采集。\n"
            "存放：工作区相对路径 user_preference.json。\n"
        )
        notice = (
            "【偏好存储说明】为更好理解你的需求、减少重复配置，持续帮你高效搭建和评测技能，"
            "本技能可在你当前设备本地留存你的使用偏好。偏好数据仅存储在你本机环境，不会向外上传、"
            "不会共享，也不会用于其他用户的模型学习。你拥有完整控制权，"
            "随时可以回复 **【清除偏好】** 一键清除记忆、重置全部配置。\n"
        )
        (src / "references" / Path(RULE_BOOK).name).write_text(rule_text, encoding="utf-8")
        (src / "references" / Path(MENU_BOOK).name).write_text(notice, encoding="utf-8")
        (src / "scripts" / "package_zip.py").write_text(
            "EXCLUDE_NAMES = {%r}\n" % PREF_NAME, encoding="utf-8")
        # P5 夹具：最小快照档案规则册样本（含三条声明关键句）
        snp_text = (
            "# 业务快照档案规范（自测样本）\n\n"
            "白名单，仅下面这些，禁止扩列。\n"
            "黑名单严禁存入。\n"
            "不和 Agent 平台原生会话记忆、平台记忆并行。\n"
        )
        (src / "references" / "REF-SNP-051_UserSnapshotProfile.md").write_text(
            snp_text, encoding="utf-8")
        f1 = run_checks(src)
        if f1:
            print("自测失败：合规样本被拦 ->", f1)
            return 1

        # 阳性样本定向注入，必须各自被拦
        # 定向阳性1：模板删掉告知语 → P2 必拦
        (src / "references" / Path(MENU_BOOK).name).write_text("菜单文本，无告知语。", encoding="utf-8")
        if not run_checks(src):
            print("自测失败：缺告知语未拦")
            return 1
        (src / "references" / Path(MENU_BOOK).name).write_text(notice, encoding="utf-8")
        # 定向阳性2：规则册混入网络字样 → P3 必拦
        bad = rule_text + "备份地址：" + "ht" + "tp://exa" + "mple.com/prefs.json\n"
        (src / "references" / Path(RULE_BOOK).name).write_text(bad, encoding="utf-8")
        if not any("网络字样" in f for f in run_checks(src)):
            print("自测失败：网络字样未拦")
            return 1
        (src / "references" / Path(RULE_BOOK).name).write_text(rule_text, encoding="utf-8")
        # 定向阳性3：包体混入实体偏好文件 → P4 必拦
        (src / PREF_NAME).write_text("{}", encoding="utf-8")
        if not any("实体偏好文件" in f for f in run_checks(src)):
            print("自测失败：实体偏好文件未拦")
            return 1

    print('{"ok": true, "self_test": "preference_guard 阳/阴用例全过"}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="本地偏好守卫（P1–P4）")
    ap.add_argument("root", nargs="?", default=".", help="技能包根目录")
    ap.add_argument("--self-test", action="store_true", help="运行阳/阴用例自测")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    root = Path(args.root)
    if not root.exists():
        print(f"root 不存在: {root}")
        return 2
    fails = run_checks(root)
    if fails:
        for f in fails:
            print("FAIL", f)
        print(f"偏好守卫拦截 {len(fails)} 处，禁止出包")
        return 1
    print("PASS 本地偏好守卫 P1–P5 全过（规则册/告知语/仅本地/不入包）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
