"""
validator.py —— 单证交叉核对 判定规则（护城河区，写死）

判定族 T-01a（跨文档相符核对子族；N-06 PI/PO、N-07 提单草单 vs 出货清单、
N-08 发票/装箱单跨单部分）限缩口径（S2.2 / 输入整治计划 §4.3）：
多份单证同场，逐字段比对；**数值一律代码算，LLM 只做字段抽取与语义对齐**
（本引擎即"代码算"部分，零 LLM 调用）。

硬性纪律（S2.2 工程含义）：
1. 口径不可比时必须停而不是凑：同一字段两侧单位/度量不可比（CTN vs PC、KG vs
   LB 无换算依据）→ `UNKNOWN`，**不得默认 1 CTN = 1 PC**。
2. 定位是硬性输出：每条不一致结论必须带 文件名+行号+原文摘录（业务可复核）。
3. 主要失败模式是漏报矛盾与编造对应关系：本引擎宁可 UNKNOWN 也不编造。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
- 只吃文本层单证（PO/PI/INV/PL/BL/SL）；扫描件、图片、截图不入判定。
- 单证行格式：`单证:类型=PO 品名=… 数量=… 单价=… 金额=… 币种=… …`
- 键名统一由宿主在整理时完成（INPUT_CONTRACT 定义键名集）。
- T-01b（单文档内部自洽：合计=分项和、箱号连续）**不在本包**——那是脚本/另一子族。

输出态：MATCH（跨单证一致）/ CONFLICT（跨单证不一致，必带定位）/
UNKNOWN（口径不可比或无法判定）。整体终态只分 DONE / REVIEW / ERROR。
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 输出态 ----------------------------------------------------------------

MATCH = "MATCH"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"

# ---- 单证类型 --------------------------------------------------------------

DOC_TYPES = ("PO", "PI", "INV", "PL", "BL", "SL")

_DOC_TYPE_ALIASES = {
    "po": "PO", "订单": "PO", "采购订单": "PO", "客户订单": "PO",
    "pi": "PI", "形式发票": "PI", "形式inv": "PI",
    "inv": "INV", "发票": "INV", "商业发票": "INV",
    "pl": "PL", "装箱单": "PL", "箱单": "PL",
    "bl": "BL", "提单": "BL", "b/l": "BL", "海运提单": "BL",
    "sl": "SL", "出货清单": "SL", "发货清单": "SL",
}

# ---- 字段识别（键名统一，宿主整理时套用） -----------------------------------

# 数值字段：值可能是 "500" / "500.00" / "1,000" / "1500KG"（数值+单位）
NUMERIC_FIELDS = {
    "数量": "qty", "数": "qty",
    "单价": "unit_price", "价格": "unit_price",
    "金额": "amount", "总价": "amount",
    "件数": "packages", "箱数": "cartons",
    "毛重": "gross_weight", "净重": "net_weight",
    "体积": "volume", "方数": "volume",
}

# 文本字段：归一化后直接比对
TEXT_FIELDS = {
    "品名": "product", "货名": "product",
    "型号": "model", "SKU": "model", "料号": "model", "规格": "model",
    "币种": "currency",
    "柜号": "container_no", "货柜号": "container_no",
    "唛头": "marks", "噱头": "marks",
    "起运港": "port_loading", "装货港": "port_loading",
    "目的港": "port_discharge", "卸货港": "port_discharge",
    "发货人": "shipper", "收货人": "consignee",
    "付款节点": "payment_term", "付款条件": "payment_term",
    "海运条款": "ship_term", "贸易条款": "ship_term",
    "包装要求": "pack_req",
}

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr",
)

# 单位别名：同度量单位归一（不同度量单位 → UNKNOWN，不换算）
_UNIT_ALIASES = {
    "CTN": "CTN", "箱": "CTN", "carton": "CTN", "cartons": "CTN",
    "PC": "PC", "件": "PC", "pcs": "PC", "PCS": "PC", "个": "PC",
    "SET": "SET", "套": "SET",
    "KG": "KG", "千克": "KG", "公斤": "KG", "kg": "KG", "KGS": "KG",
    "LB": "LB", "磅": "LB", "lbs": "LB",
    "CBM": "CBM", "立方米": "CBM", "m3": "CBM",
    "USD": "USD", "美元": "USD", "$": "USD",
    "CNY": "CNY", "RMB": "CNY", "人民币": "CNY", "¥": "CNY",
    "EUR": "EUR", "欧元": "EUR",
}


# ---- 归一化 ----------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def _norm_lite(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "").replace("\u3000", "")


def _norm_unit(raw: str) -> str:
    return _UNIT_ALIASES.get(_norm_lite(raw), _norm_lite(raw))


def _unit_label(unit: str | None) -> str:
    return "无单位" if unit is None else str(unit)


def _parse_number(raw: str) -> tuple[float | None, str | None]:
    """从 "1,500.50KG" / "500" / "1500" 提取 (数值, 单位)。单位可选。"""
    s = _norm(raw)
    m = re.match(r"^([\d,]+(?:\.\d+)?)\s*([A-Za-z\u4e00-\u9fff¥$]*)$", s)
    if not m:
        return None, None
    num = float(m.group(1).replace(",", ""))
    unit_raw = m.group(2).strip()
    unit = _norm_unit(unit_raw) if unit_raw else None
    return num, unit


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


def parse_doc_line(line: str) -> dict | None:
    """解析一条单证行：{doc_type, fields:{fid: (raw, num, unit)}, line_no} 或 None。"""
    if not line:
        return None
    if any(h in line.lower() for h in _SCAN_HINTS):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    pairs = _split_pairs(body[1])
    doc_type = None
    fields: dict = {}
    for key, val in pairs:
        k = _norm(key)
        if k in ("类型", "单证", "doc", "type"):
            doc_type = _DOC_TYPE_ALIASES.get(_norm_lite(val))
            continue
        fid = NUMERIC_FIELDS.get(k) or TEXT_FIELDS.get(k)
        if fid is None:
            continue
        fields[fid] = val
    if doc_type is None:
        return None
    return {"doc_type": doc_type, "fields": fields}


# ---- 判定 ----------------------------------------------------------------

def _field_value(fid: str, fields: dict) -> tuple:
    """取字段的归一化比较键。数值字段带单位；文本字段归一化。"""
    raw = fields.get(fid)
    if raw is None:
        return None
    if fid in NUMERIC_FIELDS.values():
        num, unit = _parse_number(raw)
        if num is None:
            return ("UNPARSEABLE", raw)
        return ("NUM", num, unit)
    return ("TXT", _norm_lite(raw))


def crosscheck_fields(docs: list[dict]) -> list[dict]:
    """对出现在 ≥2 份单证中的每个字段做跨单证比对。

    返回 [{fid, present_in:[doc_type...], locations:[{doc_type, line_no, excerpt}],
    status, detail, values}]
    比对口径：
    - 全部归一化后相同 → MATCH
    - 数值字段：数值不同 → CONFLICT；数值同但单位不同度量 → UNKNOWN（不换算）
    - 文本字段：归一化后不同 → CONFLICT
    - 值无法解析（UNPARSEABLE）→ UNKNOWN
    定位是硬性输出：locations 带 单证类型+行号+原文摘录（业务可复核）。
    """
    # 收集每个字段在每份单证中的值
    field_occurrences: dict[str, list[dict]] = {}
    for doc in docs:
        line_no = doc.get("line_no")
        source = doc.get("source")
        for fid, raw in doc["fields"].items():
            field_occurrences.setdefault(fid, []).append({
                "doc_type": doc["doc_type"],
                "raw": raw,
                "key": _field_value(fid, doc["fields"]),
                "line_no": line_no,
                "source": source,
            })

    results: list[dict] = []
    for fid, occ in field_occurrences.items():
        if len(occ) < 2:
            continue  # 只有一份有该字段，无法交叉核对，跳过
        keys = [o["key"] for o in occ]
        present_in = [o["doc_type"] for o in occ]
        locations = [
            {"doc_type": o["doc_type"], "line_no": o["line_no"],
             "excerpt": o["source"] or o["raw"]}
            for o in occ
        ]

        # 无法解析
        if any(k[0] == "UNPARSEABLE" for k in keys):
            results.append({
                "fid": fid,
                "present_in": present_in,
                "locations": locations,
                "status": UNKNOWN,
                "detail": "存在无法解析的值，转人工核对",
                "values": [o["raw"] for o in occ],
            })
            continue

        # 数值字段：比较数值；单位不同度量 → UNKNOWN
        if keys[0][0] == "NUM":
            nums = [k[1] for k in keys]
            units = [k[2] for k in keys]
            if len(set(units)) > 1:
                results.append({
                    "fid": fid,
                    "present_in": present_in,
                    "locations": locations,
                    "status": UNKNOWN,
                    "detail": (f"单位口径不可比（{_unit_label(units[0])} vs "
                               f"{_unit_label(units[-1])}），无换算依据，转人工"),
                    "values": [o["raw"] for o in occ],
                })
                continue
            if len(set(nums)) == 1:
                results.append({
                    "fid": fid, "present_in": present_in, "locations": locations,
                    "status": MATCH, "detail": "跨单证一致",
                    "values": [o["raw"] for o in occ],
                })
            else:
                results.append({
                    "fid": fid, "present_in": present_in, "locations": locations,
                    "status": CONFLICT,
                    "detail": f"数值不一致：{' vs '.join(str(n) for n in nums)}",
                    "values": [o["raw"] for o in occ],
                })
            continue

        # 文本字段
        if len(set(keys)) == 1:
            results.append({
                "fid": fid, "present_in": present_in, "locations": locations,
                "status": MATCH, "detail": "跨单证一致",
                "values": [o["raw"] for o in occ],
            })
        else:
            results.append({
                "fid": fid, "present_in": present_in, "locations": locations,
                "status": CONFLICT,
                "detail": f"内容不一致：{' vs '.join(repr(o['raw']) for o in occ)}",
                "values": [o["raw"] for o in occ],
            })
    return results


def evaluate(docs: list[dict]) -> dict:
    """全量判定，返回 {fields:[…], summary, verdict}。

    整体终态：
      - 任何 CONFLICT / UNKNOWN → REVIEW
      - 全部 MATCH → DONE
      - 单证行无法解析或为空 → ERROR（调用方兜底）
    """
    if not docs:
        return {"fields": [], "summary": {"total": 0, "match": 0, "conflict": 0,
                                          "unknown": 0}, "verdict": "REVIEW"}
    fields = crosscheck_fields(docs)
    n_match = sum(1 for f in fields if f["status"] == MATCH)
    n_conflict = sum(1 for f in fields if f["status"] == CONFLICT)
    n_unknown = sum(1 for f in fields if f["status"] == UNKNOWN)
    verdict = "REVIEW" if (n_conflict or n_unknown) else "DONE"
    return {
        "fields": fields,
        "summary": {"total": len(fields), "match": n_match, "conflict": n_conflict,
                    "unknown": n_unknown},
        "verdict": verdict,
    }


# ---- 对外判定（步骤层调用） ------------------------------------------------

def _loc_text(locations: list[dict]) -> str:
    """把定位列表压成可复核文本：PO 第2行（原文摘录…）。"""
    parts = []
    for loc in locations:
        p = loc["doc_type"]
        if loc.get("line_no"):
            p += f" 第{loc['line_no']}行"
        excerpt = (loc.get("excerpt") or "").strip()
        if excerpt:
            p += f"（{excerpt}）"
        parts.append(p)
    return "；".join(parts)


def evaluate_issues(result: dict) -> list[Issue]:
    issues: list[Issue] = []
    summ = result["summary"]
    for f in result["fields"]:
        st = f["status"]
        loc = _loc_text(f.get("locations", []))
        if st == CONFLICT:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"字段「{f['fid']}」跨单证不一致：{f['detail']}"
                f"（出现于 {'/'.join(f['present_in'])}；定位：{loc}）",
            ))
        elif st == UNKNOWN:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"字段「{f['fid']}」：{f['detail']}（定位：{loc}）",
            ))
    if summ["total"] == 0:
        issues.append(Issue(IssueLevel.INFO, "没有出现在 ≥2 份单证中的字段，无需交叉核对"))
    elif not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"全部 {summ['match']} 个跨单证字段均一致（仅核对完成，不构成通关/放行结论）",
        ))
    return issues
