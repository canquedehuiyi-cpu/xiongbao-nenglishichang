"""
steps.py —— 十三个任务的确定性步骤

分工纪律：引擎步骤只做「解析、评分、门禁、写产物」；
Prompt 的语义改写、被测 Skill 的执行与响应回填，都是宿主 Agent 的活
（SKILL.md 的 SOP 负责编排——引擎任务之间互不调用，编排不落进 dev 线，
符合《dev_pro适合的场景》的边界准绳）。

outputs 轻量纪律（大文档 token 防雷）：原文不回写 outputs，
只经 trace_check["source"] 在本次运行内传递（引擎执行完会 pop，
不进 last_result.json）；逐行缺口只进 output/ 报告文件。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time

import yaml
from scenario_api import (
    ErrorCode,
    ExecutionError,
    Issue,
    IssueLevel,
    RunContext,
    read_file_auto,
)

from .validator import (
    PROMPT_PASS,
    RISK_PASS,
    _assert_substantive,
    evaluate_assert,
    parse_frontmatter,
    prompt_issues,
    score_prompt,
    score_skill,
    skill_issues,
)

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# ---- SAG 材料层（材料契约 §11 → LIVE 补给线）----
# 引擎零联网零检索：宿主 Agent 负责「获取」（WebSearch/iFinD/…），本层只做
# 溯源→落盘→注入的确定性校验与沉淀（对齐《材料层设计》P2 最小实现）。
_SAM_SECTION = re.compile(
    r"#+\s*11\.?\s*材料契约|Material\s*Contract", re.IGNORECASE)
_MATERIAL_SOURCE_RE = re.compile(
    r"材料来源类型[:：]\s*(NONE|PROVIDED|CORPUS|LIVE)", re.IGNORECASE)
_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLUG_CLEAN = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def _skill_material_type(raw: str) -> str | None:
    """从 §11 材料契约推断材料来源类型；找不到声明返回 None（老稿按 NONE 处理）。"""
    m = _SAM_SECTION.search(raw)
    if not m:
        return None
    seg = raw[m.start():m.start() + 600]
    sm = _MATERIAL_SOURCE_RE.search(seg)
    return sm.group(1).upper() if sm else None


def _material_topic(title: str) -> str:
    """标题 → 落盘子目录（小写 kebab，保留中文，防路径穿越）。"""
    s = _SLUG_CLEAN.sub("-", str(title).strip().lower()).strip("-")
    return s[:40] or "material"


# ---------------------------------------------------------------------------
# 共用小工具
# ---------------------------------------------------------------------------

def _rules(ctx: RunContext) -> dict:
    """展示层配置 + 可运营的同义词扩展表（阈值不在这里，见 validator）。"""
    try:
        raw = ctx.runtime.read_template("rules.yaml")
    except FileNotFoundError:
        # 降级必须可见（D-014 同精神）：templates 缺失意味着运营方行业化词表
        # 无声失效，只能退内置默认表——不能静默吞掉
        ctx.issues.append(Issue(IssueLevel.WARN,
                                "scenarios/prompt_skill/assets/pro/templates/rules.yaml 缺失：本次评分退回内置默认词表，"
                                "行业化同义词扩展未生效"))
        return {}
    return yaml.safe_load(raw) or {}


def _source(ctx: RunContext) -> str:
    """从 trace_check 拿本次运行的原文（load 步已声明，引擎结束后 pop 掉）。"""
    return ctx.outputs["trace_check"]["source"]


def _lines(ctx: RunContext) -> list[str]:
    return _source(ctx).splitlines()


def _add_trace_items(ctx: RunContext, quotes: list[str]) -> None:
    items = ctx.outputs.setdefault("trace_check", {"source": "", "items": []})["items"]
    for q in quotes:
        q = q.strip()
        if q and q not in items:
            items.append(q[:120])


def _write(dir_path, name: str, text: str):
    dir_path.mkdir(parents=True, exist_ok=True)
    p = dir_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _write_report(dir_path, name: str, text: str):
    """output/ 报告落盘（D-030：同秒防覆盖）——报告名时间戳粒度为秒，
    同秒产出两份同名报告会静默互相覆盖（实战演练：v0 认证报告被 v1 覆盖丢失）。
    重名时在扩展名前追加 -N 序号，绝不静默覆盖。bundle 内固定名文件不走此助手。"""
    dir_path.mkdir(parents=True, exist_ok=True)
    p = dir_path / name
    if p.exists():
        stem, suffix = p.stem, p.suffix
        n = 1
        while (dir_path / f"{stem}-{n}{suffix}").exists():
            n += 1
        p = dir_path / f"{stem}-{n}{suffix}"
    p.write_text(text, encoding="utf-8")
    return p


def _sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _bundle_files(root) -> list:
    """参与评分/指纹/打包的文件（storage/ 与 output/ 不进指纹：
    响应留档与打包动作不应使其自身失效；config/cert_ref.txt 是认证书本身，
    写它不能反过来改掉它所证明的指纹——两边同一口径排除）。"""
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("storage/") or rel.startswith("output/") \
                or rel == "config/cert_ref.txt" or "__pycache__" in rel:
            continue
        out.append((rel, p))
    return out


def _bundle_fp(root) -> str:
    joined = "\n".join(f"{rel}:{_sha256_file(p)}" for rel, p in _bundle_files(root))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _load_bundle(root) -> dict:
    """从技能目录读齐体系 B 的原料（每步重读，inputs 里路径一直在，
    避免把全文塞进 outputs 造成回声膨胀）。"""
    skill_md_path = root / "SKILL.md"
    skill_md = skill_md_path.read_text(encoding="utf-8", errors="replace")
    perm_path = root / "PERMISSIONS.txt"
    permissions = perm_path.read_text(encoding="utf-8", errors="replace") \
        if perm_path.is_file() else None
    cases: list[dict] = []
    bad_json = 0
    tc_dir = root / "testcases"
    if tc_dir.is_dir():
        for f in sorted(tc_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                bad_json += 1
                continue
            if isinstance(data, dict):
                a = data.get("asserts")
                # 手写 case JSON 常把 asserts 写成单个字符串；代码里 `for a in asserts`
                # 会按**字符**迭代，评分与断言全部按字符判 -> 形式非法且报错文案误导。
                # 在唯一汇聚点归一化为列表（"||" 分隔，与 harvest-case 输入口径一致）。
                if isinstance(a, str):
                    data = {**data,
                            "asserts": [x.strip() for x in a.split("||") if x.strip()]}
                cases.append(data)
            else:
                bad_json += 1
    responses: dict[str, str] = {}
    resp_dir = root / "storage" / "responses"
    if resp_dir.is_dir():
        for f in sorted(resp_dir.glob("*.txt")):
            responses[f.stem] = f.read_text(encoding="utf-8", errors="replace")
    return {
        "frontmatter": parse_frontmatter(skill_md),
        "skill_md": skill_md,
        "permissions": permissions,
        "cases": cases,
        "bad_json": bad_json,
        "responses": responses,
        "has_response_dir": resp_dir.is_dir(),
    }


def _fmt_gaps_md(gaps: list[dict]) -> list[str]:
    lines = []
    for i, g in enumerate(gaps, 1):
        loc = f"（第 {g['行号']} 行：「{g['原文']}」）" \
            if g.get("行号", -1) > 0 and g.get("原文") else ""
        lines.append(f"{i}. **{g['维度']}** — {g['缺什么']}{loc}")
    return lines


# ---------------------------------------------------------------------------
# 任务 1/3 共用：Prompt 读取 + 诊断 / 认证
# ---------------------------------------------------------------------------

def step_load_prompt(ctx: RunContext) -> None:
    raw = read_file_auto(ctx.inputs["source-file"])
    lines = raw.splitlines()
    if not any(ln.strip() for ln in lines):
        ctx.issues.append(Issue(IssueLevel.ERROR, "输入文件是空的"))
        return
    ctx.outputs["line_count"] = len([ln for ln in lines if ln.strip()])
    ctx.outputs["trace_check"] = {"source": raw, "items": []}


def step_lint_fix(ctx: RunContext) -> None:
    score = score_prompt(_source(ctx), _lines(ctx), _rules(ctx).get("lexicon"))
    ctx.issues.extend(prompt_issues(score, certify=False))
    ctx.outputs["gaps_count"] = len(score["gaps"])


def step_render_fix_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    score = score_prompt(_source(ctx), _lines(ctx), rules.get("lexicon"))
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    body = [
        f"# {title} · 诊断报告 · {today}",
        "",
        f"- 输入非空行数：{ctx.outputs['line_count']}",
        f"- 缺口：{len(score['gaps'])} 处（按认证口径：{'达标' if score['total'] >= PROMPT_PASS else '未达标'}）",
        "",
        "## 修复清单（宿主 Agent 按此逐条改写，只改一次，改完送 score-prompt 认证）",
        "",
    ]
    body += _fmt_gaps_md(score["gaps"]) or ["（无缺口）"]
    body += ["", "> 权重与判定组合不随报告出境；同义词表可在 scenarios/prompt_skill/assets/pro/templates/rules.yaml 行业化扩展。"]
    report = _write_report(ctx.runtime.output_dir(), f"diagnosis-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["diagnosis_file"] = str(report)
    ctx.outputs["diagnosis_file_name"] = report.name
    _add_trace_items(ctx, [g["原文"] for g in score["gaps"] if g.get("原文")])
    ctx.outputs["explain"] = {"口径": "体系A 8 维确定性检查", "缺口数": len(score["gaps"])}


# ---------------------------------------------------------------------------
# Prompt 模块：候选状态 / 版本快照 / 门禁路由（SSOT v1.2：D-008/009/013/015/017/018/019）
# ---------------------------------------------------------------------------

# 轮次上限（D-009）：B=修复 3 轮，A=重做 2 轮；耗尽转人工
_ROUND_LIMIT = {"A": 2, "B": 3}


def _candidate_id(text: str) -> str:
    """候选指纹（D-019/D-021）：首次有效输入 sha256 前 16 位。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# 候选 ID 会直接拼进 output/prompt_versions/<cid>/ 与报告文件名，未过滤的 `../`
# 能逃出 dist_root 往任意目录写文件（实测 --set candidate=../../../../x 把认证报告
# 写到了 %TEMP%，退出码 0）。同一族的 skill-name 早有 _KEBAB 校验、candidate 却没有
# ——平行标识符的守卫不对称。因为不允许 / 与 \，`..` 只能是单个目录名的一部分，
# 不构成穿越；16 位十六进制指纹与 audit-bad-cand 这类可读标签都仍然合法。
_CANDIDATE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")


def _safe_candidate(raw: str, *, field_hint: str = "--set candidate=") -> str:
    """校验并返回候选 ID；空值或非法值一律 ExecutionError。

    刻意**不做**静默清洗（skill-name 那种「装配会清洗之」搬到这里是错的）：
    候选 ID 是版本链的身份键，把非法值悄悄改写成别的字符串会让两条本不相关的链
    合并或分叉，错得无声无息。宁可硬拒。
    """
    cid = (raw or "").strip()
    if not cid:
        raise ExecutionError(code=ErrorCode.INPUT_ERROR,
                             message=f"缺少 {field_hint}候选 ID")
    if cid.lower() in ("none", "null"):
        # 宿主把 Python None 字符串化后传进来是最常见的一种错，且后果是**静默**的：
        # 所有这类运行会共用一条名为 "None" 的版本链，把互不相关的 Prompt 混在一起
        raise ExecutionError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"candidate={cid!r} 看起来是被字符串化的空值（宿主常见错误）。"
                    f"候选 ID 必须是 score-prompt 报告里的真实指纹；"
                    f"若想让引擎按正文自动计算，请**留空**而不是传 {cid!r}")
    if not _CANDIDATE_RE.match(cid):
        raise ExecutionError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"candidate={cid!r} 非法：只允许字母/数字/下划线/点/连字符，"
                    f"须以字母或数字开头、长度 ≤64，且不得含路径分隔符（/ 或 \\）。"
                    f"该值会拼进输出路径，未过滤会导致越界写文件")
    return cid


def _cstate(ctx: RunContext, cid: str) -> dict:
    st = ctx.runtime.state_get(f"candidate:{cid}") or {}
    return {
        "route": (st.get("route") or "").upper(),
        "repair_round": int(st.get("repair_round") or 0),
        "regen_round": int(st.get("regen_round") or 0),
        "active_version": st.get("active_version"),
        "rollback_events": list(st.get("rollback_events") or []),
        "excluded_versions": list(st.get("excluded_versions") or []),
        "degraded": bool(st.get("degraded") or False),
        "last_failed_hash": st.get("last_failed_hash") or "",
    }


def _csave(ctx: RunContext, cid: str, st: dict) -> None:
    ctx.runtime.state_set(f"candidate:{cid}", st)


def _versions_dir(ctx: RunContext, cid: str):
    return ctx.runtime.output_dir() / "prompt_versions" / cid


