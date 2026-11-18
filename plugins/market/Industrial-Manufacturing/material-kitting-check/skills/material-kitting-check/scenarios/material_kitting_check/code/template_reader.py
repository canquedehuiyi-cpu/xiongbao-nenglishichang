"""template_reader.py —— 物料齐套模板 Excel → 键值行转换

模板四张数据表（订单/BOM/库存/在途）+「口径声明」表。转成与文本契约同构
的键值行（口径行在前、四表行在后），判定管线与文本输入完全一致。

读取一律经 scenario_api.read_excel_rows。不直接依赖 openpyxl，遵守
ARCH-B-002。只做文本层转换、零 LLM 调用；本模块不判定。
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from scenario_api import read_excel_rows

SHEETS = (
    ("订单", "订单:", ("订单号", "成品", "型号", "数量", "单位")),
    ("BOM", "BOM:", ("成品", "型号", "子件", "编码", "用量", "单位")),
    ("库存", "库存:", ("编码", "名称", "数量", "单位", "批次")),
    ("在途", "在途:", ("编码", "名称", "数量", "单位", "批次", "交期")),
)
DECL_SHEET = "口径声明"
_XLSX_SUFFIXES = (".xlsx", ".xlsm")


def is_template_path(path) -> bool:
    return str(path).lower().endswith(_XLSX_SUFFIXES)


def _norm(name) -> str:
    """表头归一化：全半角 + 小写 + 去空白/下划线（列名容错，防企业表头变体）。"""
    s = unicodedata.normalize("NFKC", str(name or "")).strip().lower()
    return "".join(ch for ch in s if ch not in " _-／/")


def _read_sheet(path: Path, sheet: str) -> list[list[str]] | None:
    try:
        return list(read_excel_rows(path, sheet=sheet))
    except Exception:
        return None


def _kv_rows(rows: list[list[str]], prefix: str, headers: tuple[str, ...]) -> list[str]:
    if not rows or not rows[0]:
        return []
    col_index = {_norm(name): idx for idx, name in enumerate(rows[0])}
    if not all(_norm(h) in col_index for h in headers):
        return []
    out: list[str] = []
    for row in rows[1:]:
        pairs = [
            f"{h}={str(row[col_index[_norm(h)]]).strip()}"
            for h in headers
            if col_index[_norm(h)] < len(row) and str(row[col_index[_norm(h)]]).strip()
        ]
        if pairs:
            out.append(prefix + " ".join(pairs))
    return out


def try_read(path) -> list[str] | None:
    """把模板读成键值行列表；非模板/缺表返回 None（走文本回退）。"""
    p = Path(path)
    if not p.exists() or not is_template_path(p):
        return None

    out: list[str] = []

    # 口径声明在前（可选；缺失则无声明，单位/批次缺口径时判 UNKNOWN 属正常行为）
    decl = _read_sheet(p, DECL_SHEET)
    if decl:
        for row in decl[1:]:
            if len(row) >= 2 and str(row[0]).strip() and str(row[1]).strip():
                out.append(f"口径:{str(row[0]).strip()}={str(row[1]).strip()}")

    any_data = False
    for sheet, prefix, headers in SHEETS:
        rows = _read_sheet(p, sheet)
        if not rows:
            continue
        lines = _kv_rows(rows, prefix, headers)
        if lines:
            any_data = True
            out.extend(lines)
    return out if any_data else None
