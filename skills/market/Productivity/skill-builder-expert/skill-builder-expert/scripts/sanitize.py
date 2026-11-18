# -*- coding: utf-8 -*-
"""sanitize.py —— 接料清洗层（威胁模型）：把不可见字符当攻击面清掉并如实报告。

要解决的问题：接料只判「这份材料能不能读」是不够的，还要判「读进来的东西干不干净」。
不可见字符可以把一段隐藏指令夹带进材料里 —— 人看着是正常内容，模型读到的却是被注入的指令。

分 5 组（分组本身即说明「攻击者拿它干什么」）：
  1 零宽字符     —— 渲染为无，夹在字间，人看不见、模型照读。
                    （注：ZWJ/200D 用于 emoji 家族序列时会被一并拆散，属可接受净化 —— 拆散后仍是各字符本身。）
  2 方向控制符   —— Trojan Source（CVE-2021-42574）：不改字符序列，改人眼看到的顺序，
                    于是「审阅的人看到的」与「模型读到的」不一致。删掉它，渲染顺序回到逻辑顺序。
                    （正常 RTL 书不受影响：Unicode 双向算法本就按字符自身定方向，无需这些显式控制符。）
  3 不可见字母   —— 不是格式控制符（按类别过滤会漏），却同样零宽，能撑开隐藏文本。
  4 变体选择符   —— 已知隐写通道：payload 编成 VS 序列，任何渲染器都看不见、模型读得出。
                    **边界**：U+FE0F（Emoji 呈现选择符）是彩色 emoji 的常规组成、人人可见，
                    不计入本组（有意放行）；本组只收真正不可见的那一侧 —— U+FE00–U+FE0E
                    （VS1–VS15）与 U+E0100–U+E01EF（补充变体选择符 VS17–VS256，隐蔽信道首选）。
  5 标签块字符   —— 原为语言标签，现被用来把整段 ASCII 载荷伪装成隐形「标签」字符。

与「本工具的产物不许含不可见字符」是同一条规矩的两面：这边清别人的材料，那边不许自己往产物里注。
二者必须同源 —— 故把判据做成函数 is_invisible_codepoint() 公开给下游，两处漂移即两层都没覆盖。

用法：
  from sanitize import sanitize_text, report_line
  clean, removed, groups = sanitize_text(text)
"""
import sys, os

# 1. 零宽 / 隐形间隔符
ZERO_WIDTH = frozenset({
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM（非首位时）
    0x00AD,  # SOFT HYPHEN
    0x034F,  # COMBINING GRAPHEME JOINER
    0x180E,  # MONGOLIAN VOWEL SEPARATOR
    0x2061,  # FUNCTION APPLICATION
    0x2062,  # INVISIBLE TIMES
    0x2063,  # INVISIBLE SEPARATOR
    0x2064,  # INVISIBLE PLUS
})

# 2. 双向格式控制符 —— Trojan Source 一类（CVE-2021-42574）
BIDI_CONTROLS = frozenset({
    0x200E, 0x200F, 0x061C,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
})

# 3. 不可见字母（Hangul filler 一类）
INVISIBLE_LETTERS = frozenset({0x115F, 0x1160, 0x3164, 0xFFA0})

# 4. 变体选择符（两段区间；U+FE0F 见下方放行说明）
VARIATION_SELECTOR_START = 0xFE00
VARIATION_SELECTOR_END = 0xFE0E           # VS1–VS15：改前字符呈现，几乎不可见 -> 可疑
SUPPLEMENTARY_VS_START = 0xE0100
SUPPLEMENTARY_VS_END = 0xE01EF            # VS17–VS256：完全不可见、少被渲染 -> 隐蔽信道首选
# 放行：U+FE0F 是 Emoji 呈现选择符（让前一个字符显示为彩色 emoji），
# 属 emoji 的常规组成、视觉上人人可见，不是夹带。
# 若计入，任何带 emoji 的正文与文档都会被判为命中，本项随即失去判别力。
EMOJI_PRESENTATION_SELECTOR = 0xFE0F

# 5. 标签块（区间）
TAG_BLOCK_START = 0xE0000
TAG_BLOCK_END = 0xE007F

GROUP_ZERO = "零宽字符"
GROUP_BIDI = "方向控制符"
GROUP_LETTER = "不可见字母"
GROUP_VS = "变体选择符"
GROUP_TAG = "标签块字符"

_GROUP_ORDER = (GROUP_ZERO, GROUP_BIDI, GROUP_LETTER, GROUP_VS, GROUP_TAG)


def group_of(codepoint):
    """返回码点所属分组名；不属于任何组则返回 None。"""
    if codepoint in ZERO_WIDTH:
        return GROUP_ZERO
    if codepoint in BIDI_CONTROLS:
        return GROUP_BIDI
    if codepoint in INVISIBLE_LETTERS:
        return GROUP_LETTER
    if (VARIATION_SELECTOR_START <= codepoint <= VARIATION_SELECTOR_END
            or SUPPLEMENTARY_VS_START <= codepoint <= SUPPLEMENTARY_VS_END):
        return GROUP_VS
    if TAG_BLOCK_START <= codepoint <= TAG_BLOCK_END:
        return GROUP_TAG
    return None