def _load_versions(ctx: RunContext, cid: str) -> list[dict]:
    vdir = _versions_dir(ctx, cid)
    out = []
    if vdir.is_dir():
        for f in sorted(vdir.glob("v*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "version" in data:
                    out.append(data)
            except Exception:
                continue
    return sorted(out, key=lambda v: int(str(v["version"]).lstrip("v")))


def _append_version(ctx: RunContext, cid: str, src: str, fp: str,
                    score: dict, degraded: bool, change_reason: str) -> dict:
    """追加版本快照（INV-D1/D2：append-only；同文本哈希不占新版本号）。
    写失败 → ExecutionError（FAILED 终态，D-014：数据层不降级）。"""
    vdir = _versions_dir(ctx, cid)
    try:
        vdir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ExecutionError(code=ErrorCode.RESOURCE_ERROR,
                             message=f"版本目录不可用：{vdir}（{e}）")
    versions = _load_versions(ctx, cid)
    for old in versions:
        if old.get("text_hash") == fp:
            return {**old, "_reused": True}
    n = len(versions)
    snap = {
        "version": f"v{n}",
        "text_hash": fp,
        "total": score["total"],
        "capability": score["capability"],
        "risk": score["risk"],
        "degraded": degraded,
        "dims": score["dims"],
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "change_reason": change_reason,
    }
    tmp = vdir / f".v{n}.json.tmp"
    try:
        tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(vdir / f"v{n}.json")          # 原子改名，防半截文件（12 §3）
        (vdir / f"v{n}.md").write_text(src.rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        raise ExecutionError(code=ErrorCode.RESOURCE_ERROR,
                             message=f"版本快照写入失败：{e}")
    return snap


def _best_version(versions: list[dict], excluded: list[str]) -> dict | None:
    pool = [v for v in versions if v["version"] not in excluded]
    if not pool:
        return None
    return max(pool, key=lambda v: (int(v["total"]), -int(v["version"].lstrip("v"))))


def step_certify_prompt(ctx: RunContext) -> None:
    """评分 + 复检（D-018）+ 门禁路由（总分/Risk/Gate M/degraded/轮次/回滚）。

    verdict：PASS / REVIEW / ESCALATED（D-022）。FAILED 由 ExecutionError 表达。"""
    src = _source(ctx)
    score = score_prompt(src, _lines(ctx), _rules(ctx).get("lexicon"))
    fp = hashlib.sha256(src.encode("utf-8")).hexdigest()

    # 候选身份（D-019）：显式 --set candidate 优先（跨轮续同一候选）；
    # 否则首次送检文本哈希即候选指纹。显式值必须过 _safe_candidate——它会拼进
    # output/prompt_versions/<cid>/ 与报告文件名，未过滤的 ../ 能逃出 dist_root。
    raw_cid = (ctx.inputs.get("candidate") or "").strip()
    cid = _safe_candidate(raw_cid) if raw_cid else fp[:16]
    st = _cstate(ctx, cid)
    if not st["route"]:
        st["route"] = (ctx.inputs.get("route") or "B").strip().upper()
        st["route"] = st["route"] if st["route"] in ("A", "B") else "B"
    # 降级标志单调置真（D-013：确认降级后随候选传递至 GATE）
    if str(ctx.inputs.get("degraded") or "").strip().lower() in ("true", "1", "是"):
        st["degraded"] = True

    total_ok = score["total"] >= PROMPT_PASS
    risk_ok = score["risk"] >= RISK_PASS
    material_ok = score["material"]["ok"]
    substance_ok = score["substance"]["ok"]

    # 版本快照（每次送检留版本；同文本哈希复用旧版本号，不占新号）
    snap = _append_version(ctx, cid, src, fp, score, st["degraded"],
                           (ctx.inputs.get("change-reason") or "送检").strip() or "送检")

    # 回滚（D-017）：active 指针 = 历史最高非排除版本；降分版本不接管指针并留痕
    versions = _load_versions(ctx, cid)
    best = _best_version(versions, st["excluded_versions"])
    rolled_back = False
    if best and best["version"] != snap["version"]:
        st["rollback_events"].append({
            "from": snap["version"], "to": best["version"],
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        rolled_back = True
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"本版（{snap['version']}，{snap['total']} 分）低于历史最高版 "
            f"（{best['version']}，{best['total']} 分）：已回滚指针，从最高版继续修复（回滚不耗轮次）",
            {"from": snap["version"], "to": best["version"]}))
    if best:
        st["active_version"] = best["version"]

    # 门禁路由
    verdict = "PASS"
    next_action = "deliver"
    if not total_ok or not risk_ok or not material_ok or not substance_ok or st["degraded"]:
        # D-018：先评分 → 不达标 → 查文本哈希（同文本二次仍不达标 → 转人工）
        if fp == st["last_failed_hash"]:
            verdict, next_action = "ESCALATED", "human"
            ctx.issues.append(Issue(
                IssueLevel.REVIEW,
                "同一文本第二次认证仍不达标：定向自修复机会已用完，请人工接管（edit_self）或放弃（reject）",
                {"文本哈希": fp[:12]}))
        elif st["degraded"] and total_ok and risk_ok and material_ok and substance_ok:
            # D-013：降级产物分数再高也只给 REVIEW，不放行
            verdict, next_action = "REVIEW", "material"
            ctx.issues.append(Issue(
                IssueLevel.REVIEW,
                "降级产物（无材料依据，degraded=true）：按 D-013 不得放行，需补材料后重检",
                {"总分": score["total"]}))
        else:
            key = "repair_round" if st["route"] == "B" else "regen_round"
            limit = _ROUND_LIMIT[st["route"]]
            if st[key] >= limit:
                verdict, next_action = "ESCALATED", "human"
                ctx.issues.append(Issue(
                    IssueLevel.REVIEW,
                    f"路线{st['route']} 轮次耗尽（{st[key]}/{limit}）：当前最高版 "
                    f"{st.get('active_version') or '-'}，转人工裁决",
                    {"轮次": st[key], "上限": limit}))
            else:
                st[key] += 1
                verdict, next_action = "REVIEW", "repair" if st["route"] == "B" else "regenerate"
                ctx.issues.append(Issue(
                    IssueLevel.REVIEW,
                    f"Prompt 未达标（轮次 {st[key]}/{limit}），按缺口清单修复后重送",
                    {"缺口条数": len(score["gaps"])}))
        st["last_failed_hash"] = fp
    else:
        st["last_failed_hash"] = ""
        ctx.issues.append(Issue(
            IssueLevel.INFO,
            f"Prompt 质检：达标（可用），缺口 {len(score['gaps'])} 处",
            {"缺口条数": len(score["gaps"])}))
    # Gate M / Risk 轨未过的显式提示（即使总分过线）
    if not risk_ok:
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"Risk 轨 {score['risk']}/46 < {RISK_PASS}：红线/拒答/证据/计算委托不足，"
            "能力强但风险高的 Prompt 不放行（D-010）",
            {"risk": score["risk"], "capability": score["capability"]}))
    if not material_ok:
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            "Gate M：涉及外部事实但未声明材料契约（PD-13）——补第 11 节材料契约后重送",
            {"need_line": score["material"]["need_line"]}))
    if not substance_ok:
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"Gate S：有效内容行数 {score['substance']['effective_lines']} "
            f"< {score['substance']['min']}——关键词堆砌的空壳不放行，请为契约节填写真实内容（D-029）",
            {"effective_lines": score["substance"]["effective_lines"]}))

    _csave(ctx, cid, st)
    ctx.outputs["candidate_id"] = cid
    ctx.outputs["verdict"] = verdict
    ctx.outputs["next_action"] = next_action
    ctx.outputs["score"] = {"total": score["total"], "capability": score["capability"],
                            "risk": score["risk"],
                            "effective_lines": score["substance"]["effective_lines"]}
    ctx.outputs["degraded"] = st["degraded"]
    ctx.outputs["version"] = snap["version"]
    ctx.outputs["active_version"] = st["active_version"]
    ctx.outputs["rolled_back"] = rolled_back
    ctx.outputs["route"] = st["route"]
    ctx.outputs["rounds"] = {"repair": st["repair_round"], "regen": st["regen_round"]}
    # 兼容旧消费面
    ctx.outputs["cert_result"] = "达标" if verdict == "PASS" else "未达标"
    ctx.outputs["cert_fp"] = fp[:12]
    ctx.outputs["gaps_count"] = len(score["gaps"])


def step_render_prompt_cert(ctx: RunContext) -> None:
    rules = _rules(ctx)
    score = score_prompt(_source(ctx), _lines(ctx), rules.get("lexicon"))
    today = time.strftime("%Y-%m-%d_%H%M%S")
    verdict = ctx.outputs.get("verdict", "")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    verdict_cn = {"PASS": "达标（可使用）", "REVIEW": "未达标（修复中/待补材料）",
                  "ESCALATED": "转人工（自修复通道关闭）"}.get(verdict, verdict)
    body = [
        f"# {title} · Prompt 认证报告（体系A） · {today}",
        "",
        f"- 结论：**{verdict_cn}**",
        f"- 候选：{ctx.outputs.get('candidate_id', '')}（路线 {ctx.outputs.get('route', '')}，"
        f"轮次 修复 {ctx.outputs.get('rounds', {}).get('repair', 0)} / 重做 {ctx.outputs.get('rounds', {}).get('regen', 0)}）",
        f"- 总分：{score['total']}/100 ｜ 能力轨 Capability：{score['capability']}/54 ｜ "
        f"风险轨 Risk：{score['risk']}/46（门禁线 {RISK_PASS}）",
        f"- Gate M 材料契约：{'通过' if score['material']['ok'] else '未通过（PD-13）'}"
        f" ｜ Gate S 实质内容：{score['substance']['effective_lines']} 行有效"
        f"{'（达标）' if score['substance']['ok'] else '（<10 行，堆砌空壳不放行）'}"
        f" ｜ 降级标志 degraded：{ctx.outputs.get('degraded', False)}",
        f"- 版本：{ctx.outputs.get('version', '')}（当前指针 active={ctx.outputs.get('active_version', '')}"
        f"{'，本版降分已回滚' if ctx.outputs.get('rolled_back') else ''}）",
        f"- 输入指纹：SHA-256 {ctx.outputs.get('cert_fp', '')}…（已随 last_result 留档）",
        f"- 缺口：{len(score['gaps'])} 处",
        "",
        "## 缺口明细",
        "",
    ]
    body += _fmt_gaps_md(score["gaps"]) or ["（无缺口）"]
    body += [
        "",
        "## 下一步",
        "",
        {"PASS": "可交付使用；版本链见 output/prompt_versions/<候选ID>/。",
         "REVIEW": "把缺口逐条改入原文另存，再跑 `--task score-prompt`"
                   "（同候选续跑加 `--set candidate=<候选ID>`，并写 `--set change-reason=...`）。",
         "ESCALATED": "自修复通道已关闭（同文本复检/轮次耗尽）。请人工接管："
                      "修订需求后重开候选（指针已由系统按降分自动回滚到历史最高版）。"}.get(verdict, ""),
    ]
    # D-030：报告名带候选 ID（跨候选可区分）；同秒重名由 _write_report 防覆盖
    cid_out = ctx.outputs.get("candidate_id", "unknown")
    report = _write_report(ctx.runtime.output_dir(),
                           f"prompt-cert-{cid_out}-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["cert_file"] = str(report)
    ctx.outputs["cert_file_name"] = report.name
    _add_trace_items(ctx, [g["原文"] for g in score["gaps"] if g.get("原文")])
    ctx.outputs["explain"] = {"口径": "体系A 认证判定（双轨+Gate M+轮次）",
                              "结论": ctx.outputs.get("cert_result", ""), "verdict": verdict}


# ---------------------------------------------------------------------------
# 任务 3a/3b：版本链人工干预 / 两版修复对比（D-017 的人工入口）
#
# score-prompt 只做「自动」指针治理：降分版本不接管 active、按历史最高非排除
# 版本继续修。但 SOP 的 ESCALATED 恢复路径需要人工把「目标写错」的版本踢出
# 回滚候选集，也需要量化「这轮修复到底有没有变好」——这两件事此前无任务入口。
# 数据层（_cstate / _load_versions / _best_version / 归档 v{n}.md）本来就在，
# 这里只接线，不新增状态口径。
# ---------------------------------------------------------------------------

def _signed(n: int) -> str:
    """带符号渲染升降值（+3 / -2 / 0），报告表格用。"""
    return f"+{n}" if n > 0 else str(n)


def _known_versions(versions: list[dict]) -> list[str]:
    """版本号列表（_load_versions 已按数值升序，直接取即可，勿再字典序排）。"""
    return [v["version"] for v in versions]


def step_version_control(ctx: RunContext) -> None:
    """版本链查询 / active 指针干预 / 标记不可回滚。

    纯状态操作：不重评分、不新增快照（INV-D1/D2 的 append-only 不受影响）。
    无 --set to / --set exclude 时即只读查询。
    """
    cid = _safe_candidate(ctx.inputs.get("candidate"))
    versions = _load_versions(ctx, cid)
    if not versions:
        raise ExecutionError(
            code=ErrorCode.INPUT_ERROR,
            message=f"候选 {cid} 无版本快照（output/prompt_versions/{cid}/ 不存在或为空）；"
                    f"先跑 score-prompt 建档")

    st = _cstate(ctx, cid)
    order = _known_versions(versions)
    to_v = (ctx.inputs.get("to") or "").strip()
    exclude_v = (ctx.inputs.get("exclude") or "").strip()
    changed: list[str] = []

    if exclude_v:
        if exclude_v not in order:
            raise ExecutionError(code=ErrorCode.VALIDATION_ERROR,
                                 message=f"exclude={exclude_v} 不在候选 {cid} 的版本链中"
                                         f"（可用：{', '.join(order)}）")
        if exclude_v not in st["excluded_versions"]:
            st["excluded_versions"].append(exclude_v)
            changed.append(f"标记 {exclude_v} 不可回滚（踢出回滚候选集）")

    if to_v:
        if to_v not in order:
            raise ExecutionError(code=ErrorCode.VALIDATION_ERROR,
                                 message=f"to={to_v} 不在候选 {cid} 的版本链中"
                                         f"（可用：{', '.join(order)}）")
        if to_v in st["excluded_versions"]:
            raise ExecutionError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"{to_v} 已被标记为不可回滚，不能设为 active 指针；"
                        f"当前排除集：{', '.join(st['excluded_versions'])}")
        if st["active_version"] != to_v:
            st["rollback_events"].append({
                "from": st["active_version"], "to": to_v,
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "by": "manual",
            })
            st["active_version"] = to_v
            changed.append(f"active 指针 → {to_v}（人工指定）")

    # 排除后重算指针：被排除的版本若正占着 active，必须让位给次高的非排除版本，
    # 否则「踢出回滚集」只是记账，下一次 score-prompt 仍按 _best_version 落回它。
    if exclude_v and st["active_version"] in st["excluded_versions"]:
        best = _best_version(versions, st["excluded_versions"])
        st["active_version"] = best["version"] if best else None
        changed.append(f"active 指针因排除重算 → {st['active_version'] or '（无非排除版本）'}")

    if changed:
        _csave(ctx, cid, st)
    else:
        ctx.issues.append(Issue(IssueLevel.INFO,
                                f"候选 {cid} 版本链只读查询，未做任何变更"))

    excluded = set(st["excluded_versions"])
    ctx.outputs["candidate_id"] = cid
    ctx.outputs["version_count"] = len(versions)
    ctx.outputs["versions"] = [
        {
            "version": v["version"], "total": v["total"],
            "capability": v["capability"], "risk": v["risk"],
            "degraded": bool(v["degraded"]), "ts": v["ts"],
            "change_reason": v["change_reason"],
            "excluded": v["version"] in excluded,
            "is_active": v["version"] == st["active_version"],
        }
        for v in versions
    ]
    ctx.outputs["active_version"] = st["active_version"]
    ctx.outputs["excluded_versions"] = list(st["excluded_versions"])
    ctx.outputs["route"] = st["route"]
    ctx.outputs["rounds"] = {"repair": st["repair_round"], "regen": st["regen_round"]}
    ctx.outputs["version_changed"] = changed
    ctx.outputs["explain"] = {"口径": "版本链查询 / active 指针人工干预（D-017）",
                              "变更": changed or ["（只读查询，无变更）"],
                              "active": st["active_version"] or ""}


