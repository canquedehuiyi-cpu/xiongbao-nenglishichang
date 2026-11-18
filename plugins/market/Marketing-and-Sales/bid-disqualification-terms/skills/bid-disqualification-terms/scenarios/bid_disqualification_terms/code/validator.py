"""
validator.py —— 废标条款与硬性资格打标 判定规则（护城河区，写死）

判定族 T-07（D-08 废标风险点扫描）限缩口径（N.1 §3 / 输入整治计划 §4.6）：
只做「条款定位 + 要件逐项核对」，**不输出"会废标/不会废标/可投标"结论**，
不生成废标风险摘要（D-08 提炼生成半边已拆掉）。

两条确定性动作：
1. 条款定位：把检查清单里的每个条款（废标/硬性资格）关键词，在招标文件全文
   中检索，输出 行号 + 原文摘录（可逐字回查）。
2. 要件核对：每个条款要求的材料/要件 vs 我方材料清单，标记 命中/缺失/无法判定。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
- 只吃文本层（UTF-8 TXT / 文本 PDF / DOCX / XLSX / CSV）；扫描件、图片、截图、
  手写 OCR 遗留一律不进判定，转人工。
- 检查清单与材料清单由用户提供（引擎不做"从招标文件提炼条款"——那是生成半边）。
- 关键词未命中 ≠ "条款不存在"：一律 NOT_FOUND 转人工（表述可能不同，不猜）。

输出态：LOCATED（定位+材料齐）/ MISSING（定位但材料缺）/ NOT_FOUND（未定位）/
UNKNOWN（无法判定）。整体终态只分 DONE（核对完成）与 REVIEW（需人工）。
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 输出态 ----------------------------------------------------------------

LOCATED = "LOCATED"      # 条款已定位 + 材料已齐
MISSING = "MISSING"      # 条款已定位，但要求材料缺失/未匹配
NOT_FOUND = "NOT_FOUND"  # 条款关键词未在招标文件中定位到（转人工）
UNKNOWN = "UNKNOWN"      # 无法判定（解析失败/扫描件）

# ---- 字段识别 --------------------------------------------------------------

# 检查清单行：`条款:名称=… 关键词=… 材料=… 类别=…`
CHECKLIST_FIELDS = {
    "名称": "name",
    "条款": "name",
    "关键词": "keywords",
    "关键字": "keywords",
    "材料": "materials",
    "资料": "materials",
    "类别": "category",
    "类型": "category",
}

# 材料清单行：`材料:名称=… 关键词=…`
MATERIAL_FIELDS = {
    "名称": "name",
    "材料": "name",
    "关键词": "keywords",
    "关键字": "keywords",
}

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr",
)

_CATEGORY_ALIASES = {
    "废标": "废标",
    "否决": "废标",
    "硬性资格": "硬性资格",
    "资格": "硬性资格",
    "准入": "硬性资格",
}


# ---- 归一化 ----------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def _norm_lite(s: str) -> str:
    """检索用归一化：全半角、去空白、小写。"""
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "").replace("\u3000", "")


# ---- 行解析 ----------------------------------------------------------------

def _split_pairs(body: str) -> list[tuple[str, str]]:
    """把 `键=值` 键值对串切分为 (键, 值) 列表。

    键不允许含空格/等号；值允许含空格（如公司名"北京 科技公司"），
    直到下一个 `键=` 或行尾。值内不得再出现 `键=` 形式（契约注明）。
    """
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
    """把 'a,b、c' 拆成检索词列表，去掉空串。"""
    return [t for t in re.split(r"[,，、;；]", _norm(raw)) if t]


def parse_checklist_line(line: str) -> dict | None:
    """解析一条检查清单行，返回 {name, keywords[], materials[], category} 或 None。"""
    if not line:
        return None
    if any(h in line.lower() for h in _SCAN_HINTS):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    fields: dict = {}
    for key, val in _split_pairs(body[1]):
        fid = CHECKLIST_FIELDS.get(_norm(key))
        if fid is None:
            continue
        fields.setdefault(fid, _norm(val))
    if "name" not in fields:
        return None
    keywords = _values(fields.get("keywords", "")) or [fields["name"]]
    materials = _values(fields.get("materials", ""))
    category = _CATEGORY_ALIASES.get(_norm(fields.get("category", "")), "废标")
    return {
        "name": fields["name"],
        "keywords": keywords,
        "materials": materials,
        "category": category,
    }


def parse_material_line(line: str) -> dict | None:
    """解析一条材料清单行，返回 {name, keywords[]} 或 None。"""
    if not line:
        return None
    if any(h in line.lower() for h in _SCAN_HINTS):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    fields: dict = {}
    for key, val in _split_pairs(body[1]):
        fid = MATERIAL_FIELDS.get(_norm(key))
        if fid is None:
            continue
        fields.setdefault(fid, _norm(val))
    if "name" not in fields:
        return None
    keywords = _values(fields.get("keywords", "")) or [fields["name"]]
    return {"name": fields["name"], "keywords": keywords}


# ---- 判定 ----------------------------------------------------------------

def locate_terms(tender_lines: list[str], checklist: list[dict],
                 max_hits: int = 3) -> dict:
    """条款定位：对每个条款在招标文件行中检索关键词。

    返回 {
      "terms": [ {…条款, "located": bool, "hits": [{"line_no": int, "excerpt": str}]} ]
    }
    关键词任一命中即定位；未命中 -> NOT_FOUND（表述可能不同，不猜）。
    """
    norm_lines = [_norm_lite(ln) for ln in tender_lines]
    terms: list[dict] = []
    for item in checklist:
        hits = []
        kws = [_norm_lite(k) for k in item["keywords"]]
        for idx, nl in enumerate(norm_lines):
            if any(kw and kw in nl for kw in kws):
                hits.append({"line_no": idx + 1, "excerpt": tender_lines[idx][:120]})
                if len(hits) >= max_hits:
                    break
        terms.append({**item, "located": bool(hits), "hits": hits})
    return {"terms": terms}


def check_materials(materials: list[dict], checklist: list[dict]) -> list[dict]:
    """要件核对：每个条款要求材料 vs 我方材料清单。

    返回与 checklist 同序的核对结果：
      {"required": [...], "matched": [...], "missing": [...]}
    匹配规则：材料清单任一条的 名称/关键词 与 要求材料串 归一化子串互含。
    材料清单为空 -> 全部标记"未提供材料清单"（UNKNOWN，转人工）。
    """
    results: list[dict] = []
    for item in checklist:
        required = item["materials"]
        if not required:
            results.append({"required": [], "matched": [], "missing": [],
                            "unknown": True})
            continue
        matched: list[str] = []
        for req in required:
            req_l = _norm_lite(req)
            hit = any(
                req_l in _norm_lite(m["name"]) or _norm_lite(m["name"]) in req_l
                or any(_norm_lite(k) and _norm_lite(k) in req_l or req_l in _norm_lite(k)
                       for k in m["keywords"])
                for m in materials
            )
            if hit:
                matched.append(req)
        missing = [r for r in required if r not in matched]
        results.append({
            "required": required,
            "matched": matched,
            "missing": missing,
            "unknown": not materials,
        })
    return results


def verdict_for(term: dict, mcheck: dict) -> str:
    """单条款状态：NOT_FOUND / MISSING / UNKNOWN / LOCATED。"""
    if not term["located"]:
        return NOT_FOUND
    if mcheck["unknown"]:
        return UNKNOWN if mcheck["required"] else LOCATED
    if mcheck["missing"]:
        return MISSING
    return LOCATED


def evaluate(tender_lines: list[str], checklist: list[dict],
             materials: list[dict]) -> dict:
    """全量判定，返回 {terms:[…含状态], summary, verdict}。

    整体终态只分 DONE / REVIEW：
      - 任何条款 NOT_FOUND / MISSING / UNKNOWN -> REVIEW
      - 全部 LOCATED -> DONE（只表示核对完成，**不代表可投标**）
    """
    loc = locate_terms(tender_lines, checklist)
    mchecks = check_materials(materials, checklist)
    terms = []
    for t, mc in zip(loc["terms"], mchecks):
        terms.append({**t, "material_check": mc, "status": verdict_for(t, mc)})

    n_located = sum(1 for t in terms if t["status"] == LOCATED)
    n_missing = sum(1 for t in terms if t["status"] == MISSING)
    n_not_found = sum(1 for t in terms if t["status"] == NOT_FOUND)
    n_unknown = sum(1 for t in terms if t["status"] == UNKNOWN)
    review = n_missing or n_not_found or n_unknown
    return {
        "terms": terms,
        "summary": {
            "total": len(terms),
            "located": n_located,
            "missing": n_missing,
            "not_found": n_not_found,
            "unknown": n_unknown,
        },
        "verdict": "REVIEW" if review else "DONE",
    }


# ---- 对外判定（步骤层调用） ------------------------------------------------

def evaluate_issues(result: dict) -> list[Issue]:
    """把判定结果转 issue 列表：REVIEW 项逐条列，DONE 给 INFO。"""
    issues: list[Issue] = []
    summ = result["summary"]
    for t in result["terms"]:
        st = t["status"]
        if st == NOT_FOUND:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"条款「{t['name']}」（{t['category']}）未在招标文件中定位到，"
                "可能表述不同，转人工确认",
            ))
        elif st == MISSING:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"条款「{t['name']}」已定位，但要求材料缺失："
                f"{'、'.join(t['material_check']['missing'])}",
            ))
        elif st == UNKNOWN:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"条款「{t['name']}」已定位，但未提供材料清单，无法核对要求材料",
            ))
    if summ["total"] == 0:
        issues.append(Issue(IssueLevel.ERROR, "检查清单为空或无法解析"))
    elif not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"全部 {summ['located']} 条条款已定位且要求材料齐备（仅核对完成，不构成投标判断）",
        ))
    return issues