def is_invisible_codepoint(codepoint):
    """渲染为什么都看不见、应从材料里清除的码点。

    公开给下游扫描器：让它能标出「正是抽取阶段会清掉的那些字符」。
    两处集合一旦漂移，就会出现「抽取放行、扫描器却报警」，或更糟 —— 两层都没覆盖。

    边界（有意为之，两端共用同一份口径）：U+FE0F（Emoji 呈现选择符）放行 ——
    它属 emoji 的常规组成、视觉可见；连缀多个 FE0F 可作低带宽隐写，属已知缺口。
    取舍依据：若一律计入，含 emoji 的正文与文档会被大面积误报，本项随即失去判别力。
    """
    return group_of(codepoint) is not None


def sanitize_text(text):
    """清掉不可见字符，返回 (clean_text, removed_count, groups)。

    groups: 命中过的分组名列表，按 _GROUP_ORDER 排序（用于如实报告清了哪些类）。
    """
    if not text:
        return text, 0, []
    out = []
    removed = 0
    hit = set()
    for ch in text:
        g = group_of(ord(ch))
        if g is None:
            out.append(ch)
        else:
            removed += 1
            hit.add(g)
    groups = [g for g in _GROUP_ORDER if g in hit]
    return "".join(out), removed, groups


def report_line(source, removed, groups):
    """给用户看的一句如实报告（不含任何内部术语；说人话、可被用户自行核对）。

    removed <= 0 时返回 ""（没清到就不出声，避免每次都响）。
    """
    if removed <= 0:
        return ""
    kinds = "、".join(groups) if groups else "不可见字符"
    return ("提示：从 %s 里清掉了 %d 处看不见的字符（%s）。"
            "它们可能是材料里被后加进去的隐藏内容，读的时候看不见，机器却会读到。"
            % (source, removed, kinds))


def _self_test():
    """内容级断言：每组都真被清掉、计数与分组正确、正常字符一个不动、幂等。"""
    # 用 chr() 构造，源码里不出现任何不可见字符字面（否则本文件自身会被自己的规矩判死）。
    samples = {
        GROUP_ZERO: chr(0x200B),
        GROUP_BIDI: chr(0x202E),
        GROUP_LETTER: chr(0x3164),
        GROUP_VS: chr(0xFE00),
        GROUP_TAG: chr(0xE0041),
    }
    for g, ch in samples.items():
        assert is_invisible_codepoint(ord(ch)), "%s 样本未被认作不可见" % g
        assert group_of(ord(ch)) == g, "%s 分组归属错了" % g

    # 边界：U+FE0F（emoji 常规组成）放行；补充变体选择符仍属 VS 组
    assert not is_invisible_codepoint(EMOJI_PRESENTATION_SELECTOR), \
        "U+FE0F 应放行（emoji 呈现选择符，人人可见）"
    assert group_of(0xFE0E) == GROUP_VS, "VS15（U+FE0E）仍应属变体选择符组"
    assert group_of(SUPPLEMENTARY_VS_START) == GROUP_VS, "补充变体选择符下界应归 VS 组"
    assert is_invisible_codepoint(SUPPLEMENTARY_VS_END), "补充变体选择符上界应被认出"

    # 正常字符绝不能被误伤（中文/英文/数字/换行/空格/常见符号）
    for ch in "中文Abc123\n\r\t 。，、！？-—_()【】¥%":
        assert not is_invisible_codepoint(ord(ch)), repr(ch) + " 被误判为不可见"

    dirty = "甲" + samples[GROUP_ZERO] + "乙" + samples[GROUP_BIDI] + \
            samples[GROUP_LETTER] + samples[GROUP_VS] + samples[GROUP_TAG] + "丙"
    clean, removed, groups = sanitize_text(dirty)
    assert removed == 5, "应清掉 5 处，实得 %d" % removed
    assert clean == "甲乙丙", "清的应是隐形字符、正文一字不动：%r" % clean
    for g in _GROUP_ORDER:
        assert g in groups, "命中分组缺 " + g
    assert groups == list(_GROUP_ORDER), "分组顺序应稳定：%r" % groups

    # 幂等：再清一次应 0
    clean2, removed2, groups2 = sanitize_text(clean)
    assert clean2 == clean and removed2 == 0 and groups2 == [], "清洗应幂等"

    # 空输入与纯正常输入
    assert sanitize_text("") == ("", 0, [])
    assert sanitize_text(None) == (None, 0, [])
    c3, r3, g3 = sanitize_text("完全正常的一段话。")
    assert (c3, r3, g3) == ("完全正常的一段话。", 0, []), "正常文本不该被改动"

    # 报告行：没清到空白，清到了必含处数与文件名
    assert report_line("a.docx", 0, []) == "", "没清到就不该出声"
    line = report_line("a.docx", 3, [GROUP_ZERO, GROUP_BIDI])
    assert "3" in line and "a.docx" in line and GROUP_BIDI in line, "报告行缺处数/文件名/分组"

    print("sanitize self-test: OK（5 组全命中、正文零误伤、幂等、报告行正确、U+FE0F 放行）")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--self-test":
        sys.stderr.write("用法: python sanitize.py --self-test\n")
        sys.exit(2)
    _self_test()
