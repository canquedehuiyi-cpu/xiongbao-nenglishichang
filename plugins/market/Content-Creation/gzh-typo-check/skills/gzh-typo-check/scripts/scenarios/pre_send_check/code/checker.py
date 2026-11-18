"""
checker.py —— 发文前核对·判定器(纯函数,T4 扩容版)

判定住在这里(适配层 steps.py 只做归一与翻译,不写判定)。
输入推文文本 + 个人词典白名单,输出结构化命中清单:
每条命中 = 原文片段 / 规范条目 ID / 规则名 / 依据 / 建议改法 / 位置。

两类词规范:
- WordSpec(极限词类):通用建议(删除/举证),建议文案住 specs;
- FixSpec(错写→正写类):建议按「原文 X 应为 Y」逐条生成。

白名单(个人词典)语义:命中词在白名单内 -> 整条不报(硬约束 C-3:
词典命中后同一误报不得二次出现)。白名单只作用于词类命中
(极限词/异形词/错别字);标点与数字的规范化不适用词典豁免。
"""

from __future__ import annotations

from dataclasses import dataclass

from .specs import (
    AD_LAW_LIMIT_WORDS,
    NUM_RULES,
    PUNCT_RULES,
    TYPO_PAIRS,
    UNCOVERED,
    VARIANT_WORDS,
    FixSpec,
    PatternSpec,
    WordSpec,
)

MAX_CHARS = 50_000  # 输入上限(超长 -> 异常路径:分段核对),阈值只在代码


@dataclass(frozen=True)
class Hit:
    """一条硬错命中:条条带依据。"""

    snippet: str          # 原文片段(命中词及其上下文)
    spec_id: str          # 规范条目 ID
    rule_name: str
    evidence: str         # 依据(标准/法规/词典)——硬约束 C-1
    suggestion: str
    position: int         # 命中在原文中的起始偏移

    def to_row(self) -> dict[str, object]:
        return {
            "snippet": self.snippet,
            "spec_id": self.spec_id,
            "rule_name": self.rule_name,
            "evidence": self.evidence,
            "suggestion": self.suggestion,
            "position": self.position,
        }


@dataclass(frozen=True)
class Report:
    verdict: str                     # HARD_FOUND / CLEAN
    hard: tuple[Hit, ...]
    uncovered: tuple[str, ...]


def _context(text: str, idx: int, length: int, pad: int = 6) -> str:
    """命中词连同左右各 pad 字,报告里看得见上下文。"""
    lo = max(0, idx - pad)
    hi = min(len(text), idx + length + pad)
    return text[lo:hi]


def _find_words(text: str, spec: WordSpec,
                whitelist: frozenset[str], lowered: str) -> list[Hit]:
    """WordSpec:通用建议(极限词类)。"""
    out: list[Hit] = []
    for word in spec.hits:
        wl = word.lower()
        if wl in whitelist:
            continue  # 个人词典命中 -> 不报(C-3)
        start = 0
        while True:
            idx = lowered.find(wl, start)
            if idx < 0:
                break
            out.append(Hit(
                snippet=_context(text, idx, len(wl)),
                spec_id=spec.spec_id,
                rule_name=spec.rule_name,
                evidence=spec.evidence,
                suggestion=spec.suggestion,
                position=idx,
            ))
            start = idx + len(wl)
    return out


def _find_fixes(text: str, spec: FixSpec,
                whitelist: frozenset[str], lowered: str) -> list[Hit]:
    """FixSpec:错写->正写,建议逐条生成。"""
    out: list[Hit] = []
    for wrong, right in spec.fixes:
        if wrong.lower() in whitelist:
            continue  # 个人词典命中 -> 不报(C-3)
        start = 0
        while True:
            idx = lowered.find(wrong, start)
            if idx < 0:
                break
            out.append(Hit(
                snippet=_context(text, idx, len(wrong)),
                spec_id=spec.spec_id,
                rule_name=spec.rule_name,
                evidence=spec.evidence,
                suggestion=f"「{wrong}」应为「{right}」",
                position=idx,
            ))
            start = idx + len(wrong)
    return out


def _find_patterns(text: str, specs: tuple[PatternSpec, ...]) -> list[Hit]:
    out: list[Hit] = []
    for spec in specs:
        for m in spec.pattern.finditer(text):
            out.append(Hit(
                snippet=m.group(0),
                spec_id=spec.spec_id,
                rule_name=spec.rule_name,
                evidence=spec.evidence,
                suggestion=spec.suggestion,
                position=m.start(),
            ))
    return out


def check_text(text: str, whitelist: tuple[str, ...] = ()) -> Report:
    """主判定:纯函数,同一输入永远同一输出。"""
    lowered = text.lower()
    wl = frozenset(w.strip().lower() for w in whitelist if w.strip())
    hits: list[Hit] = []
    for word_spec in AD_LAW_LIMIT_WORDS:
        hits += _find_words(text, word_spec, wl, lowered)
    for fix_spec in (*VARIANT_WORDS, *TYPO_PAIRS):
        hits += _find_fixes(text, fix_spec, wl, lowered)
    hits += _find_patterns(text, PUNCT_RULES)
    hits += _find_patterns(text, NUM_RULES)
    hits.sort(key=lambda h: h.position)
    verdict = "HARD_FOUND" if hits else "CLEAN"
    return Report(verdict=verdict, hard=tuple(hits), uncovered=UNCOVERED)
