"""_core.py —— PPT 内容核对的判定内核（纯函数，零 IO；抽取/归一/匹配逻辑只住本文件）

五态口径：
  PASS      每个数字断言都在源表找到出处（带单元格定位）
  WARNING   存在「无出处」数字（全表找不到——判不了，不说是错）
  UNKNOWN   不使用（本场景无整体不可判态；源表不可用由适配层报 ERROR）
"""

from __future__ import annotations

import re
import zipfile
from typing import Any

# ── 判定阈值与抽取规则（命名常量；改这里 = 改产品口径，须过 INTENT §2 登记）──
# 取值依据：
#   _ROUND = 6：浮点等值比较统一 round 6 位——比 %↔小数换算精度高两档，比
#     财务口径（2 位）宽，避免 0.0325 vs 0.032500000004 这类表示误差误报。
#   排除四类非数据数字（写死，不是阈值）：列表序号、页码、完整日期、
#     字母紧贴的编号（v0.3/Q3/K12）——它们是排版/版本元素不是业务断言。
#     已知边界：指标缩写紧贴数字（如「GMV68万」）也会被当编号排除而漏检，
#     报告口径节如实写明；正常写法（GMV 68 万，带空格）不受影响。
_ROUND = 6

_NUM = re.compile(r"\d+(?:[,，]\d{3})*(?:\.\d+)?\s*(?:[%％]|万|亿|千万|百万)?")
_LIST_MARKER = re.compile(r"^\s*(?:[-*·•]|\d+\s*[.、)])\s*")
_PAGE_MARK = re.compile(r"^第\s*\d+\s*页$|^[Pp]\s*\d+$")
_FULL_DATE = re.compile(r"\d{4}\s*[-/.年]\s*\d{1,2}(?:\s*[-/.月]\s*\d{1,2}\s*日?)?")

_UNIT_SCALE = {"万": 1e4, "百万": 1e6, "千万": 1e7, "亿": 1e8}


def _variants(raw: str) -> set[float]:
    """一个数字串的等值变体集：百分数↔小数、中文量级展开、千分位剥离。

    '3.25%' → {3.25, 0.0325}；'1,200 万' → {1200, 12000000}；'68' → {68}
    """
    s = raw.replace(",", "").replace("，", "").strip()
    m = re.match(r"(\d+(?:\.\d+)?)\s*(.*)$", s)
    if not m:
        return set()
    val = float(m.group(1))
    unit = m.group(2).strip()
    out = {round(val, _ROUND)}
    if unit in ("%", "％"):
        out.add(round(val / 100.0, _ROUND))
    if unit in _UNIT_SCALE:
        out.add(round(val * _UNIT_SCALE[unit], _ROUND))
    return out


def extract_assertions(lines: list[str], pages: list[int] | None = None) -> list[dict[str, Any]]:
    """从 PPT 文本逐行抽数字断言。排除排版元素（序号/页码/完整日期/版本号）。

    返回 [{line_no, raw, excerpt, start, page?}]；pages 与 lines 等长时
    （.pptx 直读）每条断言带页码。
    """
    out: list[dict[str, Any]] = []
    for no, line in enumerate(lines, start=1):
        s = line.strip()
        if not s or _PAGE_MARK.match(s):
            continue
        body = _FULL_DATE.sub(" ", s)
        offset = len(s) - len(body) if len(s) != len(body) else 0
        stripped = _LIST_MARKER.sub("", body)
        offset += len(body) - len(stripped)
        label_tokens = sorted(_label_tokens(stripped))
        for m in _NUM.finditer(stripped):
            start = m.start()
            before = stripped[start - 1] if start > 0 else ""
            if before and before.isascii() and before.isalpha():
                continue  # v0.3 / Q3 / K12 类编号,非业务断言
            out.append(
                {
                    "line_no": no,
                    "raw": m.group(0).strip(),
                    "start": start + offset,
                    "excerpt": stripped[max(0, start - 10): start + len(m.group(0)) + 6].strip(),
                    "label_tokens": label_tokens,
                    **({"page": pages[no - 1]} if pages and no <= len(pages) else {}),
                }
            )
    return out


