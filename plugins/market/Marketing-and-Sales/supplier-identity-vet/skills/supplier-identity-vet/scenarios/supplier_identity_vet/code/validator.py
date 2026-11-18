"""
validator.py —— 供应商主体一致性核验 判定规则（护城河区，写死）

判定基准 = 跨文档相符核对（槽位 2）。两侧各提供一组实体字段，取交集做归一化比对，
只对「两侧都有、且能归一化到同一语义」的字段下 PASS/CONFLICT 结论；
任一侧缺字段、或字段内容无法解析（扫描件/图片/手写残留）则按 UNKNOWN 转人工，
绝不给半参谋的"看起来一致"。

输入契约红线（与 SKILL.md / INPUT_CONTRACT.md 一致）：
- 只吃文本层（UTF-8 TXT / 文本 PDF / DOCX / XLSX / CSV）。扫描件、图片、截图、
  手写 OCR 遗留行一律判 UNKNOWN 转人工，由宿主在喂入前负责转文本层——本引擎
  不做 OCR（撞 GATE 1c / N-04 教训）。
- 判定只认「两侧同字段同步出现」；单独一侧出现的字段计入"缺口"提示，不参与判定。

字段口径（实体）：
  名称 / 法定代表人 / 开户行 / 统一社会信用代码
比对输出固定四态：PASS / CONFLICT / UNKNOWN / MISSING_FIELD
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 字段识别 ------------------------------------------------------------

# 允许的实体字段名（键）+ 其在本判定里的比对类型
ENTITY_FIELDS = {
    "名称": "name",
    "名称2": "name",        # 别名，如对外简称
    "法定代表人": "legal",
    "法人": "legal",
    "开户行": "bank",
    "银行": "bank",
    "统一社会信用代码": "uscc",
    "信用代码": "uscc",
    "社会信用代码": "uscc",
    "代码": "uscc",
}

# 侧命名空间（输入行前缀）→ 归一标记
SIDE_ALIASES = {
    "台账": "ledger",
    "我方": "ledger",
    "a": "ledger",
    "证照": "cert",
    "对方": "cert",
    "执照": "cert",
    "b": "cert",
}

# ---- 归一化 ---------------------------------------------------------------

# 全半角统一
def _unicode_norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


# 公司名称词缀归一：去掉"集团股份有限"等治理词缀的前后空白与括号内容差异
# （仅用于横向比对，不据它重写原始值）
_ORG_SWEEP = re.compile(
    r"[（(]?[\u4e00-\u9fa5]{0,4}(有限|股份|集团|责任|合伙)[\u4e00-\u9fa5]{0,4}公司?(?:\([^)]*\))?"
)


def normalize_org_name(name: str) -> str:
    """把组织名归一化：全半角、大小写、空格、常见公司词缀、括号差异。

    返回一个可比较的指纹；空串或纯符号返回 ""。
    例「深圳市蓝天科技有限公司」→ 与「深圳市蓝天科技(股份)有限公司」可比。
    """
    s = _unicode_norm(name or "").strip().lower()
    if not s or s in {"-", "/", "null", "none", "无", "—"}:
        return ""
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[，,、.;；:：]", "", s)
    # 统一括号为半角并去除括号内注释（如"股份有限公司(已变更)"）
    s = re.sub(r"\([^)]*\)", "", s)
    # 治理词缀弱化：delta 前后字母/数字需保留，中文词缀整段去掉
    s = re.sub(r"(?<=[\u4e00-\u9fa5])股份(?:有限)?公司", "有限公司", s)
    s = re.sub(r"(?<=[\u4e00-\u9fa5])集团有限公司?", "有限公司", s)
    s = re.sub(r"(?<=[\u4e00-\u9fa5])有限(?:责任)?公司", "有限公司", s)
    return s


def normalize_legal(name: str) -> str:
    """法定代表人归一：全半角、去空格、姓氏保留；名字单字差异按完全一致处理。"""
    s = _unicode_norm(name or "").strip().lower()
    if not s or s in {"-", "/", "null", "none", "无"}:
        return ""
    return re.sub(r"[\s\u3000]+", "", s)


def normalize_bank(bank: str) -> str:
    """开户行归一：全半角、去空格、中文行名大小写；分行/支行措辞弱化。"""
    s = _unicode_norm(bank or "").strip().lower()
    if not s or s in {"-", "/", "null", "none", "无"}:
        return ""
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"(城市商业银行|商业银行)", "银行", s)
    s = re.sub(r"(?:中国)?(?=(?:银行|支行|分行))", "", s)
    return s


def normalize_uscc(uscc: str) -> str:
    """统一社会信用代码归一：全半角、去空格、字母大写。"""
    s = _unicode_norm(uscc or "").strip().upper()
    return re.sub(r"[\s\u3000]+", "", s)


_NORMALIZERS = {
    "name": normalize_org_name,
    "legal": normalize_legal,
    "bank": normalize_bank,
    "uscc": normalize_uscc,
}


# ---- 判定 ----------------------------------------------------------------

# 输出四态
PASS = "PASS"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"
MISSING_FIELD = "MISSING_FIELD"

# 疑似扫描件/图片/手写占用行的特征（喂入前应被宿主转文本；命中即 UNKNOWN）
_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr",
)

def _split_pairs(body: str) -> list[tuple[str, str]]:
    """把 `键=值` 键值对串切分为 (键, 值) 列表。

    键不允许含空格/等号；值允许含空格，直到下一个 `键=` 或行尾。
    值内不得再出现 `键=` 形式（契约注明）。
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


