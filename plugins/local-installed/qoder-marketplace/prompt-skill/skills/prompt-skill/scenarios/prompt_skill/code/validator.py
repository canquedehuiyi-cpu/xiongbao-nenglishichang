"""
validator.py —— 两套定死的评分体系（护城河区，写死在 code/）

体系 A（Prompt 质量，8 维 100 分）：
  A1 角色与服务对象 / A2 输入输出契约 / A3 四层上下文 / A4 负向约束 /
  A5 拒答与不确定性 / A6 证据锚定 / A7 输出格式可控 / A8 确定性计算委托
  语义声明（D-029④）：体系A 度量「结构契约完备性下限」（必要条件），
  不是语义质量充分性；放行另需 Risk≥28 + Gate M + Gate S（实质内容门禁）。
体系 B（Skill 质量，6 维 100 分）：
  B1 Frontmatter 规范 / B2 权限声明 / B3 SOP 结构 / B4 测试矩阵覆盖 /
  B5 断言机器可执行 / B6 响应通过率

纪律：
- 权重、阈值、判定组合写死在本文件——不外置成运行期配置（scenario_api 边界第 2 条）。
- rules.yaml 明文只允许「扩展同义词」（行业化运营），改不动权重与判定。
- 评分明细与原文引证只进 output/ 报告；explain 与 Issue.detail 只带计数与口径，
  维度得分表不出现在 last_result.json（逐行依据塞 outputs 是大文档 token 地雷）。
- B6 严禁模型自评：断言只有四种机器可执行形式，写不出断言的用例算 B5 缺陷。
"""

from __future__ import annotations

import re
from typing import Any

from scenario_api import Issue, IssueLevel

# ---- 判定线（护城河区，报告里只说「达标/未达标」）----
PROMPT_PASS = 80
SKILL_PASS = 80

# ---- 双轨门禁（SSOT D-010）：零权重改动，仅聚合视图 ----
# Capability = A1+A2+A3+A7（满分 54）；Risk = A4+A5+A6+A8（满分 46）
# 放行副条件：risk >= RISK_PASS（46 分制的 60%，取整 28）
RISK_PASS = 28
_CAPABILITY_DIMS = ("角色服务对象", "输入输出契约", "四层上下文", "输出格式可控")
_RISK_DIMS = ("负向约束", "拒答声明", "证据锚定", "确定性计算委托")

# ---- 实质内容门禁（D-029，防关键词堆砌空壳）----
# 语义声明：体系A 度量的是「结构契约完备性下限」（必要条件），不是语义质量充分性；
# 语义正确性只能由执行层（体系B Gold Case 重放）验证。堆砌探针实测曾拿 100 分（假阳性），
# 故放行追加实质内容门禁：剥离标点/markdown 符号后 ≥8 字的行计为有效行，总数 <10 不放行。
EFFECTIVE_LINE_MIN = 10
EFFECTIVE_LINE_CHARS = 8
_EFFECTIVE_STRIP = " \t　#*->|，。：:；、（）()【】[]《》!！?？\"'·「」"


def _effective_line_count(lines: list[str]) -> int:
    return sum(1 for ln in lines if len(ln.strip(_EFFECTIVE_STRIP)) >= EFFECTIVE_LINE_CHARS)

# ---- Gate M 材料契约（KB v1.1 / PD-13，D-007）----
# 强信号：任务依赖外部事实（弱词如「来源/数据」不收，避免误伤普通契约文本）
_MATERIAL_NEED = [
    r"联网", r"实时", r"最新(数据|信息|报道|公开)", r"检索", r"竞品",
    r"市场(调研|分析|竞争|份额)", r"行业(报告|数据|动态)", r"法规", r"行情",
    r"Perplexity", r"perplexity", r"外部(数据|事实)", r"时间窗",
]
# 材料契约节的显式声明
_MATERIAL_CONTRACT = [r"材料契约", r"材料来源类型", r"Material\s*Contract", r"MISSING_MATERIAL"]

