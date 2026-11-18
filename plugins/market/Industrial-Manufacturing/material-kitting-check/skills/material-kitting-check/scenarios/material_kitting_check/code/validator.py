"""
validator.py —— 物料齐套核对 判定规则（护城河区，写死）

判定族 T-01（跨文档字段/数值核对，B-43 内部系统导出件线；N-15 物料齐套与
缺料风险核对），限缩口径（输入整治计划 §4.2 / N_候选节点池 §2 T-01）：
  - 单次运行读用户导出的四张表（订单 × BOM 明细 × 库存 × 在途）合并文本层，
    不做实时 API（ERP/MES 出局）。
  - 物料编码为跨表主键；按生产订单展开 BOM，比对库存+在途，标记齐套/缺套
    及缺口数量（B-43）。
  - 单位 / 批次口径**由用户声明**（口径行），引擎绝不自行换算单位、
    绝不跨批自动合并（无声明 → UNKNOWN 转人工）。

禁做（写死，不可被提示词改）：不接 ERP/MES API；不做单位自动换算；不跨批
自动合并；不下"建议下单/补货"结论（越权）。

输出态：COMPLETE（齐套，缺口 ≤ 0）/ SHORT（缺套，缺口 > 0，必带缺口数量）/
UNKNOWN（口径不可比或缺展开数据）。整体终态只分 DONE / REVIEW / ERROR。
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 输出态 ----------------------------------------------------------------

COMPLETE = "COMPLETE"
SHORT = "SHORT"
UNKNOWN = "UNKNOWN"

# ---- 字段识别（键名统一，宿主整理时套用） -----------------------------------

NUMERIC_FIELDS = {
    "数量": "qty", "数": "qty",
    "用量": "qty_per",
}

TEXT_FIELDS = {
    "订单号": "order_id", "单号": "order_id",
    "成品": "product", "品名": "product", "物料": "product",
    "名称": "name", "子件": "part_name", "物料名称": "part_name",
    "型号": "model", "规格": "model",
    "编码": "code", "料号": "code", "物料编码": "code", "物料号": "code",
    "单位": "unit", "包装单位": "unit",
    "批次": "batch", "批号": "batch",
    "交期": "due_date", "到货日": "due_date",
}

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr", "截图",
)


# ---- 归一化 ----------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def _norm_lite(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "").replace("\u3000", "")


def _parse_number(raw: str) -> float | None:
    """从纯数值串 "1,500.50" / "500" 提取数值；带任何尾缀/单位返回 None。"""
    s = _norm(raw)
    m = re.match(r"^([\d,]+(?:\.\d+)?)$", s)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def _scan_hit(line: str) -> bool:
    return any(h in line.lower() for h in _SCAN_HINTS)


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


# ---- 口径行解析 -------------------------------------------------------------

def parse_decl_line(line: str) -> dict | None:
    """解析一条口径声明行。

    支持三种键（值内不得再出现 `键=`）：
    - `口径:单位=PC`       全局单位口径（各表未标注单位时按此读）
    - `口径:批次=合并`     批次聚合口径：同编码多批求和；缺声明且多批 → UNKNOWN
    - `口径:安全库存=5`    全局预留安全库存（每子件需要量加 5；默认 0）
    - `口径:换算:KG=1000PC` 单位换算声明：1 KG = 1000 PC（不声明不换算）
    """
    if not line or _scan_hit(line):
        return None
    body = line.split(":", 1)
    if len(body) != 2 or _norm_lite(body[0]) != "口径":
        return None
    pairs = _split_pairs(body[1])
    if not pairs:
        return None
    decl: dict = {"unit": None, "batch_mode": None, "safety": None, "convs": {}}
    for key, val in pairs:
        kk = _norm_lite(key)
        if kk == "单位":
            decl["unit"] = _norm(val)
            continue
        if kk == "批次":
            v = _norm_lite(val)
            decl["batch_mode"] = "合并" if v in ("合并", "merge", "sum", "聚合") else None
            continue
        if kk == "安全库存":
            num = _parse_number(val)
            if num is not None and num >= 0:
                decl["safety"] = num
            continue
        m = re.match(r"^换算(?::([^=]+))?$", kk)
        if m:
            src = _norm_lite(m.group(1) or "")
            cm = re.match(r"^([\d.]+)\s*([A-Za-z\u4e00-\u9fff]+)$", _norm(val))
            if cm and src:
                qty = float(cm.group(1).replace(",", ""))
                to_unit = _norm(cm.group(2))
                if qty > 0:
                    decl["convs"][src] = (qty, to_unit)
            continue
    return decl


# ---- 四表行解析 -------------------------------------------------------------

def _parse_row(line: str) -> tuple[str, dict] | None:
    """解析一条数据行，返回 (行类型, 字段字典)；非数据行/扫描行返回 None。

    行类型 ∈ {订单, BOM, 库存, 在途}，前缀在冒号前。
    """
    if not line or _scan_hit(line):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    pfx = _norm_lite(body[0])
    if pfx not in ("订单", "bom", "库存", "在途"):
        return None
    pairs = _split_pairs(body[1])
    if not pairs:
        return None
    row: dict = {}
    for key, val in pairs:
        k = _norm(key)
        fid = NUMERIC_FIELDS.get(k) or TEXT_FIELDS.get(k)
        if fid is None:
            continue
        if fid in NUMERIC_FIELDS.values():
            num = _parse_number(val)
            row[fid] = num if num is not None else val
        else:
            row[fid] = val
    return pfx, row


def parse_order_line(line: str) -> dict | None:
    r = _parse_row(line)
    return r[1] if r and r[0] == "订单" else None


def parse_bom_line(line: str) -> dict | None:
    r = _parse_row(line)
    return r[1] if r and r[0] == "bom" else None


def parse_stock_line(line: str) -> dict | None:
    r = _parse_row(line)
    return r[1] if r and r[0] == "库存" else None


def parse_transit_line(line: str) -> dict | None:
    r = _parse_row(line)
    return r[1] if r and r[0] == "在途" else None


# ---- 单位换算 ----------------------------------------------------------------

def _conv_available(convs: dict, src_unit: str, target_unit: str) -> float | None:
    """src_unit → target_unit 换算系数（数量 = 源数量 × 系数）；无声明返回 None。"""
    if not src_unit or not target_unit:
        return None
    if _norm_lite(src_unit) == _norm_lite(target_unit):
        return 1.0
    conv = convs.get(_norm_lite(src_unit))
    if not conv:
        return None
    qty, to_unit = conv
    if _norm_lite(to_unit) != _norm_lite(target_unit):
        return None
    return qty


# ---- 齐套核对 ----------------------------------------------------------------

def check_kitting(orders: list[dict], boms: list[dict],
                  stocks: list[dict], transits: list[dict],
                  decl: dict | None = None) -> dict:
    """按生产订单展开 BOM，比对库存+在途，标齐套/缺套及缺口数量。

    返回 {orders:[…], summary, verdict}：
      orders[] = {order_id, product, model, status, components:[…], detail}
      components[] = {part_code, part_name, need, safety, available, gap, status, detail}
    """
    decl = decl or {"unit": None, "batch_mode": None, "safety": 0.0, "convs": {}}
    if not orders:
        return {"orders": [], "summary": {"orders": 0, "components": 0,
                                          "complete": 0, "short": 0, "unknown": 0},
                "verdict": "REVIEW"}

    # 索引：BOM 按 (product, model)（model 可空）；库存/在途按编码
    bom_index: dict[tuple[str, str], list[dict]] = {}
    for b in boms:
        prod = _norm_lite(b.get("product", ""))
        model = _norm_lite(b.get("model", "")) if b.get("model") else ""
        bom_index.setdefault((prod, model), []).append(b)

    stock_by_code: dict[str, list[dict]] = {}
    for s in stocks:
        code = _norm_lite(s.get("code", ""))
        if code:
            stock_by_code.setdefault(code, []).append(s)
    transit_by_code: dict[str, list[dict]] = {}
    for t in transits:
        code = _norm_lite(t.get("code", ""))
        if code:
            transit_by_code.setdefault(code, []).append(t)

    unit_global = _norm_lite(decl["unit"]) if decl.get("unit") else None
    batch_merge = decl.get("batch_mode") == "合并"
    safety = decl.get("safety") or 0.0
    convs = decl.get("convs", {})

    out_orders: list[dict] = []
    n_comp = n_short = n_unknown = 0

    for o in orders:
        order_id = o.get("order_id") or "?"
        product = o.get("product", "")
        model = _norm_lite(o.get("model", "")) if o.get("model") else ""
        qty = o.get("qty")
        if not isinstance(qty, float):
            out_orders.append({
                "order_id": order_id, "product": o.get("product", ""),
                "model": o.get("model", ""),
                "status": UNKNOWN, "components": [], "detail": "订单数量缺失或非数值，转人工",
            })
            n_unknown += 1
            continue

        # 按 (product, model) 精确匹配，model 为空时退化为只按 product
        boms_matched = bom_index.get((_norm_lite(product), model)) or (
            bom_index.get((_norm_lite(product), "")) if not model else []
        )
        if not boms_matched:
            out_orders.append({
                "order_id": order_id, "product": o.get("product", ""),
                "model": o.get("model", ""),
                "status": UNKNOWN, "components": [],
                "detail": f"成品「{product}」无 BOM 展开数据，转人工",
            })
            n_unknown += 1
            continue

        components: list[dict] = []
        order_unknown = False
        order_short = False
        for b in boms_matched:
            part_code = _norm_lite(b.get("code", "")) or _norm_lite(b.get("part_name", ""))
            part_name = b.get("part_name") or b.get("code") or part_code
            qty_per = b.get("qty_per")
            if not isinstance(qty_per, float) or qty_per <= 0:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": None, "safety": safety, "available": None,
                    "gap": None, "status": UNKNOWN,
                    "detail": "BOM 用量缺失或非数值，转人工",
                })
                order_unknown = True
                continue

            # 需要量单位 = BOM 用量单位（缺时用全局单位口径；再缺 → UNKNOWN）
            need_unit = _norm_lite(b.get("unit", "")) or unit_global
            if not need_unit:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": qty * qty_per, "safety": safety, "available": None,
                    "gap": None, "status": UNKNOWN,
                    "detail": "单位口径缺声明（BOM 用量无单位且无全局单位口径），转人工",
                })
                order_unknown = True
                continue
            need = qty * qty_per

            # 可得量 = 库存 + 在途（按编码聚合）
            st_rows = stock_by_code.get(part_code, [])
            tr_rows = transit_by_code.get(part_code, [])
            if not st_rows and not tr_rows:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": need, "safety": safety, "available": 0.0,
                    "gap": need + safety, "status": SHORT,
                    "detail": "无库存且在途记录，缺口 = 需要量 + 安全库存",
                })
                order_short = True
                continue

            # 批次口径：同一来源表内多批且未声明合并 → 不跨批自动合并，转人工。
            # （库存 1 批 + 在途 1 批 = B-43 定义的"比对库存+在途"，直接相加）
            if len(st_rows) > 1 and not batch_merge:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": need, "safety": safety, "available": None,
                    "gap": None, "status": UNKNOWN,
                    "detail": (f"编码 {part_code} 存在 {len(st_rows)} 批库存，"
                               f"未声明 `口径:批次=合并`，不跨批自动合并，转人工"),
                })
                order_unknown = True
                continue
            if len(tr_rows) > 1 and not batch_merge:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": need, "safety": safety, "available": None,
                    "gap": None, "status": UNKNOWN,
                    "detail": (f"编码 {part_code} 存在 {len(tr_rows)} 批在途，"
                               f"未声明 `口径:批次=合并`，不跨批自动合并，转人工"),
                })
                order_unknown = True
                continue

            # 单位：各行单位须与需要量单位一致或有换算声明
            available = 0.0
            unit_issue: str | None = None
            for row in st_rows + tr_rows:
                row_unit = _norm_lite(row.get("unit", "")) or unit_global
                if not row_unit:
                    unit_issue = f"库存/在途行「{row.get('name') or row.get('code')}」单位缺失"
                    break
                factor = _conv_available(convs, row_unit, need_unit)
                if factor is None:
                    unit_issue = (f"单位 {row_unit} 与需要量单位 {need_unit} 不一致"
                                  f"且无换算声明，转人工")
                    break
                q = row.get("qty")
                if not isinstance(q, float):
                    unit_issue = f"库存/在途行「{row.get('name') or row.get('code')}」数量缺失"
                    break
                available += q * factor
            if unit_issue:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": need, "safety": safety, "available": None,
                    "gap": None, "status": UNKNOWN, "detail": unit_issue,
                })
                order_unknown = True
                continue

            gap = need + safety - available
            if gap > 0:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": need, "safety": safety, "available": round(available, 4),
                    "gap": round(gap, 4), "status": SHORT,
                    "detail": f"缺口 {gap:g}（需要 {need:g} + 安全 {safety:g} − 可得 {available:g}）",
                })
                order_short = True
            else:
                components.append({
                    "part_code": part_code, "part_name": part_name,
                    "need": need, "safety": safety, "available": round(available, 4),
                    "gap": round(gap, 4), "status": COMPLETE,
                    "detail": f"齐套（需要 {need:g} + 安全 {safety:g} ≤ 可得 {available:g}）",
                })
                n_comp += 1

        if order_unknown:
            status = UNKNOWN
            detail = "存在口径不可比或缺数据的子件，转人工"
        elif order_short:
            status = SHORT
            detail = "存在缺套子件，缺口数量见子件明细"
        else:
            status = COMPLETE
            detail = "全部子件齐套"
        out_orders.append({
            "order_id": order_id, "product": o.get("product", ""),
            "model": o.get("model", ""),
            "status": status, "components": components, "detail": detail,
        })

    # 汇总
    for od in out_orders:
        for c in od["components"]:
            if c["status"] == SHORT:
                n_short += 1
            elif c["status"] == UNKNOWN:
                n_unknown += 1
    n_orders = len(out_orders)
    n_components = sum(len(od["components"]) for od in out_orders)
    verdict = "REVIEW" if (n_short or n_unknown) else "DONE"
    return {
        "orders": out_orders,
        "summary": {"orders": n_orders, "components": n_components,
                    "complete": n_comp, "short": n_short, "unknown": n_unknown},
        "verdict": verdict,
    }


# ---- 对外判定（步骤层调用） ------------------------------------------------

def evaluate(orders: list[dict], boms: list[dict],
             stocks: list[dict], transits: list[dict],
             decl: dict | None = None) -> dict:
    return check_kitting(orders, boms, stocks, transits, decl)


def evaluate_issues(result: dict) -> list[Issue]:
    issues: list[Issue] = []
    summ = result["summary"]
    for od in result["orders"]:
        for c in od["components"]:
            st = c["status"]
            if st == SHORT:
                issues.append(Issue(
                    IssueLevel.REVIEW,
                    f"缺套：订单「{od['order_id']}」子件「{c['part_name']}"
                    f"（{c['part_code']}）」{c['detail']}",
                ))
            elif st == UNKNOWN:
                issues.append(Issue(
                    IssueLevel.REVIEW,
                    f"不可判定：订单「{od['order_id']}」子件「{c['part_name']}"
                    f"（{c['part_code']}）」{c['detail']}",
                ))
    if summ["orders"] == 0:
        issues.append(Issue(IssueLevel.REVIEW, "没有任何可解析的订单行，转人工核对"))
    elif not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"全部 {summ['orders']} 个订单齐套，{summ['components']} 个子件无缺口"
            f"（仅完成齐套核对，不构成补货/下单建议）",
        ))
    return issues
