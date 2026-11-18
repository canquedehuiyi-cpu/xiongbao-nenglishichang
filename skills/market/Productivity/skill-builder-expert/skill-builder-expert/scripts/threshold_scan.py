#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阈值总表扫描（fail-closed）——数字定死＋代码闸门（第十闸）

定位
----
把「能变成数字的规则」全部收拢进唯一真源 references/REF-THR-060_ThresholdRegistry.md，
每条阈值一行（指标｜比较符｜数值），本闸逐条实测比对：
  == 定数锚：实测值与总表数值不符即 FAIL（改数必须先改总表并走备案——想动数字，先动总表）；
  <= / >= 阈值型：实测越线即 FAIL。
规则设计原则（律④三问全部可答）：数字进锚点（总表）、比对进扫描器（本闸）、
越线进流程（FAIL 打回修正引擎，禁止带病出包）。

指标清单（metric → 实测口径）
  direct_table_entries  直达表条目数：REF-DAT-057 内 `### DA-` 计数
  faq_entries           常见问题条目数：FAQ.md 内 `**Xn：` 计数
  closure_gates         对话闭环闸数：interaction_closure_scan.py 内唯一 IC 编号数
  visual_rules          视觉分层规则数：visual_layer_scan.py 内唯一 R 编号数
  reply_keywords        回复词数：SKILL.md／REF-SM-004／REF-DAT-057 三处「回复【X】」并集
  skill_md_bytes        主文档字节数：SKILL.md 实际体积

用法
    python scripts/threshold_scan.py <包根目录>
    python scripts/threshold_scan.py --self-test
