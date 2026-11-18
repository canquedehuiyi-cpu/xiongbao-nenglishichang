"""template_reader.py —— 单证交叉核对模板 Excel → 键值行转换

模板「单证表」：每行一份单证，列头 = 契约标准中文键（类型 + 20 个字段）。
转成与文本契约同构的 `单证:类型=X 键=值 ...` 行（只输出非空字段），判定
管线与文本输入完全一致。类型为空的行跳过（防脏数据）。

读取一律经 scenario_api.read_excel_rows。不直接依赖 openpyxl，遵守
ARCH-B-002。只做文本层转换、零 LLM 调用；本模块不判定。
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from scenario_api import read_excel_rows

SHEET = "单证表"
HEADERS = (
    "类型", "品名", "型号", "数量", "单价", "金额", "件数", "箱数",
    "毛重", "净重", "体积", "币种", "柜号", "唛头", "起运港", "目的港",
    "发货人", "收货人", "付款节点", "海运条款", "包装要求",
)
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
    col_index = {_norm(name): idx for idx, name in enumerate(rows[0])}
    if "类型" not in col_index:
        return None

    out: list[str] = []
    for row in rows[1:]:
        t_idx = col_index["类型"]
        t = str(row[t_idx]).strip() if t_idx < len(row) else ""
        if not t:
            continue
        pairs = [f"类型={t}"]
        for h in HEADERS[1:]:
            idx = col_index.get(_norm(h))
            if idx is None or idx >= len(row):
                continue
            val = str(row[idx]).strip()
            if val:
                pairs.append(f"{h}={val}")
        out.append("单证:" + " ".join(pairs))
    return out or None
