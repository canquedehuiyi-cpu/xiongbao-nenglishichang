# -*- coding: utf-8 -*-
"""lexicon.py —— 禁用词表「单一事实源」（扫描侧与规范侧共用一份）

本包所有禁用词族只在本文件定义一次；扫描器从这里取表，规范与模板也以本表为准。
一处定义、多处引用 —— 若两处各写一份，改一处忘一处，两侧口径就会分叉。

约定：
  · 被禁字面一律用 Unicode 码点拼装 —— 本文件自身也在扫描范围内，写出字面即自命中；
  · 每一族都带「条数下限」，表被删空时判 FAIL，门禁不许假绿。

用法：
  python scripts/lexicon.py --self-test     # 表结构自测（键齐全 / 下限达标 / 无重复 / 无空项）
退出码：自测通过 = 0；不通过 = 1。
"""

import sys

# 1) Red-line word list (code points; literal form never appears in this source)
REDWORDS = {
    "W1": "\u907f\u5751",
    "W2": "\u9632\u5751",
    "W3": "\u522b\u8e29\u96f9",
    "W4": "\u5c11\u8d70\u5f2f\u8def",
    "W5": "\u9677\u9631",
    "W6": "\u9a97\u5c40",
    "W7": "\u5957\u8def",
    "W8": "\u5751",
}

# 2) Single-char red line (same origin as W8, listed separately for locating)
PIT = "\u5751"

# 3) Design-layer residue markers (meta-narrative / design-side; code points, no literal in source)
DESIGN_MARKERS = [
    "\u8bbe\u8ba1\u76ee\u7684",          # design purpose
    "\u5185\u90e8\u5907\u6ce8",          # internal note
    "\u8bbe\u8ba1\u4fa7\u5185\u5bb9",     # design-side content
    "\u80cc\u666f\u6545\u4e8b",          # background story
    "\u4e3a\u4ec0\u4e48\u505a",          # why do it
    "\u6253\u7b97\u600e\u4e48\u505a",     # how planned
    "\u4f9b\u7ef4\u62a4\u8005",          # for maintainer
    "\u89c4\u5212\u8def\u7ebf",          # planning route
    "\u6218\u7565\u5b9a\u4f4d",          # strategy positioning
    "\u6211\u4eec\u878d\u5408",          # we fuse
    "\u914d\u65b9",                      # recipe / formula
    "\u79d8\u65b9",                      # secret recipe
    "\u8bbe\u8ba1\u56fe",                # design diagram
    "\u8bbe\u8ba1\u84dd\u56fe",          # design blueprint
    "\u66fe\u5bfc\u81f4",                # used-to-cause (background story of a past failure)
    "\u6700\u6613\u5931\u6548",          # most-easily-fails (our own failure analysis)
    "\u4e4b\u6240\u4ee5",                # the-reason-is (design motivation)
    "\u6211\u4eec\u5f53\u65f6",          # we-at-that-time (our past deliberation)
    "\u5f53\u65f6\u6211\u4eec",          # at-that-time-we (our past deliberation)
    "\u8bf4\u767d\u4e86",                # plainly-speaking (colloquial, explaining our thinking)
    "\u975e\u7b80\u5355\u62fc\u51d1",    # not-simply-pieced-together (our design rationale)
    "\u4e00\u5ea6",                      # once (past-state narrative)
    "\u66fe\u786c\u7f16\u7801",          # used-to-hardcode
    "\u65e7\u5b9e\u73b0",                # old implementation
    "\u6839\u6cbb",                      # root-fix narrative
    "\u75c5\u6839",                      # root-cause narrative
    "\u76f2\u533a",                      # blind-spot (our own gap analysis)
    "\u8e29\u8fc7",                      # stepped-on (past incident)
    "\u6f14\u8fdb\u53f2",                # evolution history
    "\u8fdb\u5316\u53f2",                # evolution history
    "\u8bad\u7ec3\u4eba",                # trains-people (lesson)
    "\u6bcf\u6b21\u5fc5\u54cd",          # rings-every-time (lesson)
    "\u6bd4\u4e0d\u68c0\u67e5\u66f4\u7cdf",  # worse-than-not-checking
    "\u6697\u73af",                      # hidden-loop
    "\u8986\u76d6\u5bf9\u8d26",          # coverage-reconciliation (process)
    "\u672c\u8868\u4ec5\u4f59",          # only-N-left (process)
    "\u9632\u9759\u9ed8\u5931\u6548",    # silent-failure-guard (rationale label)
    "\u6b7b\u95e8",                      # dead-gate (rationale label)
    "\u95ee\u9898\u80cc\u666f",          # issue-background (design-doc label)
    "\u76ee\u7684\uff1a",                # "purpose:" (design-rationale label; full-width colon keeps it precise)
    "\u7406\u7531\uff1a",                # "reason:" (design-rationale label; full-width colon keeps it precise)
    "\u63d0\u70bc\u81ea",                # distilled-from (how-we-made-it narrative)
    "\u53d6\u8bc1",                      # evidence-collection (how-we-made-it narrative)
    "\u6f0f\u89c4",                      # rule-omission (our own past failure)
    "\u5168\u91cf\u5ba1\u8ba1",          # full-audit (how-we-made-it narrative)
    "\uff08\u4fee\u8ba2\uff09",          # "(revised)" (version-evolution tag)
]

