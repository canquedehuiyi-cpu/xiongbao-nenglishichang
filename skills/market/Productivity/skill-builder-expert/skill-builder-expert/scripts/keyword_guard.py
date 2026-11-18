#!/usr/bin/env python3
"""keyword_guard.py —— 关键词守卫扫描器（第⑦查，挂守门闸 L2）。

背景：关键词字段完整性属于核心配置项。
版本迭代中关键词被误删、主词被移出前段、风险词混入，均会导致
检索触达能力下降或平台审核风险，故设本闸防丢失（fail-closed）。

检查项（三层）：
  G1 非空：SKILL.md frontmatter 的 keywords 与 tags 数组均非空；
  G2 主词置顶：六个一级主词必须存在于 keywords 且位于前 8 位；
  G3 风险词零容忍：卖钱/赚钱/变现/密钥托管 等审核敏感词族在两个数组零命中。

设计纪律：
  - 只扫 SKILL.md frontmatter 两个数组，不碰正文；
  - 风险词表独立成常量，新增风险词只改词表不改逻辑；
  - 任何一层不过即退出码 1（守门闸 fail-closed 接管）。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

# 六个一级主词（与整合稿定稿一致，顺序即权重顺序）
TOP_KEYWORDS = [
    "技能搭建", "Skill技能", "技能代建", "AI技能开发", "Agent技能", "技能包制作",
]
# 主词允许的最前位置（1-based）：前 8 位内视为置顶达标
TOP_POSITION_LIMIT = 8
# 审核敏感风险词族（子串命中即违例；用户定调：直接移除，不给替代）
RISK_WORDS = ["卖钱", "赚钱", "变现", "密钥托管"]
# keywords 精选上限（防平台字段截断；31±2 容差）
KEYWORDS_LIMIT = 33


def _extract_array(text: str, field: str) -> list[str] | None:
    m = re.search(rf"^{field}: \[(.*?)\]\s*$", text, re.S | re.M)
    if not m:
        return None
    return re.findall(r'"([^"]+)"', m.group(1))


def scan(root: Path) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    skill = root / "SKILL.md"
    if not skill.exists():
        return False, ["FAIL G0: SKILL.md 不存在"]
    text = skill.read_text(encoding="utf-8")
    kw = _extract_array(text, "keywords")
    tg = _extract_array(text, "tags")
    if kw is None or tg is None:
        return False, ["FAIL G1: keywords 或 tags 数组缺失（frontmatter 必填项）"]
    if not kw or not tg:
        msgs.append("FAIL G1: keywords/tags 数组为空")
    # G2 主词置顶
    for w in TOP_KEYWORDS:
        if w not in kw:
            msgs.append(f"FAIL G2: 一级主词「{w}」不在 keywords 中")
        else:
            pos = kw.index(w) + 1
            if pos > TOP_POSITION_LIMIT:
                msgs.append(f"FAIL G2: 主词「{w}」位于第 {pos} 位，超出前 {TOP_POSITION_LIMIT} 位")
    # G3 风险词零容忍
    for arr_name, arr in (("keywords", kw), ("tags", tg)):
        for w in arr:
            for r in RISK_WORDS:
                if r in w:
                    msgs.append(f"FAIL G3: {arr_name} 含审核敏感风险词「{w}」（命中 {r}）")
    # 附加项：keywords 精选上限（超限只记 WARN 级提示，不阻断）
    if len(kw) > KEYWORDS_LIMIT:
        msgs.append(f"WARN G4: keywords 共 {len(kw)} 个，超出精选上限 {KEYWORDS_LIMIT}（防平台字段截断建议精选）")
    fails = [m for m in msgs if m.startswith("FAIL")]
    return (len(fails) == 0), msgs


def main() -> int:
    # flag 与目录参数严格分离（观察项2工具链建议，定稿依据 2026-11-04 三方质检实测
    # 误把 --self-test 当目录传入产生假报警「SKILL.md 不存在」）：本脚本不支持自测，
    # 遇未知 flag 输出明确用法而非假 FAIL。
    _flags = [a for a in sys.argv[1:] if a.startswith("-")]
    _pos = [a for a in sys.argv[1:] if not a.startswith("-")]
    if _flags:
        sys.stderr.write("本脚本不支持选项 %s。用法: python keyword_guard.py <包目录>\n" % " ".join(_flags))
        return 2
    root = Path(_pos[0]).resolve() if _pos else Path.cwd()
    ok, msgs = scan(root)
    for m in msgs:
        print(m)
    if not msgs:
        print("PASS 关键词守卫: 两数组非空、核心关键词置顶、风险词零命中")
    if not ok:
        return 1
    # 有 WARN 无 FAIL 也算通过（与第七闸分级纪律一致）
    return 0


if __name__ == "__main__":
    sys.exit(main())