退出码：0 = 全过；1 = 有阈值越线或总表缺失/损坏（fail-closed）。零外部依赖，纯标准库。
"""
import io, re, sys, json, tempfile
from pathlib import Path

REGISTRY_REL = "references/REF-THR-060_ThresholdRegistry.md"
ROW_PAT = re.compile(r"^(THR-\d{2})\s*\|\s*([a-z0-9_]+)\s*\|\s*(==|<=|>=)\s*\|\s*(\d+)\s*\|\s*(.+)$")
BLOCK_PAT = re.compile(r"```thresholds\n([\s\S]*?)```")

REPLY_KW_PAT = re.compile(r"回复\s*[*＊*]*【([^【】{}]{1,14})】")
REPLY_KW_FILES = ["SKILL.md",
                  "references/REF-SM-004_StateMachine.yaml",
                  "references/REF-DAT-057_DirectAnswerTable.md"]


def _read(root, rel):
    p = root / rel
    if not p.exists():
        return None
    return io.open(p, encoding="utf-8").read()


IC_RANGE_PAT = re.compile(r"IC1[–-]IC(\d+)")
IC_RANGE_LEGAL = {6, 14}  # 6=必备件子集语境（真源 interaction_closure_scan），14=现行全闸集真值
IC_RANGE_FILES_DIR = "references"


def _measure_ic_range(root):
    """正文 IC 全范围引用漂移计数：SKILL.md＋references 内「IC1–ICN」中 N 非法（∉{6,14}）的出现数。
    「」引用段豁免（规则定义引用旧字面属合法语境，同 IC12/IC13 口径）。"""
    root = Path(root)
    qspan = re.compile(r"「[^」]*」")
    total = 0
    targets = ["SKILL.md"] + [str(p.relative_to(root)).replace("\\", "/")
                              for p in root.glob(IC_RANGE_FILES_DIR + "/*.md")]
    for rel in targets:
        p = root / rel
        if not p.exists():
            continue
        t = qspan.sub("", io.open(p, encoding="utf-8").read())
        total += sum(1 for n in IC_RANGE_PAT.findall(t) if int(n) not in IC_RANGE_LEGAL)
    return total


def _measure_gate_l3(p):
    """读 quality_gate.py 内 L3 区块计 scripts_dir 条目（定位代码层最后一处元组，到列表收口行为止）；
    无 L3 区块返回 None（结构性 fail-closed）。"""
    t = io.open(p, encoding="utf-8").read()
    idx = t.rfind('("L3 业务逻辑校验"')
    if idx == -1:
        return None
    end = t.find("\n    ]", idx)
    if end == -1:
        return None
    return len(re.findall(r"scripts_dir /", t[idx:end]))


def measure(root, metric):
    """返回 (实测值 or None, 说明)。None = 无法实测（结构性缺件）。"""
    root = Path(root)
    if metric == "growth_base":
        # 数据行：返回总表 THR-09 行记录的基准值（自洽校验）
        reg = _read(root, REGISTRY_REL)
        if reg is None:
            return None, "阈值总表缺失"
        m = re.search(r"(?m)^THR-\d{2}\s*\|\s*growth_base\s*\|\s*==\s*\|\s*(\d+)", reg)
        if not m:
            return None, "总表缺 growth_base 行"
        return int(m.group(1)), ""
    if metric == "skill_md_growth":
        p = root / "SKILL.md"
        if not p.exists():
            return None, "SKILL.md 缺失"
        base, note = measure(root, "growth_base")
        if base is None:
            return None, note
        return p.stat().st_size - base, ""
    if metric == "direct_table_entries":
        t = _read(root, "references/REF-DAT-057_DirectAnswerTable.md")
        if t is None:
            return None, "REF-DAT-057 缺失"
        return len(re.findall(r"(?m)^### DA-\d{2}", t)), ""
    if metric == "faq_entries":
        t = _read(root, "FAQ.md")
        if t is None:
            return None, "FAQ.md 缺失"
        return len(re.findall(r"(?m)^\*\*[A-F]\d{1,2}：", t)), ""
    if metric == "closure_gates":
        t = _read(root, "scripts/interaction_closure_scan.py")
        if t is None:
            return None, "interaction_closure_scan.py 缺失"
        return len(set(re.findall(r"\bIC(\d+)\b", t))), ""
    if metric == "visual_rules":
        t = _read(root, "scripts/visual_layer_scan.py")
        if t is None:
            return None, "visual_layer_scan.py 缺失"
        return len(set(re.findall(r"\bR(\d+)\b", t))), ""
    if metric == "reply_keywords":
        kws = set()
        missing = []
        for rel in REPLY_KW_FILES:
            t = _read(root, rel)
            if t is None:
                missing.append(rel)
                continue
            kws |= set(REPLY_KW_PAT.findall(t))
        if len(missing) == len(REPLY_KW_FILES):
            return None, "回复词三处目标文件全部缺失"
        return len(kws), ("缺件注意：%s" % "、".join(missing)) if missing else ""
    if metric == "skill_md_bytes":
        p = root / "SKILL.md"
        if not p.exists():
            return None, "SKILL.md 缺失"
        return p.stat().st_size, ""
    if metric == "ic_range_violations":
        return _measure_ic_range(root), ""
    if metric == "gate_l3_scanners":
        p = root / "scripts" / "quality_gate.py"
        if not p.exists():
            return None, "跳过：quality_gate.py 缺失（非工厂形态包，本项不适用）"
        n = _measure_gate_l3(p)
        if n is None:
            return None, "总闸 L3 区块缺失（结构性 fail-closed）"
        return n, ""
    if metric == "references_bytes":
        ref_dir = root / "references"
        if not ref_dir.is_dir():
            return None, "references 目录缺失"
        # 口径：公开基准层——排除自用层九册（master 注入件）。公开包与自用层装后抽检同值，
        # 锚定数字不含自用层增量（公开口径只辖公开层，2026-11-11 备案）。
        # 名单以编号段短字面判别（词面拼装防自指，同回归闸泄漏词表口径）。
        _ids = ("MASTER-", "CHG-058", "ENT-055", "EVL-053", "KWD-050", "PLT-056", "RET-059")
        return sum(f.stat().st_size for f in ref_dir.glob("*.md")
                   if not any(i in f.name for i in _ids)), ""
    return None, "未知指标（总表出现扫描器不认识的 metric，先扩扫描器再入册）"


def _load_rows(root):
    t = _read(Path(root), REGISTRY_REL)
    if t is None:
        return None, ["阈值总表缺失：%s（单点真源不在位，fail-closed）" % REGISTRY_REL]
    m = BLOCK_PAT.search(t)
    if not m:
        return None, ["阈值总表缺 ```thresholds 机读区（fail-closed）"]
    rows, seen = [], set()
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rm = ROW_PAT.match(line)
        if not rm:
            return None, ["阈值总表机读区行格式不合法：%s" % line[:60]]
        rid, metric, op, value, desc = rm.group(1), rm.group(2), rm.group(3), int(rm.group(4)), rm.group(5).strip()
        if rid in seen:
            return None, ["阈值编号重复：%s" % rid]
        seen.add(rid)
        rows.append((rid, metric, op, value, desc))
    if not rows:
        return None, ["阈值总表机读区零行（fail-closed）"]
    return rows, []


def scan(root):
    root = Path(root)
    if not root.exists():
        return ["扫描根目录不存在"]
    rows, problems = _load_rows(root)
    if rows is None:
        return problems
    for rid, metric, op, value, desc in rows:
        actual, note = measure(root, metric)
        if actual is None:
            if note.startswith("跳过"):
                continue
            problems.append("%s [%s] 无法实测：%s" % (rid, metric, note))
            continue
        if op == "==" and actual != value:
            problems.append("%s [%s] 定数锚失守：总表定 %d，实测 %d（改数必须先改总表并走备案，禁止先改产物）"
                            % (rid, metric, value, actual))
        elif op == "<=" and actual > value:
            problems.append("%s [%s] 越上限：总表限 ≤%d，实测 %d" % (rid, metric, value, actual))
        elif op == ">=" and actual < value:
            problems.append("%s [%s] 越下限：总表限 ≥%d，实测 %d" % (rid, metric, value, actual))
    return problems


def main(root):
    problems = scan(root)
    verdict = "PASS" if not problems else "FAIL"
    print(json.dumps({"tool": "threshold_scan", "problems": problems,
                      "problem_count": len(problems), "verdict": verdict}, ensure_ascii=False))
    return 0 if not problems else 1


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        (r / "references").mkdir(parents=True)
        (r / "scripts").mkdir(parents=True)
        (r / "FAQ.md").write_text(
            "".join("**%s%d：问%d**\n答。\n\n" % (chr(65 + i % 6), i, i) for i in range(1, 4)), encoding="utf-8")
        (r / "references" / "REF-DAT-057_DirectAnswerTable.md").write_text(
            "".join("### DA-%02d ｜条目%d\n\n内容\n\n" % (i, i) for i in range(1, 4)), encoding="utf-8")
        (r / "scripts" / "interaction_closure_scan.py").write_text("# 闸清单 IC1 IC2 IC3 IC4 IC5 IC6 IC7\n", encoding="utf-8")
        (r / "scripts" / "visual_layer_scan.py").write_text("# 规则 R1 R2 R3 R4\n", encoding="utf-8")
        (r / "scripts" / "quality_gate.py").write_text(
            'layers = [\n'
            '    ("L3 业务逻辑校验", [scripts_dir / "a.py",\n'
            '                        scripts_dir / "b.py",\n'
            '                        scripts_dir / "c.py"]),\n'
            '    ]\n', encoding="utf-8")
        (r / "SKILL.md").write_text("回复【甲】或回复【乙】；再提一次回复【甲】即可。词表补登「IC1–IC10」。\n", encoding="utf-8")
        registry_rows = ("```thresholds\n"
                         "THR-01 | direct_table_entries | == | 3 | 直达表条目定数\n"
                         "THR-02 | faq_entries | == | 3 | 常见问题条目定数\n"
                         "THR-03 | closure_gates | == | 7 | 闭环闸数定数\n"
                         "THR-04 | visual_rules | == | 4 | 视觉规则数定数\n"
                         "THR-05 | reply_keywords | == | 2 | 回复词定数\n"
                         "THR-06 | skill_md_bytes | <= | 100000 | 主文档体量上限\n"
                         "THR-07 | ic_range_violations | == | 0 | 正文 IC 范围引用漂移计数\n"
                         "THR-08 | gate_l3_scanners | == | 3 | 总闸 L3 扫描器数\n"
                         "THR-09 | growth_base | == | 0 | 主文档基准字节数\n"
                         "THR-10 | skill_md_growth | <= | 2000 | 每轮增量上限\n"
                         "THR-11 | skill_md_bytes | <= | 170000 | 收紧上限\n"
                         "```\n")
        (r / "references" / "REF-THR-060_ThresholdRegistry.md").write_text(
            "# 阈值总表\n\n" + registry_rows, encoding="utf-8")
        # 阳：全过
        if scan(r):
            ok = False
            print("阳例未过:", scan(r))
        # 阴1：定数锚失守应 FAIL
        (r / "references" / "REF-DAT-057_DirectAnswerTable.md").write_text(
            "".join("### DA-%02d ｜条目%d\n\n内容\n\n" % (i, i) for i in range(1, 5)), encoding="utf-8")
        p1 = scan(r)
        if not p1 or "THR-01" not in p1[0]:
            ok = False
            print("阴1（定数锚失守应 FAIL）未过:", p1)
        # 阴2：总表缺失应 FAIL
        (r / "references" / "REF-THR-060_ThresholdRegistry.md").unlink()
        p2 = scan(r)
        if not p2 or "缺失" not in p2[0]:
            ok = False
            print("阴2（总表缺失应 FAIL）未过:", p2)
        # 阴3：正文 IC 范围引用漂移应 FAIL（扩闸漏同步防线）
        (r / "references" / "REF-THR-060_ThresholdRegistry.md").write_text(
            "# 阈值总表\n\n" + registry_rows, encoding="utf-8")
        (r / "references" / "REF-DAT-057_DirectAnswerTable.md").write_text(
            "".join("### DA-%02d ｜条目%d\n\n内容\n\n" % (i, i) for i in range(1, 4)), encoding="utf-8")
        (r / "SKILL.md").write_text("对话闭环出厂必查 IC1–IC12（范围唯一真源：interaction_closure_scan）。\n", encoding="utf-8")
        p3 = scan(r)
        if not p3 or not any("THR-07" in x for x in p3):
            ok = False
            print("阴3（IC 范围引用漂移应 FAIL）未过:", p3)
        # 阴4：L3 扫描器数与总表不符应 FAIL
        (r / "SKILL.md").write_text("对话闭环出厂必查 IC1–IC14。\n", encoding="utf-8")
        (r / "references" / "REF-THR-060_ThresholdRegistry.md").write_text(
            "# 阈值总表\n\n" + registry_rows.replace(
                "THR-08 | gate_l3_scanners | == | 3", "THR-08 | gate_l3_scanners | == | 5"),
            encoding="utf-8")
        p4 = scan(r)
        if not p4 or not any("THR-08" in x for x in p4):
            ok = False
            print("阴4（L3 闸数失守应 FAIL）未过:", p4)
    print(json.dumps({"tool": "threshold_scan", "self_test": "PASS" if ok else "FAIL"},
                     ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(root))