def step_render_version_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    cid = ctx.outputs["candidate_id"]
    rounds = ctx.outputs.get("rounds", {})
    body = [
        f"# {title} · 版本链 · {cid} · {today}",
        "",
        f"- 当前 active 指针：**{ctx.outputs.get('active_version') or '（无）'}**",
        f"- 路线 {ctx.outputs.get('route', '') or '（未定）'} ｜ 轮次 "
        f"修复 {rounds.get('repair', 0)} / 重做 {rounds.get('regen', 0)}",
        f"- 不可回滚标记：{', '.join(ctx.outputs['excluded_versions']) or '（无）'}",
        f"- 本次变更：{'；'.join(ctx.outputs['version_changed']) or '（只读查询，无变更）'}",
        "",
        "## 版本链（append-only；active = 历史最高分的非排除版本）",
        "",
        "| 版本 | 总分 | 能力轨 | 风险轨 | 降级 | 排除 | active | 时间 | 说明 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for v in ctx.outputs["versions"]:
        body.append(
            f"| {v['version']} | {v['total']} | {v['capability']} | {v['risk']} "
            f"| {'是' if v['degraded'] else '否'} | {'是' if v['excluded'] else '—'} "
            f"| {'◀' if v['is_active'] else '—'} | {v['ts']} | {v['change_reason']} |")
    body += [
        "",
        "## 怎么用",
        "",
        "- 只读查询：`--task prompt-version --set candidate=" + cid + "`",
        "- 人工指定指针：追加 `--set to=vN`（不得指向已排除版本）",
        "- 把走错的版本踢出回滚候选集：追加 `--set exclude=vN`"
        "（若它正占着 active，指针会立即重算到次高的非排除版本）",
        "- 目标写错而非写得不好时：先 `exclude` 掉错误版本，再用 "
        "`--task score-prompt --set route=A` 从 0 重做（重做上限 2 轮）",
    ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"version-{cid}-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["version_report_file"] = str(report)
    ctx.outputs["version_report_file_name"] = report.name


def step_delta_compare(ctx: RunContext) -> None:
    """两版修复对比：总分 / 双轨 / 8 维升降 + 缺口增减 + 字符量 Δ。纯只读。

    口径分工（快照里有什么就用什么，不臆造）：
      - 总分 / 能力轨 / 风险轨 / 8 维 → 取**归档快照**，即当时认证的真实结论；
      - 缺口明细 / 字符量 → 快照未存，按归档正文 `v{n}.md` 以**当前评分器**重算；
      - 重算总分与归档总分不一致 → 显性 WARN。这是评分器已漂移的信号：
        归档分数是历史事实，重算分数是今天的口径，两者对不上说明词表/权重/闸门
        自那以后变过。缺口按「维度」聚合增减——Prompt 缺口模型没有 P0 分级
        （P0/P1/P2 只属于 harvest-case 的 Gold Case risk_level）。
    """
    cid = _safe_candidate(ctx.inputs.get("candidate"))
    versions = _load_versions(ctx, cid)
    if len(versions) < 2:
        raise ExecutionError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"候选 {cid} 只有 {len(versions)} 个版本快照，无法对比（需 ≥2 版）；"
                    f"再送检一次 score-prompt 即产生新版本")

    by_id = {v["version"]: v for v in versions}
    order = _known_versions(versions)
    to_v = (ctx.inputs.get("to") or "").strip() or order[-1]
    from_v = (ctx.inputs.get("from") or "").strip() or order[-2]
    for tag, ver in (("from", from_v), ("to", to_v)):
        if ver not in by_id:
            raise ExecutionError(code=ErrorCode.VALIDATION_ERROR,
                                 message=f"{tag}={ver} 不在候选 {cid} 的版本链中"
                                         f"（可用：{', '.join(order)}）")
    if from_v == to_v:
        raise ExecutionError(code=ErrorCode.VALIDATION_ERROR,
                             message=f"from 与 to 同为 {from_v}，无可对比（缺省为 次新→最新）")

    vdir = _versions_dir(ctx, cid)
    lex = _rules(ctx).get("lexicon")
    arms: dict[str, dict] = {}
    for tag, ver in (("from", from_v), ("to", to_v)):
        md = vdir / f"{ver}.md"
        if not md.is_file():
            raise ExecutionError(
                code=ErrorCode.RESOURCE_ERROR,
                message=f"版本 {ver} 的归档正文缺失：{md}——快照在但正文不在，"
                        f"无法重算缺口与字符量")
        src = md.read_text(encoding="utf-8", errors="replace")
        arms[tag] = {"version": ver, "snap": by_id[ver], "src": src,
                     "chars": len(src), "score": score_prompt(src, src.splitlines(), lex)}

    a, b = arms["from"], arms["to"]
    sa, sb = a["snap"], b["snap"]

    # 评分器漂移自检：重算总分 ≠ 归档总分
    drift = []
    for arm in (a, b):
        re_total = arm["score"]["total"]
        if re_total != arm["snap"]["total"]:
            drift.append({"version": arm["version"], "archived": arm["snap"]["total"],
                          "recomputed": re_total})
    if drift:
        detail = "；".join(f"{d['version']} 归档 {d['archived']} → 重算 {d['recomputed']}"
                           for d in drift)
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"评分器已漂移：{detail}。归档分数是当时的认证事实，重算是今天的口径；"
            f"本报告分数列取归档值，缺口列取重算值，两者口径不同不可直接相减",
            {"drift": drift}))

    def _gap_by_dim(score: dict) -> dict:
        out: dict[str, int] = {}
        for g in score["gaps"]:
            out[g["维度"]] = out.get(g["维度"], 0) + 1
        return out

    ga, gb = _gap_by_dim(a["score"]), _gap_by_dim(b["score"])
    dims_delta = {d: sb["dims"].get(d, 0) - sa["dims"].get(d, 0) for d in sb["dims"]}

    ctx.outputs["trace_check"] = {"source": a["src"] + "\n" + b["src"], "items": []}
    _add_trace_items(ctx, [g["原文"] for g in a["score"]["gaps"] + b["score"]["gaps"]
                           if g.get("原文")])

    ctx.outputs["candidate_id"] = cid
    ctx.outputs["delta_from"] = from_v
    ctx.outputs["delta_to"] = to_v
    ctx.outputs["delta"] = {
        "total": sb["total"] - sa["total"],
        "capability": sb["capability"] - sa["capability"],
        "risk": sb["risk"] - sa["risk"],
        "dims": dims_delta,
        "gaps": {d: gb.get(d, 0) - ga.get(d, 0) for d in sorted(set(ga) | set(gb))},
        "gap_count": len(b["score"]["gaps"]) - len(a["score"]["gaps"]),
        "chars": b["chars"] - a["chars"],
    }
    ctx.outputs["delta_endpoints"] = {
        tag: {
            "version": arm["version"], "total": arm["snap"]["total"],
            "capability": arm["snap"]["capability"], "risk": arm["snap"]["risk"],
            "dims": arm["snap"]["dims"], "chars": arm["chars"],
            "gap_count": len(arm["score"]["gaps"]),
            "gaps_by_dim": _gap_by_dim(arm["score"]),
            "degraded": bool(arm["snap"]["degraded"]),
            "change_reason": arm["snap"]["change_reason"], "ts": arm["snap"]["ts"],
        }
        for tag, arm in (("from", a), ("to", b))
    }
    ctx.outputs["delta_drift"] = drift
    ctx.outputs["delta_improved"] = (sb["total"] - sa["total"]) > 0
    ctx.outputs["explain"] = {
        "口径": "两版修复对比（分数取归档快照，缺口/字符量按归档正文重算）",
        "结论": ("改善" if sb["total"] > sa["total"]
                 else "退步" if sb["total"] < sa["total"] else "总分持平"),
        "from": from_v, "to": to_v,
        "总分Δ": _signed(sb["total"] - sa["total"]),
    }


def step_render_delta_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    cid = ctx.outputs["candidate_id"]
    d = ctx.outputs["delta"]
    ep = ctx.outputs["delta_endpoints"]
    f_, t_ = ep["from"], ep["to"]
    body = [
        f"# {title} · 修复对比（Repair Improvement Delta） · {today}",
        "",
        f"- 候选：{cid}",
        f"- 对比：**{f_['version']}**（{f_['ts']}，{f_['change_reason']}） → "
        f"**{t_['version']}**（{t_['ts']}，{t_['change_reason']}）",
        f"- 结论：**总分 {_signed(d['total'])}**（{f_['total']} → {t_['total']}），"
        f"{'本轮修复有效' if ctx.outputs['delta_improved'] else '本轮修复未提分'}",
        "",
        "## 双轨升降",
        "",
        "| 口径 | " + f_["version"] + " | " + t_["version"] + " | Δ |",
        "|---|---|---|---|",
        f"| 总分 | {f_['total']} | {t_['total']} | {_signed(d['total'])} |",
        f"| 能力轨 Capability | {f_['capability']} | {t_['capability']} "
        f"| {_signed(d['capability'])} |",
        f"| 风险轨 Risk（门禁线 {RISK_PASS}） | {f_['risk']} | {t_['risk']} "
        f"| {_signed(d['risk'])} |",
        f"| 字符量 | {f_['chars']} | {t_['chars']} | {_signed(d['chars'])} |",
        f"| 缺口数（重算） | {f_['gap_count']} | {t_['gap_count']} "
        f"| {_signed(d['gap_count'])} |",
        "",
        "## 8 维升降（归档快照口径）",
        "",
        "| 维度 | " + f_["version"] + " | " + t_["version"] + " | Δ |",
        "|---|---|---|---|",
    ]
    for dim, delta in d["dims"].items():
        body.append(f"| {dim} | {f_['dims'].get(dim, 0)} | {t_['dims'].get(dim, 0)} "
                    f"| {_signed(delta)} |")
    body += [
        "",
        "## 缺口增减（按维度，当前评分器重算）",
        "",
        "> Prompt 缺口模型无 P0 分级（P0/P1/P2 只属于 harvest-case 的 Gold Case "
        "risk_level），故按维度报增减。",
        "",
        "| 维度 | " + f_["version"] + " | " + t_["version"] + " | Δ |",
        "|---|---|---|---|",
    ]
    gaps_delta = d["gaps"]
    for dim in sorted(set(f_["gaps_by_dim"]) | set(t_["gaps_by_dim"]) | set(gaps_delta)):
        body.append(f"| {dim} | {f_['gaps_by_dim'].get(dim, 0)} "
                    f"| {t_['gaps_by_dim'].get(dim, 0)} | {_signed(gaps_delta.get(dim, 0))} |")
    if not gaps_delta:
        body.append("| （两版均无缺口） | 0 | 0 | 0 |")
    if ctx.outputs["delta_drift"]:
        body += [
            "",
            "## ⚠ 评分器漂移",
            "",
            "以下版本按当前评分器重算的总分与归档快照不一致——说明词表/权重/闸门"
            "自该版认证后发生过变更。分数列取归档值（历史事实），缺口列取重算值"
            "（今天口径），两者不可直接相减。",
            "",
        ]
        for x in ctx.outputs["delta_drift"]:
            body.append(f"- {x['version']}：归档 {x['archived']} → 重算 {x['recomputed']}")
    body += [
        "",
        "## 下一步",
        "",
        "- 提分且仍 <80：继续按认证报告缺口逐条改，同候选续跑 "
        "`--task score-prompt --set candidate=" + cid + " --set change-reason=...`",
        "- 未提分或退步：本轮改写方向可能错了。用 `--task prompt-version --set candidate="
        + cid + "` 看版本链，必要时 `--set exclude=vN` 把走错的版本踢出回滚候选集",
        "- 任意两版对比：追加 `--set from=vX --set to=vY`（缺省 次新→最新）",
    ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"delta-{cid}-{ctx.outputs['delta_from']}-"
                           f"{ctx.outputs['delta_to']}-{today}.md",
                           "\n".join(body) + "\n")
    ctx.outputs["delta_report_file"] = str(report)
    ctx.outputs["delta_report_file_name"] = report.name


# ---------------------------------------------------------------------------
# 任务 2：按描述新建 Prompt（标准骨架）
# ---------------------------------------------------------------------------

def step_load_brief(ctx: RunContext) -> None:
    brief = (ctx.inputs.get("task-brief") or "").strip()
    extra = (ctx.inputs.get("extra-requirements") or "").strip()
    if not brief:
        ctx.issues.append(Issue(IssueLevel.ERROR, "任务描述为空，无法生成骨架"))
        return
    src = brief + ("\n" + extra if extra else "")
    ctx.outputs["trace_check"] = {"source": src, "items": []}
    ctx.outputs["brief_chars"] = len(brief)


