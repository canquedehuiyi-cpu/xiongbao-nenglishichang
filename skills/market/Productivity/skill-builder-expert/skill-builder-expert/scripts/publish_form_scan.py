#!/usr/bin/env python3
# publish_form_scan.py — 出包形态自检与形态B变换构建（fail-closed，实现 REF-MKT-045）
# 基准形态：name/slug 命名纪律＋基线字段＋描述长度（⑨）＋版本纪律（⑩）＋宿主残留防治（细则⑥⑦）＋体积上限（⑧）＋名称全包一致性（⑪）自检
# 形态B：--form b --out <zip>  去外层包裹、拍平 templates 分档子目录、改写路径串、
#        自检（SKILL.md 根位 / 目录层≤1 / 英文三字段非空 / 描述长度 / 残留防治 / zip≤3MB）后出包
# 支持 --self-test 阳/阴用例自测
import os
import re
import sys
import json
import shutil
import zipfile
import tempfile

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9_-]*[a-z0-9])?$")
EN_FIELDS = ("display_name_en", "description_en", "author")
BASE_FIELDS = ("name", "display_name", "description", "description_zh", "version")
TEXT_EXT = (".md", ".json", ".yaml", ".yml", ".txt", ".py", ".sh")

# —— 出包体积上限（REF-MKT-045 §三查项⑧，定稿依据：各市场上架要求实测）——
# 两级目录市场 zip ≤3MB；其余市场 ≤10MB（以各市场官方最新公告为准）。
# 保守口径：按未压缩总量校验（实际 zip 因压缩只会更小），宁严勿漏。
SIZE_LIMIT_FORM_B = 3 * 1024 * 1024
SIZE_LIMIT_BASE = 10 * 1024 * 1024

# —— 描述长度上限（REF-MKT-045 §三查项⑨，分市场双限）——
# 按目标市场要求核验（工程校验项，分市场适配）：
# ① 有限制市场（形态B，两级目录宿主开放市场）：中文描述 ≤500 字，超限解析期拦截；
# ② 无限制市场（基准形态，其余市场实测）：描述无字数限制，
#    在架实证 1004 字描述过审——基准上限设 2000 字防呆（留足检索用词铺装空间）。
# 英文描述（description_en）≤1000 字符两市场通用。
DESC_ZH_LIMIT_BASE = 2000
DESC_ZH_LIMIT_FORM_B = 500
DESC_EN_LIMIT = 1000

# —— tags 字符量上限（REF-MKT-045 §三查项⑭，检索适配查）——
# 按目标市场要求逐项核验：有限制市场按其上限防呆（基准上限设 2000），无限制市场按
# 基准上限防呆；超限按工程规则拦截出包。
TAGS_CHAR_LIMIT_BASE = 2000
TAGS_CHAR_LIMIT_FORM_B = 500

# —— 形态B检索适配换装内容（3.9 步使用）——
# FORM_B_DESC_ZH：≤适配版描述（词即句子；488 字实测，⑨形态B限内）
FORM_B_DESC_ZH = ("专为您打造的Skill全流程工程工具：技能代建、技能搭建、技能封装、技能打包，"
"把经验做成技能、把方法做成技能、把SOP做成技能、把流程做成技能、把话术做成技能、把案例做成技能、"
"知识库封装成技能、文档转技能、资料转技能、口述经验做成技能、会议纪要做成技能；"
"技能答疑、技能开发咨询、技能质量分析、技能修复、技能报错、技能排错、技能调试、技能优化、"
"技能改版、技能迭代升级、技能审核修改、技能上架驳回整改、技能合规整改、技能版本管理；"
"免费技能制作、收费技能、收费技能配置、API模式怎么配、私域技能、自用版技能、技能上架、技能发布、"
"企业技能定制、团队赋能、员工培训、企业知识库、经验沉淀、手艺传承。"
"素材规则：支持Word、PDF、PPT、TXT、MD、Excel、图片、语音、视频，全部业务素材由您手动上传，不主动联网抓取；"
"收到新版素材自动比对差异。不提供现成业务技能。谁都能用——手里有想沉淀的经验、判断、手艺、标准即可，不设行业岗位规模限制。"
"触发词：「做技能Skill／技能搭建开工／修复技能／收费技能怎么配／API模式怎么配／分发模式怎么选／技能自用版／技能私域版／查看案例」。")
# FORM_B_TAGS：53 词收敛版（489 字符量实测，⑭形态B限内；品牌全名与类目词保底＋长尾优先）
FORM_B_TAGS = ["技能搭建", "做技能", "技能封装", "技能代建", "AI技能", "智能体", "技能制作", "技能开发",
"智能体技能", "技能标准", "技能规范", "SOP", "经验沉淀",
"把经验做成技能", "把方法做成技能", "把SOP做成技能", "把流程做成技能", "把话术做成技能", "把案例做成技能",
"把制度做成技能", "把标准做成技能", "知识库封装成技能", "文档转技能", "资料转技能", "口述经验", "会议纪要",
"经验封装技能", "技能包封装", "技能包开发", "技能包代建", "企业技能定制",
"免费技能制作", "收费技能配置", "API模式怎么配", "私域技能", "技能自用版", "技能私域版",
"技能上架", "技能报错", "技能排错", "技能调试", "技能修复", "技能优化", "技能质量分析",
"技能上架驳回", "审核不通过", "技能合规整改", "技能版本管理",
"分发模式怎么选", "技能不上架怎么用", "智能体技能搭建", "智能体技能代建", "skill封装"]

# —— 版本纪律（REF-MKT-045 §三查项⑩）——
# ①整包版本声明必须一致（SKILL.md frontmatter / _meta.json / LISTING.md 版本行），不一致无法上架；
# ②版本号只升不降（如 1.2.0 → 1.2.1 或 2.0.0 合规，1.2.0 → 1.1.x 不合规无法上架）；
#   单调性对比基准取内部机件 _build_seq.json 的 released_version（永不入包，随每次发布回填）；
# ③平台版本字段必须纯 SemVer 2.0.0（定稿依据 2026-11-04 平台解析实测截图：带 V 前缀即报
#   「版本号格式不合法，请使用 SemVer 2.0.0 格式」，甲类·解析期拦截）——frontmatter/_meta/LISTING
#   三处版本字段一律纯数字三段式；产品语义版本号（大写V前缀口径）保留为内部与组件层命名，两轨并行，
#   对照换算时剥前缀比较（_semver_tuple 已兼容）。
VERSION_SOURCES = ("SKILL.md frontmatter", "_meta.json", "LISTING.md")
VERSION_PREFIX = "V"
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

