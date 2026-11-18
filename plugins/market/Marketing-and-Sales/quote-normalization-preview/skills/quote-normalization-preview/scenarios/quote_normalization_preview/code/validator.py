"""
validator.py —— 多格式报价拉平预审 判定规则（护城河区，写死）

判定族 T-02（多来源报价拉平；N-01 多格式报价横向拉平预审、E-11 多供应商
报价横向比较、G-16 多供应商报价统一格式），限缩口径（输入整治计划 §4.1 /
N_候选节点池 §2 T-02）：
  - 只吃文本层报价（文本型 PDF / XLSX / CSV 经宿主转文本）；截图件/图片行
    判 UNKNOWN 转人工，不靠"以后接 OCR"绕过。
  - 币种 / 包装单位 / 含税口径**由用户声明**（口径行），引擎绝不自行换算
    （无声明 → UNKNOWN，不猜汇率/换算系数）。
  - 拉平 = 归一成可比单价；预审 = 同批横向偏离标记（E-11 基线 = 同批中位数）。
  - **不输出"推荐/选哪家"结论**（越权）；不输出"围标/串标"定性（只标偏离
    转人工复核）。

禁做（写死，不可被提示词改）：不 OCR 截图报价；不做跨页猜表头；不自行做
币种换算；不默认 1 SET = 1 PC；不下"选最低价"结论。

输出态：NORMAL（无偏离）/ DEVIATION（显著偏离，必带定位与偏离方向）/
UNKNOWN（口径不可比或无法对齐）。整体终态只分 DONE / REVIEW / ERROR。
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 输出态 ----------------------------------------------------------------

NORMAL = "NORMAL"
DEVIATION = "DEVIATION"
UNKNOWN = "UNKNOWN"
SKIPPED = "SKIPPED"

# 偏离阈值：|偏离中位数| > 20% 才标偏离（写死；展示层 rules.yaml 只影响显示）
DEVIATION_RATIO = 0.20

# ---- 字段识别（键名统一，宿主整理时套用） -----------------------------------

NUMERIC_FIELDS = {
    "单价": "unit_price", "价格": "unit_price",
    "数量": "qty", "数": "qty",
    "金额": "amount", "总价": "amount",
}

TEXT_FIELDS = {
    "供应商": "supplier", "供方": "supplier", "厂家": "supplier",
    "品名": "product", "货名": "product", "物料": "product",
    "型号": "model", "规格": "model", "SKU": "model", "料号": "model",
    "币种": "currency",
    "单位": "unit", "包装单位": "unit",
    "含税": "tax",
}

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr", "截图",
)

# 币种别名：同币种归一（不同币种换算只认用户口径声明，不猜汇率）
_CURRENCY_ALIASES = {
    "USD": "USD", "usd": "USD", "美元": "USD", "$": "USD",
    "CNY": "CNY", "cny": "CNY", "RMB": "CNY", "人民币": "CNY", "¥": "CNY", "元": "CNY",
    "EUR": "EUR", "eur": "EUR", "欧元": "EUR",
}

# 包装单位别名：同单位归一（不同单位换算只认用户口径声明，不猜 1 SET=1 PC）
_UNIT_ALIASES = {
    "PC": "PC", "pc": "PC", "件": "PC", "pcs": "PC", "PCS": "PC", "个": "PC",
    "SET": "SET", "set": "SET", "套": "SET",
    "CTN": "CTN", "ctn": "CTN", "箱": "CTN", "carton": "CTN", "cartons": "CTN",
    "KG": "KG", "kg": "KG", "千克": "KG", "公斤": "KG", "KGS": "KG",
    "LB": "LB", "lb": "LB", "磅": "LB", "lbs": "LB",
}


# ---- 归一化 ----------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def _norm_lite(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "").replace("\u3000", "")


def _norm_currency(raw: str) -> str:
    return _CURRENCY_ALIASES.get(_norm_lite(raw), _norm_lite(raw))


def _norm_unit(raw: str) -> str:
    return _UNIT_ALIASES.get(_norm_lite(raw), _norm_lite(raw))


def _parse_number(raw: str) -> float | None:
    """从纯数值串 "1,500.50" / "500" 提取数值；带任何尾缀/单位返回 None。"""
    s = _norm(raw)
    m = re.match(r"^([\d,]+(?:\.\d+)?)$", s)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


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


def _scan_hit(line: str) -> bool:
    return any(h in line.lower() for h in _SCAN_HINTS)


def parse_decl_line(line: str) -> dict | None:
    """解析一条口径声明行：{rates:{USD:7.2}, convs:{SET:(10,'PC')}, tax:是|否|None}。

    支持三种键（值内不得再出现 `键=`）：
    - `口径:USD=7.2`       币种汇率：1 USD = 7.2 CNY（目标币种固定为 CNY）
    - `口径:SET=10PC`      单位换算：1 SET = 10 PC
    - `口径:含税=是|否`     全局含税口径（各家未标注时按此口径读）
    """
    if not line or _scan_hit(line):
        return None
    body = line.split(":", 1)
    if len(body) != 2 or _norm_lite(body[0]) != "口径":
        return None
    pairs = _split_pairs(body[1])
    if not pairs:
        return None
    decl: dict = {"rates": {}, "convs": {}, "tax": None}
    for key, val in pairs:
        k = _norm_lite(key)
        if k in ("含税", "tax"):
            v = _norm_lite(val)
            decl["tax"] = "是" if v in ("是", "y", "yes", "含税", "true") else "否"
            continue
        if k in _CURRENCY_ALIASES:
            num = _parse_number(val)
            if num is not None:
                decl["rates"][_norm_currency(k)] = num
            continue
        if k in _UNIT_ALIASES or _norm_unit(k) in _UNIT_ALIASES:
            m = re.match(r"^([\d.]+)\s*([A-Za-z\u4e00-\u9fff]+)$", _norm(val))
            if m:
                qty = float(m.group(1).replace(",", ""))
                to_unit = _norm_unit(m.group(2))
                if to_unit and qty > 0:
                    decl["convs"][_norm_unit(k)] = (qty, to_unit)
    return decl


def parse_quote_line(line: str) -> dict | None:
    """解析一条报价行：{supplier, product, model, unit_price, qty, amount,
    currency, unit, tax, raw} 或 None（非报价行/扫描行/解析失败）。"""
    if not line or _scan_hit(line):
        return None
    body = line.split(":", 1)
    if len(body) != 2 or _norm_lite(body[0]) != "报价":
        return None
    pairs = _split_pairs(body[1])
    if not pairs:
        return None
    quote: dict = {}
    for key, val in pairs:
        k = _norm(key)
        fid = NUMERIC_FIELDS.get(k) or TEXT_FIELDS.get(k)
        if fid is None:
            continue
        if fid in NUMERIC_FIELDS.values():
            num = _parse_number(val)
            quote[fid] = num if num is not None else val
        else:
            quote[fid] = val
    if not quote.get("supplier") or not quote.get("product"):
        return None
    return quote


# ---- 口径应用与归一 ----------------------------------------------------------

def _apply_decl(quote: dict, decl: dict) -> tuple[float | None, str | None, str | None, str | None]:
    """归一单价：换算币种到 CNY、换算单位到声明目标单位、校验含税口径。

    返回 (price_norm, currency, unit, tax)；任一维度不可比返回 None 维度。
    """
    price = quote.get("unit_price")
    if not isinstance(price, float):
        return None, None, None, None
    cur = _norm_currency(quote.get("currency", "")) if quote.get("currency") else "CNY"
    unit = _norm_unit(quote.get("unit", "")) if quote.get("unit") else None
    tax = _norm_lite(quote.get("tax", "")) if quote.get("tax") else None

    # 币种：声明汇率才换算，否则与 CNY 不同即不可比
    if cur != "CNY":
        rate = decl["rates"].get(cur)
        if rate is None:
            return price, cur, unit, tax  # 币种维度不可比（交由组级判定）
        price = price * rate
        cur = "CNY"

    # 单位：声明换算才换算，否则原样（交由组级判定）
    if unit:
        conv = decl["convs"].get(unit)
        if conv:
            qty, to_unit = conv
            price = price / qty
            unit = to_unit

    # 含税：行标注与全局口径冲突 → 该行无可比单价（转人工）
    tax_flag = decl.get("tax")
    if tax_flag is not None and tax and tax_flag != tax:
        return None, cur, unit, tax
    return price, cur, unit, tax


# ---- 横向偏离检测 -------------------------------------------------------------

def _median(nums: list[float]) -> float:
    s = sorted(nums)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def flatten_groups(quotes: list[dict], decl: dict) -> list[dict]:
    """按 品名+型号 分组并归一单价。

    返回 [{product, model, quotes:[{supplier, price_raw, price_norm, currency,
    unit, tax, status, deviation, detail}]}]
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for q in quotes:
        product = _norm_lite(q.get("product", ""))
        model = _norm_lite(q.get("model", "")) if q.get("model") else ""
        groups.setdefault((product, model), []).append(q)

    out: list[dict] = []
    for (product, model), members in groups.items():
        items: list[dict] = []
        for q in members:
            price_raw = q.get("unit_price")
            price_norm, cur, unit, tax = _apply_decl(q, decl)
            items.append({
                "supplier": q.get("supplier"),
                "price_raw": price_raw if isinstance(price_raw, float) else None,
                "price_norm": price_norm,
                "currency": cur,
                "unit": unit,
                "tax": tax,
            })
        out.append({"product": product, "model": model, "quotes": items})
    return out