# ---- 同义词默认表（rules.yaml 的 lexicon 节可追加行业词，不能删表）----
# D-029③：为降低「好 Prompt 因措辞不合词表被误判」的假阴性，默认表收录常见近义写法；
# D-030：补英文结构头惯用词（You are/Role/Goals/Constraints/Input/Output/Source 等，
# 实战演练：英文 Prompt 的 Constrains/Goals 不命中四层上下文）。
# 扩充只进本表或 rules.yaml，不得为新词放松判定逻辑。
_LEX_DEFAULT: dict[str, list[str]] = {
    "role": [r"你是", r"作为.{0,12}(助手|专家|助理|角色|分析师|工程师|顾问|编辑|翻译|教练|设计师|运营|研究员)", r"角色[:：]",
             r"\byou are\b", r"\brole\b"],
    "target": [r"面向.{0,20}(用户|读者|客户|团队)", r"读者(是|为)", r"\baudience\b"],
    "input": [r"输入", r"给定", r"用户提供", r"参数[:：]", r"\binput\b"],
    "output": [r"输出", r"返回", r"格式[:：]", r"请生成", r"交付", r"交稿", r"\boutput\b"],
    "user_context": [r"用户(背景|上下文)", r"服务对象", r"UserContext", r"\buser context\b"],
    "task_context": [r"任务[:：]", r"任务(目标|描述)", r"工作目标", r"TaskContext", r"\bgoals?\b"],
    "constraint_context": [r"约束", r"限制", r"红线", r"硬性(规则|要求)", r"规矩", r"Constraint", r"\bconstrain"],
    "evidence_context": [r"依据", r"证据", r"来源", r"出处", r"Evidence", r"\bsources?\b"],
    "negative": [r"不要", r"不得", r"严禁", r"禁止", r"避免", r"绝不", r"不许", r"不准",
                 r"\bdo not\b", r"\bdon't\b", r"\bmust not\b", r"\bnever\b", r"\bavoid\b",
                 r"\bprohibit", r"\bforbid"],
    "abstain": [r"无法确定", r"依据不足", r"拒(绝|答)", r"标注.{0,6}(存疑|待确认|不确定)", r"请人工",
                r"不要猜测", r"不得猜测", r"材料(不全|缺失)",
                r"\bdo not (guess|invent|fabricate|make up)\b", r"\bhuman (review|input|confirmation)\b",
                r"\bask (the user|for clarification)\b", r"\bcannot (determine|verify)\b",
                r"\binsufficient\b", r"\bmark.{0,12}(unclear|uncertain)\b"],
    "evidence_ref": [r"标注(来源|出处)", r"注明来源", r"引用", r"页码", r"逐字", r"来源[:：]",
                     r"\bcite\b", r"\bverbatim\b"],
    "calc": [r"计算", r"合计", r"总价", r"单价", r"百分比", r"汇率", r"统计"],
    "calc_tool": [r"脚本", r"工具", r"程序", r"代码", r"计算器", r"确定性"],
}

# A7 格式可控的四个类别（命中一类 +3，封顶 12）
_FORMAT_CATS: dict[str, list[str]] = {
    "模板": [r"模板", r"格式[:：]"],
    "表格": [r"表格", r"列[:：]", r"\btable\b"],
    "结构化": [r"JSON", r"YAML", r"Schema", r"\bmarkdown\b"],
    "字段枚举": [r"字段[:：]", r"以下字段", r"逐项"],
}

# A4 负向约束条数 -> 得分（0/1/2/≥3 条）
_NEG_BANDS = ((0, 0), (1, 5), (2, 10), (3, 14))

# 体系 B 的硬条件：B4/B5 必须满分，光靠其它维度堆分过不了认证
_B4_FULL = 25
_B5_FULL = 15