# 4) Terminology that must be 0 (already changed to 例证 / 防外流 / 门禁; code points, no literal in source)
TERM_MUST_ZERO = ["\u6848\u4f8b", "\u9632\u62ff\u8d70", "\u95f8\u95e8"]  # case / take-away / sluice-gate

# 6) 人群限定词（第八道扫描）：「不设人群限定」铁律的机器判据。
#    口径与规则同源 —— 只收两类：「具体考试/备考词」＋「具体人群身份词」。
#    覆盖边界（刻意不收）：行业名 / 职能名 / 职级名 —— 它们在包内既可能是人群标签，
#    也可能是内容主题与渲染器 demo 数据（示例报表里的业务角色即为职能词），误伤率高；
#    与常用词强碰撞的短考试名同样不收（会撞上「其中…考」「…提高…试」这类正常表述）。
AUDIENCE_MARKERS = [
    # 考试 / 备考类
    "\u8003\u7814",              # postgrad-exam
    "\u8003\u516c",              # civil-service-exam
    "\u8003\u7f16",              # public-post-exam
    "\u56db\u516d\u7ea7",        # cet-band-4-6
    "\u96c5\u601d",              # ielts
    "\u6258\u798f",              # toefl
    "\u671f\u672b",              # final-exam
    # 人群身份类
    "\u5b66\u751f",              # student
    "\u7814\u7a76\u751f",        # postgrad-student
    "\u5e94\u5c4a\u751f",        # fresh-graduate
    "\u5b9d\u5988",              # new-mother
    "\u5b9d\u7238",              # new-father
    "\u5bb6\u5ead\u4e3b\u5987",  # homemaker
    "\u5c0f\u767d",              # novice-label
    "\u8001\u767e\u59d3",        # the-masses
    "\u6253\u5de5\u4eba",        # wage-earner
    "\u5c0f\u8001\u677f",        # small-shop-owner
    "\u5c0f\u672c\u4e70\u5356",  # small-business-label
]

# 词表条数下限：低于此数判 FAIL。
AUDIENCE_FLOOR = 15

# 白名单锚点：本包声明「不按人群收窄」的那一行本身就是规则条文，天然放行。
#   锚点串以码点给出（下），本文件不复述字面 —— 否则门禁会用自己的注释充当锚点，
#   使「声明行是否还在」这道判据恒为真（门开了却没人知道它失效）。
AUDIENCE_ANCHOR = "\u4e0d\u8bbe\u4eba\u7fa4\u9650\u5b9a"

# 7) 禁推销措辞（第九道扫描）：「不推销 / 不替用户决定掏钱」铁律的机器判据。
#    口径 = 只收**命令式购买**与**承诺收益**两类硬推销话术；
#    收词一律用码点（本文件自身也在扫描范围内，写出字面即自命中）。
PROSELL_MARKERS = [
    "\u7acb\u5373\u8d2d\u4e70",          # buy-now (imperative)
    "\u9a6c\u4e0a\u62a2\u8d2d",          # grab-now (imperative)
    "\u8d76\u7d27\u4e0b\u5355",          # hurry-order (imperative)
    "\u7acb\u5373\u4e0b\u5355",          # order-now (imperative)
    "\u626b\u7801\u8d2d\u4e70",          # scan-to-buy (imperative)
    "\u9650\u65f6\u4f18\u60e0",          # limited-time-discount
    "\u9650\u65f6\u7279\u4ef7",          # limited-time-special
    "\u79d2\u6740",                      # flash-sale
    "\u4fdd\u672c\u4fdd\u6536\u76ca",    # principal-and-return-guaranteed
    "\u7a33\u8d5a\u4e0d\u8d54",          # sure-profit
    "\u5305\u8d5a\u4e0d\u8d54",          # guaranteed-profit
    "\u8eba\u8d5a",                      # effortless-earning
    "\u65e5\u5165\u8fc7\u4e07",          # daily-income-claim
    "\u4e00\u672c\u4e07\u5229",          # huge-return-claim
    "\u96f6\u98ce\u9669\u9ad8\u6536\u76ca",  # zero-risk-high-return
]

# 词表条数下限：低于此数判 FAIL（防有人把词表删空让门禁假绿）
PROSELL_FLOOR = 12