def step_assemble_draft(ctx: RunContext) -> None:
    try:
        tpl = ctx.runtime.read_template("prompt_skeleton.tpl")
    except FileNotFoundError:
        ctx.issues.append(Issue(IssueLevel.ERROR, "缺 templates/prompt_skeleton.tpl（装配资产丢失）"))
        return
    brief = (ctx.inputs.get("task-brief") or "").strip()
    extra = (ctx.inputs.get("extra-requirements") or "").strip()
    filled = tpl.replace("{{BRIEF}}", brief).replace("{{EXTRA}}", extra or "（无附加要求）")
    today = time.strftime("%Y-%m-%d_%H%M%S")
    draft = _write_report(ctx.runtime.output_dir(), f"draft-prompt-{today}.md", filled + "\n")
    slots = re.findall(r"【待填[:：]([^】]*)】", filled)
    ctx.outputs["draft_file"] = str(draft)
    ctx.outputs["draft_file_name"] = draft.name
    # SKILL.md 承诺「会返回 candidate_id（指纹前16位），后续 score-prompt 用
    # --set candidate=<该 ID> 沿用，修复历史才不会断」——此前并未实现，宿主拿不到
    # 这个 ID，draft → 修复 → 认证 的版本链就无从续接（prompt-version / delta-report
    # 也就无从对齐）。用 read_file_auto **回读落盘文件**再算，与 score-prompt 的
    # _source() 同一读取口径，保证两个任务对同一份骨架算出同一个指纹。
    ctx.outputs["candidate_id"] = _candidate_id(read_file_auto(str(draft)))
    ctx.outputs["slot_count"] = len(slots)
    ctx.outputs["slot_list"] = slots[:20]  # 只留口径级清单，长列表进报告
    ctx.issues.append(Issue(
        IssueLevel.INFO,
        f"标准骨架已生成，{len(slots)} 处【待填】槽位由宿主/人工补全后送 score-prompt；"
        f"候选 ID = {ctx.outputs['candidate_id']}，补全后送检须带 "
        f"--set candidate={ctx.outputs['candidate_id']} 才能续上版本链"))
    _add_trace_items(ctx, [ln for ln in brief.splitlines() if ln.strip()][:10])


def step_render_draft_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    slots = ctx.outputs.get("slot_list") or []
    body = [
        f"# {title} · 新建指引 · {today}",
        "",
        f"- 骨架文件：`{ctx.outputs.get('draft_file', '')}`",
        f"- 待填槽位：{ctx.outputs.get('slot_count', 0)} 个",
        f"- **候选 ID：`{ctx.outputs.get('candidate_id', '')}`**"
        "（补全后送检必须带上它，否则版本链会断成新候选）",
        "",
        "## 槽位清单",
        "",
    ]
    body += [f"{i}. {s}" for i, s in enumerate(slots, 1)] or ["（模板未含【待填】槽——按模板正文补齐各节）"]
    body += ["", "填完后整体送 `score-prompt` 认证；**不要**为了凑词表硬塞关键词——评分看的是契约实质。",
             "", "送检命令（务必带候选 ID，版本链才连续）：", "",
             "```",
             "python engine/main.py run --scenario prompt_skill --task score-prompt <填好的骨架> \\",
             f"    --set candidate={ctx.outputs.get('candidate_id', '<上面那个候选 ID>')} \\",
             "    --set change-reason=按骨架逐槽填写",
             "```"]
    report = _write_report(ctx.runtime.output_dir(), f"draft-guide-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["draft_guide_file"] = str(report)
    ctx.outputs["draft_guide_file_name"] = report.name
    ctx.outputs["explain"] = {"口径": "骨架装配（明文模板）", "槽位数": ctx.outputs.get("slot_count", 0)}


# ---------------------------------------------------------------------------
# 任务 4：封装为 Skill（AWP 目录装配）
# ---------------------------------------------------------------------------

_NET_PRESETS = {
    "无网络·只读工作区": ("读取：本技能目录与被处理文件所在的工作区目录（只读）",
                          "写入：仅本技能目录下的 output/ 与 storage/",
                          "网络：无外连"),
    "无网络·读写工作区": ("读取：本技能目录与被处理文件所在的工作区目录",
                          "写入：工作区内对应输出目录（不触碰系统目录）",
                          "网络：无外连"),
    "允许联网": ("读取：本技能目录与授权的工作区目录",
                 "写入：仅本技能目录下的 output/ 与 storage/",
                 "网络：允许外连——联网目标域名须宿主与用户单独审查"),
}


def step_precheck_build(ctx: RunContext) -> None:
    score = score_prompt(_source(ctx), _lines(ctx), _rules(ctx).get("lexicon"))
    passed = score["total"] >= PROMPT_PASS
    ctx.outputs["build_precheck"] = "达标" if passed else "未达标"
    if not passed:
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"Prompt 未经/未达体系A认证（缺口 {len(score['gaps'])} 处）仍要求封装："
            "产物会标注『未经认证』，ship-skill 将拒绝交付",
        ))
    name = (ctx.inputs.get("skill-name") or "").strip()
    if not _KEBAB.match(name):
        ctx.issues.append(Issue(IssueLevel.REVIEW,
                                f"skill-name 不是 kebab-case（{name!r}）：装配会清洗之，认证时 B1 按清洗后名判"))
    net = (ctx.inputs.get("net-policy") or "").strip()
    if net == "允许联网":
        ctx.issues.append(Issue(IssueLevel.REVIEW, "所选权限含联网——这是敏感项，请人工确认（三键）"))


def step_assemble_awp(ctx: RunContext) -> None:
    raw = _source(ctx)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    name = re.sub(r"[^a-z0-9-]+", "-", (ctx.inputs.get("skill-name") or "").strip().lower()).strip("-")
    if not name:
        name = "unnamed-skill"
    title_line = re.sub(r"^#+\s*", "", lines[0])[:60] if lines else "未命名技能"
    desc = (ctx.inputs.get("one-liner") or "").strip() or f"封装《{title_line}》为可调起的技能"

    out_root = ctx.runtime.output_dir() / "skills"
    root = out_root / name
    if root.exists():
        root = out_root / f"{name}-{time.strftime('%H%M%S')}"

    precheck_ok = ctx.outputs.get("build_precheck") == "达标"
    net = (ctx.inputs.get("net-policy") or "").strip()
    r_read, r_write, r_net = _NET_PRESETS.get(net, _NET_PRESETS["无网络·只读工作区"])

    skill_md = "\n".join([
        "---",
        f"name: {name}",
        f'description: "{desc}"',
        "user-invocable: true",
        "---",
        "",
        f"# {title_line}",
        "",
        "## 何时使用",
        "",
        f"当用户请求与下述任务说明的输入契约匹配时调起本技能。服务对象与上下文见正文。（{'已通过体系A认证' if precheck_ok else '⚠ 未经认证封装，先跑 score-prompt 补认证'}）",
        "",
        "## 使用方法（SOP）",
        "",
        "严格按以下提示词执行，输入输出契约不得偏离：",
        "",
        "```",
        raw.rstrip(),
        "```",
        "",
        "## 不要做什么",
        "",
        "- 依据不足时不得编造：按正文的拒答/存疑协议处理并标注",
        "- 不得跳过正文声明的输出格式自行排版",
        "- 不得自评质量：结论可使用时以本包 `score-skill` 认证报告为准",
        "",
    ])
    _write(root, "SKILL.md", skill_md)
    _write(root, "PERMISSIONS.txt", "\n".join([
        "# 权限透明声明（人类与宿主双层审查）",
        "",
        f"- {r_read}",
        f"- {r_write}",
        f"- {r_net}",
        "",
    ]) + "\n")
    _write(root / "config", "source-prompt.md", raw.rstrip() + "\n")

    seeds_raw = None
    try:
        seeds_raw = ctx.runtime.read_template("seed_testcases.json")
    except FileNotFoundError as exc:
        # 种子模板缺席走通用占位路径:留痕不阻断(种子后续由 B5 硬闸把关)
        print(f"[degraded] seed_testcases.json 读取失败,走通用种子: {exc!r}", file=sys.stderr)
    written_cases = []
    if seeds_raw:
        # 用【按稿生成】的领域种子取代通用占位种子（D-0xx）：从源 Prompt 正文
        # 提取输出字段/形态/红线/存疑协议生成实质断言，避免纯 nonempty 被 B5『空转未测』。
        try:
            generic = json.loads(seeds_raw)
        except Exception:
            generic = []
        from .gen_seed import build_seed_cases

        auto = build_seed_cases(raw)
        seeds = auto if auto else generic
        for i, case in enumerate(seeds, 1):
            if not isinstance(case, dict):
                continue
            cat = case.get("category", "happy")
            cid = case.get("case_id") or f"case_{i:02d}_{cat}"
            case = dict(case)
            case["case_id"] = cid
            _write(root / "testcases", f"{cid}.json", json.dumps(case, ensure_ascii=False, indent=2) + "\n")
            written_cases.append(cid)
    else:
        ctx.issues.append(Issue(IssueLevel.WARN, "缺 seed_testcases.json：装配出的包无测试矩阵，B4/B5 必不达标"))
    _write(root / "storage" / "responses", ".gitkeep", "")

    ctx.outputs["bundle_dir"] = str(root)
    ctx.outputs["bundle_name"] = name
    ctx.outputs["case_count"] = len(written_cases)
    # 溯源条目必须是原文行（desc/标题可能来自表单输入，不是 source 的子串）
    _add_trace_items(ctx, lines[:5])


def step_render_build_report(ctx: RunContext) -> None:
    from pathlib import Path

    rules = _rules(ctx)
    root = Path(ctx.outputs["bundle_dir"])
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    files = _bundle_files(root)
    body = [
        f"# {title} · 封装报告 · {today}",
        "",
        f"- 技能目录：`{root}`",
        f"- 预检（体系A）：{ctx.outputs.get('build_precheck', '')}",
        f"- 文件清单（{len(files)} 个）：",
        "",
    ]
    body += [f"  - `{rel}` sha256:{_sha256_file(p)[:12]}…" for rel, p in files]
    body += [
        "",
        "## 下一步（宿主 SOP）",
        "",
        "1. **升级断言**：种子的 `nonempty` 只是占位。逐个用例按技能说明书把 `asserts`",
        "   改成具体预期（`contains:` 关键字段 / `regex:` 结构 / `not-contains:` 禁语）。",
        "   体系B 的 B5 是硬闸：**只要还有用例停留在纯 nonempty，就判『空转未测』直接不达标**，",
        "   ship-skill 也会因无认证记录而拒发——这是「被测过不能是假的」的产品承诺。",
        "2. 逐条执行 `testcases/` 用例：把用例 `input` 作为用户输入、按本包 SKILL.md 实际执行；",
        "3. 把每次响应**原样**存为 `storage/responses/<case_id>.txt`（文件名 = 用例 case_id）；",
        f"4. 跑 `--task score-skill --set skill-file={root / 'SKILL.md'}` 做体系B认证；",
        "5. 达标后用 `--task ship-skill` 打包——未认证/认证后改动都会被闸门拒绝。",
    ]
    report = _write_report(ctx.runtime.output_dir(), f"build-report-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["build_report_file"] = str(report)
    ctx.outputs["build_report_file_name"] = report.name
    ctx.outputs["explain"] = {"口径": "AWP 目录装配", "文件数": len(files)}


# ---------------------------------------------------------------------------
# 任务 5：Skill 质量认证（体系 B + 矩阵断言）
# ---------------------------------------------------------------------------

def step_load_skill(ctx: RunContext) -> None:
    from pathlib import Path

    skill_md = Path(str(ctx.inputs["skill-file"]))
    root = skill_md.parent
    if not (root / "SKILL.md").is_file():
        ctx.issues.append(Issue(IssueLevel.ERROR,
                                f"输入路径所在目录缺 SKILL.md，不是技能包：{root}"))
        return
    raw = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    if not raw.strip():
        ctx.issues.append(Issue(IssueLevel.ERROR, "SKILL.md 是空的"))
        return
    ctx.outputs["skill_dir"] = str(root)
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    bundle = _load_bundle(root)
    ctx.outputs["case_count"] = len(bundle["cases"])
    resp_dir = root / "storage" / "responses"
    ctx.outputs["response_count"] = len(list(resp_dir.glob("*.txt"))) if resp_dir.is_dir() else 0


def step_assert_matrix(ctx: RunContext) -> None:
    """主路径：逐用例断言响应。响应目录缺失 -> 抛错，由引擎降级到结构自检
    （fallback 成功会标 DEGRADED 并自动压 REVIEW——降级不算可用）。"""
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])
    resp_dir = root / "storage" / "responses"
    if not resp_dir.is_dir() or not list(resp_dir.glob("*.txt")):
        raise ExecutionError(code=ErrorCode.INPUT_ERROR,
                             message="storage/responses/ 缺失或为空：宿主尚未回填任何用例响应")
    bundle = _load_bundle(root)
    score = score_skill(bundle)
    ctx.outputs["matrix_asserted"] = len(bundle["cases"]) - score["no_response_cases"] \
        - len(score["failed_case_ids"])
    if score["no_response_cases"]:
        ctx.issues.append(Issue(IssueLevel.WARN,
                                f"{score['no_response_cases']} 个用例缺响应文件（B6 按未通过计）"))


def step_assert_matrix_degraded(ctx: RunContext) -> None:
    """降级路径：结构自检（B1-B5），B6 记 0。"""
    from pathlib import Path

    bundle = _load_bundle(Path(ctx.outputs["skill_dir"]))
    ctx.outputs["matrix_degraded"] = True
    ctx.outputs["matrix_asserted"] = 0
    ctx.issues.append(Issue(IssueLevel.WARN,
                            f"结构自检口径：用例 {len(bundle['cases'])} 个，响应 0 份（B6=0）"))


def step_certify_skill(ctx: RunContext) -> None:
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])
    bundle = _load_bundle(root)
    score = score_skill(bundle)
    issues = skill_issues(score, certify=True)
    if ctx.outputs.get("matrix_degraded") and score["passed"]:
        score["passed"] = False
        issues.append(Issue(IssueLevel.REVIEW,
                            "矩阵断言为降级自检（未收响应），本次不能判『可用』——补齐后重跑"))
    ctx.issues.extend(issues)
    ctx.outputs["skill_cert_result"] = "达标" if score["passed"] else "未达标"
    ctx.outputs["gaps_count"] = len(score["gaps"])