_ASSERT_PREFIXES = ("contains:", "not-contains:", "regex:")

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# 模板完成度硬闸：标准骨架的【待填】槽与 {{BRIEF}}/{{EXTRA}} 替换变量一旦残留在
# 正文里，就是未完成的模板。实测过：注入的关键词可以让 14 槽全部空着的骨架凑到
# 81 分过认证、乃至直接建包，而评分器此前没有任何一处检查占位符（draft-prompt
# 自己用同一个【待填】正则数出了 slot_count，却从没接进评分）。
_UNFILLED_SLOT = re.compile(r"【待填[:：]([^】]*)】|{{(?:BRIEF|EXTRA)}}")


def _assert_substantive(a: Any) -> bool:
    """实质断言 = contains:/not-contains:/regex: 且参数非空。
    纯 nonempty（任何非空输出都过）属空转占位，不计入「真的测过」。"""
    s = str(a).strip()
    for pfx in _ASSERT_PREFIXES:
        if s.startswith(pfx):
            return bool(s[len(pfx):].strip())
    return False


def _merge_lex(extra: dict[str, Any] | None) -> dict[str, list[str]]:
    lex = {k: list(v) for k, v in _LEX_DEFAULT.items()}
    if extra:
        for key, pats in extra.items():
            if key in lex and isinstance(pats, list):
                lex[key].extend(str(p) for p in pats)
    return lex


def _scan(text: str, lines: list[str], patterns: list[str],
          head_only: int = 0) -> tuple[bool, int]:
    """返回 (是否命中, 首个命中行号)。head_only>0 时只扫前 N 个非空行。"""
    if not patterns:
        return False, -1
    combined = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
    seen = 0
    for n, ln in enumerate(lines, 1):
        if head_only:
            if not ln.strip():
                continue
            seen += 1
            if seen > head_only:
                break
        if combined.search(ln):
            return True, n
    return False, -1


def _count_hits(lines: list[str], patterns: list[str]) -> int:
    combined = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)
    return sum(1 for ln in lines if combined.search(ln))


def gate_material(text: str, lines: list[str]) -> dict:
    """Gate M（PD-13）：涉及外部事实的 Prompt 必须显式声明材料契约。
    triggered=命中外部事实强信号；has_contract=含材料契约节；ok=无需或已声明。"""
    need, need_ln = _scan(text, lines, _MATERIAL_NEED)
    has, _ = _scan(text, lines, _MATERIAL_CONTRACT)
    return {"triggered": need, "has_contract": has, "ok": (not need) or has,
            "need_line": need_ln}