def horizontal_check(groups: list[dict]) -> list[dict]:
    """对每组做横向偏离检测：组内归一单价与中位数比较，|偏离|>阈值标 DEVIATION。

    可比前提：组内 币种/单位/含税 各维度统一（None 维度表示不可比）。≥2 家才
    计算；1 家标 SKIPPED；不可比维度 → 该行 UNKNOWN（带原因）。
    """
    for g in groups:
        items = g["quotes"]
        if len(items) < 2:
            for it in items:
                it["status"] = SKIPPED
                it["deviation"] = None
                it["detail"] = "组内仅 1 家，无横向对照，跳过"
            g["status"] = SKIPPED
            g["median"] = None
            continue

        # 可比性：币种 / 单位 / 含税 各维度必须统一
        curs = {it["currency"] for it in items}
        units = {it["unit"] for it in items}
        taxes = {it["tax"] for it in items}
        incomparable: list[str] = []
        if len(curs) > 1:
            incomparable.append("币种口径不一致（无换算声明）")
        if len(units) > 1:
            incomparable.append("包装单位不一致（无换算声明）")
        if len(taxes) > 1:
            incomparable.append("含税口径不一致")
        if incomparable:
            for it in items:
                it["status"] = UNKNOWN
                it["deviation"] = None
                it["detail"] = "；".join(incomparable) + "，转人工"
            g["status"] = UNKNOWN
            g["median"] = None
            continue

        # 缺单价的成员不可参与，标 UNKNOWN
        priced = [it for it in items if it["price_norm"] is not None]
        for it in items:
            if it["price_norm"] is None:
                it["status"] = UNKNOWN
                it["deviation"] = None
                it["detail"] = "缺可比单价（无单价或含税口径不可比），转人工"
        if not priced:
            g["status"] = UNKNOWN
            g["median"] = None
            continue

        median = _median([it["price_norm"] for it in priced])
        if median <= 0:
            for it in priced:
                it["status"] = UNKNOWN
                it["deviation"] = None
                it["detail"] = "中位数为 0，无法计算偏离"
            g["status"] = UNKNOWN
            g["median"] = None
            continue

        g["median"] = median
        g["status"] = NORMAL
        for it in priced:
            dev = (it["price_norm"] - median) / median
            it["deviation"] = round(dev, 4)
            if abs(dev) > DEVIATION_RATIO:
                it["status"] = DEVIATION
                it["detail"] = (f"偏离中位数 {dev:+.1%}，超出 ±{DEVIATION_RATIO:.0%} "
                                f"阈值，转人工复核（可能为合理价差或串标线索，不下定性）")
                g["status"] = DEVIATION
            else:
                it["status"] = NORMAL
                it["detail"] = f"偏离中位数 {dev:+.1%}，在 ±{DEVIATION_RATIO:.0%} 内"
    return groups