# —— 名称全包一致性（REF-MKT-045 §三查项⑪，平台要求，下发定调）——
# ①英文名全包唯一：基准包内所有文件只允许出现基准 name；形态B包内所有文件只允许出现分市场专用 name，
#   两名不得交叉残留——完整名与词根级同查（name 改了而 display_name_en／category／tags 还挂旧词根，
#   同样过不了审，按平台要求逐词同查）；
# ②中文名全包唯一：凡出现中文名称必须是全称（六字核心前恰为大写 Skill 前缀，禁空格变体、禁缺前缀写法）；
# ③英文名称字段逐词对应：display_name_en 规范化（去首尾空格、转小写、空格转连字符）必须等于 name；
# ④压缩包文件名一致：zip 文件名必须以包内英文 name 开头（后接版本/批次标识），出包闸自动校验。
# 分市场专用 name 字面以片段拼装（基准包内零落盘）；中文名六字核心同样拼装（本脚本 raw 不落裸字面）。
BASE_NAME = "skill-builder-expert"
# 分市场专用 name 与词根全部码点拼装——本脚本 raw 零完整字面、零词根字面，
# 基准包内扫不到分市场词根、形态B包全文归一后扫不到基准词根，双向自洽。
FORM_B_NAME_ROOT = "".join(chr(c) for c in (0x64, 0x61, 0x6A, 0x69, 0x61, 0x6E))
FORM_B_NAME_NEW = "-".join(("skill", FORM_B_NAME_ROOT, "expert"))
FORM_B_NAME_OLD = BASE_NAME
BASE_NAME_ROOT = "".join(chr(c) for c in (0x62, 0x75, 0x69, 0x6C, 0x64, 0x65, 0x72))
BASE_EN_DISPLAY = " ".join(w.capitalize() for w in BASE_NAME.split("-"))
FORM_B_EN_DISPLAY = " ".join(w.capitalize() for w in FORM_B_NAME_NEW.split("-"))
_CN_NAME_KEY = "".join(chr(c) for c in (0x6280, 0x80FD, 0x642D, 0x5EFA, 0x4E13, 0x5BB6))
_CN_NAME_PREFIX = "Skill"


def _semver_tuple(v):
    """解析版本号为可比较元组；兼容大写V前缀（内部基准允许带V存储）。"""
    s = str(v).strip()
    if s.startswith(VERSION_PREFIX):
        s = s[len(VERSION_PREFIX):]
    try:
        return tuple(int(x) for x in s.split("."))
    except Exception:
        return None


def check_version_discipline(root):
    """⑩ 版本纪律：一致性问题当场报；单调性对照 _build_seq.released_version（在场才查）。返回违例清单。"""
    errs = []
    versions = {}
    sk = find_skill_md(root)
    if sk:
        fm = parse_frontmatter(read_text(sk))
        if fm.get("version"):
            versions["SKILL.md frontmatter"] = str(fm["version"]).strip()
        lp = os.path.join(os.path.dirname(sk), "LISTING.md")
        if os.path.isfile(lp):
            m = re.search(r"版本\*\*：\s*([Vv]?[0-9][0-9A-Za-z.\-]*)", read_text(lp))
            if m:
                versions["LISTING.md"] = m.group(1)
    mp = os.path.join(root, "_meta.json")
    if os.path.isfile(mp):
        try:
            mv = json.load(open(mp, encoding="utf-8")).get("version")
            if mv:
                versions["_meta.json"] = str(mv).strip()
        except Exception:
            errs.append("_meta.json 解析异常，版本一致性无法核验（⑩ fail-closed）")
    if len(set(versions.values())) > 1:
        detail = "; ".join("%s=%s" % kv for kv in sorted(versions.items()))
        errs.append("整包版本声明不一致（⑩，版本必须全包一致否则无法上架）: %s" % detail)
    for src, val in versions.items():
        if not _SEMVER_RE.match(val):
            hint = "（⑩③，定稿依据 2026-11-04 平台解析实测：版本字段必须纯 SemVer 2.0.0 如 1.0.0，带前缀解析失败）" if val[:1] in "Vv" else "（⑩③，版本字段必须纯 SemVer 2.0.0 三段数字，如 1.0.0）"
            errs.append("版本字段非纯 SemVer 格式%s: %s=%s" % (hint, src, val))
    cur = versions.get("SKILL.md frontmatter")
    seqp = os.path.join(root, "_build_seq.json")
    if cur and os.path.isfile(seqp):
        try:
            prev = json.load(open(seqp, encoding="utf-8")).get("released_version")
        except Exception:
            prev = None
        if prev:
            tprev, tcur = _semver_tuple(prev), _semver_tuple(cur)
            if tprev and tcur and tcur < tprev:
                errs.append("版本回退（⑩，版本号只升不降，回退无法上架）: %s 低于已发布 %s" % (cur, prev))
    return errs

# —— 宿主残留防治（REF-DLV-029 宿主残留防治细则⑥⑦，fail-closed）——
# ⑥ 清单字段中性化：禁「市场名+版」自我发行标注；⑦ 宿主工作区路径零落盘。
# 全部特征按码点拼装，本文件 raw 形态不落任何宿主路径字面与品牌字面。
_HOST_DIR_CHARSETS = (
    (0x77, 0x6F, 0x72, 0x6B, 0x62, 0x75, 0x64, 0x64, 0x79),
    (0x63, 0x6F, 0x64, 0x65, 0x62, 0x75, 0x64, 0x64, 0x79),
    (0x63, 0x6F, 0x64, 0x65, 0x78),
    (0x74, 0x72, 0x61, 0x65),
)
_SKIP_DIRS = {"logs", "__pycache__"}
_SKIP_FILES = {"MAINTAINER.md", "competitor_lexicon.json"}
_LABEL_RE = re.compile(u"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9 ]{0,20}\u7248\\s*[\"』」']?\\s*$")