def score_prompt(text: str, lines: list[str],
                 lex_extra: dict[str, Any] | None = None) -> dict:
    """体系 A：8 维打分。返回 {"total","dims","gaps","capability","risk","material"}；
    gaps 含行号引证。双轨为聚合视图（零权重改动，SSOT D-010）。"""
    lex = _merge_lex(lex_extra)
    dims: dict[str, int] = {}
    gaps: list[dict] = []

    def gap(dim: str, need: str, lineno: int = -1) -> None:
        quote = ""
        if 0 < lineno <= len(lines):
            quote = lines[lineno - 1][:80]
        gaps.append({"维度": dim, "缺什么": need, "行号": lineno, "原文": quote})

    # A1 角色与服务对象（10）
    hit_role, role_ln = _scan(text, lines, lex["role"], head_only=20)
    hit_tgt, _ = _scan(text, lines, lex["target"], head_only=20)
    dims["角色服务对象"] = 10 if hit_role else (5 if hit_tgt else 0)
    if not hit_role and not hit_tgt:
        gap("角色与服务对象", "开头未声明执行角色（如「你是…」）或服务对象")
    elif not hit_role:
        gap("角色与服务对象", "只声明了服务对象，未声明执行角色")

    # A2 输入输出契约（20）
    hit_in, in_ln = _scan(text, lines, lex["input"])
    hit_out, out_ln = _scan(text, lines, lex["output"])
    dims["输入输出契约"] = (10 if hit_in else 0) + (10 if hit_out else 0)
    if not hit_in:
        gap("输入输出契约", "未声明输入：用户会给到什么材料/字段")
    if not hit_out:
        gap("输入输出契约", "未声明输出：交付什么、什么格式")

    # A3 四层上下文（12，每层 3）
    layers = (("用户层", "user_context"), ("任务层", "task_context"),
              ("约束层", "constraint_context"), ("证据层", "evidence_context"))
    ctx_score = 0
    for label, key in layers:
        hit, _ = _scan(text, lines, lex[key])
        if hit:
            ctx_score += 3
        else:
            gap("四层上下文", f"缺 {label}（依据 rules.yaml 同义词表）")
    dims["四层上下文"] = ctx_score

    # A4 负向约束（14，按条数分档；D-029②：去重 + 实质——命中行去掉关键词后 ≥4 字、
    # 规范化重复行只计一次，防止复制粘贴「不得。严禁。不要。」式堆砌刷分）
    neg_pats = re.compile("|".join(f"(?:{p})" for p in lex["negative"]), re.IGNORECASE)
    neg_seen: set[str] = set()
    for ln in lines:
        if not neg_pats.search(ln):
            continue
        norm = re.sub(r"[\s，。：:；、（）()【】\[\]!！?？·]", "", ln)
        if len(neg_pats.sub("", norm)) < 4:   # 去掉禁令词后内容不足 = 空壳
            continue
        if norm in neg_seen:                  # 复制粘贴的重复禁令只计一次
            continue
        neg_seen.add(norm)
    neg_n = len(neg_seen)
    awarded = 0
    for need, pts in _NEG_BANDS:
        if neg_n >= need:
            awarded = pts
    dims["负向约束"] = awarded
    if neg_n < 3:
        gap("负向约束", f"硬性红线句不足（有效 {neg_n} 条，去重且须有实质内容；需要更多「不要/严禁/不得」类禁令）")

    # A5 拒答与不确定性（10）
    hit_ab, ab_ln = _scan(text, lines, lex["abstain"])
    dims["拒答声明"] = 10 if hit_ab else 0
    if not hit_ab:
        gap("拒答声明", "无「依据不足则拒答/标注存疑」协议——这是防幻觉的硬要求")

    # A6 证据锚定（10）
    hit_ev, ev_ln = _scan(text, lines, lex["evidence_ref"])
    dims["证据锚定"] = 10 if hit_ev else 0
    if not hit_ev:
        gap("证据锚定", "未要求输出逐条标注来源/出处/页码")

    # A7 输出格式可控（12，四类各 3）
    fmt_hits = 0
    for label, pats in _FORMAT_CATS.items():
        hit, _ = _scan(text, lines, pats)
        if hit:
            fmt_hits += 1
        else:
            gap("输出格式可控", f"输出未约束「{label}」类形态之一")
    dims["输出格式可控"] = min(fmt_hits * 3, 12)

    # A8 确定性计算委托（12）：含计算类指令却没交给代码/工具 -> 0 分
    hit_calc, calc_ln = _scan(text, lines, lex["calc"])
    if not hit_calc:
        dims["确定性计算委托"] = 12
    else:
        hit_tool, _ = _scan(text, lines, lex["calc_tool"])
        dims["确定性计算委托"] = 12 if hit_tool else 0
        if not hit_tool:
            gap("确定性计算委托",
                "让模型自由推演计算（检测到计算类指令但无脚本/工具/程序承接）——必须改走确定性门禁",
                calc_ln)

    total = sum(dims.values())
    capability = sum(dims[d] for d in _CAPABILITY_DIMS)
    risk = sum(dims[d] for d in _RISK_DIMS)
    material = gate_material(text, lines)
    if not material["ok"]:
        gap("材料契约(Gate M)",
            "检测到外部事实依赖（联网/检索/竞品/行业数据等）但未声明材料契约节"
            "（KB v1.1 第 11 节：材料来源类型 NONE/PROVIDED/CORPUS/LIVE + 缺口协议）——PD-13",
            material["need_line"])
    # 实质内容门禁（D-029①）：堆砌空壳即使命中全部词表也不放行
    eff_lines = _effective_line_count(lines)
    substance = {"effective_lines": eff_lines, "min": EFFECTIVE_LINE_MIN,
                 "ok": eff_lines >= EFFECTIVE_LINE_MIN}
    if not substance["ok"]:
        gap("实质内容(Gate S)",
            f"有效内容行数 {eff_lines} < {EFFECTIVE_LINE_MIN}（剥离标点/markdown 符号后 "
            f"≥{EFFECTIVE_LINE_CHARS} 字为一行有效行）——关键词堆砌的空壳不放行，"
            "请为每个契约节填写真实内容（D-029）")
    # 模板完成度（Gate S 同闸）：【待填】槽或 {{BRIEF}}/{{EXTRA}} 残存 → 未完成模板，
    # 一律不发「达标」证书。走 substance["ok"] 而非新维度：直接参与 passed 判定且
    # 报错路径（REVIEW → 轮次 → ESCALATED）与既有缺口完全一致。
    if _UNFILLED_SLOT.search(text):
        seen: set[str] = set()
        for m in _UNFILLED_SLOT.finditer(text):
            if m.group(1) is not None:
                label = "待填槽位未补全：" + (m.group(1).strip() or "（空槽）")
            else:
                label = "模板替换变量未填：{{" + m.group(0)[2:-2] + "}}"
            if label not in seen:
                seen.add(label)
                gap("实质内容(Gate S)", label)
        substance["ok"] = False
    return {"total": total, "dims": dims, "gaps": gaps,
            "capability": capability, "risk": risk, "material": material,
            "substance": substance}


