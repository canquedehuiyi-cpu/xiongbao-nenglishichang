# -*- coding: utf-8 -*-
"""
constants.py —— 蒸馏成技能Skill · 交付口径常量库（唯一事实源）

职责（与 design_tokens.py 的分工，一望名知义）：
    本文件只管「与设计无关的固定口径」，共四类：
      ① 交付目录约定：两层交付（成品落最外层、中间件归隐藏子目录）的唯一来源；
      ② 成品后缀白名单：交付根外层允许出现的成品后缀闭集（文档 / 技能包 / 媒体三族）；
      ③ 三句定稿文本：溯源落款 / 免责声明 / 来源总览；
      ④ 一行反馈口：交付回执。
    字体 / 配色 / 字号 / 序号 / 模式 / 版本等「设计令牌」不在这里 —— 见 design_tokens.py。

单一事实源纪律：
    以上每一项只在此处定义一次，其余全是引用。七个生成器（md / txt / docx / pdf / ppt /
    xlsx / xlsx_chart）与门禁脚本一律引用本模块，不得各写一版字面。
    改落款 / 免责 / 来源总览 / 回执文案，或改成品后缀白名单，只改这里。
"""

# ============ 交付目录约定（全包唯一事实源） ============
# 两层交付：成品落交付根最外层，中间件一律归隐藏子目录 WORK_DIR。
# 该约定是「交付根卫生」检查与各脚本落盘路径的唯一来源，不得各写一版字面。
RUNS_ROOT = "runs"
WORK_DIR = ".work"

# 媒体·档一裁剪成品后缀（音频 / 视频 / 图片）。
# 与 media_ingest 的 AUDIO_EXT / VIDEO_EXT / IMAGE_EXT 同集合 —— 档一裁剪「保留原格式」
# （音频 -c copy 流拷贝、图片选 best-N），产出后缀即投入后缀；_self_test 断言两者一致以防漂移。
# ⚠️ 边界：媒体分段中转件（如 xxx_seg001.wav）与成品同后缀、白名单分不出，靠
#    「中间件一律进 .work/media/」的落盘规范保证 —— 与既有覆盖边界同一条，不在后缀检查内。
MEDIA_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".amr", ".ogg", ".flac", ".aac", ".wma", ".aiff")
MEDIA_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts")
MEDIA_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")

# 交付根外层允许出现的成品后缀（白名单外一律视为散落的中间件）。
# 口径＝「本包可能落在交付根的成品后缀闭集」，不是「生成器产出清单」：
#   文档类 7 生成器产 md/txt/docx/pdf/pptx/xlsx；A 模式技能包产 .zip；媒体档一裁剪产上方三组。
# 无产出路径的后缀不入表（原 .html/.htm/.csv 无产出路径，已移除，不给散落中间件开后门）。
DELIVERY_EXTS = (".md", ".txt", ".docx", ".pdf", ".pptx", ".xlsx", ".zip") \
    + MEDIA_AUDIO_EXTS + MEDIA_VIDEO_EXTS + MEDIA_IMAGE_EXTS


def work_dir(parts=None):
    """中间件路径唯一构造入口：runs/<任务>/.work[/...]。

    parts 为中间件子路径（如 "intake" / "outline.json"），可省略。
    """
    seg = [RUNS_ROOT, "<任务>", WORK_DIR]
    if parts:
        if isinstance(parts, (list, tuple)):
            seg.extend(str(p) for p in parts if p)
        else:
            seg.append(str(parts))
    return "/".join(seg)


# ============ 出包排除表（「按谁看」分类 · 全包唯一事实源） ============
# 判据不是「文件类型」，而是「用户拿它做什么」：
#   答不出用户用途的件（给改包的人看的维护记录）→ 进本表：留在源码树、不进安装包。
# 与 SKIP_DIRS / SKIP_FILES / SKIP_EXT 的分工：
#   那三组按「形态」排除（缓存 / 系统噪音 / 字节码），本表按「读者」排除（不参与 Agent 执行）。
# 纪律：包内任何**自我声明「不参与 Agent 执行」**的件，必须出现在本表里；
#   selfcheck 的 internal-declared 扫描会逐件核对，漏登记即 FAIL。
PUBLISH_EXCLUDE = (
    "MAINTAINER.md",
)


# ============ 溯源落款 + 免责声明（全格式唯一事实源） ============
# 单一事实源纪律：这两句只在此处定义，七个生成器（md / txt / docx / pdf / ppt / xlsx / xlsx_chart）
# 一律引用，不得各写一版。落款管溯源、免责管合规 —— 两句两处，不可搅成一句。改文案只改这里。
FOOTER = "由 蒸馏成技能Skill 蒸馏产出"

