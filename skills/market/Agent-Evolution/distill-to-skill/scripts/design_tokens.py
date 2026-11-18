# -*- coding: utf-8 -*-
"""
design_tokens.py —— 蒸馏成技能Skill · 全格式「设计令牌库」（前置单一事实源）

用途：
    PDF/Word/Excel/MD/TXT 五种格式的生成器不再各自 hardcode「单一字体 + 单一配色
    + 单一规格」，而是把「字体库 / 配色族 / 字号规格 / 模板模式 / 序号系统」统一预置为令牌库，
    Agent 按场景选模式（模板）即可产出有层次、有逻辑、有差异的成品，而非千篇一律。

范围（只管设计令牌，与常量分家）：
    本文件只装「设计令牌」——字体 / 配色 / 字号规格 / 序号系统 / 模式 · 版本 · 版式。
    与设计无关的固定口径（交付目录约定 / 成品后缀白名单 / 落款 · 免责 · 来源总览 · 交付回执
    四句定稿文本）**不在这里** —— 见 constants.py。两个模块各自是单一事实源、互不依赖。

使用：
    各 build_*_standard.py 调用 resolve(...) 拿合并后的令牌；Agent 在 B/C 格式确认后
    从 MODES 选一个模式（或自由组合 palette/font/scale/number），传给生成器。
    纯标准库、零第三方依赖；默认 MODES['biz'] 沿用既有取值（不影响既有产出）。

cross-platform：
    pdf 字体给「候选文件名列表」（按系统探测，不写死绝对路径）；
    office 字体给「字体名」（Word/PPT/Excel 用，宿主按本机字体回退）。
"""
import re

# ============================================================
# 1. 字体库（多种常规字体，跨平台）
# ============================================================
# key = 字体族（Agent 可选）；pdf = 候选文件名；office = Office 字体名；alt = 备选
FONTS = {
    "hei": {  # 黑体 / 无衬线（默认·现代商务）
        "pdf": ["simhei.ttf", "msyh.ttc", "msyh.ttf", "NotoSansSC-Regular.ttf",
                "NotoSansSC-VF.ttf", "NotoSansCJK-Regular.ttc", "NotoSansCJKsc-Regular.otf",
                "SourceHanSansSC-Regular.otf", "wqy-zenhei.ttc", "wqy-microhei.ttc",
                "PingFang.ttc", "STHeiti Light.ttc", "STHeiti Medium.ttc",
                "Hiragino Sans GB.ttc", "Heiti SC.ttc"],
        "office": "微软雅黑",
        "alt_office": ["思源黑体", "苹方", "等线"],
    },
    "song": {  # 宋体 / 衬线（报告 / 书籍 / 学术感）
        "pdf": ["simsun.ttc", "simsun.ttf", "Songti.ttc", "NotoSerifCJKsc-Regular.otf",
                "SourceHanSerifSC-Regular.otf", "STSong.ttc", "SimSun.ttc"],
        "office": "宋体",
        "alt_office": ["思源宋体", "华文宋体"],
    },
    "kai": {  # 楷体（金句 / 引文 / 温暖人文感）
        "pdf": ["simkai.ttf", "kaiu.ttf", "KaiTi.ttc", "STKaiti.ttc", "Kaiti SC.ttc"],
        "office": "楷体",
        "alt_office": ["华文楷体"],
    },
    "deng": {  # 等线（轻商务 / 现代简净）
        "pdf": ["deng.ttf", "msyh.ttc", "NotoSansSC-Regular.ttf", "PingFang.ttc"],
        "office": "等线",
        "alt_office": ["微软雅黑"],
    },
}