def prompt_issues(score: dict, certify: bool) -> list[Issue]:
    """fix-prompt（certify=False）压成 WARN 提示；score-prompt（True）不达标压 1 条 REVIEW。"""
    issues: list[Issue] = []
    gaps = score["gaps"]
    passed = score["total"] >= PROMPT_PASS
    detail_head = {"缺口条数": len(gaps)}
    if certify:
        if passed:
            issues.append(Issue(IssueLevel.INFO, f"Prompt 质检：达标（可用），缺口 {len(gaps)} 处", detail_head))
        else:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"Prompt 未达标（缺口 {len(gaps)} 处），结论与修复清单见报告",
                detail_head))
    else:
        if gaps:
            issues.append(Issue(IssueLevel.WARN, f"检测到 {len(gaps)} 处质量缺口，见诊断报告", detail_head))
        if score["total"] < PROMPT_PASS:
            issues.append(Issue(IssueLevel.WARN, "当前文本按认证口径不达标，修复后送 score-prompt"))
    return issues


# ---------------------------------------------------------------------------
# 体系 B：Skill 质量评分
# ---------------------------------------------------------------------------

def parse_frontmatter(md_text: str) -> dict | None:
    """取 SKILL.md 开头 --- 块并 safe_load；结构错误返回 None（不抛）。"""
    import yaml

    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def evaluate_assert(assertion: Any, response: str) -> bool | None:
    """四种机器可执行断言；None = 形式非法（B5 缺陷）。"""
    if not isinstance(assertion, str):
        return None
    a = assertion.strip()
    if a == "nonempty":
        return bool(response.strip())
    if a.startswith("contains:"):
        return a[len("contains:"):] in response
    if a.startswith("not-contains:"):
        return a[len("not-contains:"):] not in response
    if a.startswith("regex:"):
        try:
            return re.search(a[len("regex:"):], response) is not None
        except re.error:
            return None
    return None