_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def extract_pptx_text(path: str) -> tuple[list[str], list[int]]:
    """直读 .pptx：逐页抽段落文本（zipfile + ElementTree，标准库零新依赖）。

    每个段落(<a:p>)拼为一行，跨 run(<a:r>)的文本接回去（「1,2」「00 万」→「1,200 万」）；
    返回 (lines, pages)，页码按 slideN.xml 的 N 排序。
    解析不了的文件抛 ValueError——由适配层转 ERROR，不硬判。
    """
    import xml.etree.ElementTree as ET

    try:
        with zipfile.ZipFile(path) as z:
            slide_names = sorted(
                (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                key=lambda n: int(re.search(r"(\d+)", n).group(1)),
            )
            lines: list[str] = []
            pages: list[int] = []
            for name in slide_names:
                page_no = int(re.search(r"(\d+)", name).group(1))
                root = ET.fromstring(z.read(name))
                # 注意:命名空间括号用拼接而非 f-string 转义——发布方占位扫描会拦 \"{{\"
                p_tag = "{" + _A_NS + "}p"
                t_tag = "{" + _A_NS + "}t"
                for p in root.iter(p_tag):
                    text = "".join(t.text or "" for t in p.iter(t_tag))
                    if text.strip():
                        lines.append(text)
                        pages.append(page_no)
    except (zipfile.BadZipFile, ET.ParseError, OSError) as exc:
        raise ValueError(f".pptx 解析失败：{exc}") from exc
    if not lines:
        raise ValueError(".pptx 里没有抽出任何文本（可能是纯图片页）")
    return lines, pages


def _label_tokens(text: str) -> set[str]:
    """标签语料 → 二字组集合(中文)与拉丁整词,用于指标名模糊对齐。"""
    out: set[str] = set()
    for run in re.findall(r"[一-龥]{2,}", text):
        out.update(run[i:i + 2] for i in range(len(run) - 1))
    out.update(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9+#-]{1,}", text))
    return out


def build_source_index(rows: list[list[str]], header: list[str] | None) -> tuple[dict[float, list[dict[str, str]]], bool]:
    """源表数值索引：等值变体 → [{ref, label}]（最多记 4 处）。

    label = 行标签(该行首个非数字单元格;无则空) + 列名。has_labels = 表里
    是否存在任何文字标签——纯数字表没有标签可对,调用方据此降级为存在性核对。
    """
    index: dict[float, list[dict[str, str]]] = {}
    has_labels = False
    for r_no, row in enumerate(rows, start=2 if header else 1):
        row_label = next((str(c).strip() for c in row if str(c).strip() and not _NUM.search(str(c))), "")
        if row_label:
            has_labels = True
        for c_no, cell in enumerate(row, start=1):
            col_name = header[c_no - 1] if header and c_no <= len(header) else f"第{c_no}列"
            if col_name and any(k for k in _label_tokens(col_name)):
                has_labels = True
            ref = f"{row_label}·{col_name}·第{r_no}行" if row_label else f"{col_name}·第{r_no}行"
            label = f"{row_label}{col_name}"
            for m in _NUM.finditer(str(cell)):
                for v in _variants(m.group(0)):
                    entries = index.setdefault(v, [])
                    if not any(e["ref"] == ref for e in entries) and len(entries) < 4:
                        entries.append({"ref": ref, "label": label})
    return index, has_labels


def match(assertion: dict[str, Any], index: dict[float, list[dict[str, str]]], has_labels: bool = True) -> dict[str, Any]:
    """单断言对账（0.2.0 标签感知）：

    - 数值命中且指标标签对得上（二字组/拉丁词有交集）→ PASS + 该出处；
    - 数值命中但所有出处标签都对不上 → WARNING「数值存在但指标对不上」+ 真实出处（错位点名）；
    - 数值不命中 → WARNING「无出处」；
    - 纯数字表（无标签可对）→ 退回存在性核对（如实降级，不算误报）。
    """
    hits: list[dict[str, str]] = []
    for v in _variants(assertion["raw"]):
        hits.extend(index.get(v, []))
    if not hits:
        return {**assertion, "status": "WARNING", "refs": [], "note": "源表全表未找到该数值（含 %↔小数/万·亿换算）"}
    if not has_labels or not assertion.get("label_tokens"):
        return {**assertion, "status": "PASS", "refs": [e["ref"] for e in hits]}
    want = set(assertion["label_tokens"])
    matched = [e for e in hits if _label_tokens(e["label"]) & want]
    if matched:
        return {**assertion, "status": "PASS", "refs": [e["ref"] for e in matched]}
    return {
        **assertion,
        "status": "WARNING",
        "refs": [e["ref"] for e in hits],
        "note": "数值在源表存在但指标对不上（该数挂在别的指标下）——请人工核对是否抄错行",
    }


def aggregate(results: list[dict[str, Any]]) -> str:
    if not results:
        return "PASS"
    return "PASS" if all(r["status"] == "PASS" for r in results) else "WARNING"
