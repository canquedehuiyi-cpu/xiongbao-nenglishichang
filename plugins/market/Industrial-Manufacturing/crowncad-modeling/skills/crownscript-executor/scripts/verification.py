"""CrownCAD 要求比较与报告；不代表任务整体完成。"""

from __future__ import annotations

# scripts/verification.py
import json
import math
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any


def _evidence_complete(evidence: Any) -> bool:
    """只核对引用格式，不验证文件真实、最新或对象正确。"""
    return (
        isinstance(evidence, (list, tuple))
        and bool(evidence)
        and all(isinstance(ref, str) and bool(ref.strip()) for ref in evidence)
    )


def check_result(requirement, *, stage, status, actual=None, reason="", evidence=()):
    if status not in {"passed", "failed", "unverified"}:
        raise ValueError("检查状态无效")
    # 无效引用保存为空，不把路径字符串拆成字符；通过条件由入口复核。
    safe_evidence = list(evidence) if _evidence_complete(evidence) else []
    return deepcopy(
        {
            "id": requirement["id"],
            "title": requirement["title"],
            "kind": requirement.get("kind"),
            "purpose": requirement.get("purpose"),
            "stage": stage,
            "status": status,
            "expected": requirement.get("expected"),
            "actual": actual,
            "unit": requirement.get("unit", ""),
            "tolerance": requirement.get("tolerance"),
            "tolerance_basis": requirement.get("tolerance_basis", ""),
            "reason": reason,
            "evidence": safe_evidence,
        }
    )


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _numeric_comparison(actual, expected, tolerance):
    """返回实际差值和是否符合容差；统一处理浮点边界。"""
    if (
        not finite_number(actual)
        or not finite_number(expected)
        or not finite_number(tolerance)
        or tolerance < 0
    ):
        raise ValueError("实际值、要求值或比较容差无效")
    # 零容差先比较原值，避免 float 转换丢失整数精度。
    if tolerance == 0:
        return abs(actual - expected), actual == expected
    actual, expected, tolerance = float(actual), float(expected), float(tolerance)
    error = abs(actual - expected)
    if error <= tolerance:
        return error, True
    if not math.isfinite(error):
        return error, False
    # ULP 为各数值附近的浮点间隔；不添加固定毫米容差。
    roundoff = math.fsum(
        math.ulp(value) for value in (actual, expected, error, tolerance)
    )
    return error, error - tolerance <= roundoff


def compare_number(
    requirement: Mapping[str, Any],
    actual: Any,
    *,
    stage: str,
    evidence: Sequence[str] = (),
    target_basis: str = "",
) -> dict[str, Any]:
    # 对象确认和尺寸比较分开：没有目标依据时不比较。
    if requirement.get("kind") != "number":
        raise ValueError("该要求不是数值检查")
    if not target_basis.strip():
        return check_result(
            requirement,
            stage=stage,
            status="unverified",
            reason="尚未确认测量对象",
            evidence=evidence,
        )
    if not _evidence_complete(evidence):
        return check_result(
            requirement, stage=stage, status="unverified",
            reason="缺少有效测量依据：需要非空的证据引用列表",
        )
    expected, tolerance = requirement.get("expected"), requirement.get("tolerance")
    if not finite_number(expected) or not finite_number(tolerance) or tolerance < 0:
        raise ValueError("要求值或比较容差无效")
    if not requirement.get("tolerance_basis"):
        raise ValueError("需要说明容差依据")
    if not finite_number(actual):
        return check_result(
            requirement,
            stage=stage,
            status="unverified",
            reason="没有有效实际值",
            evidence=evidence,
        )
    error, within_tolerance = _numeric_comparison(actual, expected, tolerance)
    status = "passed" if within_tolerance else "failed"
    result = check_result(
        requirement,
        stage=stage,
        status=status,
        actual=actual,
        reason=f"实际差值 {error:g}；定位依据：{target_basis}",
        evidence=evidence,
    )
    result["error"] = error
    return result


def _visual_evidence_complete(item):
    # 核对记录格式，不证明图片真实性或 Agent 确实看过。
    observation = item.get("actual")
    return (
        isinstance(observation, str) and bool(observation.strip())
        and _evidence_complete(item.get("evidence"))
    )