# 8) 内部标记（模板层专属，成品中必须 0 残留）。
#    三项管同一件事：给改编者看的说明与自检，不许跟着成品交付给用户。
#    仅在「产物扫描」模式下检查；模板自身含这些字样属正常，不参与该扫描。
INTERNAL_BEGIN_MARK = "<!-- INTERNAL:BEGIN"
PLACEHOLDER_MARK = "\u3010\u6539\u7f16\u4f4d"            # template placeholder opener
INTERNAL_MARKERS = [
    "\u5b57\u6bb5 schema \u9501\u5b9a",       # field-schema-lock line
    "\u9aa8\u67b6\u6765\u6e90",               # skeleton-source line
    "\u6539\u7f16\u4f4d",                     # template-placeholder word
    "\u51fa\u5382\u81ea\u68c0",               # factory-selfcheck heading
    "\u4ea4\u4ed8\u524d\u9010\u6761\u52fe",   # tick-before-delivery line
]
INTERNAL_FLOOR = 5


# ============================================================
# 词表自测（结构级 + 内容级）
# ============================================================
REDWORD_FLOOR = 8
DESIGN_FLOOR = 40
TERM_FLOOR = 3


def _self_test():
    """表结构自测：键齐全 / 下限达标 / 无重复 / 无空项 / 关键项在位。

    内容级断言：不只数条数，还逐项核「关键值确实在表里」——
    抓得住「表还在、值被换掉」这类隐性改动。
    """
    # 1) 红线词族：键恰为 W1..W8
    want = {"W%d" % i for i in range(1, 9)}
    assert set(REDWORDS) == want, "红线词族键不齐: %s" % (set(REDWORDS) ^ want)
    for k, v in REDWORDS.items():
        assert v and v.strip() == v, "红线词 %s 取值异常" % k
    assert len(REDWORDS) >= REDWORD_FLOOR, "红线词族低于下限 %d" % REDWORD_FLOOR

    # 2) 单字红线与红线词族的 W8 同源
    assert len(PIT) == 1, "单字红线必须恰为 1 个字符"
    assert PIT == REDWORDS["W8"], "单字红线与红线词族 W8 不同源"

    # 3) 构思层标记：非空 + 达下限
    assert all(m and m.strip() == m for m in DESIGN_MARKERS), "构思层标记有空项或首尾空白"
    assert len(DESIGN_MARKERS) >= DESIGN_FLOOR, "构思层标记低于下限 %d" % DESIGN_FLOOR

    # 4) 术语零容忍：非空 + 达下限
    assert all(t and t.strip() == t for t in TERM_MUST_ZERO), "术语零容忍表有空项"
    assert len(TERM_MUST_ZERO) >= TERM_FLOOR, "术语零容忍低于下限 %d" % TERM_FLOOR

    # 5) 人群限定词：达下限 + 白名单锚点在位
    assert len(AUDIENCE_MARKERS) >= AUDIENCE_FLOOR, "人群限定词低于下限 %d" % AUDIENCE_FLOOR
    assert AUDIENCE_ANCHOR and AUDIENCE_ANCHOR.strip() == AUDIENCE_ANCHOR, "白名单锚点异常"

    # 6) 禁推销措辞：达下限
    assert len(PROSELL_MARKERS) >= PROSELL_FLOOR, "禁推销措辞低于下限 %d" % PROSELL_FLOOR

    # 6b) 内部标记：达下限 + 无重复 + 占位符开头串须同时在表内
    assert len(INTERNAL_MARKERS) >= INTERNAL_FLOOR, "内部标记低于下限 %d" % INTERNAL_FLOOR
    assert len(INTERNAL_MARKERS) == len(set(INTERNAL_MARKERS)), "内部标记表存在重复项"
    assert any(m in PLACEHOLDER_MARK for m in INTERNAL_MARKERS), \
        "占位符开头串必须被内部标记表覆盖（表项为该串的子串）"
    assert INTERNAL_BEGIN_MARK.startswith("<!--") and INTERNAL_BEGIN_MARK.endswith("BEGIN"), \
        "内部块起始标记形态异常"

    # 7) 各族内部无重复（重复会让「命中数」虚高、定位串行）
    for name, seq in (("DESIGN", DESIGN_MARKERS), ("TERM", TERM_MUST_ZERO),
                      ("AUDIENCE", AUDIENCE_MARKERS), ("PROSELL", PROSELL_MARKERS)):
        assert len(seq) == len(set(seq)), "%s 表存在重复项" % name
    assert len(set(REDWORDS.values())) == len(REDWORDS), "红线词族存在重复值"

    # 8) 内容级抽样：各族关键值确实在位
    assert "\u907f\u5751" in REDWORDS.values(), "红线词族缺关键项"
    assert "\u5c0f\u767d" in AUDIENCE_MARKERS, "人群限定词缺关键项"
    assert "\u79d2\u6740" in PROSELL_MARKERS, "禁推销措辞缺关键项"

    print("self-test PASS: 红线 %d / 构思层 %d / 术语 %d / 人群 %d / 推销 %d / 内部标记 %d"
          % (len(REDWORDS), len(DESIGN_MARKERS), len(TERM_MUST_ZERO),
             len(AUDIENCE_MARKERS), len(PROSELL_MARKERS), len(INTERNAL_MARKERS)))


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
        raise SystemExit(0)
    print("lexicon: 禁用词表单一事实源（用 --self-test 自测）")
