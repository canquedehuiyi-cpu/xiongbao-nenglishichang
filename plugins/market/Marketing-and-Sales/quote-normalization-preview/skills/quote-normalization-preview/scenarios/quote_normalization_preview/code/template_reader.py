"""
template_reader.py —— 标准报价模板 Excel → 键值行转换

使"内部汇聚总表"模板可直接作为 T-02 输入：采购把同一票询价下各家报价按
固定列填进一张 Excel，引擎读模板即完成拉平预审，无需采集真实异构文件
（输入整治：统一格式 = 模板列，格式天然可比，引擎只负责数值归一与偏离）。

模板结构（工作表名固定，与 tools/quote_template_gen.py 一致）：
  - Sheet「报价明细」：列头 = 中文键（供应商/品名/型号/单价/数量/金额/币种/单位/含税），
    每行一家报价。
  - Sheet「口径声明」：两列 `键 | 值`，一行一个口径（如 键=USD 值=7.2；
    键=SET 值=10PC；键=含税 值=是）。键值一切换给 validator.parse_decl_line，
    单位/币种别名与换算规则见 validator。

读取一律经 scenario_api.read_excel_rows——它按单元格读回二维表、**保留格间
边界**，格值里含逗号（如千分位金额 "50,000.00"）也不会错列（这是 T-1 必测
陷阱）。不直接依赖 openpyxl，遵守 ARCH-B-002"场景包只准 import scenario_api /
yaml / 标准库"。只做文本层转换、零 LLM 调用；本模块不判定，判定由 validator 完成。
"""

from __future__ import annotations

from pathlib import Path

from scenario_api import read_excel_rows

# 模板工作表名（与 tools/quote_template_gen.py 保持一致）
QUOTE_SHEET = "报价明细"
DECL_SHEET = "口径声明"

# 报价明细列头 -> 键值行键（中文键，validator.parse_quote_line 直接识别）
QUOTE_COLUMNS = ("供应商", "品名", "型号", "单价", "数量", "金额", "币种", "单位", "含税")

_XLSX_SUFFIXES = (".xlsx", ".xlsm")


def _cell_text_safe(value) -> str:
    # read_excel_rows 已把格值转 str；此处仅兜底去空格
    if value is None:
        return ""
    return str(value).strip()


def is_template_path(path) -> bool:
    """扩展名是否可能是模板 Excel（预算检查，避免对文本/PDF 强行读表）。"""
    return str(path).lower().endswith(_XLSX_SUFFIXES)


def try_read_template(path) -> list[str] | None:
    """尝试把模板 Excel 读成键值行列表（口径行在前、报价行在后）。

    仅当「报价明细」表头含"单价"列时视为模板；否则返回 None（非模板/旧文本）。
    """
    p = Path(path)
    if not p.exists() or not is_template_path(p):
        return None

    # 报价明细表：read_excel_rows 可按 sheet 名读取；缺表/异常都当作"非模板"处理
    try:
        quote_rows = list(read_excel_rows(p, sheet=QUOTE_SHEET))
    except Exception:
        return None
    if not quote_rows:
        return None

    header = quote_rows[0]
    if "单价" not in header or "供应商" not in header:
        return None
    col_index = {name: idx for idx, name in enumerate(header)}

    out_lines: list[str] = []
    for data_row in quote_rows[1:]:
        pairs = [
            f"{name}={_cell_text_safe(data_row[col_index[name]])}"
            for name in QUOTE_COLUMNS
            if name in col_index and col_index[name] < len(data_row)
            and _cell_text_safe(data_row[col_index[name]])
        ]
        if not pairs:
            continue
        out_lines.append("报价:" + " ".join(pairs))

    # 口径声明表：可选（缺失则无声明，报价缺汇率/换算时判 UNKNOWN，属正常行为）
    decl_lines: list[str] = []
    try:
        decl_rows = list(read_excel_rows(p, sheet=DECL_SHEET))
    except Exception:
        decl_rows = []
    for row in decl_rows[1:]:
        if len(row) < 2 or not row[0] or not row[1]:
            continue
        key, val = row[0].strip(), row[1].strip()
        if key and val and key.lower() != "键":
            decl_lines.append(f"口径:{key}={val}")

    if not out_lines:
        return None
    return decl_lines + out_lines