def score_skill(bundle: dict) -> dict:
    """体系 B。bundle:
    {"frontmatter": dict|None, "skill_md": str, "permissions": str|None,
     "cases": [dict], "bad_json": int, "responses": {case_id: text},
     "responses_missing": int}
    """
    dims: dict[str, int] = {}
    gaps: list[dict] = []

    def gap(dim: str, need: str) -> None:
        gaps.append({"维度": dim, "缺什么": need})

    fm = bundle.get("frontmatter")
    body = bundle.get("skill_md", "")
    # B1 Frontmatter 规范（20）：name kebab 6 / description≥15字 8 / user-invocable 6
    b1 = 0
    if isinstance(fm, dict):
        name = fm.get("name")
        if isinstance(name, str) and _KEBAB.match(name):
            b1 += 6
        else:
            gap("Frontmatter", "name 缺失或非 kebab-case")
        desc = fm.get("description")
        if isinstance(desc, str) and len(desc.strip()) >= 15:
            b1 += 8
        else:
            gap("Frontmatter", "description 缺失或少于 15 字（宿主靠它判断何时调起）")
        if fm.get("user-invocable") is True:
            b1 += 6
        else:
            gap("Frontmatter", "user-invocable 未声明为 true")
    else:
        gap("Frontmatter", "SKILL.md 开头缺合法 --- frontmatter 块")
    dims["Frontmatter"] = b1

    # B2 权限声明（15）：读取/写入/网络 三节各 5
    perm = bundle.get("permissions") or ""
    b2 = 0
    for key, pats in (("读取", [r"读取", r"只读", r"访问"]),
                      ("写入", [r"写入", r"输出目录"]),
                      ("网络", [r"网络", r"联网", r"外连"])):
        if any(re.search(p, perm) for p in pats):
            b2 += 5
        else:
            gap("权限声明", f"PERMISSIONS.txt 缺「{key}」相关声明")
    dims["权限声明"] = b2

    # B3 SOP 结构（15）：何时使用/怎么调用/不要做什么 三节各 5
    b3 = 0
    for label, pats in (("何时使用", [r"何时使用", r"适用场景"]),
                        ("怎么调用", [r"使用方法", r"怎么调", r"调用", r"步骤"]),
                        ("不要做什么", [r"不要做什么", r"禁止", r"别做"])):
        if any(re.search(p, body) for p in pats):
            b3 += 5
        else:
            gap("SOP 结构", f"SKILL.md 正文缺「{label}」节")
    dims["SOP结构"] = b3

    # B4 测试矩阵覆盖（25）：总数≥5 给 10，happy/edge/adversarial 各 5
    cases = [c for c in bundle.get("cases", []) if isinstance(c, dict)]
    bad = int(bundle.get("bad_json", 0))
    cats = {c.get("category") for c in cases}
    b4 = 0
    if len(cases) >= 5:
        b4 += 10
    else:
        gap("测试矩阵", f"testcases/ 用例不足 5 个（现有 {len(cases)}" +
            (f"，另有 {bad} 个 JSON 解析失败）" if bad else "）"))
    for want in ("happy", "edge", "adversarial"):
        if want in cats:
            b4 += 5
        else:
            gap("测试矩阵", f"缺 {want} 类用例（正常/边界/对抗必须齐全）")
    dims["测试矩阵覆盖"] = b4

    # B5 断言实质可执行（15，硬性）：结构完整 + 形式合法 + 至少一条实质断言。
    # 纯 nonempty 种子会被判「空转未测」——把「交付前必须升级断言」从文档承诺
    # 变成编译进 exe 的闸门（用户拍板的产品承诺：被测过不能是假的）。
    def _is_valid(c: dict) -> bool:
        return (isinstance(c.get("case_id"), str) and bool(c["case_id"])
                and isinstance(c.get("input"), str) and bool(c["input"].strip())
                and isinstance(c.get("asserts"), list) and bool(c["asserts"])
                and all(evaluate_assert(a, "") is not None for a in c["asserts"]))

    n_cases = len(cases) + bad
    good_cases = [c for c in cases if _is_valid(c)]
    substantive_cases = [c for c in good_cases
                         if any(_assert_substantive(a) for a in c["asserts"])]
    if n_cases:
        dims["断言可执行"] = round(len(substantive_cases) * 15 / n_cases)
    else:
        dims["断言可执行"] = 0
        gap("断言可执行", "没有任何用例可解析")
    if len(good_cases) != n_cases:
        gap("断言可执行",
            f"{n_cases - len(good_cases)} 个用例缺 case_id/input 或断言形式非法"
            "（仅支持 nonempty / contains: / not-contains: / regex:）")
    elif len(substantive_cases) != n_cases:
        vac = [c["case_id"] for c in good_cases
               if not any(_assert_substantive(a) for a in c["asserts"])]
        gap("断言可执行",
            f"{len(vac)} 个用例只有 nonempty 空断言（任何输出都算过 = 未真正测试）："
            + ", ".join(vac[:5]) + ("…" if len(vac) > 5 else "")
            + "——按技能说明书升级为 contains:/not-contains:/regex: 具体预期后重认证")

    # B6 响应通过率（10）：逐用例全断言通过计分；缺响应目录 = 0 分（降级）
    responses: dict = bundle.get("responses", {})
    passed_cases = 0
    no_resp = 0
    fail_ids: list[str] = []
    for c in good_cases:
        resp = responses.get(c["case_id"])
        if resp is None:
            no_resp += 1
            continue
        if all(evaluate_assert(a, resp) for a in c["asserts"]):
            passed_cases += 1
        else:
            fail_ids.append(c["case_id"])
    if good_cases:
        dims["响应通过率"] = round(passed_cases * 10 / len(good_cases))
    else:
        dims["响应通过率"] = 0
    if no_resp or fail_ids:
        gap("响应通过率",
            f"缺响应文件 {no_resp} 个；断言未通过 {len(fail_ids)} 个" +
            ("（未通过用例: " + ", ".join(fail_ids[:5]) +
             ("…" if len(fail_ids) > 5 else "") + "）" if fail_ids else ""))
    total = sum(dims.values())
    hard_ok = dims["测试矩阵覆盖"] == _B4_FULL and dims["断言可执行"] == _B5_FULL
    passed = total >= SKILL_PASS and hard_ok and not no_resp
    if not hard_ok:
        gap("判定口径", "B4 矩阵覆盖与 B5 断言可执行为硬性条件，未满分不达标")
    elif no_resp:
        gap("判定口径",
            f"{no_resp} 个用例没有响应文件：未完整实测不得判「可用」"
            "——与响应目录缺失时 DEGRADED 不判可用的口径一致。此前部分回填"
            "（哪怕只回填 1 份响应）就会绕过降级、带未测用例出货，这是闭环缺口"
            "（B6 的缺响应缺口另列）")
    return {"total": total, "dims": dims, "gaps": gaps, "passed": passed,
            "hard_ok": hard_ok, "failed_case_ids": fail_ids, "no_response_cases": no_resp}


def skill_issues(score: dict, certify: bool) -> list[Issue]:
    issues: list[Issue] = []
    detail = {"缺口条数": len(score["gaps"])}
    if certify:
        if score["passed"]:
            issues.append(Issue(IssueLevel.INFO, f"Skill 质检：达标（可用），缺口 {len(score['gaps'])} 处", detail))
        else:
            issues.append(Issue(IssueLevel.REVIEW,
                                f"Skill 未达标（缺口 {len(score['gaps'])} 处），结论与清单见认证报告", detail))
    elif score["gaps"]:
        issues.append(Issue(IssueLevel.WARN, f"检测到 {len(score['gaps'])} 处质量缺口，见报告", detail))
    return issues
