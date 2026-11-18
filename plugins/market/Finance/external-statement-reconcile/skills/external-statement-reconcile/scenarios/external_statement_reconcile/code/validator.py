"""
validator.py —— 外部单据对账 勾兑判定（护城河区，写死）

判定基准 = 跨文档相符核对（槽位 2）+ 统计异常（槽位 5 的差异定性），
对应判定族 **T-11 外部线**（银行流水勾兑 / 客户账单核对，N-13 / N-24）。

只做确定性勾兑，**绝不编造勾兑关系把表做平**（FM-01 一票否决）：
- 匹配必须同时满足「客户名归一化相等」+「金额在容差内」；
- 无法归入任何匹配关系的记录 → 未匹配，转人工，禁止硬凑。

输入契约（与 SKILL.md / INPUT_CONTRACT.md 一致）：
- 左表（银行流水 CSV/XLSX 文本层）每行 `流水:键=值`；
- 右表（订单/应收文本层）每行 `订单:键=值`；
- 扫描件/图片不得入内；无法解析的行一律转人工。

判定结果形态：
  matched   = [{left_key, right_keys[], relation: 1:1|1:N|N:1, 尾差?}]
  matched_1_1 / 1_N / N_1 分列便于报告
  writeoff  = 红字冲销对（同单号 ± 金额）
  unmatched = 未匹配记录（左/右分开，转人工）
  tail_diff = 尾差清单（金额差 ≤ TAIL_TOLERANCE 但仍匹配的关系）
  cross_period = 跨期提示（回款日 - 订单日 > CROSS_PERIOD_DAYS，WARN 不阻断）
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from scenario_api import Issue, IssueLevel

# ---- 容差与阈值（写死，不外部化） ------------------------------------------

TAIL_TOLERANCE = 0.02        # 尾差容差（元）：≤ 此差仍判"尾差匹配"
MATCH_TOLERANCE = 0.005      # 精确匹配容差：|a-b| ≤ 此值视为相等
CROSS_PERIOD_DAYS = 60       # 回款日 - 单据日超过此天数 -> 跨期提示

# ---- 字段识别 --------------------------------------------------------------

# 键 -> 语义
RECORD_FIELDS = {
    "日期": "date", "日": "date",
    "客户": "customer", "客户名称": "customer", "对方": "customer",
    "金额": "amount", "金额2": "amount", "发生额": "amount",
    "单号": "ref", "发票号": "ref", "发票": "ref", "订单号": "ref", "单据号": "ref",
    "类型": "kind", "借贷": "kind", "方向": "kind", "摘要": "memo",
}

SIDE_ALIASES = {
    "流水": "left", "银行": "left", "回款": "left", "a": "left",
    "订单": "right", "应收": "right", "发票": "right", "账单": "right", "b": "right",
}

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr",
)


# ---- 归一化 ----------------------------------------------------------------

def _norm_text(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def normalize_customer(name: str) -> str:
    """客户名归一化：全半角、去空格、弱化公司治理词缀，返回可比较指纹。

    例「甲（集团）股份有限公司」→ 与「甲公司」可比。简写"甲"vs"甲公司"
    无法机械判定 -> 不在此归一，交给未匹配转人工（不猜）。
    """
    s = _norm_text(name).lower()
    if not s or s in {"-", "/", "null", "none", "无"}:
        return ""
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[，,、.;；:：]", "", s)
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"(?<=[\u4e00-\u9fa5])股份(?:有限)?公司", "有限公司", s)
    s = re.sub(r"(?<=[\u4e00-\u9fa5])集团有限公司?", "有限公司", s)
    s = re.sub(r"(?<=[\u4e00-\u9fa5])有限(?:责任)?公司", "有限公司", s)
    return s


_DATE_PATTERNS = (
    (re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$"), "%Y-%m-%d"),
    (re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$"), "%d-%m-%Y"),
    (re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日?$"), "%Y-%m-%d"),
    (re.compile(r"^(\d{1,2})[-\s]([A-Za-z]{3})[-\s](\d{4})$"), "%d-%b-%Y"),
)


def parse_date(s: str) -> str | None:
    """多格式日期归一为 ISO `YYYY-MM-DD`；无法解析返回 None（转人工）。"""
    t = _norm_text(s)
    if not t:
        return None
    for pat, fmt in _DATE_PATTERNS:
        m = pat.match(t)
        if m:
            try:
                if "%b" in fmt:
                    d = datetime.strptime(t, fmt).date()
                else:
                    g = m.groups()
                    d = date(int(g[0]), int(g[1]), int(g[2]))
                return d.isoformat()
            except ValueError:
                continue
    return None


def parse_amount(s: str) -> float | None:
    """金额解析：去 ¥￥ 与千分位逗号；负数/借贷方向由符号表示。

    返回 float；无法解析返回 None（转人工，不猜）。保留两位精度由 float 足够。
    """
    t = _norm_text(s).replace("¥", "").replace("￥", "").replace(",", "")
    t = t.replace("（", "(").replace("）", ")")
    if not t or t in {"-", "/", "null", "none", "无"}:
        return None
    try:
        return float(t)
    except ValueError:
        return None


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


def parse_record(line: str) -> dict | None:
    """从一行 `侧:键=值 键=值` 解析记录。

    返回 {side, fields:{date/customer/amount/ref/kind/memo}}；命中扫描提示或
    无法归侧/无键值对返回 None（由调用方转人工）。
    """
    if not line:
        return None
    low = line.lower()
    if any(h in low for h in _SCAN_HINTS):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    side = SIDE_ALIASES.get(_norm_text(body[0]).lower(), _norm_text(body[0]).lower())
    if side not in ("left", "right"):
        return None
    fields: dict = {}
    for key, val in _split_pairs(body[1]):
        k = RECORD_FIELDS.get(_norm_text(key))
        if k is None:
            continue
        if not val:
            continue
        fields.setdefault(k, val)
    if not fields:
        return None
    return {"side": side, "fields": fields}


def _as_float(rec: dict) -> float | None:
    return parse_amount(rec["fields"].get("amount", ""))


def _as_date(rec: dict) -> str | None:
    return parse_date(rec["fields"].get("date", ""))


def _as_customer(rec: dict) -> str:
    return normalize_customer(rec["fields"].get("customer", ""))


# ---- 勾兑判定 --------------------------------------------------------------

def reconcile(left: list[dict], right: list[dict]) -> dict:
    """对左右两侧记录做确定性勾兑。

    返回结构：
      {
        "matched": [...],          # 已匹配关系（含 relation / tail_diff）
        "writeoff": [...],         # 红字冲销对
        "unmatched_left": [...],   # 银行侧未匹配（转人工）
        "unmatched_right": [...],  # 订单侧未匹配（转人工）
        "tail_diff": [...],        # 尾差提示
        "cross_period": [...],     # 跨期提示（WARN）
      }
    未匹配项一律保留转人工，绝不自动凑平。
    """
    left = [r for r in left if _as_float(r) is not None]
    right = [r for r in right if _as_float(r) is not None]

    matched: list[dict] = []
    writeoff: list[dict] = []
    tail_diff: list[dict] = []
    cross_period: list[dict] = []

    used_l: set[int] = set()
    used_r: set[int] = set()

    # ---- 0) 红字冲销：同单号同客户 ± 金额（先于普通匹配，防把冲销对当 1:1 或未匹配）
    for li, lr in enumerate(left):
        if li in used_l:
            continue
        l_ref = lr["fields"].get("ref", "")
        l_amt = _as_float(lr) or 0.0
        for ri, rr in enumerate(right):
            if ri in used_r:
                continue
            r_ref = rr["fields"].get("ref", "")
            r_amt = _as_float(rr) or 0.0
            if (
                l_ref and l_ref == r_ref
                and _as_customer(lr) and _as_customer(lr) == _as_customer(rr)
                and abs(l_amt + r_amt) <= MATCH_TOLERANCE
                and l_amt * r_amt < 0
            ):
                writeoff.append({
                    "left_ref": l_ref, "left_amount": l_amt,
                    "right_ref": r_ref, "right_amount": r_amt,
                })
                used_l.add(li)
                used_r.add(ri)
                break

    # ---- 1) 精确 1:1（±MATCH_TOLERANCE）+ 尾差 1:1（±TAIL_TOLERANCE，标 tail_diff）：
    # 客户名 + 金额唯一互配
    for li, lr in enumerate(left):
        if li in used_l:
            continue
        l_cust = _as_customer(lr)
        l_amt = _as_float(lr) or 0.0
        if not l_cust:
            continue
        cand = [ri for ri, rr in enumerate(right)
                if ri not in used_r and _as_customer(rr) == l_cust
                and abs((_as_float(rr) or 0.0) - l_amt) <= TAIL_TOLERANCE]
        if len(cand) == 1:
            ri = cand[0]
            r_amt = _as_float(right[ri]) or 0.0
            diff = r_amt - l_amt
            tail = abs(diff) > MATCH_TOLERANCE
            _push_match(matched, cross_period, {
                "relation": "1:1",
                "left_ref": lr["fields"].get("ref", ""),
                "left_amount": l_amt,
                "left_date": _as_date(lr),
                "right_refs": [right[ri]["fields"].get("ref", "")],
                "right_amount": r_amt,
                "right_dates": [_as_date(right[ri])],
                "customer": lr["fields"].get("customer", ""),
                "tail_diff": tail,
            })
            if tail:
                tail_diff.append({"left_ref": lr["fields"].get("ref", ""),
                                  "diff": round(diff, 2), "relation": "1:1"})
            used_l.add(li)
            used_r.add(ri)

    # ---- 2) 一对多：一笔左记录 = 多张右记录之和（容差 TAIL_TOLERANCE）
    # 贪心：按客户分组，组内用右侧未用记录组合和匹配
    for li, lr in enumerate(left):
        if li in used_l:
            continue
        l_cust = _as_customer(lr)
        l_amt = _as_float(lr) or 0.0
        if not l_cust:
            continue
        grp = [ri for ri, rr in enumerate(right)
               if ri not in used_r and _as_customer(rr) == l_cust
               and (_as_float(rr) or 0.0) > 0]
        combo = _find_combo(grp, lambda ri: _as_float(right[ri]) or 0.0, l_amt)
        if combo is not None and len(combo) >= 2:
            sum_amt = sum(_as_float(right[ri]) or 0.0 for ri in combo)
            diff = sum_amt - l_amt
            _push_match(matched, cross_period, {
                "relation": "1:N",
                "left_ref": lr["fields"].get("ref", ""),
                "left_amount": l_amt,
                "left_date": _as_date(lr),
                "right_refs": [right[ri]["fields"].get("ref", "") for ri in combo],
                "right_amount": sum_amt,
                "right_dates": [_as_date(right[ri]) for ri in combo],
                "customer": lr["fields"].get("customer", ""),
                "tail_diff": abs(diff) > MATCH_TOLERANCE,
            })
            if abs(diff) > MATCH_TOLERANCE:
                tail_diff.append({"left_ref": lr["fields"].get("ref", ""),
                                  "diff": round(diff, 2), "relation": "1:N"})
            used_l.add(li)
            used_r.update(combo)

    # ---- 3) 多对一：多笔左记录 = 一张右记录
    for ri, rr in enumerate(right):
        if ri in used_r:
            continue
        r_cust = _as_customer(rr)
        r_amt = _as_float(rr) or 0.0
        if not r_cust:
            continue
        grp = [li for li, lr in enumerate(left)
               if li not in used_l and _as_customer(lr) == r_cust
               and (_as_float(lr) or 0.0) > 0]
        combo = _find_combo(grp, lambda li: _as_float(left[li]) or 0.0, r_amt)
        if combo is not None and len(combo) >= 2:
            sum_amt = sum(_as_float(left[li]) or 0.0 for li in combo)
            diff = sum_amt - r_amt
            _push_match(matched, cross_period, {
                "relation": "N:1",
                "left_refs": [left[li]["fields"].get("ref", "") for li in combo],
                "left_amount": sum_amt,
                "left_dates": [_as_date(left[li]) for li in combo],
                "right_ref": rr["fields"].get("ref", ""),
                "right_amount": r_amt,
                "right_date": _as_date(rr),
                "customer": rr["fields"].get("customer", ""),
                "tail_diff": abs(diff) > MATCH_TOLERANCE,
            })
            if abs(diff) > MATCH_TOLERANCE:
                tail_diff.append({"right_ref": rr["fields"].get("ref", ""),
                                  "diff": round(diff, 2), "relation": "N:1"})
            used_l.update(combo)
            used_r.add(ri)

    # ---- 4) 未匹配（保留转人工，不凑平）
    unmatched_left = [left[i] for i in range(len(left)) if i not in used_l]
    unmatched_right = [right[i] for i in range(len(right)) if i not in used_r]

    return {
        "matched": matched,
        "writeoff": writeoff,
        "unmatched_left": unmatched_left,
        "unmatched_right": unmatched_right,
        "tail_diff": tail_diff,
        "cross_period": cross_period,
    }


def _push_match(matched: list, cross_period: list, entry: dict) -> None:
    """加入一条匹配关系，并顺带判定跨期提示（WARN 不阻断）。"""
    matched.append(entry)
    if entry.get("relation") == "1:1":
        pairs = [(entry.get("left_date"), d) for d in entry.get("right_dates", [])]
        refs = [(entry.get("left_ref"), r) for r in entry.get("right_refs", [])]
    elif entry.get("relation") == "1:N":
        pairs = [(entry.get("left_date"), d) for d in entry.get("right_dates", [])]
        refs = [(entry.get("left_ref"), r) for r in entry.get("right_refs", [])]
    else:  # N:1
        pairs = [(d, entry.get("right_date")) for d in entry.get("left_dates", [])]
        refs = [(left_ref, entry.get("right_ref")) for left_ref in entry.get("left_refs", [])]
    for (ld, rd), (lref, rref) in zip(pairs, refs):
        if not ld or not rd:
            continue
        try:
            days = (date.fromisoformat(ld) - date.fromisoformat(rd)).days
        except ValueError:
            continue
        if abs(days) > CROSS_PERIOD_DAYS:
            cross_period.append({
                "left_ref": lref, "right_ref": rref, "days": days,
            })


def _find_combo(indices: list[int], amount_of, target: float) -> list[int] | None:
    """在 indices 中找一组和 ≈ target（容差 TAIL_TOLERANCE）的组合。

    优先 2 项组合（一对多/多对一最常见形态），失败再尝试 3 项（受限于规模，穷举 3 项即可）。
    """
    if not indices:
        return None
    n = len(indices)
    # 2 项
    for i in range(n):
        for j in range(i + 1, n):
            s = amount_of(indices[i]) + amount_of(indices[j])
            if abs(s - target) <= TAIL_TOLERANCE:
                return [indices[i], indices[j]]
    # 3 项
    if n >= 3:
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    s = (amount_of(indices[i]) + amount_of(indices[j])
                         + amount_of(indices[k]))
                    if abs(s - target) <= TAIL_TOLERANCE:
                        return [indices[i], indices[j], indices[k]]
    return None


# ---- 对外判定（步骤层调用） ------------------------------------------------

def reconcile_issues(result: dict) -> list[Issue]:
    """把勾兑结果转成 issue 列表：有未匹配/尾差/跨期 -> REVIEW。"""
    issues: list[Issue] = []
    n_um_l = len(result["unmatched_left"])
    n_um_r = len(result["unmatched_right"])
    n_tail = len(result["tail_diff"])
    n_w = len(result["writeoff"])

    if n_um_l or n_um_r:
        issues.append(Issue(
            IssueLevel.REVIEW,
            f"未匹配 {n_um_l + n_um_r} 条（银行侧 {n_um_l} / 订单侧 {n_um_r}），转人工核对",
        ))
    for t in result["tail_diff"]:
        issues.append(Issue(IssueLevel.REVIEW,
                            f"尾差 {t['relation']}：{t.get('left_ref') or t.get('right_ref')} 差 {t['diff']} 元"))
    for c in result["cross_period"]:
        issues.append(Issue(IssueLevel.REVIEW,
                            f"跨期提示：{c['left_ref']} vs {c['right_ref']} 相差 {c['days']} 天"))
    if n_w:
        issues.append(Issue(IssueLevel.REVIEW, f"识别红字冲销 {n_w} 对（非重复，已单独标记）"))
    if not n_um_l and not n_um_r and not n_tail:
        issues.append(Issue(IssueLevel.INFO, "全部勾兑完成，无未匹配项"))
    return issues


def summarize(result: dict) -> dict:
    n_1_1 = sum(1 for m in result["matched"] if m["relation"] == "1:1")
    n_1_n = sum(1 for m in result["matched"] if m["relation"] == "1:N")
    n_n_1 = sum(1 for m in result["matched"] if m["relation"] == "N:1")
    return {
        "matched_total": len(result["matched"]),
        "matched_1_1": n_1_1,
        "matched_1_n": n_1_n,
        "matched_n_1": n_n_1,
        "writeoff": len(result["writeoff"]),
        "unmatched_left": len(result["unmatched_left"]),
        "unmatched_right": len(result["unmatched_right"]),
        "tail_diff": len(result["tail_diff"]),
        "cross_period": len(result["cross_period"]),
    }