DISCLAIMER_MAIN = "本产物为对源材料的个人蒸馏整理，仅供学习参考"
DISCLAIMER_TOPICS = {
    "invest": "，不构成任何投资建议",
    "biz": "，不代表对任何商业行为的建议",
    "other": "",
}


def disclaimer(topic=None):
    """免责声明唯一句式 = 固定主句 + 题材槽。

    topic ∈ {invest(投资/理财/股票/基金/房产增值), biz(商业/管理/思维/学习方法), other(其他)}；
    未知或未填按 other 处理（只留主句、不加槽）。
    """
    return DISCLAIMER_MAIN + DISCLAIMER_TOPICS.get((topic or "other").lower(), "")


def footer_text():
    """统一溯源落款文本（与免责声明是两句两处，不可混写）。"""
    return FOOTER


# ============ 来源总览（来源追溯 · 页脚唯一事实源） ============
# 多份材料合成一份产物时，页脚给出「这份产物由哪些材料来的、各走了哪条路读出来的」；
# 正文不逐条插页码 —— 让正文保持干净，溯源集中在一处。
# 单一事实源纪律：这一行只在此处定义，七个生成器一律引用，不得各写一版。
SOURCE_OVERVIEW_PREFIX = "来源总览："
SOURCE_OVERVIEW_ONE = "来源总览：本产物来自 1 份材料"   # 单份：只报份数，不列条目（避免噪音）


