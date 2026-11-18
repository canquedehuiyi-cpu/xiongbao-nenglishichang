#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""package_check.py —— 成品包六合一机检（禁词 / 交易杂质 / CRLF / 隐形字符 / zip时间戳 / 脚本工程护栏）

定位
----
交付闸门第 3.5 查的执行工具（细则见 references/delivery-gates.md 第四节）。
机器判定优先于人工判读：本脚本 FAIL 即 FAIL，不得以「语境不同」放行。

查什么
------
① 禁词：包内文案不得出现任何把用户放在「正在犯错、缺乏判断力」位置上的词。
   词表只以码点内嵌（本文件不含任何禁词字面——存放它的文本自己也不能违）。
② 交易信息杂质：**仅对代建产出的成品启用**（--paying-clean 旗标）。成品要装进团队、
   转给员工，不得携带订单号、金额符号、支付状态字样——交易信息只属于对话与平台账单。
   注意：本规格包自身（SKILL.md / references 等）是计费规则的载体，按单计费口径说明、
   支付账单与授权支付声明、回执纪律条款必然提及金额与订单号，**默认模式不查杂质**；真红线是回执与成品
   模板零杂质（references/receipts.md 与 templates/ 下的成品骨架在成品模式下一并受检）。
③ CRLF：文本文件一律 LF 换行。
④ 隐形字符：零宽字符、方向控制符、不可见字母等隐藏字符零容忍（含文件首 BOM）。
⑤ zip 时间戳一致性（仅当传入 .zip 时）：包内全部条目的 mtime 必须同一值。
⑥ 脚本工程护栏（.py 结构检查）：定义了 main() 的脚本必须带 __main__ 自测入口（守卫内
   可直接运行自验，对照 REF-SKL-007 卡B 第 6 条）；带守卫的脚本必须用 sys.exit 返回
   退出码（宿主可机判）。纯模块文件（无 main 定义）豁免。

用法
----
    python scripts/package_check.py <成品目录>                    # 默认：查①③④⑥
    python scripts/package_check.py <成品.zip>                    # 默认：查①③④⑤⑥
    python scripts/package_check.py <目录|.zip> --paying-clean    # 追加查②（代建成品/回执场景）

