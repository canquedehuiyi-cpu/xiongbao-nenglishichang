# -*- coding: utf-8 -*-
"""stamp_signature.py —— 代建成品自动盖戳

作用：每个代建出来的技能包，自动加盖「技术来源署名 + 统一编号」，
让交付物自带可追溯标识（谁做的 + 第几个），同时作为口碑 / 转介绍的有机入口
（克制一行落款，不催、不写分享话术）。

机器盖戳比 AI 凭记忆更可靠，也符合「出厂即达标、自动强制」的底线。

用法：
  python scripts/stamp_signature.py <生成的成品技能目录>            # 盖戳
  python scripts/stamp_signature.py --verify <生成的成品技能目录>   # 只校验，不改文件
  python scripts/stamp_signature.py --self-test                     # 跑六个内置回归用例，不碰任何真实文件
退出码：成功=0；参数错=2；自检不通过=3（拒写，不产生半成品）；自测不过=1。

为什么必须有 --self-test：
  本脚本历史上的两次失效，同属一个模式 —— **改一处、坏一处，而且两次都发生在"改脚本"这个动作上**：
    · 一次：把闭合符当正文结尾 → **整篇正文被丢弃**；
    · 另一次：修"吞正文"时顺手把分隔符也吞了 → **frontmatter 不闭合**，平台解析必失败。
  两次都照样返回 ok:true。所以把四类输入固化成六个用例：**每次改这个脚本，先跑 --self-test 再动手。**
  判据：六个用例里任何一个从 ✅ 变 ❌，就是这次改动引进来的，**不许合入**。
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

# 固定署名文本（门面名 + 品牌口号「只为你更好！」，不抢戏、不低段位）
SOURCE_TEXT = "AI技能Skill代建助手制作，只为你更好！"
SIGNATURE_MARK = "技术来源：AI技能Skill代建助手制作，只为你更好！"
READMORE_MARK = "编号："

BOM = b"\xef\xbb\xbf"


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
    """按字节读入，返回 (文本, 是否有 BOM)。不做 universal-newline 转换。"""
    raw = p.read_bytes()
    if raw.startswith(BOM):
        return raw[len(BOM):].decode("utf-8"), True
    return raw.decode("utf-8"), False


def _write(p: Path, text: str, bom: bool = False) -> None:
    """按字节写回，BOM 原样保留；换行符由文本自身决定，不被平台改写。"""
    data = text.encode("utf-8")
    p.write_bytes((BOM + data) if bom else data)


def _detect_nl(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def split_frontmatter(text: str):
    """把文本切成 (头块, 正文, 换行符)。

    头块 = **含开、闭两行** 的 frontmatter 整块（含各自换行符）；
    正文 = 闭合行之后的**全部内容，逐字不动**。

    找不到可识别的闭合 frontmatter 时返回 (None, text, nl)：
      · 文本不以 ``---`` 开头  → 压根没有 frontmatter（可新建）；
      · 以 ``---`` 开头但无第二个 ``---`` → **有开无闭，文件本身是坏的**（调用方必须拒写）。
    """
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
    """取 frontmatter 头块的「内部各行」（不含开、闭两行）。"""
    lines = head.splitlines()
    return lines[1:-1]


def _postcheck(orig: str, new: str, old_head: Optional[str]) -> Optional[str]:
    """盖戳后自检：返回 None = 通过；返回字符串 = 失败原因（调用方须拒写）。

    为什么必须自检：已知失效形态 —— 分隔符被吞、frontmatter 不闭合，
    脚本照样返回 ``ok: true``，坏包一路走到交付。**「改完了」与「改对了」是两件事**，
    所以这里逐条验，不靠脚本自己说 ok。
    """
    head, body, _ = split_frontmatter(new)
    if head is None:
        return "盖戳后 frontmatter 仍未闭合（缺第二个 ---）"

    inner = _fm_inner_lines(head)

    # ① 正文必须逐字不变（历史失效的同一个位置）
    if old_head is not None:
        _, old_body, _ = split_frontmatter(orig)
        if body != old_body:
            return "盖戳后正文被改动（应逐字不变，长度 %d → %d）" % (len(old_body), len(body))

    # ② 署名与编号各恰好一行（重复盖戳不得叠加）
    if sum(1 for l in inner if l.startswith("tech_source:")) != 1:
        return "tech_source 行数不为 1（重复盖戳会叠加）"
    if sum(1 for l in inner if re.match(r"^build_no:", l)) != 1:
        return "build_no 行数不为 1（重复盖戳会叠加）"

    # ③ frontmatter 内部不得混入分隔符
    if any(l.strip() == "---" for l in inner):
        return "frontmatter 内部混入了分隔符 ---"

    # ④ 原有 frontmatter 各项不得丢
    if old_head is not None:
        old_keys = {l.split(":", 1)[0].strip() for l in _fm_inner_lines(old_head)
                    if ":" in l and not l.startswith(("tech_source:", "build_no:"))}
        new_keys = {l.split(":", 1)[0].strip() for l in inner if ":" in l}
        lost = sorted(old_keys - new_keys)
        if lost:
            return "原有 frontmatter 项丢失：%s" % lost
    return None


def inject_frontmatter(skill_md: Path, source: str, n: Optional[int]) -> None:
    """在 SKILL.md frontmatter 注入 tech_source + build_no（幂等，重复跑不叠加）。

    ⚠️ 关键修复：旧实现把 frontmatter 关闭符 ``\\n---\\n`` 当成正文结尾，
    导致关闭符之后的**整篇正文被丢弃**（区域锚点全部丢失）。

    ⚠️ 关键修复：上一条的修法用
    ``text.split("\\n---\\n", 1)`` 把"frontmatter 块"与"正文"切开 —— 保住了正文，
    **但分隔符本身被 split 吃掉了，重组时没有补回** → 盖完戳 frontmatter 不再闭合，
    平台解析必失败；而且**再盖一次会叠出第二块 frontmatter + 第二行 tech_source**，
    脚本仍然返回 ``ok: true``。根因一句话：**修"吞正文"的时候，顺手把"吞分隔符"引进来了。**
    正确做法：分开取"内部各行"与"正文"，重组时**显式补回开、闭两个分隔符**，
    并在写盘前跑 ``_postcheck`` 自检，不通过一律拒写。
    """
    text, bom = _read(skill_md)
    fm_line = 'tech_source: "%s"' % source
    no_line = "build_no: %d" % n if n is not None else 'build_no: "待登记"'
    head, body, nl = split_frontmatter(text)

    if head is None:
        if text.startswith("---"):
            # 有开无闭：文件本身已经坏了。任何"猜"都会吞正文或毁掉 frontmatter
            # （历史教训就是这么来的）→ 拒写，把问题交给人。
            raise StampError(
                "SKILL.md 的 frontmatter 未闭合（有开头的 --- 但没有第二个 ---）。"
                "先修好这个文件再盖戳；本脚本不猜、不覆盖。")
        new_text = ("---" + nl + fm_line + nl + no_line + nl + "---" + nl + text)
    else:
        kept = [ln for ln in _fm_inner_lines(head)
                if not ln.startswith("tech_source:") and not ln.startswith("build_no:")]
        kept.append(fm_line)
        kept.append(no_line)
        # ★ 修复点：显式补回开、闭两个分隔符（原实现漏了闭合符）
        new_text = "---" + nl + nl.join(kept) + nl + "---" + nl + body

    problem = _postcheck(text, new_text, head)
    if problem:
        raise StampError("盖戳后自检不通过，已拒绝写入：%s" % problem)
    _write(skill_md, new_text, bom)


def append_footer(readme_md: Path, source: str, n: Optional[int]) -> None:
    """在 README.md 末尾追加一行克制落款（用户一眼看到谁做的、第几个）。

    ⚠️ 幂等修复：旧实现用 `open(..., "a")` 追加，
    重复跑会**叠加落款行**（"第1号"、"第2号"…一排），既难看又自相矛盾。
    现在先清掉末尾已有的落款块再写，重跑多少次都只有一行。
    （编号本身仍随每次盖戳递增——那是"第几个代建成品"的计数，属预期行为。）
    """
    no_str = "第%d号" % n if n else "（待登记）"
    text, bom = _read(readme_md)
    nl = _detect_nl(text)
    # ⚠️ 渲染修复：落款前的分隔线**必须自带空行**。
    #   旧写法 text.rstrip("\n") + "\n---\n\n> …" 会让 `---` 紧贴上一行正文，
    #   Markdown 把它读成"上划线标题"（setext H2），上一段正文被渲染成大标题。
    #   实例：成品包 README 的「**常见问题**：见 INSTALL.md 末尾。」正好被 `---` 顶成标题。
    line = nl + nl + "---" + nl + nl + "> " + SIGNATURE_MARK + " · " + READMORE_MARK + no_str + nl
    text = re.sub(r"(?:\r?\n)*---\r?\n\r?\n> " + re.escape(SIGNATURE_MARK) + r"[^\n]*\r?\n?\s*$",
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
            if sum(1 for l in inner if l.startswith("tech_source:")) != 1:
                problems.append("SKILL.md frontmatter 里 tech_source 行数不为 1")
            if sum(1 for l in inner if re.match(r"^build_no:", l)) != 1:
                problems.append("SKILL.md frontmatter 里 build_no 行数不为 1")
    else:
        problems.append("SKILL.md 不存在")

    if readme_md.exists():
        text, _ = _read(readme_md)
        if SIGNATURE_MARK not in text:
            problems.append("README.md 末尾缺落款（技术来源署名）")
    else:
        problems.append("README.md 不存在")
    return problems


# ---------------------------------------------------------------- self-test
# 六个用例覆盖四类输入：标准 / 坏输入 / 无 frontmatter / 结构保真。
# 全部在临时目录里跑，**不碰真实包、不动计数器**（不调 next_seq）。

def _t_standard(d: Path) -> None:
    """① 标准输入：闭合符保留 · 两个键各注入一行 · 正文逐字不变。"""
    body = "# 标题\n\n正文一行\n"
    f = d / "SKILL.md"
    f.write_bytes(("---\nname: x\nversion: \"1.0.0\"\n---\n" + body).encode("utf-8"))
    r = d / "README.md"
    r.write_bytes("## 常见问题\n见 INSTALL.md 末尾。\n".encode("utf-8"))
    inject_frontmatter(f, SOURCE_TEXT, 1)
    append_footer(r, SOURCE_TEXT, 1)
    text = f.read_text(encoding="utf-8")
    head, got_body, _ = split_frontmatter(text)
    if head is None:
        raise AssertionError("盖戳后 frontmatter 未闭合")
    if got_body != body:
        raise AssertionError("盖戳后正文被改动")
    inner = _fm_inner_lines(head)
    if sum(1 for l in inner if l.startswith("tech_source:")) != 1:
        raise AssertionError("tech_source 行数不为 1")
    if sum(1 for l in inner if re.match(r"^build_no:", l)) != 1:
        raise AssertionError("build_no 行数不为 1")
    if "name: x" not in inner:
        raise AssertionError("原有项 name 丢失")
    if SIGNATURE_MARK not in r.read_text(encoding="utf-8"):
        raise AssertionError("README 落款未写入")
    probs = verify(d)
    if probs:
        raise AssertionError("总校验未过：%s" % probs)


def _t_broken(d: Path) -> None:
    """② 坏输入（有开无闭）：必须拒写，文件一字不动。

    这一形态不是假想 —— 它正是**旧版盖过一次戳之后留下的样子**，
    真实会发生的操作就是"拿脚本去救一份已经被盖坏的文件"。
    """
    raw = "---\nname: x\n\n# 标题\n\n正文\n".encode("utf-8")
    f = d / "SKILL.md"
    f.write_bytes(raw)
    try:
        inject_frontmatter(f, SOURCE_TEXT, 1)
    except StampError:
        pass
    else:
        raise AssertionError("坏输入未拒写（期望 StampError）")
    if f.read_bytes() != raw:
        raise AssertionError("拒写后文件仍被改写")


def _t_nofm(d: Path) -> None:
    """③ 无 frontmatter：新建一个闭合块，正文逐字不变。"""
    body = "# 标题\n\n正文\n"
    f = d / "SKILL.md"
    f.write_bytes(body.encode("utf-8"))
    inject_frontmatter(f, SOURCE_TEXT, 1)
    text = f.read_text(encoding="utf-8")
    head, got_body, _ = split_frontmatter(text)
    if head is None:
        raise AssertionError("新建的 frontmatter 未闭合")
    if got_body != body:
        raise AssertionError("新建后正文被改动")
    if any(l.strip() == "---" for l in _fm_inner_lines(head)):
        raise AssertionError("新建块内部混入了分隔符")


def _t_idempotent(d: Path) -> None:
    """④ 幂等：连盖 3 次，结构恒为「独立分隔符 2 · tech_source 1 · build_no 1」。"""
    body = "# 标题\n\n正文\n"
    f = d / "SKILL.md"
    f.write_bytes(("---\nname: x\n---\n" + body).encode("utf-8"))
    seen = set()
    for i in range(3):
        inject_frontmatter(f, SOURCE_TEXT, 1)
        text = f.read_text(encoding="utf-8")
        _, got_body, _ = split_frontmatter(text)
        if got_body != body:
            raise AssertionError("第 %d 次盖戳后正文被改动" % (i + 1))
        seen.add((sum(1 for l in text.splitlines() if l.strip() == "---"),
                  text.count("tech_source:"), text.count("build_no:")))
    if seen != {(2, 1, 1)}:
        raise AssertionError("连盖 3 次结构不稳定：%s" % sorted(seen))


def _t_readme_footer(d: Path) -> None:
    """⑤ README 落款幂等 + 落款分隔线必须自带空行。

    分隔线紧贴上一行时，Markdown 会把它读成 **setext 上划线标题**，
    上一段正文被渲染成大标题（实例：成品的「**常见问题**：见 INSTALL.md 末尾。」正好中招）。
    """
    f = d / "README.md"
    f.write_bytes("## 常见问题\n见 INSTALL.md 末尾。\n".encode("utf-8"))
    for _ in range(3):
        append_footer(f, SOURCE_TEXT, 1)
    text = f.read_text(encoding="utf-8")
    if text.count(SIGNATURE_MARK) != 1:
        raise AssertionError("落款行数为 %d（应恒 1）" % text.count(SIGNATURE_MARK))
    if "\n\n---\n\n> " not in text:
        raise AssertionError("落款分隔线前缺空行（会渲染成上划线标题）")


def _t_bom_crlf(d: Path) -> None:
    """⑥ BOM 与 CRLF 保真：逐字节读写，不被隐式换行转换吞掉。"""
    body = "# 标题\r\n\r\n正文\r\n"
    f = d / "SKILL.md"
    f.write_bytes(BOM + ("---\r\nname: x\r\n---\r\n" + body).encode("utf-8"))
    inject_frontmatter(f, SOURCE_TEXT, 1)
    raw = f.read_bytes()
    if not raw.startswith(BOM):
        raise AssertionError("BOM 丢失")
    text = raw[len(BOM):].decode("utf-8")
    if "\n" in text.replace("\r\n", ""):
        raise AssertionError("行尾被改写（应保持 CRLF）")
    head, got_body, nl = split_frontmatter(text)
    if nl != "\r\n":
        raise AssertionError("换行符识别错：%r" % nl)
    if got_body != body:
        raise AssertionError("正文被改动")


SELFTEST_CASES = (
    ("① 标准输入（带闭合符）：闭合保留 · 键注入 · 正文逐字不变", _t_standard),
    ("② 坏输入（有开无闭）：必须拒写，文件 0 字节变化", _t_broken),
    ("③ 无 frontmatter：新建闭合块，正文逐字不变", _t_nofm),
    ("④ 幂等：连盖 3 次，结构恒为「分隔符 2 · 署名 1 · 编号 1」", _t_idempotent),
    ("⑤ README 落款幂等 + 分隔线自带空行（防上划线标题）", _t_readme_footer),
    ("⑥ BOM 与 CRLF 保真：BOM 仍在 · 行尾不被改写", _t_bom_crlf),
)


def run_self_test() -> int:
    """跑六个回归用例。全部通过返回 0，任一失败返回 1。"""
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
            inject_frontmatter(skill_md, SOURCE_TEXT, n)
        if readme_md.exists():
            append_footer(readme_md, SOURCE_TEXT, n)
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
        "source": SOURCE_TEXT,
        "stamped": {
            "SKILL.md_frontmatter": skill_md.exists(),
            "README.md_footer": readme_md.exists(),
        }
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
