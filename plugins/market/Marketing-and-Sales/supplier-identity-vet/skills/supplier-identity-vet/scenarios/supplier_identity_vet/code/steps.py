"""
steps.py —— 供应商主体一致性核验 处理步骤

步骤纪律：只往 ctx.outputs 写结果、往 ctx.issues 记问题；
溯源自检：load 步骤声明 trace_check，render 把进产物的关键条目填进 items；
explain：判定依据写进 outputs["explain"]（只写事实与计数，不泄阈值）。

输入契约：单文件，每行 `侧:键=值`，键 ∈ 名称/法定代表人/开户行/统一社会信用代码
（及别名），侧 ∈ 台账|我方|a / 证照|对方|b。扫描件/图片行在喂入前由宿主转文本，
残余未解析行命中 _SCAN_HINTS 时按 UNKNOWN 转人工，不静默放行。
"""

from __future__ import annotations

import time

from scenario_api import Issue, IssueLevel, RunContext, read_file_auto

from .validator import parse_entities, summarize, verify_supplier
from .template_reader import try_read


def _read_source(path: str) -> str:
    """模板优先读取：模板 Excel 转键值行；否则回退 read_file_auto。"""
    lines = try_read(path)
    if lines is not None:
        return "\n".join(lines)
    return read_file_auto(path)


def step_load_entries(ctx: RunContext) -> None:
    """读输入并通过 read_file_auto 归一化文本；记录溯源原文。"""
    raw = _read_source(ctx.inputs["source-file"])
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    ctx.outputs["raw"] = raw
    ctx.outputs["lines"] = lines
    ctx.outputs["trace_check"] = {"source": raw, "items": []}
    if not lines:
        ctx.issues.append(Issue(IssueLevel.ERROR, "输入文件是空的"))
    return None


def step_partition_entities(ctx: RunContext) -> None:
    """把两侧实体行归类为台账侧与证照侧；无法归侧/解析的行计入待人工。"""
    lines: list[str] = ctx.outputs.get("lines", [])
    ledger: dict = {}
    cert: dict = {}
    ledger_lines: list[str] = []
    cert_lines: list[str] = []
    unresolved: list[str] = []
    for line in lines:
        ent = parse_entities(line)
        if not ent:
            unresolved.append(line)
            continue
        # 取该行首个字段的归侧；字段异侧混排时视作无法归类 → 转人工
        sides = {info["side"] for info in ent.values()}
        if sides == {"ledger"}:
            for fid, info in ent.items():
                ledger.setdefault(fid, info)
            ledger_lines.append(line)
        elif sides == {"cert"}:
            for fid, info in ent.items():
                cert.setdefault(fid, info)
            cert_lines.append(line)
        else:
            unresolved.append(line)
    ctx.outputs["ledger"] = ledger
    ctx.outputs["cert"] = cert
    ctx.outputs["ledger_lines"] = ledger_lines
    ctx.outputs["cert_lines"] = cert_lines
    ctx.outputs["unresolved"] = unresolved
    if unresolved:
        ctx.issues.append(
            Issue(IssueLevel.REVIEW,
                  f"{len(unresolved)} 行未能解析为实体（可能为扫描件/图片/格式不符），转人工核对")
        )
    return None


def step_cross_check(ctx: RunContext) -> None:
    """执行跨文档一致性判定，并把结论与判定依据挂到 outputs。"""
    ledger = ctx.outputs.get("ledger", {})
    cert = ctx.outputs.get("cert", {})
    ctx.issues.extend(verify_supplier(ledger, cert))
    summ = summarize(ledger, cert)
    ctx.outputs["verdict"] = summ["verdict"]
    ctx.outputs["diffs"] = summ["diffs"]
    ctx.outputs["judged_fields"] = summ["judged_fields"]
    ctx.outputs["ledger_fields"] = summ["ledger_fields"]
    ctx.outputs["cert_fields"] = summ["cert_fields"]

    # 溯源：进产物的关键条目用输入原文的行，保证在 source 里能逐字找到出处
    ctx.outputs["trace_check"]["items"] = (
        ctx.outputs.get("ledger_lines", []) + ctx.outputs.get("cert_lines", [])
    )
    return None


def step_render_report(ctx: RunContext) -> None:
    """渲染核验报告到 output/ 目录，填入溯源条目与判定依据。"""
    today = time.strftime("%Y-%m-%d")
    verdict = ctx.outputs.get("verdict", "UNKNOWN")
    diffs = ctx.outputs.get("diffs", ["无"])
    judged = ctx.outputs.get("judged_fields", [])
    ledger_fields = ctx.outputs.get("ledger_fields", [])
    cert_fields = ctx.outputs.get("cert_fields", [])
    unresolved = ctx.outputs.get("unresolved", [])

    lines = [
        "# 供应商主体一致性核验报告",
        "",
        f"- 日期：{today}",
        f"- 结论：**{verdict}**",
        f"- 已判定字段：{ '、'.join(judged) if judged else '—' }",
        "",
        "## 差异 / 待核验项",
        *[f"- {d}" for d in diffs],
        "",
        "## 两侧字段覆盖",
        f"- 台账侧：{ '、'.join(ledger_fields) if ledger_fields else '—' }",
        f"- 证照侧：{ '、'.join(cert_fields) if cert_fields else '—' }",
    ]
    if unresolved:
        lines += ["", "## 未解析行（转人工）", *[f"- {ln}" for ln in unresolved]]

    out_dir = ctx.runtime.output_dir()
    file_name = f"supplier-vet-{today}.md"
    (out_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    ctx.outputs["report_file_name"] = file_name
    ctx.outputs["report_file"] = str(out_dir / file_name)

    # 判定依据摘要（事实 + 计数，不泄阈值/归一规则）
    ctx.outputs["explain"] = {
        "判定依据": f"共比对 {len(judged)} 个字段，{verdict}",
        "转人工原因": (f"{len(unresolved)} 行未解析；差异 {len(diffs)} 项" if verdict != "PASS" else "无"),
    }
    return None