def record_visual(requirement, *, stage, status, observation, evidence=(), source=None):
    # 只记录观察，不调用浏览器；来源未提供时不自动称为实际 CAD。
    if requirement.get("kind") != "visual":
        raise ValueError("视觉记录不能代替精确尺寸检查")
    valid_evidence = isinstance(evidence, (list, tuple))
    result = check_result(
        requirement, stage=stage, status=status, actual=observation,
        reason="Agent 实际查看后记录", evidence=evidence if valid_evidence else (),
    )
    result["source"] = source
    if not _visual_evidence_complete(result):
        # 缺记录不能证明通过，也不能抹掉调用方已报告的失败。
        if result["status"] != "failed":
            result["status"] = "unverified"
        result["reason"] = "缺少具体观察或有效图片依据"
    return result


def build_report(
    requirements: Sequence[Mapping[str, Any]],
    checks: Sequence[Mapping[str, Any]],
    *,
    stage: str,
    additional_ids: Sequence[str] = (),
) -> dict[str, Any]:
    # additional_ids 由 AI 选出本次操作影响的旧要求，不做自动依赖分析。
    # 最终阶段始终检查全部要求，不允许缩小范围。
    if len({item["id"] for item in requirements}) != len(requirements):
        raise ValueError("检查项编号不能重复")
    all_requirement_ids = {item["id"] for item in requirements}
    if any(item_id not in all_requirement_ids for item_id in additional_ids):
        raise ValueError("补查项目不在要求清单中")
    selected = (
        requirements
        if stage == "final"
        else [
            item
            for item in requirements
            if item["stage"] == stage or item["id"] in additional_ids
        ]
    )
    ids = {item["id"] for item in selected}
    all_ids = {item["id"] for item in requirements}
    if any(item["id"] not in all_ids for item in checks):
        raise ValueError("结果有清单外的检查项")
    current = [item for item in checks if item["stage"] == stage and item["id"] in ids]
    if any(
        item["status"] not in {"passed", "failed", "unverified"} for item in current
    ):
        raise ValueError("检查状态无效")
    rows = []
    completion_issues = []
    for requirement in selected:
        candidates = [item for item in current if item["id"] == requirement["id"]]
        findings, rejected = [], []
        fields = ("kind", "expected", "unit", "tolerance", "tolerance_basis", "purpose")
        for item in candidates:
            # 必须具有对应字段，不能把缺字段当作匹配。
            # expected 为结构化要求时按完整值比较，不根据显示文字猜测。
            matches = all(
                (field in item or field == "purpose")
                and item.get(field)
                == requirement.get(
                    field, "" if field in {"unit", "tolerance_basis"} else None
                )
                for field in fields
            )
            if matches:
                # 汇总只复核“数值通过”是否自洽，不证明对象或证据真实性。
                # 原始记录保留；已报告的失败不会被重新计算成通过。
                if requirement.get("kind") == "number" and item["status"] == "passed":
                    expected = requirement.get("expected")
                    tolerance = requirement.get("tolerance")
                    actual = item.get("actual")
                    valid_numbers = (
                        finite_number(expected)
                        and finite_number(actual)
                        and finite_number(tolerance)
                        and tolerance >= 0
                    )
                    if not valid_numbers:
                        findings.append(check_result(
                            requirement, stage=stage, status="unverified",
                            reason="数值通过复核：要求值、实际值或容差无效",
                        ))
                    else:
                        _, within_tolerance = _numeric_comparison(
                            actual, expected, tolerance
                        )
                        if not within_tolerance:
                            findings.append(check_result(
                                requirement, stage=stage, status="failed", actual=actual,
                                reason="数值通过复核：实际差值超过容差",
                                evidence=item.get("evidence", ()),
                            ))
                    # 独立检查证据，缺证据不能覆盖已经发现的超差。
                    if not _evidence_complete(item.get("evidence")):
                        findings.append(check_result(
                            requirement, stage=stage, status="unverified",
                            reason="数值通过复核：缺少有效测量依据",
                        ))
                # 阶段名不写死；已安排的实际模型视觉项均检查来源。
                needs_cad_visual = (
                    requirement.get("kind") == "visual"
                    and requirement.get("purpose") in {
                        "stage_model_visual", "final_model_visual",
                    }
                )
                if needs_cad_visual:
                    if (
                        item.get("source") != "cad_browser"
                        or not _visual_evidence_complete(item)
                    ):
                        issue = (
                            f"{requirement['title']}：缺少实际浏览器来源、"
                            "具体观察或截图依据"
                        )
                        # 可选项缺证据只影响该行，不阻止必需项通过。
                        if requirement.get("required", True):
                            completion_issues.append(issue)
                        findings.append(check_result(
                            requirement, stage=stage, status="unverified",
                            reason=issue,
                        ))
                    # 保留已确认的失败，不让缺失证据覆盖原始失败记录。
                findings.append(item)
            else:
                rejected.append(item)
                findings.append(
                    check_result(
                        requirement,
                        stage=stage,
                        status="unverified",
                        reason="检查结果与当前要求不一致，需要重新比较或测量",
                        evidence=item.get("evidence", ()),
                    )
                )
        if not findings:
            findings = [
                check_result(
                    requirement,
                    stage=stage,
                    status="unverified",
                    reason="本阶段没有该项检查结果",
                )
            ]
        # 同一次检查保留全部证据；失败不能被另一条通过覆盖。
        # 修正后只传修正后这一次结果，旧结果留在旧记录中。
        status = (
            "failed"
            if any(f["status"] == "failed" for f in findings)
            else "unverified"
            if any(f["status"] == "unverified" for f in findings)
            else "passed"
        )
        rows.append(
            {
                "requirement": requirement,
                "status": status,
                "findings": findings,
                "rejected_findings": rejected,
            }
        )
    if stage == "final":
        visual_rows = [row for row in rows
                       if row["requirement"].get("kind") == "visual"
                       and row["requirement"].get("purpose") == "final_model_visual"
                       and row["requirement"].get("required", True)]
        if not visual_rows:
            completion_issues.append("缺少必需的最终实际模型视觉检查要求")
        elif any(row["status"] != "passed" for row in visual_rows):
            completion_issues.append("最终实际模型视觉检查未通过或未完成")
    required_rows = [row for row in rows if row["requirement"].get("required", True)]
    if not required_rows:
        overall = "unverified"  # 空清单不能证明通过。
    elif any(row["status"] == "failed" for row in required_rows):
        overall = "failed"
    elif completion_issues or any(row["status"] == "unverified" for row in required_rows):
        overall = "unverified"
    else:
        overall = "passed"
    # 报告保存本次检查快照，调用方后续改清单或证据不能改变已有结论。
    return deepcopy(
        {
            "scope": "requirements_check",
            "stage": stage,
            "status": overall,
            "checks": rows,
            "completion_issues": list(dict.fromkeys(completion_issues)),
        }
    )


