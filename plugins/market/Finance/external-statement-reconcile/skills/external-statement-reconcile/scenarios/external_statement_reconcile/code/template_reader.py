"""template_reader.py —— 外部对账模板 Excel → 键值行转换

模板两张数据表：流水表（左）/ 订单表（右），列头 = 契约标准中文键。
按输入字段读对应表，转成与文本契约同构的 `流水:键=值 ...` / `订单:键=值 ...`
行，判定管线与文本输入完全一致。

读取一律经 scenario_api.read_excel_rows。不直接依赖 openpyxl，遵守
ARCH-B-002。只做文本层转换、零 LLM 调用；本模块不判定。
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from scenario_api import read_excel_rows

# 输入字段 → (工作表名, 行前缀, 列头)
FIELD_SHEETS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "source-file": ("流水表", "流水:", ("日期", "客户", "金额", "单号", "类型", "摘要")),
    "right-file": ("订单表", "订单:", ("日期", "客户", "金额", "单号", "摘要")),
}
_XLSX_SUFFIXES = (".xlsx", ".xlsm")


def is_template_path(path) -> bool:
    return str(path).lower().endswith(_XLSX_SUFFIXES)


def _norm(name) -> str:
    """表头归一化：全半角 + 小写 + 去空白/下划线（列名容错，防企业表头变体）。"""
    s = unicodedata.normalize("NFKC", str(name or "")).strip().lower()
    return "".join(ch for ch in s if ch not in " _-／/")


def _match_headers(header_row: list, headers: tuple[str, ...]) -> dict[str, int] | None:
    """归一化列定位：标准列名与表头全半角/空白/大小写不敏感匹配。"""
    norm_row = {_norm(c): idx for idx, c in enumerate(header_row)}
    col_index: dict[str, int] = {}
    for h in headers:
        idx = norm_row.get(_norm(h))
        if idx is None:
            return None
        col_index[h] = idx
    return col_index


def try_read(path, field_id: str) -> list[str] | None:
    """读指定输入字段对应表；非模板/缺表/未知字段返回 None（走文本回退）。"""
    if field_id not in FIELD_SHEETS:
        return None
    p = Path(path)
    if not p.exists() or not is_template_path(p):
        return None
    sheet, prefix, headers = FIELD_SHEETS[field_id]
    try:
        rows = list(read_excel_rows(p, sheet=sheet))
    except Exception:
        return None
    if not rows or not rows[0]:
        return None
    col_index = _match_headers(rows[0], headers)
    if col_index is None:
        return None

    out: list[str] = []
    for row in rows[1:]:
        pairs = [
            f"{h}={str(row[col_index[h]]).strip()}"
            for h in headers
            if col_index[h] < len(row) and str(row[col_index[h]]).strip()
        ]
        if pairs:
            out.append(prefix + " ".join(pairs))
    return out or None