# 待解析行里识别出的实体（按实体字段 id 汇总，值带原始文本）
def parse_entities(line: str) -> dict:
    """从一行 `侧:键=值` 文本抽取实体字典 {field_idx: (origin_side, raw_value)}。

    返回 {norm_field_id: {"side": "ledger"|"cert", "raw": str}}。
    解析失败（找不到 `键=值`、或命中扫描提示）返回空 dict——由调用方按 UNKNOWN 处理。
    """
    out: dict = {}
    if not line:
        return out
    low = line.lower()
    if any(h in low for h in _SCAN_HINTS):
        return out
    body = line.split(":", 1)
    if len(body) != 2:
        return out
    side_label = body[0].strip()
    side = SIDE_ALIASES.get(side_label.lower(), side_label)
    for key, val in _split_pairs(body[1]):
        k = _unicode_norm(key).strip()
        fid = ENTITY_FIELDS.get(k)
        if fid is None:
            continue
        v = _unicode_norm(val).strip()
        if not v:
            continue
        out.setdefault(fid, {"side": side, "raw": v})
    return out


def _identity_compare(a: dict, b: dict) -> tuple[str, list[str]]:
    """逐字段比对，返回 (结论, 差异说明列表)。

    只有两侧都有、且均归一化出非空指纹的字段才计入判定。
    """
    diffs: list[str] = []
    judged = 0
    for fid, nrm in _NORMALIZERS.items():
        va = nrm(a.get(fid, {}).get("raw", ""))
        vb = nrm(b.get(fid, {}).get("raw", ""))
        if not va or not vb:
            continue  # 两侧非同步非空 -> 不计入判定
        judged += 1
        if va != vb:
            diffs.append(
                f"{fid}:台账「{a[fid]['raw']}」≠ 证照「{b[fid]['raw']}」"
            )
    if judged == 0:
        return UNKNOWN, ["两侧无任何可判定字段（缺字段或无法解析）"]
    if diffs:
        return CONFLICT, diffs
    return PASS, ["已比对字段全部一致"]


def verify_supplier(ledger: dict, cert: dict) -> list[Issue]:
    """对台账侧与证照侧实体做一致性核验，返回 issue 列表（REVIEW=待人工/冲突）。

    ledger / cert：{fid: {"side", "raw"}}；任一侧为空视作"该侧无有效输入"。
    """
    issues: list[Issue] = []
    if not ledger and not cert:
        # 「彻底空输入」由 load 步骤按 ERROR 处理；这里到不了两侧都非空却无法解析时，
        # 一律按"缺可判定输入"转人工（REVIEW），不静默给结论。
        issues.append(Issue(IssueLevel.REVIEW, "两侧均无可解析的实体信息，转人工核对"))
        return issues
    if not ledger or not cert:
        side = "证照" if ledger else "台账"
        issues.append(
            Issue(IssueLevel.REVIEW, f"只收到「{side}」单侧信息，缺另一侧，无法比对（MISSING_FIELD）")
        )
        return issues

    verdict, diffs = _identity_compare(ledger, cert)
    if verdict == CONFLICT:
        for d in diffs:
            issues.append(Issue(IssueLevel.REVIEW, f"主体不一致：{d}"))
    elif verdict == UNKNOWN:
        for d in diffs:
            issues.append(Issue(IssueLevel.REVIEW, f"无法判定：{d}"))
    # PASS 不写 REVIEW——一致即放行
    return issues


def summarize(ledger: dict, cert: dict) -> dict:
    """供 render 步骤使用的结构化结论，不写死文案细节。"""
    verdict, diffs = (UNKNOWN, ["两侧无有效输入"])
    if ledger and cert:
        verdict, diffs = _identity_compare(ledger, cert)
    judged_fields = [fid for fid in _NORMALIZERS
                     if ledger.get(fid, {}).get("raw") and cert.get(fid, {}).get("raw")]
    return {
        "verdict": verdict,
        "diffs": diffs,
        "judged_fields": judged_fields,
        "ledger_fields": sorted(ledger.keys()),
        "cert_fields": sorted(cert.keys()),
    }