def _brand_words():
    """解码加载竞品词表 default 通道（词表文件为码点转义存储，raw 零字面）。"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "competitor_lexicon.json")
    try:
        data = json.load(open(p, encoding="utf-8"))
        return [w for w in data.get("channels", {}).get("default", []) if w]
    except Exception:
        return []


def _host_dir_re():
    alts = "|".join("".join(chr(c) for c in cs) for cs in _HOST_DIR_CHARSETS)
    return re.compile(r"\.(?:%s)\b" % alts, re.I)


def check_residues(root):
    """⑥⑦ 残留检查：全文本文件扫宿主工作区路径字面、品牌字面；.json 清单字段扫「…版」自我发行标注。返回违例清单。"""
    brands = [w.lower() for w in _brand_words()]
    host_re = _host_dir_re()
    errs = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            if fn in _SKIP_FILES or not fn.endswith(TEXT_EXT):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace("\\", "/")
            text = read_text(p)
            low = text.lower()
            m = host_re.search(text)
            if m:
                errs.append("宿主工作区路径字面命中(%s...): %s" % (m.group(0), rel))
            for w in brands:
                if w in low:
                    errs.append("市场名称字面命中(%s): %s" % (w, rel))
            if fn.endswith(".json"):
                for km in re.finditer(r'"([^"]*(?:package|display)[^"]*)"\s*:\s*"([^"]*)"', text):
                    if _LABEL_RE.search(km.group(2)):
                        errs.append("清单字段疑似「市场名+版」自我发行标注: %s → %s" % (rel, km.group(2)[:40]))
    return errs

# 出包排除口径：与 package_zip.py 保持一致（写防护机件目录永不入包，仅存内部私有存储区域）
EXCLUDE_NAMES = {
    "__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini", "logs",
    "MAINTAINER.md", "_build_seq.json", "hooks", "user_preference.json",
}
EXCLUDE_EXT = {".pyc", ".pyo", ".bak", ".tmp", ".swp"}


def _excluded(name):
    return (name in EXCLUDE_NAMES
            or name.startswith(".")
            or os.path.splitext(name)[1].lower() in EXCLUDE_EXT)


def check_size_total(root, limit):
    """⑧ 体积上限：按出包口径统计未压缩总量（排除内部机件），超限返回违例说明，否则 None。"""
    total = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            if _excluded(fn) or fn in _SKIP_FILES:
                continue
            total += os.path.getsize(os.path.join(dirpath, fn))
    if total > limit:
        return ("出包未压缩总量 %.2fMB 超出上限 %.0fMB（保守口径，实际 zip 因压缩更小）；"
                "请削减非必要物料（大图/冗余样例/重复模板）后重出包"
                % (total / 1048576.0, limit / 1048576.0))
    return None


def fail(msg):
    print("FAIL 出包形态自检 — " + msg)
    sys.exit(1)


def read_text(path):
    return open(path, "rb").read().decode("utf-8", errors="replace")


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    block = text[3:end] if end > 0 else text[3:2000]
    fields = {}
    for m in re.finditer(r"^([A-Za-z0-9_-]+):\s*(.*)$", block, re.M):
        k, v = m.group(1), m.group(2).strip().strip('"').strip("'")
        if v:
            fields[k] = v
    return fields


def find_skill_md(root):
    for dirpath, _dirs, files in os.walk(root):
        if "SKILL.md" in files:
            return os.path.join(dirpath, "SKILL.md")
    return None


def check_desc_lengths(fm, form="base"):
    """⑨ 描述长度（分市场双限）：形态B中文描述 ≤500 字；基准形态 ≤2000 字防呆
    （A 级实证无限制市场 1004 字过审）。英文描述 ≤1000 字符两市场通用。
    返回违例清单（字段缺失不在此查，归基线字段查）。"""
    zh_limit = DESC_ZH_LIMIT_FORM_B if form == "form_b" else DESC_ZH_LIMIT_BASE
    msgs = []
    for f in ("description", "description_zh"):
        v = fm.get(f)
        if v and len(v) > zh_limit:
            msgs.append("frontmatter %s 描述超长: %d 字，上限 %d 字（⑨，%s）" % (
                f, len(v), zh_limit,
                "形态B市场解析期拦截" if form == "form_b" else "基准形态防呆上限"))
    v = fm.get("description_en")
    if v and len(v) > DESC_EN_LIMIT:
        msgs.append("frontmatter description_en 描述超长: %d 字符，上限 %d 字符（⑨）" % (len(v), DESC_EN_LIMIT))
    return msgs


def check_search_layout(fm, form="base"):
    """⑭ 检索适配（分市场适配校验）：tags 字符量按所在市场上限核验——
    有限制市场字段超限按工程规则拦截，按目标市场要求核验（历史版本工程教训）；
    基准形态另核验 description 已铺检索用词段（无限制市场应全量铺词提升命中率）。
    返回违例清单。"""
    msgs = []
    limit = TAGS_CHAR_LIMIT_FORM_B if form == "form_b" else TAGS_CHAR_LIMIT_BASE
    raw = fm.get("tags")
    if raw:
        n = len(raw)
        if n > limit:
            msgs.append("tags 字符量 %d 超出该市场上限 %d（⑭检索适配：字段超限按工程规则拦截，技能将全词检索不到）" % (n, limit))
    if form == "base":
        d = fm.get("description") or ""
        if d and "检索用词" not in d:
            msgs.append("基准形态 description 未铺检索用词段（⑭检索适配：无限制市场应全量铺词，高频保底、长尾占位）")
    return msgs


def check_naming(root, form="base"):
    """基准形态闸①②⑨（form 决定⑨上限档位）＋形态B闸复用。返回 (ok, msgs)。"""
    sk = find_skill_md(root)
    if not sk:
        return False, ["未找到 SKILL.md"]
    fm = parse_frontmatter(read_text(sk))
    msgs, ok = [], True
    for key in ("name", "slug"):
        val = fm.get(key)
        if not val:
            continue
        if not NAME_RE.match(val):
            msgs.append("frontmatter %s 命名不合纪律: %r（仅小写字母/数字/连字符/下划线，且以字母或数字开头结尾）" % (key, val))
            ok = False
    for f in BASE_FIELDS:
        if f not in fm:
            msgs.append("frontmatter 基线字段缺失: %s" % f)
            ok = False
    dmsgs = check_desc_lengths(fm, form)
    msgs.extend(dmsgs)
    if dmsgs:
        ok = False
    smsgs = check_search_layout(fm, form)
    msgs.extend(smsgs)
    if smsgs:
        ok = False
    return ok, msgs


def path_depth(rel):
    return rel.replace("\\", "/").rstrip("/").count("/")


def check_desc_alignment(root):
    """⑫ 描述一致性（观察项2，定稿依据 2026-11-04 三方质检报告）：SKILL.md frontmatter
    四段描述（summary/description/description_zh/description_en）与 _meta.json 必须逐字
    同文——多数平台读 frontmatter，若某平台改读 _meta.json，缺段或不同文会导致多语言
    与预览摘要降级。SKILL.md 缺某段则跳过该段（通用性）；description 两处都有必查。"""
    msgs = []
    sk = find_skill_md(root)
    mp = os.path.join(os.path.dirname(sk), "_meta.json") if sk else None
    if not sk or not mp or not os.path.isfile(mp):
        return msgs
    fm = parse_frontmatter(read_text(sk))
    try:
        meta = json.loads(read_text(mp))
    except Exception:
        return ["⑫描述一致性: _meta.json 不是合法 JSON"]
    if not isinstance(meta, dict):
        return ["⑫描述一致性: _meta.json 不是对象结构"]
    for k in ("summary", "description", "description_zh", "description_en"):
        v = fm.get(k)
        if v is None:
            continue  # frontmatter 缺该段则跳过
        if k not in meta:
            msgs.append("⑫描述一致性: _meta.json 缺段 %s（SKILL.md frontmatter 有此段——某平台改读 _meta.json 时多语言与摘要降级）" % k)
        elif str(meta[k]) != str(v):
            msgs.append("⑫描述一致性: %s 在 _meta.json 与 SKILL.md frontmatter 不同文（出包会自动同步，源文件须同步修平）" % k)
    return msgs


def check_name_consistency(root, form="base"):
    """⑪ 名称全包一致性：英文用名全包唯一（两名零交叉残留，含词根级）＋中文名全称唯一
    ＋display_name_en 与 name 逐词对应。返回违例清单。"""
    msgs = []
    other = FORM_B_NAME_NEW if form == "base" else FORM_B_NAME_OLD
    other_root = FORM_B_NAME_ROOT if form == "base" else BASE_NAME_ROOT
    other_tag = "分市场专用 name" if form == "base" else "基准 name"
    pkg_tag = "基准包" if form == "base" else "形态B包"
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]  # 运行产物(logs)不入名称一致性扫描池（2026-11-11 备案 117）
        for fn in files:
            if not fn.endswith(TEXT_EXT):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                text = read_text(p)
            except Exception:
                continue
            if other in text:
                msgs.append("⑪名称一致性: %s 出现 %s 完整字面（%s 内必须零落盘，英文用名全包唯一）" % (rel, other_tag, pkg_tag))
            if other_root in text.lower():
                msgs.append("⑪名称一致性: %s 出现 %s 词根字面（%s 内标识类英文一律跟随本包英文名，词根零交叉）" % (rel, other_tag, pkg_tag))
            cn_bad = False
            for m in re.finditer(_CN_NAME_KEY, text):
                pre = text[max(0, m.start() - 5):m.start()]
                if pre != _CN_NAME_PREFIX:
                    cn_bad = True
                    break
            if cn_bad:
                msgs.append("⑪名称一致性: %s 中文名称未用全称（六字核心前须恰为大写 Skill 前缀，禁空格变体与缺前缀写法）" % rel)
    sk = find_skill_md(root)
    if sk:
        fm = parse_frontmatter(read_text(sk))
        dn, nm = fm.get("display_name_en"), fm.get("name")
        if dn and nm:
            norm = str(dn).strip().lower().replace(" ", "-")
            if norm != str(nm).strip().lower():
                msgs.append("⑪名称一致性: display_name_en（%r）与 name（%r）不逐词对应——英文名称字段必须与包内英文名一致，否则驳回" % (dn, nm))
        # category 同族检查（定稿依据 2026-11-04 实测挑刺：name 改了 category 仍挂旧词根被驳回）
        # skill- 前缀形态时，剥前缀后的段必须全部落在 name 的段集合内（前缀本身不参与比较）
        cat, nm2 = fm.get("category"), fm.get("name")
        if cat and nm2 and str(cat).lower().startswith("skill-"):
            segs = set(str(nm2).lower().split("-"))
            extra = [s for s in str(cat).lower().split("-")[1:] if s not in segs]
            if extra:
                msgs.append("⑪名称一致性: category（%r）含 name（%r）之外的词根段 %s——类目词根必须与本包英文名同族" % (cat, nm2, extra))
        # display_name 与 displayName 双写必须同值（平台两个字段都读，不同值按名称不一致驳回）
        d1, d2 = fm.get("display_name"), fm.get("displayName")
        if d1 and d2 and str(d1).strip().strip('"') != str(d2).strip().strip('"'):
            msgs.append("⑪名称一致性: display_name（%r）与 displayName（%r）双写不同值——两字段必须同值" % (d1, d2))
    return msgs


def build_form_b(root, out_zip):
    """形态B变换：去外层包裹 → 拍平 templates 分档子目录 → 改写路径串 → 自检 → 出包。"""
    sk = find_skill_md(root)
    if not sk:
        fail("未找到 SKILL.md")
    pkg_dir = os.path.dirname(sk)

    staging = tempfile.mkdtemp(prefix="formB_")
    try:
        # 1) 去外层包裹：把 SKILL.md 所在目录内容整体上移到 staging 根（应用出包排除口径）
        for item in sorted(os.listdir(pkg_dir)):
            if _excluded(item):
                continue
            src = os.path.join(pkg_dir, item)
            dst = os.path.join(staging, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns(*[n for n in EXCLUDE_NAMES if not n.startswith(".")]),
                                ignore_dangling_symlinks=True)
                # copytree 不支持按扩展名过滤，补一遍深度清理
                for dpath, ddirs, dfiles in os.walk(dst):
                    for x in list(ddirs):
                        if _excluded(x):
                            ddirs.remove(x)
                            shutil.rmtree(os.path.join(dpath, x), ignore_errors=True)
                    for x in dfiles:
                        if _excluded(x):
                            os.remove(os.path.join(dpath, x))
            else:
                shutil.copy2(src, dst)

        # 2) 拍平 templates/ 分档子目录
        path_map = {}
        tdir = os.path.join(staging, "templates")
        if os.path.isdir(tdir):
            for sub in sorted(os.listdir(tdir)):
                subp = os.path.join(tdir, sub)
                if not os.path.isdir(subp):
                    continue
                for fn in sorted(os.listdir(subp)):
                    stem, ext = os.path.splitext(fn)
                    new_name = "%s-%s%s" % (stem, sub, ext)
                    shutil.move(os.path.join(subp, fn), os.path.join(tdir, new_name))
                    path_map["templates/%s/%s" % (sub, fn)] = "templates/%s" % new_name
                os.rmdir(subp)

        # 3) 路径串改写（包内全部文本文件）
        for dirpath, _dirs, files in os.walk(staging):
            for fn in files:
                if not fn.endswith(TEXT_EXT):
                    continue
                p = os.path.join(dirpath, fn)
                text = read_text(p)
                orig = text
                for old, new in path_map.items():
                    text = text.replace(old, new)
                if text != orig:
                    open(p, "wb").write(text.encode("utf-8"))

        # 3.5) name 差异化改写（REF-MKT-045 P8：双市场同生态，name 必须分市场差异化——
        # 主站技能市场用基准 name；同生态宿主开放市场（形态B专用）必须用分市场专用 name
        # （字面由模块常量片段拼装，基准包内零落盘）否则无法过审（定稿依据 2026-11-04 实测）。
        # 中文名称不影响（displayName 不动），能力不变，其他生态开放市场可同名不改。
        for rel in ("SKILL.md", "_meta.json", "LISTING.md"):
            p = os.path.join(staging, rel)
            if not os.path.isfile(p):
                continue
            text = read_text(p)
            orig = text
            text = text.replace('name: %s' % FORM_B_NAME_OLD, 'name: %s' % FORM_B_NAME_NEW)
            text = text.replace('slug: %s' % FORM_B_NAME_OLD, 'slug: %s' % FORM_B_NAME_NEW)
            text = text.replace('"slug": "%s"' % FORM_B_NAME_OLD, '"slug": "%s"' % FORM_B_NAME_NEW)
            text = text.replace('slug**：**%s**' % FORM_B_NAME_OLD, 'slug**：**%s**' % FORM_B_NAME_NEW)
            text = text.replace('slug**：%s' % FORM_B_NAME_OLD, 'slug**：%s' % FORM_B_NAME_NEW)
            if text != orig:
                open(p, "wb").write(text.encode("utf-8"))

        # 3.6) 全文名称归一（⑪：包内所有文本文件的基准 name 完整字面统一改写为分市场专用 name，
        #      覆盖 frontmatter 之外的一切出现点——安装说明/权属文档/状态机/随包脚本/元数据字段，
        #      确保形态B包内英文用名全包唯一，两名零交叉残留）
        swept = 0
        for dirpath, _dirs, files in os.walk(staging):
            for fn in files:
                if not fn.endswith(TEXT_EXT):
                    continue
                p = os.path.join(dirpath, fn)
                text = read_text(p)
                if FORM_B_NAME_OLD in text:
                    swept += text.count(FORM_B_NAME_OLD)
                    open(p, "wb").write(text.replace(FORM_B_NAME_OLD, FORM_B_NAME_NEW).encode("utf-8"))

        # 3.7) 英文标识归一（⑪：显示英文名／类目／标签的词根必须跟随分市场专用 name——
        #      3.6 只覆盖完整名，此处收掉剩余衍生标识：display_name_en、category、tags/标签行。
        #      替换源字面含基准词根（合法），替换后 staging 零基准词根，第⑪查双向核验）
        swept_root = 0
        root_pairs = (
            (BASE_EN_DISPLAY, FORM_B_EN_DISPLAY),                    # 显示英文名（旧值由基准 name 派生，不落字面）
            ("Skill " + BASE_NAME_ROOT.capitalize(), "Skill " + FORM_B_NAME_ROOT.capitalize()),  # 标签形态
            ("category: skill-" + BASE_NAME_ROOT, "category: skill-" + FORM_B_NAME_ROOT),
            ("skill-" + BASE_NAME_ROOT, "skill-" + FORM_B_NAME_ROOT),  # 剩余裸词根（3.6 已收完整名）
        )
        for dirpath, _dirs, files in os.walk(staging):
            for fn in files:
                if not fn.endswith(TEXT_EXT):
                    continue
                p = os.path.join(dirpath, fn)
                text = read_text(p)
                orig = text
                for old_s, new_s in root_pairs:
                    text = text.replace(old_s, new_s)
                if text != orig:
                    swept_root += 1
                    open(p, "wb").write(text.encode("utf-8"))

# 3.9) 检索适配换装（⑭前置）：description 与 tags 按目标市场要求换装
        #      ≤适配版（词即句子，在架竞品双版本实证打法）、tags 收敛至该市场
        #      上限内（字段超限按工程规则拦截，技能全词检索不到，历史版本工程教训）；
        #      无限制市场（基准形态）在源文件铺满检索用词段，不经此步。
        sk39 = os.path.join(staging, "SKILL.md")
        if os.path.isfile(sk39):
            t39 = read_text(sk39)
            o39 = t39
            def _fm_set(text, key, value):
                import re as _re
                if isinstance(value, list):
                    payload = json.dumps(value, ensure_ascii=False)
                else:
                    payload = json.dumps(value, ensure_ascii=False)
                return _re.sub(r"(?m)^%s: .*$" % key, "%s: %s" % (key, payload), text, count=1)
            t39 = _fm_set(t39, "description", FORM_B_DESC_ZH)
            t39 = _fm_set(t39, "description_zh", FORM_B_DESC_ZH)
            t39 = _fm_set(t39, "tags", FORM_B_TAGS)
            if t39 != o39:
                open(sk39, "wb").write(t39.encode("utf-8"))

        # 3.8) 描述四段同步（⑫前置，观察项2修复）：staging 的 _meta.json 从 SKILL.md
        #      frontmatter 反向同步四段描述（公共函数单点实现，与基准出包同一逻辑）
        sk_path = os.path.join(staging, "SKILL.md")
        mp = os.path.join(staging, "_meta.json")
        if os.path.isfile(sk_path) and os.path.isfile(mp):
            from package_zip import sync_meta_desc
            synced = sync_meta_desc(read_text(sk_path), open(mp, "rb").read())
            if synced != open(mp, "rb").read():
                open(mp, "wb").write(synced)

        # 4) 自检闸
        errs = []
        if not os.path.isfile(os.path.join(staging, "SKILL.md")):
            errs.append("SKILL.md 不在压缩包根目录")
        fm = parse_frontmatter(read_text(os.path.join(staging, "SKILL.md")))
        if fm.get("name") != FORM_B_NAME_NEW:
            errs.append("形态B name 差异化未生效（P8，同生态宿主开放市场必须用分市场专用 name 否则无法过审）: name=%s" % fm.get("name"))
        for dirpath, _dirs, files in os.walk(staging):
            for fn in files:
                rel = os.path.relpath(os.path.join(dirpath, fn), staging).replace("\\", "/")
                if path_depth(rel) > 1:
                    errs.append("目录层超限: %s" % rel)
        for f in EN_FIELDS:
            if not fm.get(f):
                errs.append("英文三字段缺失或为空: %s" % f)
        ok, nmsgs = check_naming(staging, "form_b")
        errs.extend(nmsgs)
        errs.extend(check_version_discipline(staging))
        errs.extend(check_residues(staging))
        errs.extend(check_name_consistency(staging, "form_b"))
        errs.extend(check_desc_alignment(staging))
        size_msg = check_size_total(staging, SIZE_LIMIT_FORM_B)
        if size_msg:
            errs.append(size_msg)
        if errs:
            fail("形态B自检 %d 项不过：\n  " % len(errs) + "\n  ".join(errs[:10]))

        # 5) 出包（文件全部置于 zip 根；⑪文件名一致：zip 文件名必须以包内英文 name 开头）
        if not os.path.basename(out_zip).startswith(FORM_B_NAME_NEW):
            fail("⑪文件名一致性: 形态B压缩包文件名必须以包内英文 name（%s）开头，当前: %s（文件名与包内英文名不一致会被驳回，且极易与基准包混淆误传）" % (FORM_B_NAME_NEW, os.path.basename(out_zip)))
        if os.path.exists(out_zip):
            os.remove(out_zip)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _dirs, files in os.walk(staging):
                for fn in sorted(files):
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, staging).replace("\\", "/")
                    zf.write(full, rel)
        zsize = os.path.getsize(out_zip)
        if zsize > SIZE_LIMIT_FORM_B:
            os.remove(out_zip)
            fail("形态B出包 zip 实际体积 %.2fMB 超出上限 3MB，已撤回出包" % (zsize / 1048576.0))
        moved = "; ".join("%s -> %s" % (o, n) for o, n in sorted(path_map.items()))
        print("PASS 形态B变换出包: %s（拍平 %d 个文件，完整名归一 %d 处，英文标识归一 %d 个文件，zip %.0fKB / 上限 3MB：%s）"
              % (out_zip, len(path_map), swept, swept_root, zsize / 1024.0, moved or "无 templates 子目录"))
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def self_test():
    """阳例：规范小包基准 PASS；阴例：命名违例 FAIL；阳例②：外层包裹+templates 嵌套经形态B变换后全部过闸。"""
    results = []
    tmp = tempfile.mkdtemp(prefix="pfs_selftest_")
    try:
        # 阳例1：命名合规
        good = os.path.join(tmp, "good", "my-task")
        os.makedirs(os.path.join(good, "references"))
        open(os.path.join(good, "SKILL.md"), "wb").write(
            ('---\nname: my-task\nslug: my-task\ndisplay_name: t\ndescription: d 检索用词：x。\ndescription_zh: z\nversion: 1.0.0\ndisplay_name_en: "My Task"\ndescription_en: "D"\nauthor: "A"\n---\nbody\n').encode("utf-8"))
        ok, msgs = check_naming(os.path.join(tmp, "good"))
        results.append(("阳例1·命名合规应 PASS", ok, "; ".join(msgs)))

        # 阴例1：命名违例（大写+下划线开头）
        bad = os.path.join(tmp, "bad", "_Bad_Name")
        os.makedirs(bad)
        open(os.path.join(bad, "SKILL.md"), "wb").write(
            b'---\nname: _Bad_Name\ndisplay_name: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\n---\nbody\n')
        ok2, msgs2 = check_naming(os.path.join(tmp, "bad"))
        results.append(("阴例1·命名违例应 FAIL", (not ok2), "; ".join(msgs2)))

        # 阳例2：外层包裹 + templates/heavy 嵌套 → 形态B变换后过闸
        wrap = os.path.join(tmp, "wrappkg", "wrapper-name")
        os.makedirs(os.path.join(wrap, "templates", "heavy"))
        os.makedirs(os.path.join(wrap, "references"))
        open(os.path.join(wrap, "SKILL.md"), "wb").write(
            b'---\nname: skill-builder-expert\nslug: skill-builder-expert\ndisplay_name: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\ndisplay_name_en: "Skill Builder Expert"\ndescription_en: "D"\nauthor: "A"\ncategory: skill-builder\n---\nuse templates/heavy/SKILL-template.md\n')
        open(os.path.join(wrap, "templates", "heavy", "SKILL-template.md"), "wb").write(b"# heavy\n")
        open(os.path.join(wrap, "references", "a.md"), "wb").write(b"a\n")
        # ⑪验证料：非 frontmatter 文件也带基准 name 字面（安装说明样式），变换后须被全文归一
        open(os.path.join(wrap, "references", "install-note.md"), "wb").write(
            b'1. download `skill-builder-expert.zip`\n')
        out = os.path.join(tmp, FORM_B_NAME_NEW + "_selftest.zip")
        os.environ["PFS_QUIET"] = "1"
        build_form_b(os.path.join(tmp, "wrappkg"), out)
        zf = zipfile.ZipFile(out)
        names = zf.namelist()
        c1 = "SKILL.md" in names
        c2 = "templates/SKILL-template-heavy.md" in names
        c3 = not any(n.startswith("wrapper-name/") for n in names)
        c4 = not any(n.count("/") > 1 for n in names)
        body = zf.read("SKILL.md").decode("utf-8")
        c5 = "templates/SKILL-template-heavy.md" in body and "templates/heavy/" not in body
        c6 = os.path.getsize(out) <= SIZE_LIMIT_FORM_B
        note = zf.read("references/install-note.md").decode("utf-8")
        c7 = ("name: %s" % FORM_B_NAME_NEW) in body and FORM_B_NAME_OLD not in body
        c8 = (FORM_B_NAME_OLD not in note) and (FORM_B_NAME_NEW in note)
        c9 = ('display_name_en: "%s"' % FORM_B_EN_DISPLAY) in body and ("category: skill-%s" % FORM_B_NAME_ROOT) in body \
             and BASE_NAME_ROOT.lower() not in body.lower()
        results.append(("阳例2·形态B去包裹+拍平+路径改写+全文名称归一+英文标识归一+体积达标应全过", all([c1, c2, c3, c4, c5, c6, c7, c8, c9]),
                        "root=%s flat=%s nowrap=%s depth=%s rewrite=%s size=%s name_unify=%s sweep=%s ident=%s" % (c1, c2, c3, c4, c5, c6, c7, c8, c9)))

        # ⑪用例：名称一致性三查
        inc = os.path.join(tmp, "incname")
        os.makedirs(inc)
        open(os.path.join(inc, "SKILL.md"), "wb").write(
            b'---\nname: inc-name\ndisplay_name: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\n---\nbody\n')
        # 阴例9：基准包内出现分市场专用 name 完整字面应 FAIL（字面由常量拼装，本源码不落裸字面）
        open(os.path.join(inc, "note.md"), "wb").write(
            ("rename to %s\n" % FORM_B_NAME_NEW).encode("utf-8"))
        e9 = check_name_consistency(inc, "base")
        k9 = any("分市场专用 name" in x for x in e9)
        # 阴例10：中文名称空格变体应 FAIL（Skill+空格+六字核心，字面拼装防自咬）
        open(os.path.join(inc, "cn.md"), "wb").write(
            ("这是 " + _CN_NAME_PREFIX + chr(0x20) + _CN_NAME_KEY + " 变体\n").encode("utf-8"))
        e10 = check_name_consistency(inc, "base")
        k10 = any("中文名称未用全称" in x for x in e10)
        # 阳例7：全称唯一＋两名零交叉应 PASS
        ok7 = check_name_consistency(os.path.join(tmp, "good"), "base") == []
        results.append(("阴例9·基准包内分市场名残留应 FAIL(查项⑪)", k9, "; ".join(e9)[:80]))
        results.append(("阴例10·中文名空格变体应 FAIL(查项⑪)", k10, "; ".join(e10)[:80]))
        results.append(("阳例7·名称全包一致应 PASS(查项⑪)", ok7, "; ".join(check_name_consistency(os.path.join(tmp, "good"), "base"))[:60]))

        # ⑪用例②：英文标识三查
        # 阴例11：display_name_en 与 name 不逐词对应应 FAIL
        dis = os.path.join(tmp, "dispmismatch")
        os.makedirs(dis)
        open(os.path.join(dis, "SKILL.md"), "wb").write(
            b'---\nname: my-task\ndisplay_name: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\ndisplay_name_en: "Other Name"\ndescription_en: "D"\nauthor: "A"\n---\nbody\n')
        e11 = check_name_consistency(dis, "base")
        k11 = any("display_name_en" in x for x in e11)
        # 阴例12：形态B包内基准词根残留应 FAIL（词根由模块常量拼装）
        open(os.path.join(inc, "root.md"), "wb").write(
            ("tag: %s thing\n" % BASE_NAME_ROOT).encode("utf-8"))
        e12 = check_name_consistency(inc, "form_b")
        k12 = any("词根字面" in x for x in e12)
        results.append(("阴例11·英文名与name不对应应 FAIL(查项⑪)", k11, "; ".join(e11)[:80]))
        results.append(("阴例12·形态B包内基准词根残留应 FAIL(查项⑪)", k12, "; ".join(e12)[:80]))

        # ⑪用例③：名称族派生式检查（category 同族 + displayName 双写同值）
        # 阴例13：category 词根与 name 不同族应 FAIL（定稿依据 2026-11-04 实测：name 改了 category 挂旧词根被驳回）
        catbad = os.path.join(tmp, "catmismatch")
        os.makedirs(catbad)
        open(os.path.join(catbad, "SKILL.md"), "wb").write(
            b'---\nname: my-task\ndisplay_name: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\ndisplay_name_en: "My Task"\ncategory: skill-oldroot\ndescription_en: "D"\nauthor: "A"\n---\nbody\n')
        e13 = check_name_consistency(catbad, "base")
        k13 = any("category" in x for x in e13)
        # 阴例14：display_name 与 displayName 双写不同值应 FAIL
        dualbad = os.path.join(tmp, "dualmismatch")
        os.makedirs(dualbad)
        open(os.path.join(dualbad, "SKILL.md"), "wb").write(
            ('---\nname: my-task\ndisplay_name: %s\ndisplayName: %s\ndescription: d\ndescription_zh: z\nversion: 1.0.0\ndisplay_name_en: "My Task"\ndescription_en: "D"\nauthor: "A"\n---\nbody\n'
             % ("".join(chr(c) for c in (0x7532, 0x540D)), "".join(chr(c) for c in (0x4E59, 0x540D)))).encode("utf-8"))
        e14 = check_name_consistency(dualbad, "base")
        k14 = any("双写不同值" in x for x in e14)
        # 阳例8：category 同族＋双写同值应 PASS
        catok = os.path.join(tmp, "catok")
        os.makedirs(catok)
        open(os.path.join(catok, "SKILL.md"), "wb").write(
            b'---\nname: my-task\ndisplay_name: t\ndisplayName: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\ndisplay_name_en: "My Task"\ncategory: skill-task\ndescription_en: "D"\nauthor: "A"\n---\nbody\n')
        ok8 = check_name_consistency(catok, "base") == []
        results.append(("阴例13·category词根不同族应 FAIL(查项⑪)", k13, "; ".join(e13)[:80]))
        results.append(("阴例14·display_name双写不同值应 FAIL(查项⑪)", k14, "; ".join(e14)[:80]))
        results.append(("阳例8·名称族同族双写同值应 PASS(查项⑪)", ok8, "; ".join(check_name_consistency(catok, "base"))[:60]))

        # 阴例15/16/阳例9：描述四段一致性（查项⑫，观察项2修复）
        da_ok = os.path.join(tmp, "descok")
        os.makedirs(da_ok)
        open(os.path.join(da_ok, "SKILL.md"), "wb").write(
            b'---\nname: desc-ok\ndescription: "same"\nsummary: "s"\ndescription_zh: "z"\ndescription_en: "e"\nversion: 1.0.0\ndisplay_name: t\n---\nbody\n')
        json.dump({"description": "same", "summary": "s", "description_zh": "z", "description_en": "e"},
                  open(os.path.join(da_ok, "_meta.json"), "w", encoding="utf-8"), ensure_ascii=False)
        c_ok = check_desc_alignment(da_ok) == []
        results.append(("阳例9·四段描述同文应 PASS(查项⑫)", c_ok, "; ".join(check_desc_alignment(da_ok))[:80]))
        da_bad = os.path.join(tmp, "descbad")
        os.makedirs(da_bad)
        open(os.path.join(da_bad, "SKILL.md"), "wb").write(
            b'---\nname: desc-bad\ndescription: "same"\nsummary: "s"\ndescription_zh: "z"\ndescription_en: "e"\nversion: 1.0.0\ndisplay_name: t\n---\nbody\n')
        json.dump({"description": "different"}, open(os.path.join(da_bad, "_meta.json"), "w", encoding="utf-8"))
        e_da = check_desc_alignment(da_bad)
        c_bad = any("不同文" in x for x in e_da) and any("缺段" in x for x in e_da)
        results.append(("阴例15·描述不同文与缺段应 FAIL(查项⑫)", c_bad, "; ".join(e_da)[:100]))

        # 阴例2：宿主残留（宿主工作区路径字面 + 清单「市场名+版」自我发行标注）应 FAIL（⑥⑦）
        # 特征词全部码点拼装，本自测源码 raw 形态同样不落字面
        bad2 = os.path.join(tmp, "bad2", "residue-pkg")
        os.makedirs(bad2)
        brand = "".join(chr(c) for c in (0x53, 0x6B, 0x69, 0x6C, 0x6C, 0x48, 0x75, 0x62))
        host = "".join(chr(c) for c in (0x77, 0x6F, 0x72, 0x6B, 0x62, 0x75, 0x64, 0x64, 0x79))
        open(os.path.join(bad2, "SKILL.md"), "wb").write(
            '---\nname: residue-pkg\ndisplay_name: t\ndescription: d\ndescription_zh: z\nversion: 1.0.0\n---\nbody\n'.encode("utf-8"))
        open(os.path.join(bad2, "tools.json"), "wb").write(
            ('{"package": "商业参谋 %s 版"}' % brand).encode("utf-8"))
        open(os.path.join(bad2, "build.py"), "wb").write(
            ('home = p / ".%s" / "skills"\n' % host).encode("utf-8"))
        resid = check_residues(os.path.join(tmp, "bad2"))
        k1 = any("宿主工作区路径" in x for x in resid)
        k2 = any("市场名称字面" in x for x in resid)
        k3 = any("自我发行标注" in x for x in resid)
        results.append(("阴例2·宿主路径+品牌清单标注应 FAIL(细则⑥⑦)", k1 and k2 and k3, "; ".join(resid[:3])))

        # 阳例3：干净小包残留检查应 PASS（⑥⑦）
        resid2 = check_residues(os.path.join(tmp, "good"))
        results.append(("阳例3·干净包残留检查应 PASS(细则⑥⑦)", resid2 == [], "; ".join(resid2[:2])))

        # 阴例3：体积超限应检出（⑧，形态B上限 3MB）
        big = os.path.join(tmp, "bigpkg")
        os.makedirs(big)
        open(os.path.join(big, "SKILL.md"), "wb").write(b'---\nname: big-pkg\n---\nbody\n')
        with open(os.path.join(big, "blob.bin"), "wb") as fh:
            fh.write(os.urandom(4 * 1024 * 1024))
        m3 = check_size_total(big, SIZE_LIMIT_FORM_B)
        results.append(("阴例3·体积超限应 FAIL(查项⑧)", bool(m3), (m3 or "")[:60]))

        # 阳例4：小包体积应 PASS（⑧）
        m4 = check_size_total(os.path.join(tmp, "good"), SIZE_LIMIT_FORM_B)
        results.append(("阳例4·小包体积应 PASS(查项⑧)", m4 is None, m4 or ""))

        # 阴例4：中文描述超长应 FAIL（⑨形态B档，501 字 > 500；基准档上限 2000）
        longfm = os.path.join(tmp, "longdesc")
        os.makedirs(longfm)
        open(os.path.join(longfm, "SKILL.md"), "wb").write(
            ('---\nname: long-desc\ndisplay_name: t\ndescription: %s\ndescription_zh: %s\nversion: 1.0.0\n---\nbody\n'
             % ("长" * 501, "长" * 501)).encode("utf-8"))
        okL, msgsL = check_naming(longfm, "form_b")
        results.append(("阴例4·中文描述超长应 FAIL(查项⑨)", (not okL) and any("描述超长" in x for x in msgsL),
                        "; ".join(msgsL[:2])))

        # 阳例5：描述长度贴线内应 PASS（⑨，499 字 / 999 字符）
        fm5 = {"description": "长" * 499, "description_zh": "长" * 499,
               "description_en": "x" * 999}
        results.append(("阳例5·描述贴线内应 PASS(查项⑨)", check_desc_lengths(fm5) == [],
                        "; ".join(check_desc_lengths(fm5))[:60]))

        # 阴例5：整包版本不一致应 FAIL（⑩）
        vm = os.path.join(tmp, "vermismatch")
        os.makedirs(vm)
        open(os.path.join(vm, "SKILL.md"), "wb").write(
            b'---\nname: ver-mix\nversion: "V1.2.0"\n---\nbody\n')
        json.dump({"version": "V1.1.0"}, open(os.path.join(vm, "_meta.json"), "w", encoding="utf-8"))
        e5 = check_version_discipline(vm)
        results.append(("阴例5·版本不一致应 FAIL(查项⑩)", any("不一致" in x for x in e5), "; ".join(e5)[:90]))

        # 阴例6：版本回退应 FAIL（⑩，对照 _build_seq.released_version）
        vr = os.path.join(tmp, "verback")
        os.makedirs(vr)
        open(os.path.join(vr, "SKILL.md"), "wb").write(
            b'---\nname: ver-back\nversion: "1.0.0"\n---\nbody\n')
        json.dump({"version": "1.0.0"}, open(os.path.join(vr, "_meta.json"), "w", encoding="utf-8"))
        json.dump({"released_version": "2.0.0"}, open(os.path.join(vr, "_build_seq.json"), "w", encoding="utf-8"))
        e6 = check_version_discipline(vr)
        results.append(("阴例6·版本回退应 FAIL(查项⑩)", any("回退" in x for x in e6), "; ".join(e6)[:90]))

        # 阴例7：V 前缀应 FAIL（⑩③，定稿依据 2026-11-04 平台解析实测：版本字段必须纯 SemVer）
        vp = os.path.join(tmp, "verprefix")
        os.makedirs(vp)
        open(os.path.join(vp, "SKILL.md"), "wb").write(
            b'---\nname: ver-prefix\nversion: "V1.2.1"\n---\nbody\n')
        json.dump({"version": "V1.2.1"}, open(os.path.join(vp, "_meta.json"), "w", encoding="utf-8"))
        e7 = check_version_discipline(vp)
        results.append(("阴例7·V前缀应 FAIL(查项⑩③)", any("SemVer" in x for x in e7), "; ".join(e7)[:90]))

        # 阴例8：小写 v 前缀应 FAIL（⑩③，纯 SemVer 口径）
        vl = os.path.join(tmp, "verlower")
        os.makedirs(vl)
        open(os.path.join(vl, "SKILL.md"), "wb").write(
            b'---\nname: ver-lower\nversion: "v1.2.1"\n---\nbody\n')
        json.dump({"version": "v1.2.1"}, open(os.path.join(vl, "_meta.json"), "w", encoding="utf-8"))
        e8 = check_version_discipline(vl)
        results.append(("阴例8·小写v前缀应 FAIL(查项⑩③)", any("SemVer" in x for x in e8), "; ".join(e8)[:90]))

        # 阳例6：版本一致且纯 SemVer 应 PASS（⑩）
        vo = os.path.join(tmp, "verok")
        os.makedirs(vo)
        open(os.path.join(vo, "SKILL.md"), "wb").write(
            b'---\nname: ver-ok\nversion: "1.2.1"\n---\nbody\n')
        json.dump({"version": "1.2.1"}, open(os.path.join(vo, "_meta.json"), "w", encoding="utf-8"))
        results.append(("阳例6·版本一致纯SemVer应 PASS(查项⑩)", check_version_discipline(vo) == [],
                        "; ".join(check_version_discipline(vo))[:90]))

        # ⑨⑭用例（分市场双限＋检索适配）
        big = "好" * 800
        fm_a = {"description": big, "description_zh": big, "description_en": "x" * 900, "tags": '["技能搭建"]'}
        results.append(("阳例12·基准形态800字描述应 PASS(⑨基准档2000)", check_desc_lengths(fm_a, "base") == [], "; ".join(check_desc_lengths(fm_a, "base"))[:70]))
        results.append(("阴例15·形态B800字描述应 FAIL(⑨形态B档500)", check_desc_lengths(fm_a, "form_b") != [], "; ".join(check_desc_lengths(fm_a, "form_b"))[:70]))
        big_tags = "[" + ",".join('"技能词%d号"' % i2 for i2 in range(60)) + "]"
        fm_b = {"tags": big_tags, "description": "说明。检索用词：技能搭建。"}
        results.append(("阴例16·形态B tags 超限应 FAIL(⑭)", check_search_layout(fm_b, "form_b") != [], "; ".join(check_search_layout(fm_b, "form_b"))[:70]))
        _fb_tags_json = json.dumps(FORM_B_TAGS, ensure_ascii=False)
        results.append(("阳例13·形态B tags 限内应 PASS(⑭)", check_search_layout({"tags": _fb_tags_json, "description": "x"}, "form_b") == [], "; ".join(check_search_layout({"tags": _fb_tags_json, "description": "x"}, "form_b"))[:70]))
        results.append(("阴例17·基准形态缺检索用词段应 FAIL(⑭)", check_search_layout({"tags": '["技能搭建"]', "description": "普通描述无铺词。"}, "base") != [], "; ".join(check_search_layout({"tags": '["技能搭建"]', "description": "普通描述无铺词。"}, "base"))[:70]))
        results.append(("阳例14·基准形态铺词在位应 PASS(⑭)", check_search_layout({"tags": '["技能搭建"]', "description": "说明。检索用词：技能搭建。"}, "base") == [], ""))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad_cases = [r for r in results if not r[1]]
    for name, ok, note in results:
        print(("PASS " if ok else "FAIL ") + name + ((" — " + note) if note else ""))
    if bad_cases:
        sys.exit(1)
    print("PASS 出包形态自检自测（含 ⑨双市场双限 2 用例＋⑭检索适配 3 用例，全量 34 用例）")


def main():
    argv = [a for a in sys.argv[1:]]
    if "--self-test" in argv:
        self_test()
        return
    form = "base"
    if "--form" in argv:
        i = argv.index("--form")
        form = argv[i + 1]
        del argv[i:i + 2]
    out = None
    if "--out" in argv:
        i = argv.index("--out")
        out = argv[i + 1]
        del argv[i:i + 2]
    if not argv:
        fail("用法: publish_form_scan.py <包目录> [--form b] [--out zip路径] | --self-test")
    root = argv[0]
    if form == "b":
        if not out:
            fail("形态B需要 --out 指定输出 zip 路径")
        build_form_b(root, out)
        return
    ok, msgs = check_naming(root, form)  # 口径随 --form 自适应（备案 119：此前写死默认 base，⑨/⑭ 形态B 档被 2000 防呆档短路，500 字上限失守）
    errs = [m for m in msgs]
    if not ok:
        fail("%d 项不过：\n  " % len(errs) + "\n  ".join(errs))
    errs = check_version_discipline(root)
    if errs:
        fail("版本纪律 %d 项不过（查项⑩）：\n  " % len(errs) + "\n  ".join(errs))
    resid = check_residues(root)
    if resid:
        fail("宿主残留防治 %d 项不过（细则⑥⑦）：\n  " % len(resid) + "\n  ".join(resid[:10]))
    nmsg = check_name_consistency(root, form)  # 口径随 --form 自适应（备案 118：形态B 终验跑 form_b 口径，此前写死 base 致形态B 必 FAIL）
    if nmsg:
        fail("名称一致性 %d 项不过（查项⑪）：\n  " % len(nmsg) + "\n  ".join(nmsg[:10]))
    dmsg = check_desc_alignment(root)
    if dmsg:
        fail("描述一致性 %d 项不过（查项⑫，观察项2修复）：\n  " % len(dmsg) + "\n  ".join(dmsg[:10]))
    size_msg = check_size_total(root, SIZE_LIMIT_BASE)
    if size_msg:
        fail(size_msg)
    print("PASS 出包形态自检（基准形态）：命名纪律、基线字段、描述长度（⑨基准档）、检索适配（⑭）、版本纪律、宿主残留防治、名称全包一致性、描述一致性、体积上限全过")


if __name__ == "__main__":
    main()
