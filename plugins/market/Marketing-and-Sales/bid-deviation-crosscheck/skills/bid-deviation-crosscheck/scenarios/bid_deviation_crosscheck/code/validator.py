"""
validator.py —— 偏离表与正文矛盾核对 判定规则（护城河区，写死）

判定族 T-07（N-17 / D-07，槽位 2 相符核对变体）限缩口径（N.1 §3 / 输入整治计划 §4.7）：
只做「核验用户**既有偏离表** vs 方案正文」——对偏离表逐行，用关键词在方案正文
定位，检测矛盾信号（表称满足但正文回避/否定；表称偏离但正文声称全满足）。
**不生成偏离表/响应矩阵（G-01 出局），不做"建议怎么改"**。

两条确定性动作：
1. 行定位：偏离表每行的关键词在方案正文中检索，输出 行号 + 原文摘录。
2. 矛盾检测：按该行声明的类型（满足/偏离），在定位段落检测相反信号：
   - 表称「满足」：正文出现否定/回避信号（不提供/未按/不满足/暂不…）→ CONFLICT
   - 表称「偏离」：正文出现完全满足信号（完全满足/无偏离/全部响应…）→ CONFLICT
   - 未发现相反信号 → LOCATED（一致）
   - 关键词未命中 → NOT_FOUND 转人工（表述可能不同，不猜）

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
- 只吃文本层；扫描件、图片、截图不入判定。
- 偏离表由用户提供，引擎不生成（G-01 已拆）。
- 检测的是"信号"不是语义：引擎不下"正文是否真的满足"的结论——没检出相反
  信号只代表"未发现矛盾"，不代表"内容真达标"（README §三 第 3 行：表称满足、
  正文不满足＝评标当场翻车；引擎负责把翻车点抓出来）。

输出态：LOCATED（定位且未见矛盾）/ CONFLICT（定位但发现矛盾信号）/
NOT_FOUND（未定位）/ UNKNOWN（无法判定）。整体终态只分 DONE 与 REVIEW。
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 输出态 ----------------------------------------------------------------

LOCATED = "LOCATED"      # 定位成功且未发现相反信号
CONFLICT = "CONFLICT"    # 定位成功但发现相反信号（表与正文矛盾）
NOT_FOUND = "NOT_FOUND"  # 关键词未在正文定位到（转人工）
UNKNOWN = "UNKNOWN"      # 无法判定（解析失败/扫描件）

# ---- 声明类型归一 ----------------------------------------------------------

_SATISFY_ALIASES = ("满足", "完全满足", "全部满足", "无偏离", "无差异", "符合")
_DEVIATE_ALIASES = ("偏离", "不满足", "部分偏离", "部分满足", "不符合", "负偏离")

# 矛盾信号：表称满足时，正文出现这些 → 回避/否定
_NEG_SIGNALS = (
    "不提供", "未按", "不满足", "未满足", "无法满足", "暂不", "未能",
    "不响应", "无法响应", "不承诺", "不包含", "不承担", "不足", "不适用",
    "不予", "婉拒",
)

# 矛盾信号：表称偏离时，正文出现这些 → 声称全满足
_POS_SIGNALS = (
    "完全满足", "全部满足", "无偏离", "完全响应", "全部响应",
    "满足全部", "无差异", "完全符合", "全部符合", "无保留响应",
)

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr",
)

# ---- 字段识别 --------------------------------------------------------------

DEVIATION_FIELDS = {
    "条目": "item",
    "项": "item",
    "声明": "decl",
    "类型": "decl",
    "关键词": "keywords",
    "关键字": "keywords",
    "依据": "basis",
    "位置": "basis",
}

# ---- 归一化 ----------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def _norm_lite(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "").replace("\u3000", "")


# ---- 行解析 ----------------------------------------------------------------

def _split_pairs(body: str) -> list[tuple[str, str]]:
    keys = list(re.finditer(r"[^=\s]+=", body))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(keys):
        key = m.group(0)[:-1]
        end = keys[i + 1].start() if i + 1 < len(keys) else len(body)
        val = body[m.end():end].strip()
        if key and val:
            out.append((key, val))
    return out


def _values(raw: str) -> list[str]:
    return [t for t in re.split(r"[,，、;；]", _norm(raw)) if t]


def _norm_decl(raw: str) -> str:
    s = _norm(raw)
    if not s:
        return "满足"
    # 先匹配更长别名（"不满足"含"满足"，但语义是偏离）
    for a in sorted(_DEVIATE_ALIASES, key=len, reverse=True):
        if a in s:
            return "偏离"
    for a in sorted(_SATISFY_ALIASES, key=len, reverse=True):
        if a in s:
            return "满足"
    return s


def parse_deviation_line(line: str) -> dict | None:
    """解析一条偏离表行：{item, decl(满足|偏离), keywords[], basis} 或 None。"""
    if not line:
        return None
    if any(h in line.lower() for h in _SCAN_HINTS):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    fields: dict = {}
    for key, val in _split_pairs(body[1]):
        fid = DEVIATION_FIELDS.get(_norm(key))
        if fid is None:
            continue
        fields.setdefault(fid, _norm(val))
    if "item" not in fields:
        return None
    keywords = _values(fields.get("keywords", "")) or [fields["item"]]
    return {
        "item": fields["item"],
        "decl": _norm_decl(fields.get("decl", "满足")),
        "keywords": keywords,
        "basis": fields.get("basis", ""),
    }


# ---- 判定 ----------------------------------------------------------------

def detect_signals(text: str) -> dict:
    """在文本中检测否定/回避信号与完全满足信号，返回命中的信号词列表。"""
    t = _norm_lite(text)
    return {
        "neg": [s for s in _NEG_SIGNALS if _norm_lite(s) in t],
        "pos": [s for s in _POS_SIGNALS if _norm_lite(s) in t],
    }


def crosscheck_row(dev: dict, tender_lines: list[str], max_hits: int = 3) -> dict:
    """单行核对：定位 + 矛盾检测。

    返回 {**dev, located, hits[], signals, status}
    """
    norm_lines = [_norm_lite(ln) for ln in tender_lines]
    kws = [_norm_lite(k) for k in dev["keywords"]]
    hits = []
    for idx, nl in enumerate(norm_lines):
        if any(kw and kw in nl for kw in kws):
            hits.append({"line_no": idx + 1, "excerpt": tender_lines[idx][:120]})
            if len(hits) >= max_hits:
                break

    if not hits:
        return {**dev, "located": False, "hits": [], "signals": {"neg": [], "pos": []},
                "status": NOT_FOUND}

    # 只取命中行聚合做信号检测（避免全文误报）
    agg = "\n".join(tender_lines[h["line_no"] - 1] for h in hits)
    signals = detect_signals(agg)

    if dev["decl"] == "满足":
        status = CONFLICT if signals["neg"] else LOCATED
    else:  # 偏离
        status = CONFLICT if signals["pos"] else LOCATED

    return {**dev, "located": True, "hits": hits, "signals": signals, "status": status}


def evaluate(tender_lines: list[str], deviations: list[dict]) -> dict:
    """全量判定，返回 {rows:[…], summary, verdict}。

    整体终态只分 DONE / REVIEW：
      - 任何 CONFLICT / NOT_FOUND / UNKNOWN -> REVIEW
      - 全部 LOCATED -> DONE（未发现矛盾；不代表内容真达标）
    """
    rows = [crosscheck_row(d, tender_lines) for d in deviations]
    n_located = sum(1 for r in rows if r["status"] == LOCATED)
    n_conflict = sum(1 for r in rows if r["status"] == CONFLICT)
    n_not_found = sum(1 for r in rows if r["status"] == NOT_FOUND)
    n_unknown = sum(1 for r in rows if r["status"] == UNKNOWN)
    return {
        "rows": rows,
        "summary": {
            "total": len(rows),
            "located": n_located,
            "conflict": n_conflict,
            "not_found": n_not_found,
            "unknown": n_unknown,
        },
        "verdict": "REVIEW" if (n_conflict or n_not_found or n_unknown) else "DONE",
    }


# ---- 对外判定（步骤层调用） ------------------------------------------------

def evaluate_issues(result: dict) -> list[Issue]:
    issues: list[Issue] = []
    summ = result["summary"]
    for r in result["rows"]:
        st = r["status"]
        if st == CONFLICT:
            sig = r["signals"]
            detail = "、".join(sig["neg"]) if sig["neg"] else "、".join(sig["pos"])
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"偏离表「{r['item']}」声明为[{r['decl']}]，但正文定位处出现"
                f"相反信号「{detail}」（第 {r['hits'][0]['line_no']} 行），"
                "表与正文矛盾，转人工复核",
            ))
        elif st == NOT_FOUND:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"偏离表「{r['item']}」关键词未在方案正文定位到，可能表述不同，转人工确认",
            ))
        elif st == UNKNOWN:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"偏离表「{r['item']}」无法判定（行无法解析/疑似扫描件），转人工",
            ))
    if summ["total"] == 0:
        issues.append(Issue(IssueLevel.ERROR, "偏离表为空或无法解析"))
    elif not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"全部 {summ['located']} 行偏离表声明均未在正文发现相反信号"
            "（仅核对完成，不构成达标/可投标判断）",
        ))
    return issues