def sources_overview(sources):
    """来源总览唯一句式。

    sources：逐份料的可读条目（Agent 从接料台账 sources.json 取名 + 读取方式组成）。
    - 无/空 → 返回 ""（没接料就不出这行，避免空壳）
    - 1 份  → 只报份数（单来源不必罗列）
    - 多份  → 一行列全：来源总览：共 N 份 —— A｜B｜C
    """
    items = [str(s).strip() for s in (sources or []) if str(s).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return SOURCE_OVERVIEW_ONE
    return "%s共 %d 份 —— %s" % (SOURCE_OVERVIEW_PREFIX, len(items), "｜".join(items))


# ============ 交付回执（闭环·反馈口 + 零内容边界） ============
# 单一事实源纪律：这一行只在此处定义，七个生成器一律引用，不得各写一版。
# 位置：紧跟免责声明之后（落款 → 免责 → 回执），三句三处、互不合并。
# 守二·补38：只陈述本产物事实（这是给用户的一扇反馈口），不做任何承诺。
RECEIPT_PREFIX = "交付回执："
RECEIPT_TAG_WORD = "做法标签"
RECEIPT_BOUND = "（这一行不含您的任何内容。）"
RECEIPT_NO_TAG = "若这份产物有用，回评论区说一句「哪块想调」就行。"
RECEIPT_WITH_TAG = "若这份产物有用，回评论区贴这一行就行。"


def receipt_line(tags=None):
    """交付回执唯一句式（一行）。

    tags：Agent 传入的做法标签（材料类型 / 模式 / 格式 / 深度 的可读串）。
          传了 → 回执带上做法标签，用户贴回评论区即携带「哪类材料配哪种做法」的用法信号；
          没传 → 只出反馈口与零内容边界，**不留占位符、不留空壳**。
    """
    t = (str(tags).strip() if tags else "")
    if t:
        return "%s%s %s；%s%s" % (RECEIPT_PREFIX, RECEIPT_TAG_WORD, t,
                                  RECEIPT_WITH_TAG, RECEIPT_BOUND)
    return "%s%s%s" % (RECEIPT_PREFIX, RECEIPT_NO_TAG, RECEIPT_BOUND)


def _self_test():
    """最小自测：交付口径常量自洽（句式固定 / 白名单合法 / 与媒体层同集合 / 拼接正确）。

    纯数据 + 纯函数模块无副作用可测，能测的就是「口径自洽」：落款 / 免责 / 来源总览 /
    回执句式被改动、白名单被改宽改窄、媒体后缀与接料层漂移 —— 任一发生立即报警。
    """
    # 7) 溯源落款 + 免责声明单一事实源：句式固定、题材槽可挂、未知题材回落主句
    assert FOOTER.startswith("由 ") and FOOTER.endswith("蒸馏产出"), "落款文本形态异常"
    assert footer_text() == FOOTER, "footer_text() 与 FOOTER 不一致"
    assert set(DISCLAIMER_TOPICS) == {"invest", "biz", "other"}, "题材槽只允许 invest/biz/other 三档"
    assert DISCLAIMER_TOPICS["other"] == "", "other 档必须是空槽（只留主句）"
    assert disclaimer() == DISCLAIMER_MAIN, "缺省题材应只留主句"
    assert disclaimer("other") == DISCLAIMER_MAIN, "other 档应只留主句"
    assert disclaimer("invest").startswith(DISCLAIMER_MAIN) and "投资建议" in disclaimer("invest")
    assert disclaimer("biz").startswith(DISCLAIMER_MAIN) and "商业行为" in disclaimer("biz")
    assert disclaimer("UNKNOWN") == DISCLAIMER_MAIN, "未知题材应回落主句（不加槽）"
    # 8) 交付回执单一事实源：无标签时只出反馈口与边界；传标签时必带做法标签
    assert receipt_line() == RECEIPT_PREFIX + RECEIPT_NO_TAG + RECEIPT_BOUND, "无标签回执句式变了"
    assert RECEIPT_BOUND in receipt_line(), "无标签回执必须带零内容边界"
    assert RECEIPT_TAG_WORD in receipt_line("口述经验 / B / Word / D1"), "传标签时回执须带做法标签"
    assert RECEIPT_BOUND in receipt_line("口述经验 / B / Word / D1"), "带标签回执必须带零内容边界"
    assert receipt_line("   ") == receipt_line(), "纯空白标签应等同未传（不留空壳）"
    # 9) 交付目录约定：常量形态固定、work_dir 拼接正确、白名单后缀合法
    assert RUNS_ROOT == "runs" and WORK_DIR == ".work", "交付目录常量被改名"
    assert work_dir() == "runs/<任务>/.work", "work_dir() 缺省拼接异常"
    assert work_dir("intake") == "runs/<任务>/.work/intake", "work_dir(单值) 异常"
    assert work_dir(["a", "b.json"]) == "runs/<任务>/.work/a/b.json", "work_dir(多段) 异常"
    # 9c) 出包排除表：形态合法（包根相对名、不带路径分隔符、非空）
    assert PUBLISH_EXCLUDE, "出包排除表为空（至少应含 MAINTAINER.md）"
    assert all(isinstance(x, str) and x and "/" not in x and "\\" not in x
               for x in PUBLISH_EXCLUDE), "出包排除表条目形态异常"
    assert all(e.startswith(".") and len(e) > 1 for e in DELIVERY_EXTS), "交付白名单后缀形态异常"
    # 9b) 媒体成品后缀必须在白名单内，且与 media_ingest 的三组同集合（两处不许漂移）
    for _grp, _nm in ((MEDIA_AUDIO_EXTS, "音频"), (MEDIA_VIDEO_EXTS, "视频"),
                      (MEDIA_IMAGE_EXTS, "图片")):
        assert _grp and all(e in DELIVERY_EXTS for e in _grp), "%s 成品后缀未进交付白名单" % _nm
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import media_ingest as _mi
    assert set(MEDIA_AUDIO_EXTS) == set(_mi.AUDIO_EXT), "音频后缀与 media_ingest 漂移"
    assert set(MEDIA_VIDEO_EXTS) == set(_mi.VIDEO_EXT), "视频后缀与 media_ingest 漂移"
    assert set(MEDIA_IMAGE_EXTS) == set(_mi.IMAGE_EXT), "图片后缀与 media_ingest 漂移"
    assert ".docx" in DELIVERY_EXTS and ".html" not in DELIVERY_EXTS, "交付白名单口径被改"
    # 10) 来源总览单一事实源：空不出声、单份只报份数、多份列全且序号正确
    assert sources_overview(None) == "" and sources_overview([]) == "", "无来源应不出这行"
    assert sources_overview([" "]) == "", "纯空白条目应等同无来源"
    assert sources_overview(["《A》（Word 文档层）"]) == SOURCE_OVERVIEW_ONE, "单份应只报份数"
    ov = sources_overview(["《A》（Word 文档层）", "《B》（PDF 文本层）", "《C》（音频转写）"])
    assert ov.startswith(SOURCE_OVERVIEW_PREFIX) and "3 份" in ov, "多份应报份数并带前缀"
    assert "《A》" in ov and "《B》" in ov and "《C》" in ov, "多份应列全每一份"
    assert ov.count("｜") == 2, "多份分隔符数应等于份数-1"
    print("self-test PASS: 落款/免责/来源总览/回执句式 + 交付目录约定 + 白名单 %d 项（含媒体 %d 项）"
          % (len(DELIVERY_EXTS), len(MEDIA_AUDIO_EXTS) + len(MEDIA_VIDEO_EXTS) + len(MEDIA_IMAGE_EXTS)))


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
        raise SystemExit(0)
    print("constants.py —— 交付口径常量库；--self-test 跑自测。")