def write_report(
    report: Mapping[str, Any],
    output_dir: str | Path,
    *,
    write_text: Callable[[Path, str], None] | None = None,
) -> None:
    # 只写本任务普通报告文件，不操作 CAD，不处理保存导出。
    output_dir = Path(output_dir)
    json_text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    labels = {"passed": "通过", "failed": "失败", "unverified": "未验证"}

    def cell(value):
        # 避免观察文字中的竖线和换行破坏 Markdown 表格。
        return str(value).replace("|", r"\|").replace("\n", "<br>")

    lines = [
        f"# {report['stage']} 要求检查报告",
        "",
        "范围：汇总指定要求，不单独代表任务全部完成。",
        "",
        f"要求检查结果：{labels[report['status']]}",
        "",
        "| 检查项 | 要求 | 实际及原因 | 结论 | 依据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    issues = report.get("completion_issues", [])
    if issues:
        heading = "最终完整性检查：" if report["stage"] == "final" else "阶段完整性检查："
        lines[6:6] = [heading, "", *[f"- {cell(issue)}" for issue in issues], ""]
    for row in report["checks"]:
        requirement, findings = row["requirement"], row["findings"]
        actual = "；".join(f"{f['actual']}；{f['reason']}" for f in findings)
        evidence = "；".join(str(ref) for f in findings for ref in f["evidence"])
        expected = f"{requirement.get('expected', '')} {requirement.get('unit', '')}"
        if requirement.get("kind") == "number":
            expected += f"；容差 {requirement.get('tolerance')}；{requirement.get('tolerance_basis', '')}"
        lines.append(
            "| "
            + " | ".join(
                cell(v)
                for v in (
                    requirement["title"],
                    expected,
                    actual,
                    labels[row["status"]],
                    evidence,
                )
            )
            + " |"
        )
    markdown_text = "\n".join(lines) + "\n"
    # 两份完整文本均准备成功才开始写；单文件回调不承诺跨文件原子提交。
    output_dir.mkdir(parents=True, exist_ok=True)
    if write_text is None:
        def write_text(path: Path, text: str) -> None:
            path.write_text(text, encoding="utf-8")
    write_text(output_dir / "verification.json", json_text)
    write_text(output_dir / "verification.md", markdown_text)
