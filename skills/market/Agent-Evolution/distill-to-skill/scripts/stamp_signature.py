# -*- coding: utf-8 -*-
"""stamp_signature.py —— 蒸馏成品自动盖戳（溯源落款）

作用：每个蒸馏出来的标准件，在 README 写入统一溯源落款，用于溯源与权责归属。
落款克制一行、不写营销话术、不锁用户（用户买的是产出，无授权即能运行）。
落款为**可见**的一行；不嵌入任何不可见字符 —— 对用户不透明的东西一律不植。

⚠️ 关键约束（A7 schema 锁定）：溯源信息**只进 README，绝不写进 SKILL.md frontmatter**。
   frontmatter 仅允许骨架列出字段；本脚本不写入 tech_source / build_no 等非标字段，
   只校验 frontmatter 合规（闭合 + 无被禁字段），不改不动 frontmatter 任何一个字。

机器盖戳比 AI 凭记忆更可靠，也符合「出厂即达标、自动强制」的底线。

用法：
  python scripts/stamp_signature.py <生成的成品技能目录>            # 盖戳（README 落款）
  python scripts/stamp_signature.py --verify <生成的成品技能目录>   # 只校验，不改文件
  python scripts/stamp_signature.py --self-test                     # 跑六个内置回归用例，不碰任何真实文件
退出码：成功=0；参数错=2；自检不通过=3（拒写，不产生半成品）；自测不过=1。

--self-test 覆盖：
  把四类输入固化成六个用例；六个用例里任何一个从 ✅ 变 ❌，即判不通过。
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

# 统一溯源落款（与 A0.4 落款文案、selfcheck.py FOOTER 完全一致）
FOOTER = "由 蒸馏成技能Skill 蒸馏产出"

BOM = b"\xef\xbb\xbf"

# 成品里一律不许出现的不可见字符码点（零宽 / 隐形间隔 / 软连字符等）。
# 落款是**可见**的一行；对用户不透明的东西一律不植。
_INVIS_CODES = (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x034F)


def _hex_invis(s: str) -> bool:
    """成品里是否混入不可见字符（零宽 / 隐形间隔等）。"""
    return any(chr(c) in s for c in _INVIS_CODES)


class StampError(Exception):
    """盖戳前置/后置校验不通过 —— 一律拒写，绝不产出半成品。"""


# 计数器放在 builder 包根目录（scripts/ 的上一级）。
# 计数器文件不进成品 zip，
# 因此每台安装环境各自从 1 计数（每台 builder 实例独立编号，不假称全局）。
def seq_path() -> Path:
    return Path(__file__).resolve().parent.parent / "_build_seq.json"


def next_seq() -> Optional[int]:
    """读取并自增本地计数器；计数器不可写时优雅降级为 None（编号记「待登记」）。"""
    p = seq_path()
    n = 1
    try:
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                n = int(d.get("seq", 0)) + 1
            except Exception:
                n = 1
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"seq": n}, f, ensure_ascii=False)
        return n
    except Exception:
        return None


# ---------- 逐字节读写：保住 BOM 与 CRLF，不做任何隐式换行转换 ----------

def _read(p: Path):
    raw = p.read_bytes()
    if raw.startswith(BOM):
        return raw[len(BOM):].decode("utf-8"), True
    return raw.decode("utf-8"), False


def _write(p: Path, text: str, bom: bool = False) -> None:
    data = text.encode("utf-8")
    p.write_bytes((BOM + data) if bom else data)


def _detect_nl(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def split_frontmatter(text: str):
    nl = _detect_nl(text)
    if not text.startswith("---"):
        return None, text, nl
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text, nl
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[:i + 1]), "".join(lines[i + 1:]), nl
    return None, text, nl


def _fm_inner_lines(head: str):
    lines = head.splitlines()
    return lines[1:-1]


def verify_schema(skill_md: Path) -> None:
    """溯源不污染 frontmatter：仅校验 schema 合规，不写入任何字段。

    A7 schema 锁定要求 frontmatter 仅含骨架字段，故盖戳只查不改：
      · 必须闭合（有开头 --- 也有第二个 ---）
      · 不得含 tech_source / build_no 等非标字段
    """
    text, _ = _read(skill_md)
    head, _, _ = split_frontmatter(text)
    if head is None:
        if text.startswith("---"):
            raise StampError(
                "SKILL.md 的 frontmatter 未闭合（有开头的 --- 但没有第二个 ---）。"
                "先修好这个文件再盖戳；本脚本不猜、不覆盖。")
        raise StampError("SKILL.md 没有 frontmatter（骨架模板应自带）。本脚本不新建 frontmatter，避免污染 schema。")
    inner = _fm_inner_lines(head)
    for bad in ("tech_source:", "build_no:"):
        if any(l.startswith(bad) for l in inner):
            raise StampError("frontmatter 含非标字段 %s（A7 schema 锁定禁止，溯源改走 README 落款）" % bad)


def append_footer(readme_md: Path) -> None:
    """在 README.md 末尾追加一行克制落款（统一溯源文本）。

    ⚠️ 幂等保证：直接 `open(..., "a")` 追加会在重复运行时叠加落款行。
    故先清掉末尾已有的落款块再写，重跑多少次都只有一行。
    落款不含任何不可见字符 —— 成品里不存在「用户看不见的标识」。
    """
    text, bom = _read(readme_md)
    nl = _detect_nl(text)
    line = nl + nl + "---" + nl + nl + "> " + FOOTER + nl
    text = re.sub(r"(?:\r?\n)*---\r?\n\r?\n> " + re.escape(FOOTER) + r"[^\n]*\r?\n?\s*$",
                  "", text)
    _write(readme_md, text.rstrip("\r\n") + line, bom)


def verify(out: Path) -> list:
    """只校验，不改文件。返回问题清单（空 = 过）。"""
    problems = []
    skill_md = out / "SKILL.md"
    readme_md = out / "README.md"

    if skill_md.exists():
        text, _ = _read(skill_md)
        head, _, _ = split_frontmatter(text)
        if head is None:
            problems.append("SKILL.md frontmatter 未闭合（缺第二个 ---）")
        else:
            inner = _fm_inner_lines(head)
            if any(l.startswith("tech_source:") for l in inner):
                problems.append("SKILL.md frontmatter 含非标字段 tech_source（A7 禁止）")
            if any(re.match(r"^build_no:", l) for l in inner):
                problems.append("SKILL.md frontmatter 含非标字段 build_no（A7 禁止）")
    else:
        problems.append("SKILL.md 不存在")

    if readme_md.exists():
        rt = _read(readme_md)[0]
        if FOOTER not in rt:
            problems.append("README.md 缺溯源落款")
        if _hex_invis(rt):
            problems.append("README.md 含不可见字符（一律不许植）")
    else:
        problems.append("README.md 不存在")
    return problems


# ---------------------------------------------------------------- self-test
# 六个用例覆盖四类输入：标准 / 坏输入 / 无 frontmatter / 结构保真。
# 全部在临时目录里跑，**不碰真实包、不动计数器**（不调 next_seq）。

def _t_standard(d: Path) -> None:
    """① 标准输入：README 落款写入 · frontmatter 不动、无被禁字段、无不可见字符。"""
    body = "# 标题\n\n正文一行\n"
    f = d / "SKILL.md"
    f.write_bytes(("---\nname: x\nversion: \"1.0.0\"\n---\n" + body).encode("utf-8"))
    r = d / "README.md"
    r.write_bytes("## 常见问题\n见 INSTALL.md 末尾。\n".encode("utf-8"))
    verify_schema(f)
    append_footer(r)
    text = f.read_text(encoding="utf-8")
    head, got_body, _ = split_frontmatter(text)
    if head is None:
        raise AssertionError("frontmatter 未闭合")
    if got_body != body:
        raise AssertionError("frontmatter 被改动（不该动）")
    inner = _fm_inner_lines(head)
    if any(l.startswith("tech_source:") for l in inner):
        raise AssertionError("出现了 tech_source（A7 禁止）")
    if any(re.match(r"^build_no:", l) for l in inner):
        raise AssertionError("出现了 build_no（A7 禁止）")
    rt = r.read_text(encoding="utf-8")
    if FOOTER not in rt:
        raise AssertionError("README 落款未写入")
    probs = verify(d)
    if probs:
        raise AssertionError("总校验未过：%s" % probs)


def _t_broken(d: Path) -> None:
    """② 坏输入（有开无闭）：必须拒写，文件一字不动。"""
    raw = "---\nname: x\n\n# 标题\n\n正文\n".encode("utf-8")
    f = d / "SKILL.md"
    f.write_bytes(raw)
    try:
        verify_schema(f)
    except StampError:
        pass
    else:
        raise AssertionError("坏输入未拒写（期望 StampError）")
    if f.read_bytes() != raw:
        raise AssertionError("拒写后文件仍被改写")


def _t_nofm(d: Path) -> None:
    """③ 无 frontmatter：必须拒写并说明，不自动新建（避免污染 schema）。"""
    body = "# 标题\n\n正文\n"
    f = d / "SKILL.md"
    f.write_bytes(body.encode("utf-8"))
    try:
        verify_schema(f)
    except StampError:
        pass
    else:
        raise AssertionError("无 frontmatter 未拒写（期望 StampError）")


def _t_idempotent(d: Path) -> None:
    """④ 幂等：连盖 3 次，README 落款恒 1 行；frontmatter 结构不变。"""
    body = "# 标题\n\n正文\n"
    f = d / "SKILL.md"
    f.write_bytes(("---\nname: x\n---\n" + body).encode("utf-8"))
    r = d / "README.md"
    r.write_bytes("## 常见问题\n见 INSTALL.md 末尾。\n".encode("utf-8"))
    for _ in range(3):
        verify_schema(f)
        append_footer(r)
    rt = r.read_text(encoding="utf-8")
    if rt.count(FOOTER) != 1:
        raise AssertionError("落款行数为 %d（应恒 1）" % rt.count(FOOTER))
    if _hex_invis(rt):
        raise AssertionError("落款含不可见字符（一律不许植）")
    text = f.read_text(encoding="utf-8")
    head, got_body, _ = split_frontmatter(text)
    if head is None:
        raise AssertionError("frontmatter 被破坏")
    if got_body != body:
        raise AssertionError("frontmatter 被改动")


def _t_readme_footer(d: Path) -> None:
    """⑤ README 落款幂等 + 分隔线自带空行 + 落款不含任何不可见字符。"""
    f = d / "README.md"
    f.write_bytes("## 常见问题\n见 INSTALL.md 末尾。\n".encode("utf-8"))
    for _ in range(3):
        append_footer(f)
    text = f.read_text(encoding="utf-8")
    if text.count(FOOTER) != 1:
        raise AssertionError("落款行数为 %d（应恒 1）" % text.count(FOOTER))
    if "\n\n---\n\n> " not in text:
        raise AssertionError("落款分隔线前缺空行（会渲染成上划线标题）")
    if _hex_invis(text):
        raise AssertionError("落款含不可见字符（一律不许植）")


def _t_bom_crlf(d: Path) -> None:
    """⑥ BOM 与 CRLF 保真：逐字节读写，不被隐式换行转换吞掉。"""
    body = "# 标题\r\n\r\n正文\r\n"
    f = d / "SKILL.md"
    f.write_bytes(BOM + ("---\r\nname: x\r\n---\r\n" + body).encode("utf-8"))
    r = d / "README.md"
    r.write_bytes(BOM + "## 常见问题\r\n见 INSTALL.md 末尾。\r\n".encode("utf-8"))
    verify_schema(f)
    append_footer(r)
    raw = r.read_bytes()
    if not raw.startswith(BOM):
        raise AssertionError("BOM 漏失")
    text = raw[len(BOM):].decode("utf-8")
    if "\n" in text.replace("\r\n", ""):
        raise AssertionError("行尾被改写（应保持 CRLF）")
    if FOOTER not in text:
        raise AssertionError("落款缺失")


SELFTEST_CASES = (
    ("① 标准输入：README 落款写入 · frontmatter 不动 · 无被禁字段 · 无不可见字符", _t_standard),
    ("② 坏输入（有开无闭）：必须拒写，文件 0 字节变化", _t_broken),
    ("③ 无 frontmatter：必须拒写并说明，不自动新建", _t_nofm),
    ("④ 幂等：连盖 3 次，README 落款恒 1 · frontmatter 不变 · 无不可见字符", _t_idempotent),
    ("⑤ README 落款幂等 + 分隔线自带空行 + 落款无不可见字符", _t_readme_footer),
    ("⑥ BOM 与 CRLF 保真：BOM 仍在 · 行尾不被改写", _t_bom_crlf),
)


def run_self_test() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="stamp_selftest_"))
    print("— stamp_signature.py 边界自测 —")
    passed = 0
    for i, (name, fn) in enumerate(SELFTEST_CASES, 1):
        d = tmp / ("case%d" % i)
        d.mkdir()
        try:
            fn(d)
        except Exception as e:
            print("  ❌ %s" % name)
            print("       原因：%s: %s" % (type(e).__name__, e))
        else:
            passed += 1
            print("  ✅ %s" % name)
    total = len(SELFTEST_CASES)
    ok = passed == total
    print("  self-test: %s（%d/%d）" % ("✅ 通过" if ok else "❌ 失败", passed, total))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", nargs="?", help="生成的成品技能目录")
    ap.add_argument("--verify", action="store_true", help="只校验盖戳与 frontmatter 闭合，不改文件")
    ap.add_argument("--self-test", dest="self_test", action="store_true",
                    help="跑六个内置回归用例（拒写 / 幂等 / BOM / CRLF），不碰任何真实文件")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(run_self_test())

    if not args.out_dir:
        print(json.dumps({"ok": False, "error": "缺少参数：成品技能目录（或改用 --self-test）"},
                         ensure_ascii=False))
        sys.exit(2)

    out = Path(args.out_dir).resolve()
    if not out.is_dir():
        print(json.dumps({"ok": False, "error": "目录不存在: %s" % out}, ensure_ascii=False))
        sys.exit(2)

    if args.verify:
        problems = verify(out)
        print(json.dumps({"ok": not problems, "verify": True, "problems": problems},
                         ensure_ascii=False))
        sys.exit(0 if not problems else 3)

    n = next_seq()
    skill_md = out / "SKILL.md"
    readme_md = out / "README.md"
    try:
        if skill_md.exists():
            verify_schema(skill_md)
        if readme_md.exists():
            append_footer(readme_md)
    except StampError as e:
        print(json.dumps({"ok": False, "build_no": n, "error": str(e), "written": False},
                         ensure_ascii=False))
        sys.exit(3)

    problems = verify(out)
    if problems:
        print(json.dumps({"ok": False, "build_no": n, "error": "盖戳后总校验未过",
                          "problems": problems, "written": True}, ensure_ascii=False))
        sys.exit(3)

    print(json.dumps({
        "ok": True,
        "build_no": n,
        "source": FOOTER,
        "stamped": {
            "README.md_footer": readme_md.exists(),
            "invisible_chars": False,
            "frontmatter_touched": False,
        }
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
