"""template_reader.py —— 供应商核验模板 Excel → 键值行转换

模板「两侧对照」：每行一个字段 × 台账侧/证照侧两列。转成与文本契约同构的
`侧:键=值` 行（每行一字段），判定管线与文本输入完全一致：台账侧与证照侧
各自只输出非空字段，两侧都填才参与比对（单侧缺失由 validator 判
MISSING_FIELD 转人工）。

读取一律经 scenario_api.read_excel_rows（按单元格读、保留格间边界，格值
含逗号不错列）。不直接依赖 openpyxl，遵守 ARCH-B-002。只做文本层转换、
零 LLM 调用；本模块不判定。
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from scenario_api import read_excel_rows

SHEET = "两侧对照"
_XLSX_SUFFIXES = (".xlsx", ".xlsm")


def is_template_path(path) -> bool:
    return str(path).lower().endswith(_XLSX_SUFFIXES)


def _norm(name) -> str:
    """表头归一化：全半角 + 小写 + 去空白/下划线（列名容错，防企业表头变体）。"""
    s = unicodedata.normalize("NFKC", str(name or "")).strip().lower()
    return "".join(ch for ch in s if ch not in " _-／/")


def try_read(path) -> list[str] | None:
    """把模板读成键值行列表；非模板/缺表返回 None（走文本回退）。"""
    p = Path(path)
    if not p.exists() or not is_template_path(p):
        return None
    try:
        rows = list(read_excel_rows(p, sheet=SHEET))
    except Exception:
        return None
    if not rows:
        return None
    col = {_norm(c): i for i, c in enumerate(rows[0])}
    if "台账侧" not in col:
        return None
    f_idx = col.get("字段", 0)
    l_idx = col.get("台账侧", 1)
    c_idx = col.get("证照侧", 2)

    out: list[str] = []
    for row in rows[1:]:
        if len(row) < max(f_idx, l_idx, c_idx) + 1:
            continue
        fname = str(row[f_idx]).strip()
        if not fname:
            continue
        ledger = str(row[l_idx]).strip()
        cert = str(row[c_idx]).strip()
        if ledger:
            out.append(f"台账:{fname}={ledger}")
        if cert:
            out.append(f"证照:{fname}={cert}")
    return out or None