# ============================================================
# 2. 配色族（多种，均非 Office 默认蓝；贯穿全篇主导 2–3 色）
# ============================================================
# 每族键固定：MAIN 主色 / ACCENT 强调 / AUX 辅助 / BODY 正文 / GRAY 注释灰
#            LIGHT 浅底 / BORDER 边框 / ANNOT 注释文字
PALETTES = {
    "amber": {  # 琥珀金蓝（默认·商用正式）
        "MAIN": "16335B", "ACCENT": "E0A33E", "AUX": "2E6E9E",
        "BODY": "1F2733", "GRAY": "6B7480", "LIGHT": "F4F6F9",
        "BORDER": "D8DEE6", "ANNOT": "6B7480",
    },
    "red": {  # 红黑（强对比·营销 / 硬核 / 行动号召）
        "MAIN": "C00000", "ACCENT": "C00000", "AUX": "595959",
        "BODY": "1A1A1A", "GRAY": "7A7A7A", "LIGHT": "F7F7F7",
        "BORDER": "E0E0E0", "ANNOT": "7A7A7A",
    },
    "sky": {  # 天蓝科技（科技 / 互联网 / 数据）
        "MAIN": "04AEDA", "ACCENT": "0072BC", "AUX": "00B0F0",
        "BODY": "1F2733", "GRAY": "6B7480", "LIGHT": "F2FAFD",
        "BORDER": "CDE7F2", "ANNOT": "6B7480",
    },
    "teal": {  # 欧美 teal（清新 / 咨询 / 可持续）
        "MAIN": "0E7FB7", "ACCENT": "1B998B", "AUX": "45C1A4",
        "BODY": "1F2733", "GRAY": "6B7480", "LIGHT": "F1F8F6",
        "BORDER": "CDEAE2", "ANNOT": "6B7480",
    },
    "warm": {  # 暖橙商务（财富 / 商业 / 温暖交付感）
        "MAIN": "E8730C", "ACCENT": "F2A900", "AUX": "C75B12",
        "BODY": "2B2118", "GRAY": "8A7B6B", "LIGHT": "FFF6EC",
        "BORDER": "F0D9BE", "ANNOT": "8A7B6B",
    },
    "ink": {  # 墨绿学术（报告 / 研究 / 严肃）
        "MAIN": "1F4E3D", "ACCENT": "C9A227", "AUX": "3E7C5F",
        "BODY": "1F2A24", "GRAY": "6B7A72", "LIGHT": "F3F7F4",
        "BORDER": "D2E0D8", "ANNOT": "6B7A72",
    },
    "violet": {  # 紫灰高级（创意 / 文化 / 高端）
        "MAIN": "4B3F72", "ACCENT": "9B7EDE", "AUX": "6C5B9E",
        "BODY": "26223A", "GRAY": "7A7390", "LIGHT": "F5F3FA",
        "BORDER": "DED7EE", "ANNOT": "7A7390",
    },
}

# ============================================================
# 3. 字号规格（层级：封面主标题 / 一级 / 二级 / 三级 / 正文 / 核心句 / 注释 / 页码）
# ============================================================
# docx 单位为半磅（sz = pt*2）；pdf 单位为点（pt）。scale 因子用于模式微调，默认 1.0。
SCALES = {
    "standard": {  # 标准商务（默认）
        "docx": {"cover": 44, "h1": 32, "h2": 26, "h3": 22, "body": 24, "core": 24, "annot": 18, "page": 18},
        "pdf":  {"cover": 40, "h1": 30, "h2": 24, "h3": 20, "body": 14, "core": 14, "annot": 11, "page": 11},
        "factor": 1.0,
    },
    "compact": {  # 极简骨架（D3 用·更紧凑·留白多）
        "docx": {"cover": 40, "h1": 28, "h2": 22, "h3": 18, "body": 22, "core": 22, "annot": 16, "page": 16},
        "pdf":  {"cover": 36, "h1": 26, "h2": 21, "h3": 17, "body": 13, "core": 13, "annot": 10, "page": 10},
        "factor": 1.0,
    },
    "report": {  # 学术报告（正式·正文略大·行距宽松）
        "docx": {"cover": 46, "h1": 34, "h2": 28, "h3": 24, "body": 26, "core": 26, "annot": 19, "page": 19},
        "pdf":  {"cover": 42, "h1": 32, "h2": 26, "h3": 22, "body": 15, "core": 15, "annot": 12, "page": 12},
        "factor": 1.0,
    },
}

# ============================================================
# 4. 序号系统（层级编号样式，Agent 组大纲时用）
# ============================================================
# 返回 (大标题前缀, 中标题前缀, 小标题前缀) 的格式化函数；idx 从 1 起。
def _num_arabic(level, idx, parent=0):
    if level == 1:
        return f"{idx}."
    if level == 2:
        return f"{parent}.{idx}." if parent else f"{idx}."
    return f"{parent}.{idx}." if parent else f"{idx}."

def _num_cn(level, idx, parent=0):
    cn = "一二三四五六七八九十"
    s = cn[idx - 1] if idx <= 10 else str(idx)
    if level == 1:
        return f"{s}、"
    if level == 2:
        return f"（{s}）"
    return f"{s}）"

def _num_circle(level, idx, parent=0):
    circles = "①②③④⑤⑥⑦⑧⑨⑩"
    s = circles[idx - 1] if idx <= 10 else str(idx)
    return s

def _num_none(level, idx, parent=0):
    return ""

NUMBER_SYSTEMS = {
    "arabic": _num_arabic,   # 1. / 1.1. / 1.1.1.
    "cn": _num_cn,           # 一、 / （一） / 1）
    "circle": _num_circle,   # ①②③
    "none": _num_none,       # 无前缀（极简）
}

