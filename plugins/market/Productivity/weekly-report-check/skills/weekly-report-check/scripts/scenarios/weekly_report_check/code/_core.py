"""_core.py —— 周报体检的判定内核（纯函数，零 IO；节识别逻辑与阈值只住本文件顶部）

分层纪律：本模块不读文件、不写文件——节名清单/期限词/交付物词是数据面
（rules.yaml，用户可改），由 steps.py 传入；怎么用这些数据的逻辑在这里。

五态口径：
  PASS      无任何发现（待办都有主有期、进展句都有数字或交付物）
  WARNING   存在空转句（进展句无数字且无交付物）/ 待办缺期
  MISSING   待办行缺负责人标记
  UNKNOWN   认不出任何已知节名（格式不认识，整体转人工，不硬判）
"""

from __future__ import annotations

import re
from typing import Any

# ── 判定阈值与结构逻辑（命名常量；改这里 = 改产品口径，须过 INTENT §2 登记）──
# 取值依据：
#   BARE_HEADER_MAX_LEN = 8：无结构的裸词行（如单独一行「下周计划」）要当标题，
#     长度必须 ≤ 8——实测 13 字的正文句「和团队保持沟通，同步进展」会被 15 字
#     上限误判成标题、整行从正文消失（2026-10-13 真实反例，测试钉住）。
#   MIN_SENTENCE_LEN = 4：短于 4 字的行（"无""同上"）不判空转——信息量不足以定罪。
#   空转规则（0.2.0 起）：无交付物词 且（无数字 或 数字全部只是数量词）——
#     「完成3项沟通」的 3 是数量词不是事实，照样定罪（2026-10-13 探针1）；
#     有交付物词（接口/版本/报告…）一票放行，不误伤正常汇报。
BARE_HEADER_MAX_LEN = 8
MIN_SENTENCE_LEN = 4
_COUNTER_WORD = "项次个场轮份起条位人家篇张"

_MD_HEADER = re.compile(r"^#{1,6}\s*\S")
_CN_NUM_HEADER = re.compile(r"^[一二三四五六七八九十\d]+\s*[、..]")
_BRACKET_HEADER = re.compile(r"^【.+】$")
_COLON_HEADER = re.compile(r"[:：]$")
_DATE_LIKE = re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]|\d{1,2}\s*号|周[一二三四五六日末]|\d+\s*日前")
_DIGIT = re.compile(r"\d")


def is_header(line: str, todo_names: list[str], progress_names: list[str]) -> str | None:
    """识别节标题行，返回 'todo' / 'progress' / None。

    只认四类形态：markdown 标题、中文序号开头、「【】」包裹、冒号结尾；
    裸词行（如单独一行「下周计划」）长度 ≤ BARE_HEADER_MAX_LEN 才认。
    认不出 = None——不脑补节名（硬约束）。
    """
    s = (line or "").strip()
    if not s:
        return None
    structural = bool(
        _MD_HEADER.match(s) or _CN_NUM_HEADER.match(s) or _BRACKET_HEADER.match(s) or _COLON_HEADER.search(s)
    )
    if not structural and len(s) > BARE_HEADER_MAX_LEN:
        return None
    if any(name in s for name in todo_names):
        return "todo"
    if any(name in s for name in progress_names):
        return "progress"
    return None


def split_sections(
    lines: list[str], todo_names: list[str], progress_names: list[str]
) -> dict[str, list[tuple[int, str]]]:
    """把周报切成节。返回 {'todo': [(行号,行)], 'progress': [...]}。

    头部（第一个节标题之前）的正文行不计入任何节——没有节语境的行
    判不了归属，不猜。
    """
    sections: dict[str, list[tuple[int, str]]] = {"todo": [], "progress": []}
    current: str | None = None
    for no, raw in enumerate(lines, start=1):
        kind = is_header(raw, todo_names, progress_names)
        if kind:
            current = kind
            continue
        if current is None:
            continue
        s = raw.strip()
        if s:
            sections[current].append((no, s))
    return sections


def split_sentences(text: str) -> list[str]:
    """按句末标点切句；无标点的行整行作一句。"""
    parts = re.split(r"[。；;.;;!！?？\n]+", text)
    return [p.strip() for p in parts if len(p.strip()) >= MIN_SENTENCE_LEN]


def check_todo_line(line: str, deadline_words: list[str]) -> list[str]:
    """待办行体检：返回缺失项列表（'负责人' / '期限'）。

    负责人 = 行内含 @ 或「负责」字样（可数启发，v1 口径，如实标注覆盖边界）。
    期限 = 期限词命中 或 日期式（X月X日/周X/X号/X日前）。
    """
    missing: list[str] = []
    if "@" not in line and "负责" not in line:
        missing.append("负责人")
    if not any(w in line for w in deadline_words) and not _DATE_LIKE.search(line):
        missing.append("期限")
    return missing


def _all_digits_are_countwords(sentence: str) -> bool:
    """句内每个数字是否都只是数量词（数字+项/次/个…）——数量词不构成事实。"""
    for m in _DIGIT.finditer(sentence):
        after = sentence[m.end():].lstrip()
        if not after or after[0] not in _COUNTER_WORD:
            return False
    return bool(_DIGIT.search(sentence))


def is_empty_progress(sentence: str, deliverable_words: list[str]) -> bool:
    """空转句判定（0.2.0）：无交付物词 且（无数字 或 数字全是数量词）。"""
    if any(w in sentence for w in deliverable_words):
        return False
    if _DIGIT.search(sentence):
        return _all_digits_are_countwords(sentence)
    return True


def normalize_text_for_match(text: str) -> str:
    """呼应匹配基准态：去所有空白。"""
    return re.sub(r"\s+", "", text)


def _bigrams(text: str) -> set[str]:
    """中文二字组集合(跨期呼应的匹配单元——同义改写共享二字组,整句匹配太脆)。"""
    out: set[str] = set()
    for run in re.findall(r"[一-龥]{2,}", text):
        out.update(run[i:i + 2] for i in range(len(run) - 1))
    return out


def is_followed(todo_line: str, current_text_norm: str, min_shared: int = 2) -> bool:
    """上周待办是否被本周正文呼应：内容二字组与本周全文有 ≥ min_shared 个交集。

    只判「提没提」不判「做完没做」——完成与否是语义判断,不在本件口径内。
    """
    content = _bigrams(todo_line)
    if not content:
        return True  # 提取不出内容(纯符号/数字)——无从对照,不点名
    shared = sum(1 for b in content if b in current_text_norm)
    return shared >= min_shared


def aggregate(todo_missing: int, empty_progress: int, sections_found: bool, unfollowed: int = 0) -> str:
    """总判定：五态归并。无节 → UNKNOWN；有发现(含上周未呼应) → WARNING；
    全清 → PASS。"""
    if not sections_found:
        return "UNKNOWN"
    if todo_missing + empty_progress + unfollowed == 0:
        return "PASS"
    return "WARNING"