def step_render_skill_cert(ctx: RunContext) -> None:
    from pathlib import Path

    rules = _rules(ctx)
    root = Path(ctx.outputs["skill_dir"])
    bundle = _load_bundle(root)
    score = score_skill(bundle)
    # 降级否决（与 step_certify_skill 同口径）：未收响应 = 不能判可用 = 不写认证
    degraded = bool(ctx.outputs.get("matrix_degraded"))
    if degraded and score["passed"]:
        score["passed"] = False
    fp = _bundle_fp(root)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    body = [
        f"# {title} · Skill 认证报告（体系B） · {today}",
        "",
        f"- 结论：**{'达标（可使用）' if score['passed'] else '未达标（进入人审，不可交付）'}**"
        + ("（DEGRADED：结构自检）" if degraded else ""),
        f"- 包指纹：{fp[:12]}…（ship 时复算，认证后改动即失效）",
        f"- 用例：{len(bundle['cases'])} 个，响应：{len(bundle['responses'])} 份，"
        f"断言未通过：{len(score['failed_case_ids'])} 个",
        "",
        "## 文件清单",
        "",
    ]
    body += [f"- `{rel}` sha256:{_sha256_file(p)[:12]}…" for rel, p in _bundle_files(root)]
    body += ["", "## 缺口明细", ""]
    body += _fmt_gaps_md(score["gaps"]) or ["（无缺口）"]
    report = _write_report(ctx.runtime.output_dir(), f"skill-cert-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["skill_cert_file"] = str(report)
    ctx.outputs["skill_cert_file_name"] = report.name

    if score["passed"]:
        _write(root / "config", "cert_ref.txt",
               f"fp={fp}\nts={today}\ntask=score-skill\n")
        ctx.runtime.state_set("skill_cert", {"dir": root.name, "fp": fp,
                                             "ts": time.strftime("%Y-%m-%d"),
                                             "degraded": False})
    ctx.outputs["explain"] = {"口径": "体系B 认证判定", "结论": ctx.outputs.get("skill_cert_result", ""),
                              "降级": degraded}


# ---------------------------------------------------------------------------
# 任务 6：打包交付（认证闸门 + 目录交付 + manifest）
# ---------------------------------------------------------------------------

def step_verify_ship_gate(ctx: RunContext) -> None:
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])
    ref_path = root / "config" / "cert_ref.txt"
    reason = ""
    ref_fp = ""
    if not ref_path.is_file():
        reason = "未找到认证记录（config/cert_ref.txt）——必须先跑 score-skill 并达标"
    else:
        for ln in ref_path.read_text(encoding="utf-8").splitlines():
            if ln.startswith("fp="):
                ref_fp = ln[3:].strip()
        if not ref_fp:
            reason = "认证记录缺指纹字段"
        elif ref_fp != _bundle_fp(root):
            reason = "认证后包内容有改动，认证作废——重新跑 score-skill"
    if reason:
        ctx.outputs["ship_gate"] = "refused"
        ctx.outputs["ship_refuse_reason"] = reason
        ctx.issues.append(Issue(IssueLevel.REVIEW, f"交付闸门拒绝：{reason}"))
    else:
        ctx.outputs["ship_gate"] = "ok"
        ctx.issues.append(Issue(IssueLevel.INFO, "交付闸门放行：指纹与认证记录一致"))


def _case_passed(case: dict, response) -> bool:
    """用例在指定响应下是否全断言通过（断言形式非法 None 按未通过计）。"""
    if response is None:
        return False
    asserts = case.get("asserts") or []
    return bool(asserts) and all(
        evaluate_assert(a, response) is True for a in asserts)


def step_replay_regression(ctx: RunContext) -> None:
    """ship 前回归重放（D-026，机制 12）：同名技能最近历史版本中「通过」的用例，
    用旧断言评新版本响应；任何 PASS→非 PASS（含用例/响应缺失）= 回归 → 拒发。
    无历史版本时重放为空，不拦截。本步只读，不改任何包内容。"""
    from pathlib import Path

    if ctx.outputs.get("ship_gate") != "ok":
        return  # 指纹闸门已拒，无需重放
    root = Path(ctx.outputs["skill_dir"])

    # 基线版本 = output/skills/ 下同基名（剥掉 -HHMMSS 后缀）的最近一个其它目录
    m = re.match(r"^(.*?)(-\d{6})?$", root.name)
    base = m.group(1) if m else root.name
    siblings = []
    skills_dir = root.parent
    if skills_dir.is_dir():
        for d in skills_dir.iterdir():
            if d.is_dir() and d != root and (d / "SKILL.md").is_file():
                dm = re.match(r"^(.*?)(-\d{6})?$", d.name)
                if dm and dm.group(1) == base:
                    siblings.append(d)
    if not siblings:
        ctx.outputs["regression"] = {"baseline": None, "replayed": 0, "regressed": []}
        ctx.issues.append(Issue(IssueLevel.INFO,
                                "回归重放：无同名历史版本，跳过（首次交付）"))
        return
    baseline = max(siblings, key=lambda d: d.stat().st_mtime)

    old = _load_bundle(baseline)
    new = _load_bundle(root)
    new_cases = {c.get("case_id"): c for c in new["cases"]}
    new_resp = new["responses"]

    replayed, regressed = 0, []
    for oc in old["cases"]:
        cid = oc.get("case_id")
        if not cid:
            continue
        if not _case_passed(oc, old["responses"].get(cid)):
            continue  # 旧版本就没通过的不在回归保护范围
        replayed += 1
        if cid not in new_cases:
            regressed.append(f"{cid}（用例已删除）")
        elif cid not in new_resp:
            regressed.append(f"{cid}（新版本缺响应）")
        elif not _case_passed(oc, new_resp[cid]):  # 旧断言 × 新响应
            regressed.append(cid)

    ctx.outputs["regression"] = {"baseline": baseline.name,
                                 "replayed": replayed, "regressed": regressed}
    if regressed:
        ctx.outputs["ship_gate"] = "refused"
        ctx.outputs["ship_refuse_reason"] = (
            f"回归重放失败：{len(regressed)}/{replayed} 个旧版本通过用例在新版本上不再通过"
            f"（基线 {baseline.name}）：{', '.join(regressed[:5])}"
            + ("…" if len(regressed) > 5 else ""))
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"交付闸门拒绝：{ctx.outputs['ship_refuse_reason']}——"
            "若是刻意行为变更，请升级旧用例断言后重认证；否则回退改动（D-026）",
            {"baseline": baseline.name, "replayed": replayed,
             "regressed": len(regressed)}))
    else:
        ctx.issues.append(Issue(
            IssueLevel.INFO,
            f"回归重放通过：{replayed} 个旧版本通过用例在新版本响应上全部保持"
            f"（基线 {baseline.name}）"))


def step_finalize_delivery(ctx: RunContext) -> None:
    """交付定稿（不打包 zip）：把 AWP 目录本身作为交付单元，另出 manifest.json
    （逐文件 SHA-256 + 包指纹 + 认证记录），收包方按清单逐文件复算即可验真。
    指纹闸门未放行时不产出任何交付物。"""
    from pathlib import Path

    if ctx.outputs.get("ship_gate") != "ok":
        return
    root = Path(ctx.outputs["skill_dir"])
    name = root.name
    today = time.strftime("%Y-%m-%d_%H%M%S")
    out_dir = ctx.runtime.output_dir()
    files = _bundle_files(root)
    manifest = {
        "skill": name,
        "delivery": "directory",
        "bundle_fp": _bundle_fp(root),
        "file_count": len(files),
        "files": [
            {"path": rel, "size": p.stat().st_size, "sha256": _sha256_file(p)}
            for rel, p in files
        ],
        "cert": ctx.runtime.state_get("skill_cert") or {},
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    mpath = _write(out_dir, f"{name}-{today}-manifest.json",
                   json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    ctx.outputs["ship_dir"] = str(root)
    ctx.outputs["ship_dir_name"] = name
    ctx.outputs["ship_manifest_file"] = str(mpath)
    ctx.outputs["ship_manifest_file_name"] = mpath.name
    ctx.outputs["ship_fingerprint"] = manifest["bundle_fp"][:12]


def step_render_ship_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    body = [f"# {title} · 交付报告 · {today}", ""]
    if ctx.outputs.get("ship_gate") != "ok":
        reason = ctx.outputs.get("ship_refuse_reason", "闸门拒绝")
        body += [f"- 本次未交付。原因：{reason}", ""]
        if "回归重放" in reason:
            body.append("若是**刻意行为变更**：升级旧用例断言并重新跑 score-skill 认证；否则回退改动后重跑 ship-skill。")
        else:
            body.append("按 SKILL.md 的 SOP 补齐认证后重跑 ship-skill。")
    else:
        body += [
            f"- 交付目录：`{ctx.outputs.get('ship_dir', '')}`",
            f"- 包指纹（前 12 位）：{ctx.outputs.get('ship_fingerprint', '')}…（全量见 manifest）",
            f"- 验真清单：`{ctx.outputs.get('ship_manifest_file', '')}`",
        ]
        reg = ctx.outputs.get("regression") or {}
        if reg.get("baseline"):
            body.append(
                f"- 回归重放：{reg['replayed']} 个旧版本通过用例全部保持"
                f"（基线 {reg['baseline']}，D-026）")
        body += [
            "",
            "收包方可脱离本引擎复算：对交付目录逐文件 SHA-256 对照 manifest 即可验真。",
        ]
    report = _write_report(ctx.runtime.output_dir(), f"ship-report-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["ship_report_file"] = str(report)
    ctx.outputs["ship_report_file_name"] = report.name
    ctx.outputs["explain"] = {"口径": "ship 闸门结果", "gate": ctx.outputs.get("ship_gate", "")}


# ---------------------------------------------------------------------------
# 任务 7：飞轮沉淀（M2-P3，REVIEW 案例回流 Gold Set，D-027 / 机制 13）
# ---------------------------------------------------------------------------

_HARVEST_CATEGORIES = ("happy", "edge", "adversarial", "refusal", "conflict")
_HARVEST_P0 = ("adversarial", "refusal", "conflict")   # P0 类：默认 P0 风险 + verdict 必填
_HARVEST_VERDICTS = ("PASS", "REVIEW", "FAIL", "REJECT", "UNKNOWN")
_GOLD_ORIGINS = ("seed", "human_feedback", "failure_case")   # gold_case.schema.json 的 origin 枚举


def _approve_case(*, case_input: str, category: str, asserts: list[str],
                  verdict: str, risk: str, existing: list[dict],
                  input_hint: str = "--set case-input=",
                  verdict_hint: str = "--set verdict=") -> str | None:
    """Gold Case 审批规则（D-027）——**harvest-case 与 import-cases 共用同一套**。

    返回 None = 通过；返回字符串 = 拒绝理由。规则内容与判定顺序刻意与单条沉淀
    逐字一致，保证「批量导入」不会比「单条沉淀」宽松——两处各写一遍必然漂移
    （《Knowledge 目录重组指南》§七.3：代码行为不双写）。

      ① 至少一条实质断言（纯 nonempty = 空转占位，拒绝）
      ② 同技能内 input 文本哈希去重（existing 由调用方给，批量时含本批已收案例）
      ③ P0 类（adversarial/refusal/conflict）必须显式 verdict ≠ UNKNOWN
      ④ risk_level 缺省按类别推导（P0 类→P0，其余→P1），由调用方在传入前完成
    """
    if not case_input:
        return f"缺 {input_hint}（当时喂给技能的真实输入）"
    if category not in _HARVEST_CATEGORIES:
        return f"category 必须是：{' / '.join(_HARVEST_CATEGORIES)}"
    bad_asserts = [a for a in asserts if evaluate_assert(a, "") is None]
    if bad_asserts:
        return f"断言形式非法：{bad_asserts[:3]}（仅支持 nonempty / contains: / not-contains: / regex:）"
    if not any(_assert_substantive(a) for a in asserts):
        return ("审批规则①：至少一条实质断言（contains:/not-contains:/regex:）——"
                "飞轮案例禁止纯 nonempty 空转占位")
    if verdict not in _HARVEST_VERDICTS:
        return f"verdict 必须是：{' / '.join(_HARVEST_VERDICTS)}"
    if category in _HARVEST_P0 and verdict == "UNKNOWN":
        return f"审批规则③：{category} 是 P0 类，必须显式 {verdict_hint}（PASS/REVIEW/FAIL/REJECT）"
    if risk not in ("P0", "P1", "P2"):
        return "risk-level 必须是：P0 / P1 / P2"
    fp_in = hashlib.sha256(case_input.encode("utf-8")).hexdigest()
    for c in existing:
        if hashlib.sha256(str(c.get("input", "")).encode("utf-8")).hexdigest() == fp_in:
            return f"审批规则②：相同 input 的案例已存在（{c.get('case_id')}），不重复沉淀"
    return None


def _next_gold_num(tc_dir) -> int:
    """gold_NNN 递增编号（harvest-case 与 import-cases 共用）。"""
    nums = [int(m.group(1)) for f in tc_dir.glob("gold_*.json")
            if (m := re.match(r"gold_(\d+)$", f.stem))]
    return max(nums, default=0) + 1


def step_harvest_case(ctx: RunContext) -> None:
    """把真实 REVIEW/失败案例沉淀为 Gold Case（origin=human_feedback）。

    审批规则（D-027，引擎强制，不过即 ERROR/FAILED）：
      ① 至少一条实质断言（纯 nonempty = 空转占位，拒绝）
      ② 同技能内 input 文本哈希去重
      ③ P0 类（adversarial/refusal/conflict）必须显式 verdict ≠ UNKNOWN
      ④ risk_level 缺省按类别推导（P0 类→P0，其余→P1）
    沉淀即改包指纹 → 认证自动作废（复用既有指纹闸门，交付前必须重跑 score-skill）。
    """
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])

    def _err(msg: str) -> None:
        ctx.issues.append(Issue(IssueLevel.ERROR, msg))

    case_input = (ctx.inputs.get("case-input") or "").strip()
    category = (ctx.inputs.get("category") or "").strip()
    error_type = (ctx.inputs.get("error-type") or "").strip()
    actual = (ctx.inputs.get("actual") or "").strip()
    verdict = (ctx.inputs.get("verdict") or "").strip().upper() or "UNKNOWN"
    risk = (ctx.inputs.get("risk-level") or "").strip().upper() \
        or ("P0" if category in _HARVEST_P0 else "P1")
    label = f"人工回流案例（{category}）"
    note = (ctx.inputs.get("note") or "").strip()

    raw_asserts = [a.strip() for a in (ctx.inputs.get("asserts") or "").split("||") if a.strip()]
    reject = _approve_case(case_input=case_input, category=category, asserts=raw_asserts,
                           verdict=verdict, risk=risk, existing=_load_bundle(root)["cases"])
    if reject:
        _err(reject)
        return

    tc_dir = root / "testcases"
    cid = f"gold_{_next_gold_num(tc_dir):03d}"

    case = {
        "case_id": cid,
        "category": category,
        "label": label,
        "input": case_input,
        "expected": {"verdict": verdict, "review_required": verdict == "REVIEW"},
        "asserts": raw_asserts,
        "origin": "human_feedback",
        "risk_level": risk,
    }
    if error_type or note:
        case["note"] = "；".join(x for x in
                                (f"error_type={error_type}" if error_type else "", note) if x)
    _write(tc_dir, f"{cid}.json", json.dumps(case, ensure_ascii=False, indent=2) + "\n")

    # 飞轮日志（§2.4：记录 {expected, actual, error_type}，供后续筛选/Benchmark）
    log_path = root / "storage" / "feedback_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "case_id": cid,
            "category": category, "error_type": error_type, "verdict": verdict,
            "actual": actual, "asserts": raw_asserts,
        }, ensure_ascii=False) + "\n")

    ctx.outputs["harvested_case"] = case
    ctx.outputs["harvested_case_id"] = cid
    ctx.issues.append(Issue(
        IssueLevel.INFO,
        f"案例已沉淀为 {cid}（origin=human_feedback，{category}/{risk}，verdict={verdict}）",
        {"case_id": cid}))
    ctx.issues.append(Issue(
        IssueLevel.WARN,
        "沉淀已改动包内容：原认证作废——交付前必须重跑 score-skill 重认证"
        "（指纹闸门会拒绝旧认证发货，这是飞轮的天然审批闸）"))