# ============================================================
# 4b. 序号辅助（剥离旧前缀 + 按系统重编号，生成器复用）
# ============================================================
_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"(?:[0-9]+\.)+[0-9]*"            # 1. / 1.1. / 1.1.1.
    r"|[一二三四五六七八九十百零]+[、.．]"  # 一、 / 一.
    r"|（[一二三四五六七八九十]+）"        # （一）
    r"|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]"  # 带圈数字
    r"|[\(（]?[0-9]+[\)）\.．]?"        # (1) / 1) / 1.
    r")\s*"
)


def strip_number_prefix(h):
    """去掉标题首部已有的数字/序号前缀，返回纯标题文本。"""
    if not h:
        return ""
    return _PREFIX_RE.sub("", h).strip()


def number_heading(h, level, idx, parent=0, num_fn=None):
    """按序号系统给标题加前缀。num_fn 为 None 时原样返回（向后兼容·不回归）。"""
    if not h:
        return ""  # 原标题为空：不渲染任何前缀（避免幽灵序号）
    if not num_fn:
        return h
    clean = strip_number_prefix(h)
    pre = num_fn(level, idx, parent) if callable(num_fn) else ""
    pre = (pre or "").strip()
    if not pre:
        return clean
    # 前缀以中文标点（、。．）) 结尾时不额外加空格，避免「一、 标题」这类双空格
    if pre[-1:] in "、。．）)":
        return pre + clean
    return (pre + " " + clean).strip() if clean else pre

# ============================================================
# 5. 模板 / 模式（预设组合 = palette + font + scale + number）
# ============================================================
# Agent 选一个模式即可拿到连贯的「字体+配色+规格+序号」整套，产出有差异、有层次。
MODES = {
    "biz":    {"palette": "amber", "font": "hei",  "scale": "standard", "number": "arabic",
               "desc": "标准商务（默认）· 琥珀金蓝 + 黑体 + 标准规格 + 阿拉伯层级"},
    "lean":    {"palette": "ink",  "font": "hei",  "scale": "compact",  "number": "cn",
               "desc": "极简骨架（D3 用）· 墨绿 + 黑体 + 紧凑 + 中文数字"},
    "report": {"palette": "ink",  "font": "song", "scale": "report",   "number": "arabic",
               "desc": "学术报告 · 墨绿 + 宋体 + 报告规格 + 阿拉伯层级"},
    "warm":   {"palette": "warm", "font": "kai",  "scale": "standard", "number": "circle",
               "desc": "暖橙交付 · 暖橙 + 楷体 + 标准规格 + 圈码（财富/商业温暖感）"},
    "red":    {"palette": "red",  "font": "hei",  "scale": "standard", "number": "arabic",
               "desc": "红黑硬核 · 红黑 + 黑体 + 标准规格 + 阿拉伯层级"},
    "sky":    {"palette": "sky",  "font": "hei",  "scale": "standard", "number": "arabic",
               "desc": "天蓝科技 · 科技蓝 + 黑体 + 标准规格"},
    "teal":   {"palette": "teal", "font": "hei",  "scale": "standard", "number": "arabic",
               "desc": "欧美 teal · teal 蓝 + 黑体 + 标准规格"},
    "violet": {"palette": "violet","font": "deng","scale": "standard", "number": "cn",
               "desc": "紫灰高级 · 紫 + 等线 + 标准规格 + 中文数字"},
}

DEFAULT_MODE = "biz"