def evaluate(quotes: list[dict], decl: dict | None = None) -> dict:
    """全量判定，返回 {groups:[…], summary, verdict}。

    整体终态：
      - 任何 DEVIATION / UNKNOWN → REVIEW
      - 全部 NORMAL / SKIPPED → DONE
      - 无任何报价行 → REVIEW（调用方兜底）
    """
    decl = decl or {"rates": {}, "convs": {}, "tax": None}
    if not quotes:
        return {"groups": [], "summary": {"groups": 0, "quoted": 0, "normal": 0,
                                          "deviation": 0, "unknown": 0, "skipped": 0},
                "verdict": "REVIEW"}
    groups = flatten_groups(quotes, decl)
    groups = horizontal_check(groups)

    n_normal = sum(1 for g in groups for it in g["quotes"] if it["status"] == NORMAL)
    n_dev = sum(1 for g in groups for it in g["quotes"] if it["status"] == DEVIATION)
    n_unknown = sum(1 for g in groups for it in g["quotes"] if it["status"] == UNKNOWN)
    n_skipped = sum(1 for g in groups for it in g["quotes"] if it["status"] == SKIPPED)
    n_quoted = sum(len(g["quotes"]) for g in groups)
    n_groups = len(groups)
    verdict = "REVIEW" if (n_dev or n_unknown) else "DONE"
    return {
        "groups": groups,
        "summary": {"groups": n_groups, "quoted": n_quoted, "normal": n_normal,
                    "deviation": n_dev, "unknown": n_unknown, "skipped": n_skipped},
        "verdict": verdict,
    }


# ---- 对外判定（步骤层调用） ------------------------------------------------

def evaluate_issues(result: dict) -> list[Issue]:
    issues: list[Issue] = []
    summ = result["summary"]
    for g in result["groups"]:
        for it in g["quotes"]:
            st = it["status"]
            if st == DEVIATION:
                issues.append(Issue(
                    IssueLevel.REVIEW,
                    f"报价偏离：{it['supplier']}「{g['product']}"
                    f"{('/' + g['model']) if g['model'] else ''}」{it['detail']}"
                    f"（归一单价 {it['price_norm']}，中位数 {g['median']}）",
                ))
            elif st == UNKNOWN:
                issues.append(Issue(
                    IssueLevel.REVIEW,
                    f"报价不可比：{it['supplier']}「{g['product']}」{it['detail']}",
                ))
    if summ["quoted"] == 0:
        issues.append(Issue(IssueLevel.REVIEW, "没有任何可解析的报价行，转人工核对"))
    elif not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"全部 {summ['quoted']} 条报价已拉平，{summ['normal']} 条无偏离"
            f"（仅完成拉平与偏离标记，不构成选商结论）",
        ))
    return issues