def step_render_harvest_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    case = ctx.outputs.get("harvested_case") or {}
    if not case:
        return  # 前步已 ERROR
    body = [
        f"# {title} · 飞轮沉淀报告 · {today}",
        "",
        f"- 技能包：`{ctx.outputs.get('skill_dir', '')}`",
        f"- 新案例：**{case.get('case_id', '')}**（{case.get('category', '')} / "
        f"{case.get('risk_level', '')} / origin=human_feedback）",
        f"- 期望结论：{case.get('expected', {}).get('verdict', '')}",
        f"- 断言：{'、'.join(f'`{a}`' for a in case.get('asserts', []))}",
        "",
        "## 案例原文",
        "",
        "```",
        case.get("input", ""),
        "```",
        "",
        "## 下一步",
        "",
        "1. 对该 input 重跑技能，把响应存为 `storage/responses/" + case.get("case_id", "") + ".txt`",
        "2. 重跑 `score-skill` 重认证（沉淀已改动包指纹，旧认证作废）",
        "3. 认证达标后 `ship-skill` 会先做回归重放再打包",
    ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"harvest-report-{case.get('case_id', 'case')}-{today}.md",
                           "\n".join(body) + "\n")
    ctx.outputs["harvest_report_file"] = str(report)
    ctx.outputs["harvest_report_file_name"] = report.name
    ctx.outputs["explain"] = {"口径": "REVIEW 案例回流 Gold Set（D-027）",
                              "case_id": case.get("case_id", "")}


# ---------------------------------------------------------------------------
# 任务 7b：Gold Case 批量导入（让 benchmark 的 D-028 门槛**可达**）
#
# benchmark 的启用门槛是 Gold Set ≥30 例（BENCH_ELIGIBLE_MIN），而 build-skill 只产
# 5 个种子、harvest-case 每次沉淀 1 个 —— 靠单条沉淀要人工跑约 25 次才可能让
# benchmark 产出结论，实测下它恒返回 NOT_ELIGIBLE。解法是让 30 例**可达**，
# 不是把门槛调低：门槛是 A.7「反空转」的刻意设计，AP-11 要求结论必须回连 Gate，
# 不产「仅供参考」的平均分。
#
# 审批规则复用 _approve_case（与 harvest-case 同一套，不双写），批量不比单条宽松。
# ---------------------------------------------------------------------------

def step_import_cases(ctx: RunContext) -> None:
    """按 cases-file 批量导入 Gold Case，逐条走 harvest-case 的同一套审批规则。

    cases-file 是一个 JSON 数组，每个元素一个案例对象：
      必填 input / category / asserts（数组或 "||" 分隔字符串）
      P0 类（adversarial/refusal/conflict）必须给 expected.verdict 或 verdict
      可选 risk_level（缺省按类别推导）、origin（缺省 human_feedback）、
           label、note、error_type、case_id（缺省自动 gold_NNN 递增）
    被拒的案例逐条给理由、不写入；**只要有 1 例通过就算成功**（部分导入），
    0 例通过才 FAILED——本任务会改动技能包，与只读诊断任务不同。
    """
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])
    tc_dir = root / "testcases"
    try:
        payload = json.loads(read_file_auto(ctx.inputs["cases-file"]))
    except Exception as exc:  # noqa: BLE001 —— 用户给的文件，任何解析异常都要说清是哪一步
        ctx.issues.append(Issue(IssueLevel.ERROR, f"cases-file 不是合法 JSON：{exc}"))
        return
    if not isinstance(payload, list):
        ctx.issues.append(Issue(
            IssueLevel.ERROR,
            "cases-file 顶层必须是**数组**（每个元素一个案例对象）；只导入一条请用 harvest-case"))
        return
    if not payload:
        ctx.issues.append(Issue(IssueLevel.ERROR, "cases-file 是空数组，没有可导入的案例"))
        return

    existing = _load_bundle(root)["cases"]
    accepted: list[dict] = []
    rejected: list[dict] = []
    num = _next_gold_num(tc_dir)

    for i, raw in enumerate(payload):
        where = f"cases[{i}]"
        if not isinstance(raw, dict):
            rejected.append({"at": where, "case_id": "",
                             "reason": "不是对象（每个元素须为一个案例 JSON 对象）"})
            continue
        supplied_id = str(raw.get("case_id") or "").strip()
        case_input = str(raw.get("input") or "").strip()
        category = str(raw.get("category") or "").strip()
        a_raw = raw.get("asserts")
        if isinstance(a_raw, str):
            asserts = [a.strip() for a in a_raw.split("||") if a.strip()]
        elif isinstance(a_raw, list):
            asserts = [str(a).strip() for a in a_raw if str(a).strip()]
        else:
            asserts = []
        verdict = str((raw.get("expected") or {}).get("verdict")
                      or raw.get("verdict") or "").strip().upper() or "UNKNOWN"
        risk = str(raw.get("risk_level") or raw.get("risk-level") or "").strip().upper() \
            or ("P0" if category in _HARVEST_P0 else "P1")
        origin = str(raw.get("origin") or "").strip() or "human_feedback"
        if origin not in _GOLD_ORIGINS:
            rejected.append({"at": where, "case_id": supplied_id,
                             "reason": f"origin 必须是：{' / '.join(_GOLD_ORIGINS)}"})
            continue
        # 去重必须把**本批已收**的也算进去：只看包内既有案例的话，
        # 同一份文件里两条相同 input 会双双通过——这是批量特有、单条沉淀遇不到的坑
        reject = _approve_case(case_input=case_input, category=category, asserts=asserts,
                               verdict=verdict, risk=risk, existing=existing + accepted,
                               input_hint=f"{where}.input",
                               verdict_hint=f"{where}.expected.verdict")
        if reject:
            rejected.append({"at": where, "case_id": supplied_id, "reason": reject})
            continue

        cid = supplied_id
        if cid:
            if not re.match(r"^(case|gold)_[0-9]+[a-z0-9_]*$", cid):
                rejected.append({"at": where, "case_id": cid,
                                 "reason": "case_id 不符合 gold_case.schema.json 的 pattern "
                                           "^(case|gold)_[0-9]+[a-z0-9_]*$"})
                continue
            if (tc_dir / f"{cid}.json").is_file() \
                    or any(str(c.get("case_id")) == cid for c in existing + accepted):
                rejected.append({"at": where, "case_id": cid,
                                 "reason": "case_id 已存在，拒绝覆盖（append-only）"})
                continue
        else:
            cid = f"gold_{num:03d}"
            num += 1

        case = {
            "case_id": cid,
            "category": category,
            "label": str(raw.get("label") or f"批量导入案例（{category}）"),
            "input": case_input,
            "expected": {"verdict": verdict, "review_required": verdict == "REVIEW"},
            "asserts": asserts,
            "origin": origin,
            "risk_level": risk,
        }
        note = str(raw.get("note") or "").strip()
        err_type = str(raw.get("error_type") or "").strip()
        if supplied_id and supplied_id != cid:
            note = "；".join(x for x in (f"原 case_id={supplied_id}", note) if x)
        if err_type or note:
            case["note"] = "；".join(x for x in
                                    (f"error_type={err_type}" if err_type else "", note) if x)
        _write(tc_dir, f"{cid}.json", json.dumps(case, ensure_ascii=False, indent=2) + "\n")
        accepted.append(case)

    if not accepted:
        ctx.issues.append(Issue(
            IssueLevel.ERROR,
            f"批量导入 0/{len(payload)} 例通过审批，**未改动技能包**。"
            f"首条拒绝理由：{rejected[0]['reason'] if rejected else '（无）'}"))
        return

    # 飞轮日志：与 harvest-case 同一份 jsonl，同样只记元数据、不记响应内容
    log_path = root / "storage" / "feedback_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        for c in accepted:
            fh.write(json.dumps({
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "case_id": c["case_id"],
                "category": c["category"], "error_type": "",
                "verdict": c["expected"]["verdict"], "actual": "",
                "asserts": c["asserts"], "via": "import-cases",
            }, ensure_ascii=False) + "\n")

    total_now = len(existing) + len(accepted)
    ctx.outputs["import_total"] = len(payload)
    ctx.outputs["import_accepted"] = [c["case_id"] for c in accepted]
    ctx.outputs["import_rejected"] = rejected
    ctx.outputs["import_case_count"] = total_now
    ctx.outputs["import_bench_eligible"] = total_now >= BENCH_ELIGIBLE_MIN

    ctx.issues.append(Issue(
        IssueLevel.INFO,
        f"批量导入 {len(accepted)}/{len(payload)} 例通过审批，Gold Set 现有 {total_now} 例"
        f"（benchmark 门槛 {BENCH_ELIGIBLE_MIN}）",
        {"accepted": ctx.outputs["import_accepted"]}))
    if rejected:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"{len(rejected)} 例被审批规则拒绝、未写入（逐条理由见报告）——"
            f"批量导入与单条沉淀走同一套规则，不会更宽松"))
    if not ctx.outputs["import_bench_eligible"]:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"Gold Set {total_now} 例仍 < {BENCH_ELIGIBLE_MIN}，benchmark 仍会返回 "
            f"NOT_ELIGIBLE。门槛是 A.7「反空转」的刻意设计（AP-11 要求结论回连 Gate），"
            f"请继续补充真实案例，**不要调低门槛**"))
    ctx.issues.append(Issue(
        IssueLevel.WARN,
        "导入已改动包内容：原认证作废——交付前必须重跑 score-skill 重认证"
        "（指纹闸门会拒绝旧认证发货）"))
    ctx.outputs["explain"] = {
        "口径": "Gold Case 批量导入（审批规则与 harvest-case 共用 _approve_case）",
        "通过": len(accepted), "拒绝": len(rejected),
        "Gold Set": total_now, "达到 benchmark 门槛": ctx.outputs["import_bench_eligible"],
    }


def step_render_import_report(ctx: RunContext) -> None:
    from pathlib import Path

    if not ctx.outputs.get("import_accepted") and not ctx.outputs.get("import_rejected"):
        return                                  # 前步已 ERROR，没有可报的
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    acc = ctx.outputs.get("import_accepted") or []
    rej = ctx.outputs.get("import_rejected") or []
    total_now = ctx.outputs.get("import_case_count", 0)
    body = [
        f"# {title} · Gold Case 批量导入报告 · {today}",
        "",
        f"- 技能包：`{ctx.outputs.get('skill_dir', '')}`",
        f"- 提交 {ctx.outputs.get('import_total', 0)} 例 ｜ 通过 **{len(acc)}** ｜ 拒绝 {len(rej)}",
        f"- Gold Set 现有 **{total_now}** 例（benchmark 门槛 {BENCH_ELIGIBLE_MIN}）"
        f" → {'**已达门槛，benchmark 可产出结论**' if ctx.outputs.get('import_bench_eligible') else '仍不足，benchmark 会返回 NOT_ELIGIBLE'}",
        "",
        "## 已通过并写入 testcases/",
        "",
    ]
    body += [f"- `{c}`" for c in acc] or ["（无）"]
    if rej:
        body += ["", "## 被拒案例（逐条理由）", "",
                 "| 位置 | 声称的 case_id | 拒绝理由 |", "|---|---|---|"]
        body += [f"| {r['at']} | {r.get('case_id') or '—'} | {r['reason']} |" for r in rej]
    body += [
        "",
        "## 下一步",
        "",
        "1. 用 `--task plan-responses` 取响应回填作业单（新增案例也要回填响应）",
        "2. 逐条执行被测技能，把原样响应存为 `storage/responses/<case_id>.txt`",
        "3. 重跑 `--task score-skill` 重认证（导入已改动包指纹，旧认证作废）",
        f"4. Gold Set ≥{BENCH_ELIGIBLE_MIN} 且响应齐备后，`--task benchmark` 才会产出 "
        f"Gate 判定而非 NOT_ELIGIBLE",
    ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"import-cases-{Path(ctx.outputs.get('skill_dir', '')).name}-{today}.md",
                           "\n".join(body) + "\n")
    ctx.outputs["import_report_file"] = str(report)
    ctx.outputs["import_report_file_name"] = report.name