# ---- 版本族（用户可点的"模板版本" · 全中性命名 · 不挂任何厂商标识）----
# 每个版本 = 连贯的「配色 + 字体 + 规格 + 序号 + 版式风格」整套；用户选一个即得一致观感。
# 与 MODES 区别：MODES 是自由组合预设（Agent 内部/高级用），VERSIONS 是给最终用户点的"版本"。
VERSIONS = {
    "standard": {"palette": "amber", "font": "hei",  "scale": "standard", "number": "arabic",
                 "layout": "balanced",
                 "desc": "标准商务（默认）· 琥珀金蓝 + 黑体 + 标准规格 + 阿拉伯层级 + 平衡版式"},
    "minimal":  {"palette": "sky",   "font": "hei",  "scale": "compact",  "number": "cn",
                 "layout": "airy",
                 "desc": "简约商务 · 天蓝 + 黑体 + 紧凑规格 + 中文数字 + 通透版式"},
    "classic":  {"palette": "ink",   "font": "song", "scale": "report",   "number": "arabic",
                 "layout": "formal",
                 "desc": "经典商务 · 墨绿 + 宋体 + 报告规格 + 阿拉伯层级 + 端正版式"},
    "premium":  {"palette": "violet","font": "deng", "scale": "standard", "number": "cn",
                 "layout": "elegant",
                 "desc": "高级商务 · 紫灰 + 等线 + 标准规格 + 中文数字 + 雅致版式"},
    "summary":  {"palette": "warm",  "font": "kai",  "scale": "report",   "number": "circle",
                 "layout": "balanced",
                 "desc": "总结汇报 · 暖橙 + 楷体 + 报告规格 + 圈码 + 平衡版式（年终/复盘/成果萃取）"},
    "course":   {"palette": "teal",  "font": "hei",  "scale": "standard", "number": "arabic",
                 "layout": "airy",
                 "desc": "课件讲义 · 欧美 teal + 黑体 + 标准规格 + 阿拉伯层级 + 通透版式（培训/教学）"},
    "data":     {"palette": "red",   "font": "hei",  "scale": "compact",  "number": "arabic",
                 "layout": "balanced",
                 "desc": "数据简报 · 红黑 + 黑体 + 紧凑规格 + 阿拉伯层级 + 平衡版式（图表/数据为主）"},
}

# ---- 版式风格（同一页型在不同版本下呈现不同几何/装饰，让"版本"真正看得见、可区分）----
LAYOUT_STYLES = {
    "balanced": {"cover_align": "ctr",  "card_bar": 0.07, "gap": 1.00, "accent_card": False},
    "airy":     {"cover_align": "left", "card_bar": 0.05, "gap": 1.30, "accent_card": True},
    "formal":   {"cover_align": "ctr",  "card_bar": 0.11, "gap": 0.90, "accent_card": False},
    "elegant":  {"cover_align": "left", "card_bar": 0.04, "gap": 1.18, "accent_card": True},
}


def resolve(mode=None, palette=None, font=None, scale=None, number=None,
            version=None, layout=None, fmt="docx"):
    """合并令牌。mode 优先；未给的维度回退默认 biz；返回可直接用的字典。

    fmt: 'docx' | 'pdf' | 'ppt' | 'xlsx' —— 决定字号用哪套单位。
    返回键：palette(dict), font_family(str, pdf 用候选列表在 font_pdf),
            font_office(str), scale(dict, 含 factor), number(fn), mode_name(str)
    """
    if version and version in VERSIONS:
        m = VERSIONS[version]
    else:
        m = MODES.get(mode or DEFAULT_MODE, MODES[DEFAULT_MODE])
    pal_name = palette or m["palette"]
    font_name = font or m["font"]
    scale_name = scale or m["scale"]
    num_name = number or m["number"]

    pal = dict(PALETTES.get(pal_name, PALETTES["amber"]))
    fdef = FONTS.get(font_name, FONTS["hei"])
    sc = SCALES.get(scale_name, SCALES["standard"])
    num_fn = NUMBER_SYSTEMS.get(num_name, _num_arabic)

    layout_name = layout or m.get("layout", "balanced")
    layout_dict = LAYOUT_STYLES.get(layout_name, LAYOUT_STYLES["balanced"])

    return {
        "mode_name": mode or DEFAULT_MODE,
        "version_name": version,
        "layout_name": layout_name,
        "layout": layout_dict,
        "palette_name": pal_name,
        "font_name": font_name,
        "palette": pal,
        "font_family": font_name,            # pdf 探测用 key
        "font_pdf": fdef["pdf"],             # pdf 候选文件名列表
        "font_office": fdef["office"],       # office 字体名
        "alt_office": fdef["alt_office"],
        "scale": sc,
        "scale_name": scale_name,
        "number": num_fn,
        "number_name": num_name,
        "fmt": fmt,
    }


def available_summary():
    """给人读（Agent 选模式/版本时打印）的简短清单。"""
    lines = ["【设计令牌库 · 用户可选版本（模板族）】"]
    for k, v in VERSIONS.items():
        lines.append(f"  {k:8s} → {v['desc']}")
    lines.append("【模板模式预设（自由组合用）】")
    for k, v in MODES.items():
        lines.append(f"  {k:7s} → {v['desc']}")
    lines.append("自由组合：--palette {%s}" % "|".join(PALETTES))
    lines.append("          --font {%s}" % "|".join(FONTS))
    lines.append("          --scale {%s}" % "|".join(SCALES))
    lines.append("          --number {%s}" % "|".join(NUMBER_SYSTEMS))
    lines.append("          --version {标准商务 standard / 简约商务 minimal / 经典商务 classic / 高级商务 premium / 总结汇报 summary / 课件讲义 course / 数据简报 data}")
    return "\n".join(lines)