退出码：0 = 全部通过（PASS）；1 = 有命中（FAIL）；2 = 参数/环境错误。
零外部依赖，纯标准库，不发起任何网络请求。
"""
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

# ---- ① 禁词表（仅以码点存在；任何文档不得复述字面）----
FORBIDDEN_WORDS = {
    "W1": "\u907f\u5751",
    "W2": "\u9632\u5751",
    "W3": "\u522b\u8e29\u96f7",
    "W4": "\u5c11\u8d70\u5f2f\u8def",
    "W5": "\u9677\u9631",
    "W6": "\u9a97\u5c40",
    "W7": "\u5957\u8def",
    "W8": "\u5751",
}

# ---- ② 交易信息杂质样式 ----
ORDER_NO = re.compile(r"\b(?:out_trade_no|X-Out-Trade-No|交易单号|商户单号|订单号)\s*[:=＝]?\s*\S+", re.I)
MONEY = re.compile(r"[¥￥]\s*\d|\b\d+(?:\.\d+)?\s*元(?![\u4e00-\u9fff])")
PAY_STATE = re.compile(r"paid\s*:\s*true|支付成功|已支付成功|扣款成功", re.I)

# ---- ④ 隐形字符 ----
INVISIBLE = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060\u2061\u2062\u2063\u2064"
    "\ufeff\ufeff\u00ad\u180e]"
)

# 生成器侧自述文件（脚本自己的 docstring 会提到「交易杂质」等词，属工具说明）
TOOL_FILES = {"package_check.py", "package_zip.py", "scan_name_conflict.py"}
TEXT_EXT = {
    ".md", ".txt", ".json", ".py", ".html", ".css", ".js", ".yaml", ".yml",
    ".csv", ".xml", ".ini", ".cfg", ".toml",
}
SKIP_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db"}


def _is_text(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in TEXT_EXT


def _mask(line: str, hit: str) -> str:
    return line.replace(hit, "\u3007" * len(hit))


def check_text(rel: str, text: str, problems: list, paying_clean: bool = False) -> None:
    """对单个文本文件跑 ①③④（默认）或 ①②③④（paying_clean=True）；.py 文件追加第⑥查。rel 为包内相对路径（报告用）。"""
    base = os.path.basename(rel)
    if base in TOOL_FILES:
        return  # 工具自述文件跳过（其 docstring 含检查器自身的词样）
    if rel.lower().endswith(".py"):
        check_py(rel, text, problems)
    for ln, line in enumerate(text.splitlines(), 1):
        for wid, w in FORBIDDEN_WORDS.items():
            if w in line:
                problems.append("[禁词%s] %s:%d | %s" % (wid, rel, ln, _mask(line.strip()[:60], w)))
        if paying_clean:
            for pat, tag in ((ORDER_NO, "订单号"), (MONEY, "金额"), (PAY_STATE, "支付状态")):
                m = pat.search(line)
                if m:
                    problems.append("[杂质·%s] %s:%d | %s" % (tag, rel, ln, _mask(line.strip()[:60], m.group(0))))
        if "\r\n" in line or line.endswith("\r"):
            problems.append("[CRLF] %s:%d" % (rel, ln))
        m = INVISIBLE.search(line)
        if m:
            problems.append("[隐形字符 U+%04X] %s:%d" % (ord(m.group(0)), rel, ln))


# ---- ⑥ 脚本工程护栏（对照 REF-SKL-007 卡B 第 6 条 / 第 4 条）----
def check_py(rel: str, text: str, problems: list) -> None:
    """对 .py 文件做结构级检查（整文本）：有 main() 定义必须带 __main__ 守卫；带守卫必须 sys.exit 退回退出码。"""
    if not re.search(r"^def main\s*\(", text, re.M):
        return  # 纯模块文件（无 main 入口定义）豁免
    if "__main__" not in text:
        problems.append("[脚本护栏·缺自测入口] %s | 定义了 main() 但缺 __main__ 守卫，无法直接运行自验" % rel)
    elif "sys.exit" not in text:
        problems.append("[脚本护栏·退出码缺失] %s | __main__ 守卫未用 sys.exit 返回退出码，宿主无法机判" % rel)


def check_dir(root: Path, problems: list, paying_clean: bool = False) -> int:
    n = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_NAMES and not d.startswith(".")]
        for fn in fns:
            p = Path(dp) / fn
            rel = str(p.relative_to(root)).replace("\\", "/")
            if not _is_text(fn):
                continue
            try:
                raw = p.read_bytes()
            except Exception as e:
                problems.append("[读取失败] %s | %s" % (rel, e))
                continue
            n += 1
            text = raw.decode("utf-8", errors="replace")
            check_text(rel, text, problems, paying_clean)
    return n


def check_zip(zpath: Path, problems: list, paying_clean: bool = False) -> int:
    n = 0
    mtimes = set()
    with zipfile.ZipFile(zpath) as zf:
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            # GBK 文件名兼容（无 0x800 标志位的包按 cp437→gbk 还原）
            name = zi.filename
            if not (zi.flag_bits & 0x800):
                try:
                    name = zi.filename.encode("cp437").decode("gbk")
                except Exception:
                    pass
            n += 1
            mtimes.add(zi.date_time)
            if not _is_text(name):
                continue
            try:
                data = zf.read(zi)
            except Exception as e:
                problems.append("[读取失败] %s | %s" % (name, e))
                continue
            text = data.decode("utf-8", errors="replace")
            check_text(name, text, problems, paying_clean)
    if len(mtimes) > 1:
        problems.append("[zip时间戳不统一] 共 %d 组不同时间戳：%s"
                        % (len(mtimes), sorted(mtimes)[:4]))
    return n


def main() -> int:
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    paying_clean = "--paying-clean" in flags
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(json.dumps({"ok": False, "error": "用法: package_check.py <成品目录|.zip> [--paying-clean]"}, ensure_ascii=False))
        return 2
    target = Path(args[0])
    if not target.exists():
        print(json.dumps({"ok": False, "error": "不存在: %s" % target}, ensure_ascii=False))
        return 2
    problems = []
    if target.is_file() and target.suffix.lower() == ".zip":
        n = check_zip(target, problems, paying_clean)
        mode = "zip"
    else:
        n = check_dir(target, problems, paying_clean)
        mode = "dir"
    ok = not problems
    checks = ["禁词", "CRLF", "隐形字符", "脚本护栏"] + (["交易杂质"] if paying_clean else []) \
        + (["zip时间戳统一"] if mode == "zip" else [])
    print(json.dumps({
        "ok": ok,
        "mode": mode + ("+paying_clean" if paying_clean else ""),
        "files_scanned": n,
        "checks": checks,
        "problems": problems[:80],
        "problem_count": len(problems),
        "verdict": "PASS" if ok else "FAIL",
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