# ---------------------------------------------------------------------------
# 任务 6b：响应回填作业单与体检（SOP 第 5 行那个人工步骤的管道支持）
#
# 边界（不可越）：B6「严禁模型自评」+「引擎零 LLM 调用」决定了响应内容只能由
# 宿主/人执行被测技能后回填。本任务**不生成、不评判、不修改任何响应内容**，
# 只做两件确定性的事：产出作业单（该跑什么、存到哪个文件名）、体检回填结果
# （漏填 / 空文件 / 孤儿文件名 / 非 .txt / 用例 JSON 损坏）。
# 此前 score-skill 只给一个 response_count 计数，宿主把文件名填错或漏填都无从发现，
# 于是体系B 整条尾巴（认证→交付→benchmark）长期卡在 DEGRADED 上而看不出卡在哪。
# ---------------------------------------------------------------------------

def step_plan_responses(ctx: RunContext) -> None:
    """回填体检：把「响应齐不齐、齐在哪、缺在哪」变成逐条可执行的清单。

    outputs 轻量纪律：只回写计数与 case_id 列表，**不回写 input 原文**——
    原文只进报告文件（同 step_render_fix_report 的处置），否则几十例原文会灌进
    last_result.json，正是 docstring 点名的大文档 token 地雷。
    """
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])
    bundle = _load_bundle(root)
    cases = bundle["cases"]
    resp_dir = root / "storage" / "responses"

    ids = [str(c.get("case_id", "")) for c in cases]
    idset = set(ids)

    on_disk: dict[str, list] = {}
    non_txt: list[str] = []
    if resp_dir.is_dir():
        for p in sorted(resp_dir.iterdir()):
            if not p.is_file() or p.name.startswith("."):
                continue
            if p.suffix.lower() != ".txt":
                non_txt.append(p.name)          # 只认 .txt，与 _load_bundle 同口径
                continue
            on_disk.setdefault(p.stem, []).append(p)

    def _all_blank(paths: list) -> bool:
        return all(not p.read_text(encoding="utf-8", errors="replace").strip()
                   for p in paths)

    filled = [i for i in ids if i in on_disk and not _all_blank(on_disk[i])]
    empty = [i for i in ids if i in on_disk and _all_blank(on_disk[i])]
    missing = [i for i in ids if i not in on_disk]
    orphan = sorted(n for n in on_disk if n not in idset)
    bad_json = int(bundle.get("bad_json") or 0)

    ctx.outputs["resp_total_cases"] = len(cases)
    ctx.outputs["resp_filled"] = filled
    ctx.outputs["resp_missing"] = missing
    ctx.outputs["resp_empty"] = empty
    ctx.outputs["resp_orphan"] = orphan
    ctx.outputs["resp_non_txt"] = non_txt
    ctx.outputs["resp_bad_case_json"] = bad_json
    ctx.outputs["resp_dir_exists"] = bool(resp_dir.is_dir())
    ctx.outputs["resp_complete"] = bool(cases) and not (missing or empty or orphan
                                                        or non_txt or bad_json)

    # 本步骤是**只读诊断**，一律用 WARN 不用 ERROR：引擎在步骤收尾时
    # `_has(issues, ERROR)` 成立即判 FAILED（workflow.py L297），而诊断任务
    # FAILED 会让宿主当成基础设施错误、并且抑制作业单渲染——恰恰是发现问题时
    # 最需要那份清单。发现多少问题都该 DONE 返回，把结论交给 issue 与报告。
    if not cases:
        ctx.issues.append(Issue(IssueLevel.WARN,
                                "技能包内没有任何用例（testcases/ 为空或全部损坏），"
                                "无响应可回填——先跑 build-skill 生成种子用例"))
        return
    if bad_json:
        # 损坏的用例 JSON 会被 _load_bundle 静默跳过，于是它既不在 case_count 里、
        # 也不会被当成"漏填"——不显式说出来，宿主只会看到一个对不上的计数
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"testcases/ 下有 {bad_json} 个用例 JSON 解析失败，已被跳过（不计入用例数）："
            f"这些用例既不会参与矩阵断言，也不会出现在下面的漏填清单里，请先修好 JSON"))
    if missing:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"待回填 {len(missing)}/{len(cases)} 例：{', '.join(missing[:8])}"
            f"{' 等' if len(missing) > 8 else ''}——作业单见报告，逐条执行后存为 "
            f"storage/responses/<case_id>.txt",
            {"missing": missing}))
    if empty:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"已存在但内容为空 {len(empty)} 例：{', '.join(empty[:8])}"
            f"{' 等' if len(empty) > 8 else ''}——空响应会被当成未回填，不计入通过率"))
    if orphan:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"孤儿响应文件 {len(orphan)} 个（文件名对不上任何 case_id，不会被任何用例消费）："
            f"{', '.join(orphan[:8])}{' 等' if len(orphan) > 8 else ''}"
            f"——多半是文件名拼错或用例已改名，请核对 storage/responses/"))
    if non_txt:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"非 .txt 文件 {len(non_txt)} 个（引擎只读 .txt）：{', '.join(non_txt[:8])}"
            f"{' 等' if len(non_txt) > 8 else ''}——请另存为 <case_id>.txt"))
    if ctx.outputs["resp_complete"]:
        ctx.issues.append(Issue(
            IssueLevel.INFO,
            f"响应回填齐备（{len(filled)}/{len(cases)} 例）：可以跑 score-skill 做体系B 认证，"
            f"不会降级为结构自检"))

    ctx.outputs["explain"] = {
        "口径": "响应回填体检（引擎不生成也不评判响应内容，B6 严禁模型自评）",
        "已回填": len(filled), "待回填": len(missing),
        "空文件": len(empty), "孤儿文件": len(orphan),
        "非txt": len(non_txt), "用例JSON损坏": bad_json,
        "齐备": ctx.outputs["resp_complete"],
    }


def step_render_response_plan(ctx: RunContext) -> None:
    """产出作业单：每个用例该跑什么 input、断言是什么、响应存到哪个文件名。

    这里才回读用例原文（step_plan_responses 刻意没往 outputs 里塞），
    与 step_render_prompt_cert 重跑 score_prompt 同一套路。
    """
    from pathlib import Path

    if not ctx.outputs.get("resp_total_cases"):
        return                                  # 前步已 ERROR，没有作业单可出
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    root = Path(ctx.outputs["skill_dir"])
    cases = _load_bundle(root)["cases"]
    filled = set(ctx.outputs.get("resp_filled") or [])
    empty = set(ctx.outputs.get("resp_empty") or [])

    body = [
        f"# {title} · 响应回填作业单 · {today}",
        "",
        f"- 技能包：`{root}`",
        f"- 用例 {ctx.outputs['resp_total_cases']} 例 ｜ 已回填 {len(filled)} ｜ "
        f"待回填 {len(ctx.outputs.get('resp_missing') or [])} ｜ "
        f"空文件 {len(empty)}",
        f"- 回填齐备：**{'是' if ctx.outputs.get('resp_complete') else '否'}**",
        "",
        "## 怎么做（引擎不会替你做——B6 严禁模型自评）",
        "",
        "1. 逐条把下面的 `input` **原样**喂给被测技能（不要改写、不要补全、不要提示它期望什么）",
        "2. 把技能的**原样响应**存为 `storage/responses/<case_id>.txt`（UTF-8，后缀必须 .txt）",
        "3. 全部回填后重跑 `--task score-skill` 做体系B 认证",
        "",
        "> 文件名必须与 `case_id` 完全一致：填错名字会变成「孤儿文件」，"
        "既不计入通过率、也看不出是哪条用例缺响应。",
        "",
    ]
    if ctx.outputs.get("resp_bad_case_json"):
        body += [f"⚠ testcases/ 下有 {ctx.outputs['resp_bad_case_json']} 个用例 JSON 解析失败"
                 f"（已被跳过，不在下表内），请先修好再回填。", ""]
    for c in cases:
        cid = str(c.get("case_id", ""))
        state = "已回填" if cid in filled else ("空文件" if cid in empty else "待回填")
        asserts = list(c.get("asserts") or [])
        subst = any(_assert_substantive(a) for a in asserts)
        body += [
            f"### {cid} · {c.get('category', '')} · {c.get('risk_level', '')} · 【{state}】",
            "",
            f"- 目标文件：`storage/responses/{cid}.txt`",
            f"- 期望结论：{(c.get('expected') or {}).get('verdict', '') or '（未声明）'}"
            f" ｜ origin：{c.get('origin', '')}",
            f"- 断言：{'、'.join(f'`{a}`' for a in asserts) or '（无）'}"
            + ("" if subst else "  ⚠ **纯 nonempty 属空转占位，B5 硬闸会判不达标**"),
            f"- 说明：{c.get('label', '') or c.get('note', '') or '—'}",
            "",
            "输入原文（原样喂给技能）：",
            "",
            "```",
            str(c.get("input", "")),
            "```",
            "",
        ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"response-plan-{root.name}-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["resp_plan_file"] = str(report)
    ctx.outputs["resp_plan_file_name"] = report.name


# ---------------------------------------------------------------------------
# 任务 8：Gold Set 指标引擎（Benchmark，机制 10，D-028 启用门槛 Gold Set ≥30 例）
# ---------------------------------------------------------------------------
# 设计边界（SSOT 质量工程层设计 v1 §3「不做」→ owner 2026-09-07 授权启动）：
#  · 引擎零 LLM 调用，只对技能包内 Gold Case 做确定性统计；
#  · AP-11：结论必须回连 Gate，不产「仅供参考」的平均分——输出达标/不达标判定；
#  · FAR/CAR 需要「应拒答的正例」ground truth + 真实响应，无响应时降级为
#    断言可执行率与覆盖度（可回测性），并把 FAR/CAR 标注为「需响应后启用」（嵌入提示，不硬造）。

BENCH_ELIGIBLE_MIN = 30          # A.7：Gold Set ≥30 例才产指标（对齐 KB rules v1.2）
_BENCH_CATS = ("happy", "edge", "adversarial", "refusal", "conflict")


def _bench_analyze(bundle: dict) -> dict:
    """确定性统计技能包 Gold Case。返回各维度聚合 + gate 判定。"""
    from collections import Counter
    cases = bundle.get("cases") or []
    responses = bundle.get("responses") or {}

    by_cat = Counter()
    by_origin = Counter()
    by_risk = Counter()
    n_substantive = 0        # 至少一条实质断言（非纯 nonempty）
    n_illegal = 0            # 断言形式非法（B5 缺陷）
    n_has_resp = 0           # 匹配到响应文件
    n_pass = 0               # has_resp 且全断言通过
    empty_asserts = 0
    abstain_tot = 0    # 应拒答正例（REJECT/REVIEW verdict）且有响应数
    abstain_ok = 0     # 其中正确拒答数（断言在响应上满足）

    for c in cases:
        cat = c.get("category") or "?"
        by_cat[cat] += 1
        by_origin[c.get("origin") or "?"] += 1
        by_risk[c.get("risk_level") or "?"] += 1
        asserts = c.get("asserts") or []
        if not asserts:
            empty_asserts += 1
        sub = [a for a in asserts if _assert_substantive(a)]
        flag = [a for a in asserts if evaluate_assert(a, "") is None]
        if sub:
            n_substantive += 1
        if flag:
            n_illegal += 1

        cid = c.get("case_id") or ""
        resp = responses.get(cid)
        if resp is not None:
            n_has_resp += 1
            # 有响应就用实质断言判定（纯 nonempty 判定无意义，不算通过）
            if sub and compute_resp_passed(c, resp, asserts):
                n_pass += 1

    n = len(cases)
    # —— 可回测性（是 FAR/CAR 的前提：没断言/没响应谈不上「假放」） ——
    substantive_rate = (n_substantive / n) if n else 0.0
    has_resp_rate = (n_has_resp / n) if n else 0.0
    illegal_rate = (n_illegal / n) if n else 0.0

    # —— Gate 判定（AP-11 回连 Gate，防空转/防噪音） ——
    eligible = n >= BENCH_ELIGIBLE_MIN
    cat_ok = all(c in by_cat and by_cat.get(c, 0) >= 1 for c in _BENCH_CATS) \
        if n else False              # 五类齐备（机制 7）
    substantive_ok = n_substantive >= int(0.8 * n)   # B5 精神：≥80% 有实质断言
    legal_ok = illegal_rate <= 0.05                  # 断言行形式 95% 合法
    ready = eligible and cat_ok and substantive_ok and legal_ok

    # —— FAR/CAR（风险轨，到数才报）：应拒答正例必须显式 verdict=REJECT/REVIEW 且有响应 ——
    # FAR（虚假保证率）= 应答拒答却放行 / 应拒答有响应；CAR（正确拒答率）= 1 - FAR。
    # 应拒答正例的断言表达「应出现拒答/存疑信号」，断言满足 = 正确拒答，失败 = 虚假放行。
    abstain_note = (
        "FAR/CAR 需『应拒答正例』（expected.verdict=REJECT/REVIEW 且断言含拒答/存疑信号）"
        "+ 真实响应样本。请回填 refusal/adversarial/conflict 类响应的 `storage/responses/` "
        "后重跑。当前该样本集为空——本指标已在可回测性维度给出判据，不硬造数值。"
    )
    for c in cases:
        cid = c.get("case_id") or ""
        resp = responses.get(cid)
        if resp is None:
            continue
        ver = (c.get("expected") or {}).get("verdict")
        if ver not in ("REJECT", "REVIEW"):
            continue  # 非应拒答正例（happy/PASS）不参与 FAR/CAR
        abstain_tot += 1
        sub = [a for a in (c.get("asserts") or []) if _assert_substantive(a)]
        if sub and all(evaluate_assert(a, resp) is True for a in sub):
            abstain_ok += 1
    far = None
    car = None
    if abstain_tot:
        car = round(abstain_ok / abstain_tot, 3)
        far = round(1 - car, 3)
        abstain_note = (
            f"FAR（虚假保证率）={far}，CAR（正确拒答率）={car}："
            f"在 {abstain_tot} 例应拒答正例（REJECT/REVIEW，有响应）中，"
            f"{abstain_ok} 例正确拒答，{abstain_tot - abstain_ok} 例被虚假放行。")

    return {
        "total_cases": n,
        "eligible": eligible,
        "eligible_min": BENCH_ELIGIBLE_MIN,
        "category_dist": dict(by_cat),
        "origin_dist": dict(by_origin),
        "risk_dist": dict(by_risk),
        "categories_complete": cat_ok,
        "substantive_rate": round(substantive_rate, 3),
        "has_resp_rate": round(has_resp_rate, 3),
        "illegal_assert_rate": round(illegal_rate, 3),
        "n_has_resp": n_has_resp,
        "n_pass": n_pass,
        "empty_assert_cases": empty_asserts,
        "ready": ready,
        "far": far,
        "car": car,
        "abstain_positive": abstain_tot,
        "abstain_ok": abstain_ok,
        "metric_note": abstain_note,
    }


def compute_resp_passed(case: dict, response: str, asserts: list | None = None) -> bool:
    """实质断言全过才算 passed（纯 nonempty 不构成『通过』，防空转）。"""
    asserts = asserts if asserts is not None else (case.get("asserts") or [])
    substantive = [a for a in asserts if _assert_substantive(a)]
    if not substantive:
        return False
    return all(evaluate_assert(a, response) is True for a in substantive)


def step_benchmark(ctx: RunContext) -> None:
    """Gold Set 指标引擎：对已 build 的技能包做确定性统计与 Gate 判定。"""
    from pathlib import Path
    root = Path(ctx.outputs["skill_dir"])
    bundle = _load_bundle(root)

    if not bundle["cases"]:
        ctx.issues.append(Issue(IssueLevel.ERROR,
                                "技能包 testcases/ 为空：没有 Gold Set 可测。先 build-skill 或 harvest-case"))
        return
    r = _bench_analyze(bundle)
    ctx.outputs["benchmark"] = r

    if not r["eligible"]:
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"Benchmark 未达可测门槛：Gold Set {r['total_cases']} 例 < {r['eligible_min']}（A.7）。"
            "指标引擎不产结论（反空转）。请 harvest 攒足 30 例。"))
        return
    if not r["ready"]:
        detail = []
        if not r["categories_complete"]:
            detail.append("五类未齐备")
        if r["substantive_rate"] < 0.8:
            detail.append(f"实质断言率 {r['substantive_rate']} < 80%")
        if r["illegal_assert_rate"] > 0.05:
            detail.append(f"非法断言 {r['illegal_assert_rate']} > 5%")
        ctx.issues.append(Issue(
            IssueLevel.REVIEW,
            f"Benchmark 结论：Gold Set 不达标 —— {'；'.join(detail)}"
            "（AP-11：不产『仅供参考』均值，未促成可回测的 Gold Set 前不晋升基线）"))
        return
    ctx.issues.append(Issue(
        IssueLevel.INFO,
        f"Benchmark 通过：{r['total_cases']} 例五类齐备，实质断言率 {r['substantive_rate']}，"
        f"命中响应 {r['n_has_resp']} 例通过 {r['n_pass']} 例——Gold Set 已达可回测基线，可支撑回归基准与后续 FAR/CAR 计算"))
    ctx.issues.append(Issue(IssueLevel.INFO, r["metric_note"]))