def _self_test():
    """最小自测：令牌库完整性对账（键齐全 / 取值合法 / 模式引用的键必须真实存在）。

    纯数据模块无副作用可测，能测的就是「数据自洽」：任何一处改了配色族键名、
    删了字体族，或模式里引用了不存在的 palette/font/scale/number，立即报警。
    （交付口径常量 —— 落款 / 免责 / 来源总览 / 回执 / 交付目录 / 白名单 —— 的自测
     已随内容迁至 constants.py，见那边的 --self-test。）
    """
    PAL_KEYS = ("MAIN", "ACCENT", "AUX", "BODY", "GRAY", "LIGHT", "BORDER", "ANNOT")
    SCALE_KEYS = ("cover", "h1", "h2", "h3", "body", "core", "annot", "page")
    hexset = set("0123456789ABCDEFabcdef")
    # 1) 配色族：键齐全 + 六位十六进制取值
    for name, p in PALETTES.items():
        miss = [k for k in PAL_KEYS if k not in p]
        assert not miss, "配色族 %s 缺键: %s" % (name, miss)
        for k in PAL_KEYS:
            v = str(p[k])
            assert len(v) == 6 and all(c in hexset for c in v), \
                "配色族 %s.%s 取值非法: %s" % (name, k, v)
    # 2) 字体族：pdf 候选列表与 office 名均非空
    for name, f in FONTS.items():
        assert f.get("pdf"), "字体族 %s 缺 pdf 候选" % name
        assert f.get("office"), "字体族 %s 缺 office 名" % name
    # 3) 字号规格：docx/pdf 两套键齐全且为正整数
    for name, s in SCALES.items():
        for unit in ("docx", "pdf"):
            miss = [k for k in SCALE_KEYS if k not in s.get(unit, {})]
            assert not miss, "规格 %s.%s 缺键: %s" % (name, unit, miss)
            for k in SCALE_KEYS:
                assert isinstance(s[unit][k], int) and s[unit][k] > 0, \
                    "规格 %s.%s.%s 非正整数" % (name, unit, k)
    # 4) 模式/版本：引用的 palette/font/scale/number/layout 必须真实存在（防悬空引用）
    for group, table in (("MODES", MODES), ("VERSIONS", VERSIONS)):
        for name, m in table.items():
            assert m["palette"] in PALETTES, "%s %s 引用未知配色 %s" % (group, name, m["palette"])
            assert m["font"] in FONTS, "%s %s 引用未知字体 %s" % (group, name, m["font"])
            assert m["scale"] in SCALES, "%s %s 引用未知规格 %s" % (group, name, m["scale"])
            assert m["number"] in NUMBER_SYSTEMS, "%s %s 引用未知序号 %s" % (group, name, m["number"])
            if "layout" in m:
                assert m["layout"] in LAYOUT_STYLES, "%s %s 引用未知版式 %s" % (group, name, m["layout"])
    # 5) 默认模式存在且 resolve() 返回完整键
    assert DEFAULT_MODE in MODES, "DEFAULT_MODE=%s 不在 MODES" % DEFAULT_MODE
    tk = resolve()
    for k in ("palette", "font_pdf", "font_office", "scale", "number", "layout"):
        assert tk.get(k), "resolve() 缺键: %s" % k
    # 6) 四种序号系统可用；旧前缀能被剥离；num_fn=None 时原样返回（向后兼容）
    assert number_heading("标题", 1, 1, 0, NUMBER_SYSTEMS["arabic"]) == "1. 标题"
    assert number_heading("1.1. 标题", 1, 1, 0, NUMBER_SYSTEMS["cn"]) == "一、标题"
    assert number_heading("标题", 1, 1, 0, NUMBER_SYSTEMS["circle"]) == "① 标题"
    assert number_heading("标题", 1, 1, 0, NUMBER_SYSTEMS["none"]) == "标题"
    for src in ("一、标题", "1.1 标题", "（一）标题", "①标题", "(1)标题"):
        assert strip_number_prefix(src) == "标题", "前缀未剥离: %s -> %s" % (src, strip_number_prefix(src))
    assert number_heading("一、标题", 1, 1, 0, None) == "一、标题", "num_fn=None 应原样返回"
    print("self-test PASS: %d 配色 / %d 字体 / %d 规格 / %d 模式 / %d 版本"
          % (len(PALETTES), len(FONTS), len(SCALES), len(MODES), len(VERSIONS)))


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
        raise SystemExit(0)
    print(available_summary())