def step_render_benchmark_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    r = ctx.outputs.get("benchmark") or {}
    if not r:
        return
    verdict = {
        True: "READY（可回测基线）",
        False: r.get("eligible") and "NOT_READY" or "NOT_ELIGIBLE",
    }
    body = [
        f"# {title} · Gold Set 指标引擎报告 · {today}",
        "",
        f"- 技能包：`{ctx.outputs.get('skill_dir', '')}`",
        f"- Gold Set 规模：**{r.get('total_cases')} 例**（门槛 ≥{r.get('eligible_min')}）",
        f"- 结论：**{verdict.get(r.get('ready'), 'READY')}**",
        "",
        "## 覆盖度（机制 7）",
        "",
        f"- 五类齐备：{'✅' if r.get('categories_complete') else '❌'} "
        f"分布 {r.get('category_dist', {})}",
        f"- origin：{r.get('origin_dist', {})}",
        f"- risk：{r.get('risk_dist', {})}",
        "",
        "## 可回测性（FAR/CAR 前提）",
        "",
        f"- 实质断言率：**{r.get('substantive_rate')}**（B5：防纯 nonempty 空转）",
        f"- 命中响应率：{r.get('has_resp_rate')}（{r.get('n_has_resp')}/"
        f"{r.get('total_cases')} 例）",
        f"- 非法断言率：{r.get('illegal_assert_rate')}",
        f"- 目标漏检参考：响应通过 {r.get('n_pass')} 例",
        "",
        "## Gate 判定（AP-11：Metrics→Decision）",
        "",
        "Benchmark 不是『平均分好看』：未促成可回测的 Gold Set 前不晋升基线。",
        "",
        "## FAR / CAR（风险轨）",
        "",
        (f"- FAR（虚假保证率）：**{r.get('far')}** · CAR（正确拒答率）：**{r.get('car')}**"
         f"（应拒答正例 {r.get('abstain_positive', 0)} 例，正确 {r.get('abstain_ok', 0)} 例）"
         if r.get("far") is not None
         else r.get("metric_note", "")),
    ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"benchmark-report-{today}.md",
                           "\n".join(body) + "\n")
    ctx.outputs["benchmark_report_file"] = str(report)
    ctx.outputs["benchmark_report_file_name"] = report.name
    ctx.outputs["explain"] = {"口径": "Gold Set 指标引擎（D-028 门槛已满足）",
                              "ready": r.get("ready")}


# ---------------------------------------------------------------------------
# 任务 9：SAG 执行层（材料契约 §11 = LIVE 的补给线，材料层 P2 最小实现）
# ---------------------------------------------------------------------------
# 产品边界：引擎零联网零检索。宿主 Agent 用 WebSearch / iFinD 等先「获取」材料，
# 本任务只做三条铁律的确定性承接：
#  ① 溯源齐（来源/日期/标题/摘录/正文）才落盘；缺溯源 → FAILED 硬拒、不落盘不注入；
#  ② 快照 append-only：materials/<topic>/<asof>.md，不覆盖同名；
#  ③ 时效数据只当次有效，重用时须重新 SAG 校验日期（新鲜度 fault 记录在案）。


def step_sag_fetch(ctx: RunContext) -> None:
    """判定并为 LIVE 类 prompt 沉淀运行时可注入材料。非 LIVE 早退不落盘，WARN 显性标注未执行。"""
    from pathlib import Path

    root = Path(ctx.outputs["skill_dir"])
    raw = (root / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    mtype = _skill_material_type(raw)

    if mtype != "LIVE":
        ctx.outputs["sag_needed"] = False
        ctx.outputs["sag_not_executed"] = True          # 显性标记：本任务对该包不适用，未做任何落盘/注入
        ctx.outputs["sag_material_type"] = mtype or "未声明(按 NONE)"
        ctx.issues.append(Issue(
            IssueLevel.WARN,
            f"材料来源类型 = {mtype or '未声明(按 NONE)'}，非 LIVE：sag-fetch 不适用，未执行任何落盘/注入。" +
            "PROVIDED 走输入契约、CORPUS 走本地语料(RAG)，缺失走缺口协议 MISSING_MATERIAL；" +
            "若本意是补 LIVE 材料，请先确认技能包 §11 材料来源类型标注为 LIVE"))
        return

    ctx.outputs["sag_needed"] = True
    source = (ctx.inputs.get("source") or "").strip()
    as_of = (ctx.inputs.get("asof") or "").strip()
    title = (ctx.inputs.get("title") or "").strip()
    excerpt = (ctx.inputs.get("excerpt") or "").strip()
    body = (ctx.inputs.get("body") or "").strip()
    note = (ctx.inputs.get("note") or "").strip()
    topic = (ctx.inputs.get("topic") or "").strip() or _material_topic(title)

    # 铁律①：溯源必填，缺一项都禁止注入（引擎终态是 FAILED 硬拒，不是降级为
    # REVIEW——「MISSING_MATERIAL 压级」指 Prompt 运行期协议，与引擎任务终态两回事）
    missing = [n for n, v in (("source", source), ("asof", as_of), ("title", title),
                              ("excerpt", excerpt), ("body", body)) if not v]
    if missing:
        ctx.outputs["sag_blocked"] = True
        ctx.outputs["sag_missing"] = missing
        ctx.issues.append(Issue(
            IssueLevel.ERROR,
            f"材料缺溯源依据，禁止注入：{missing}（source/asof/title/excerpt/body 必填；"
            "溯源缺项即 **FAILED 硬拒**、不落盘、不注入——引擎不做降级注入；"
            "Prompt 运行期的 MISSING_MATERIAL 缺口协议是另一层，两者勿混）",
            {"missing": missing}))
        return
    if not _ASOF_RE.match(as_of):
        ctx.outputs["sag_blocked"] = True
        ctx.outputs["sag_missing"] = ["asof"]
        ctx.issues.append(Issue(IssueLevel.ERROR,
                                f"asof 日期格式应为 YYYY-MM-DD，收到：{as_of}"))
        return

    # 铁律②/③：落盘 materials/<topic>/<asof>.md（append-only，不覆盖）
    mdir = root / "materials" / topic
    text_lines = [
        "---",
        "type: sag-material",
        f"topic: {topic}",
        f"asof: {as_of}",
        f"source: {source}",
        f"title: {title}",
        "status: fresh",
        "---",
        "",
        "## 摘要（原文摘录，供溯源锚定）",
        "",
        excerpt,
        "",
        "## 正文（本次注入用）",
        "",
        body,
    ]
    if note:
        text_lines += ["", "## note", "", note]
    mfile = _write(mdir, f"{as_of}.md", "\n".join(text_lines) + "\n")
    sha = _sha256_file(mfile)
    injection = f"[材料·{title}（{as_of}，{source}，sha256:{sha[:12]}…）] → materials/{topic}/{as_of}.md"
    entry = {
        "path": str(mfile.relative_to(root)).replace("\\", "/"),
        "topic": topic, "asof": as_of, "source": source,
        "title": title, "sha256": sha, "status": "fresh",
        "injection": injection,
    }
    ctx.outputs["material_entry"] = entry
    ctx.outputs["sag_material_type"] = "LIVE"
    ctx.issues.append(Issue(
        IssueLevel.INFO,
        f"材料已落盘 materials/{topic}/{as_of}.md（{source}@{as_of}，溯源齐，status=fresh）",
        {"sha256": sha}))
    if topic not in ctx.outputs.get("sag_topics", ()):
        ctx.outputs["sag_topics"] = list(ctx.outputs.get("sag_topics", ())) + [topic]
    ctx.issues.append(Issue(
        IssueLevel.WARN,
        "材料入包已改动技能指纹：本次认证作废，交付前须重跑 score-skill 重认证；"
        "时效数据只当次有效，重用时须按新鲜度重新 SAG 校验 asof 日期"))


def step_render_sag_report(ctx: RunContext) -> None:
    rules = _rules(ctx)
    today = time.strftime("%Y-%m-%d_%H%M%S")
    title = (rules.get("report") or {}).get("title_prefix", "Prompt 质检产线")
    entry = ctx.outputs.get("material_entry")
    missing = ctx.outputs.get("sag_missing")
    mtype = ctx.outputs.get("sag_material_type", "未声明")

    body = [
        f"# {title} · SAG 材料层报告 · {today}",
        "",
        f"- 技能包：`{ctx.outputs.get('skill_dir', '')}`",
        f"- 材料来源类型：**{mtype}**",
        "",
    ]
    if ctx.outputs.get("sag_blocked"):
        body += [
            "## 结论：**缺失依据，禁止注入（MISSING_MATERIAL）**",
            "",
            f"- 缺口项：{'、'.join(missing or [])}",
            "- 规则：溯源缺项引擎即 FAILED 硬拒（不落盘不注入）；Prompt 运行期材料缺失"
            "按 MISSING_MATERIAL 协议处理，禁止用模型内部知识冒充外部事实。",
            "- 下一步：由宿主 Agent 补齐 source/asof/title/excerpt/body 后重跑。",
        ]
    elif entry:
        body += [
            "## 结论：**材料已沉淀（溯源齐，可注入）**",
            "",
            f"- 落盘：`{entry['path']}`",
            f"- 来源：{entry['source']} @ {entry['asof']}",
            f"- sha256：{entry['sha256']}",
            f"- status：{entry['status']}",
            "",
            "## 注入说明（宿主 Agent 持此引用注入 prompt / 执行时消费）",
            "",
            f"`{entry['injection']}`",
            "",
            "## 注意",
            "",
            "- 时效数据只当次有效：重用时须重新 SAG 校验 asof 日期。",
            "- 材料入包已改动技能指纹，交付前须重跑 score-skill 重认证。",
        ]
    else:
        body += [
            "## 结论：**任务不适用，未执行（非 LIVE）**",
            "",
            f"- 材料来源类型 = {mtype}，sag-fetch 只服务 LIVE 类材料。",
            ("- 非 LIVE 补给线：PROVIDED 走输入契约、CORPUS 走本地语料(RAG)；"
             "材料缺失时按缺口协议输出 MISSING_MATERIAL。"),
            "- 未做任何落盘 / 注入（避免误以为材料已就绪）。若本意是补 LIVE 材料，先确认技能包 §11 标注为 LIVE。",
        ]
    report = _write_report(ctx.runtime.output_dir(),
                           f"sag-report-{today}.md", "\n".join(body) + "\n")
    ctx.outputs["sag_report_file"] = str(report)
    ctx.outputs["sag_report_file_name"] = report.name
    ctx.outputs["explain"] = {"口径": "SAG 材料层 P2（溯源→落盘→注入）",
                              "needed": ctx.outputs.get("sag_needed"),
                              "not_executed": bool(ctx.outputs.get("sag_not_executed")),
                              "rejected": bool(ctx.outputs.get("sag_blocked"))}
