"""Offline assembly comparisons and reports; no CAD execution or object selection.

The caller confirms query scope, component identity and evidence freshness.
File checks and matching records cannot authenticate geometry or screenshots.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

STATUSES = frozenset({"passed", "failed", "unverified"})
CONTEXT_FIELDS = (
    "documentId",
    "versionId",
    "docType",
    "stage",
    "scriptFile",
    "responseFile",
)
MATCH_FIELDS = ("target", "expected", "unit", "tolerance", "tolerance_basis")
MATE_KINDS = frozenset(
    {"mateCreation", "mateParticipants", "mateGeometryRefs", "mateParameters"}
)
FINAL_KINDS = MATE_KINDS | {
    "instances",
    "componentSource",
    "solver",
    "position",
    "interference",
    "visual",
}


def _identity(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    return str(value).strip() or None


def _index(items: Any, field: str) -> dict[str, dict]:
    if not isinstance(items, list):
        raise TypeError("查询或对应资料必须是数组")
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("资料中有非对象记录")
        key = _identity(item.get(field))
        if key is None or key in result:
            raise ValueError(f"缺少或重复的 {field}")
        result[key] = item
    return result


def make_check(requirement, status, actual, reason, *, context, evidence):
    """Record a comparison or Agent observation, without claiming to verify its truth."""
    if status not in STATUSES:
        raise ValueError("检查状态无效")
    if not isinstance(evidence, list) or any(
        not isinstance(p, str) or not p.strip() for p in evidence
    ):
        raise ValueError("evidence 必须是非空路径字符串组成的数组")
    if not isinstance(context, dict) or not _identity(requirement.get("id")):
        raise ValueError("缺少检查编号或上下文")
    if status == "passed" and not evidence:
        status, reason = "unverified", "缺少实际证据引用"
    # Copy only the fields being compared, not the full plan or requirement.
    return deepcopy(
        {
            "requirementId": requirement["id"],
            "kind": requirement.get("kind"),
            "purpose": requirement.get("purpose"),
            **{field: requirement.get(field) for field in MATCH_FIELDS},
            "actual": actual,
            "status": status,
            "reason": reason,
            "evidence": evidence,
            "context": context,
        }
    )


def _component_instances(items):
    """直接使用接口实例记录，仅从组件数量检查中排除组织文件夹。"""
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise TypeError("实例查询必须是对象组成的数组")
    return [item for item in items if item.get("IsFolder") is not True]


def _source_text(value):
    """无效来源字段代表缺少证据；局部去空白后比较，不改写接口原数据。"""
    return value.strip() if isinstance(value, str) and value.strip() else None


def check_instances(
    requirement, actual_instances, bindings, *, context, evidence, scope_confirmed=False
):
    """检查当前完整范围的 data.Instances；计划绑定错误不等于模型已确认出错。"""

    def result(status, actual, reason):
        return make_check(
            requirement, status, actual, reason, context=context, evidence=evidence
        )

    if scope_confirmed is not True:
        return result("unverified", None, "尚未确认查询完整且与要求范围一致")
    try:
        # 接口对象使用原字段 ID；计划组件绑定仍使用 componentId、instanceId。
        actual = _index(_component_instances(actual_instances), "ID")
        expected = requirement["expected"]["componentIds"]
        if (
            not isinstance(expected, list)
            or not expected
            or any(not _identity(v) for v in expected)
        ):
            raise ValueError("预期组件清单为空或无效")
        expected_ids = [_identity(v) for v in expected]
        if len(set(expected_ids)) != len(expected_ids):
            raise ValueError("预期组件编号重复")
    except (ValueError, KeyError, TypeError) as error:
        return result("unverified", None, str(error))
    if len(actual) != len(expected):
        return result(
            "failed",
            {"expectedCount": len(expected), "actualCount": len(actual)},
            "当前完整同范围查询的实例数量不符",
        )
    # 先检查已确认范围的数量，再检查计划绑定，避免绑定缺项掩盖实际少件或多件。
    try:
        bound = _index(bindings, "componentId")
    except (ValueError, TypeError) as error:
        return result("unverified", None, str(error))
    if set(bound) != set(expected_ids):
        return result("unverified", None, "计划组件的身份对应尚不完整或含清单外对象")
    ids = [_identity(bound[key].get("instanceId")) for key in expected_ids]
    if None in ids or len(set(ids)) != len(ids) or set(ids) != set(actual):
        return result(
            "unverified", {"instanceIds": ids}, "对应资料使用旧编号、缺编号或重复认领"
        )
    return result(
        "passed",
        {"instanceIds": ids},
        "数量与当前对应资料一致；身份由 Agent 确认，来源另查",
    )


def check_component_source(
    requirement, actual_instances, bindings, *, context, evidence
):
    """从原实例记录检查明确的来源要求；缺字段记未验证，实际不符才记失败。"""

    def result(status, actual, reason):
        return make_check(
            requirement, status, actual, reason, context=context, evidence=evidence
        )

    try:
        actual = _index(_component_instances(actual_instances), "ID")
        bound = _index(bindings, "componentId")
        binding = bound[requirement["target"]["componentId"]]
        instance = actual[_identity(binding.get("instanceId"))]
        # 只在检查内部把接口字段对应到计划要求名，不再对外返回一套重命名数据。
        # 无原生来源的 docName 等要求保持缺证据，不从 Name 或文件名猜测。
        source = {
            "documentId": _source_text(instance.get("DocID")),
            "versionId": _source_text(instance.get("VersionID")),
            "protoId": _source_text(instance.get("ProtoID")),
        }
        expected = requirement["expected"]["source"]
        if (
            not isinstance(expected, dict)
            or not expected
            or any(v is None or v == "" for v in expected.values())
        ):
            raise ValueError("来源要求仍为空或待定")
    except (ValueError, KeyError, TypeError) as error:
        return result("unverified", None, str(error))
    missing, mismatches = [], []
    for field, value in expected.items():
        if source.get(field) is None:
            missing.append(field)
        elif source[field] != value:
            mismatches.append(
                {"field": field, "expected": value, "actual": source[field]}
            )
    detail = {
        "instanceId": binding["instanceId"],
        "missing": missing,
        "mismatches": mismatches,
    }
    if mismatches:
        # 已有有效证据确认的不符不能被其他字段缺失覆盖。
        return result("failed", detail, "实际可确认的来源字段不符")
    if missing:
        return result("unverified", detail, "实际查询缺少部分要求的来源字段")
    return result("passed", detail, "全部明确要求的来源字段符合")


def check_mate_readback(
    requirement,
    feature_id,
    actual_mates,
    *,
    move_instance_id,
    ref_instance_id,
    context,
    evidence,
):
    """按配合 ID 回查 data.Matings，区分移动方与参考方；求解、参数和选面另查。"""

    def result(status, actual, reason):
        return make_check(
            requirement, status, actual, reason, context=context, evidence=evidence
        )

    ids = tuple(_identity(v) for v in (feature_id, move_instance_id, ref_instance_id))
    if None in ids or ids[0] == "0":
        return result("unverified", None, "缺少本轮有效特征或实例编号")
    if not isinstance(actual_mates, list):
        return result("unverified", None, "配合查询未取得有效数组")
    # 仅定位目标配合；无关记录不完整不能掩盖这条配合已经确认的双方引用错误。
    matches = [
        m
        for m in actual_mates
        if isinstance(m, dict) and _identity(m.get("ID")) == ids[0]
    ]
    if len(matches) != 1:
        return result("unverified", None, "预期配合未回查到或重复")
    current = matches[0]
    pair = (
        _identity(current.get("MoveInstance")),
        _identity(current.get("RefInstance")),
    )
    if None in pair:
        return result("unverified", current, "回查双方字段缺失或无法确认")
    if pair != ids[1:]:
        return result("failed", current, "回查双方与已确认要求不符")
    return result("passed", current, "回查双方符合；实际选面、参数、求解另查")


def compare_value(actual, expected, tolerance):
    """Same finite-number/roundoff principles as part checks, no part-report import."""
    values = (actual, expected, tolerance)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
        raise ValueError("实测、要求和容差必须是数值")
    try:
        if not all(math.isfinite(float(v)) for v in values) or tolerance < 0:
            raise ValueError("数值非有限或容差为负")
    except OverflowError as error:
        raise ValueError("数值超出范围") from error
    if isinstance(actual, int) and isinstance(expected, int):
        difference = abs(actual - expected)
        return {"error": difference, "withinTolerance": difference <= tolerance}
    if tolerance == 0:
        return {"error": abs(actual - expected), "withinTolerance": actual == expected}
    a, e, t = map(float, values)
    difference = abs(a - e)
    if not math.isfinite(difference):
        raise ValueError("实测差值溢出")
    rounding = math.fsum(math.ulp(v) for v in (a, e, t, difference))
    return {
        "error": difference,
        "withinTolerance": difference <= t or difference - t <= rounding,
    }


def _evidence_files(evidence, context):
    """Only inspect explicit paths. Existence is not authenticity or freshness."""
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(p, str) or not p.strip() for p in evidence)
    ):
        return False
    root = Path(context.get("runDir", "."))
    return all((root / path).is_file() for path in evidence)


def _review_check(requirement, check, context):
    # Preserve original records; report corrections do not rewrite historical findings.
    reviewed = deepcopy(check)
    matches = (
        all(check.get(field) == requirement.get(field) for field in MATCH_FIELDS)
        and check.get("kind") == requirement.get("kind")
        and check.get("purpose") == requirement.get("purpose")
        and all(
            check.get("context", {}).get(k) == context.get(k) for k in CONTEXT_FIELDS
        )
    )
    if not matches:
        reviewed.update(
            status="unverified", reason="要求、对象或阶段资料已变化，需要重新检查"
        )
        return reviewed
    if reviewed.get("status") not in STATUSES:
        raise ValueError("检查状态无效")
    if reviewed["status"] != "passed":
        return reviewed  # Current failures are not hidden by missing data elsewhere.
    if not _evidence_files(check.get("evidence"), context):
        reviewed.update(status="unverified", reason="缺少实际证据文件，或文件不可读取")
        return reviewed
    kind, actual = requirement.get("kind"), check.get("actual")
    if actual is None:
        reviewed.update(status="unverified", reason="缺少实际检查结果")
        return reviewed
    if kind == "visual":
        observation = actual if isinstance(actual, dict) else {}
        has_image = any(
            Path(p).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            for p in check["evidence"]
        )
        if (
            observation.get("method") != "cad_browser"
            or not str(observation.get("observation") or "").strip()
            or not has_image
        ):
            reviewed.update(status="unverified", reason="缺少当前 CAD 浏览器观察和截图")
    elif kind == "position" and (
        "tolerance" in requirement
        or isinstance(requirement.get("expected"), (int, float))
    ):
        measurement = actual if isinstance(actual, dict) else {}
        try:
            if (
                not isinstance(requirement.get("unit"), str)
                or not requirement["unit"].strip()
                or measurement.get("unit") != requirement.get("unit")
                or not str(measurement.get("target_basis") or "").strip()
                or measurement.get("coordinateFrame") != "assembly_world"
                or not requirement.get("tolerance_basis")
            ):
                raise ValueError("缺少实际装配测量对象、单位、坐标系或容差依据")
            compared = compare_value(
                measurement.get("value"),
                requirement.get("expected"),
                requirement.get("tolerance"),
            )
            reviewed["actual"] = {**measurement, **compared}
            if not compared["withinTolerance"]:
                reviewed.update(status="failed", reason="实测值超出要求容差")
        except ValueError as error:
            reviewed.update(status="unverified", reason=str(error))
    elif kind in {
        "solver",
        "position",
        "interference",
        "motion",
        "mateGeometryRefs",
        "mateParameters",
    }:
        if not isinstance(actual, dict) or not actual:
            reviewed.update(
                status="unverified", reason="缺少实际检查内容；计划或空值不能证明通过"
            )
    return reviewed


def _coverage_issues(requirements, *, final):
    """Basic checklist completeness only; never traverse an operation graph."""
    required = [r for r in requirements if r.get("required") is True]
    issues = []

    def missing(reason):
        issues.append({"status": "unverified", "reason": reason})

    if not required:
        missing("没有必需检查，不能证明通过")
    if final:
        kinds = {r.get("kind") for r in required}
        for kind in sorted(FINAL_KINDS - kinds):
            missing(f"最终清单缺少必需类别：{kind}")
        mates = {
            r.get("target", {}).get("mateId")
            for r in required
            if r.get("kind") in MATE_KINDS
        }
        for mate in mates:
            covered = {
                r.get("kind")
                for r in required
                if r.get("target", {}).get("mateId") == mate
            }
            if not mate or not MATE_KINDS <= covered:
                missing(f"配合 {mate} 的创建/双方/引用/参数检查不完整")
        components = set()
        for req in required:
            if req.get("kind") == "instances":
                components.update(req.get("expected", {}).get("componentIds", []))
        sources = {
            r.get("target", {}).get("componentId")
            for r in required
            if r.get("kind") == "componentSource"
        }
        for component in sorted(components - sources):
            missing(f"组件 {component} 缺来源检查")
    purpose = "final_model_visual" if final else "stage_model_visual"
    if not any(
        r.get("kind") == "visual" and r.get("purpose") == purpose for r in required
    ):
        missing(f"缺少必需的 {purpose} 检查")
    return issues


def build_assembly_report(
    requirements, checks, *, context, final=False, additional_ids=(), issues=()
):
    """Compare current check records to selected requirements; report, never execute."""
    indexed = _index(requirements, "id")
    if any(identity not in indexed for identity in additional_ids):
        raise ValueError("受影响旧检查编号不在清单中")
    if any(
        not isinstance(c, dict) or c.get("requirementId") not in indexed for c in checks
    ):
        raise ValueError("检查结果引用清单外的要求")
    if any(not isinstance(r.get("required"), bool) for r in requirements):
        raise ValueError("每项要求必须明确 required")
    selected = [
        r
        for r in requirements
        if final or r.get("stage") == context.get("stage") or r["id"] in additional_ids
    ]
    report_issues = deepcopy(list(issues))
    if any(
        not isinstance(i, dict) or i.get("status") not in STATUSES
        for i in report_issues
    ):
        raise ValueError("问题必须有明确状态")
    report_issues += _coverage_issues(selected, final=final)
    if (
        any(
            not isinstance(context.get(key), str) or not context[key].strip()
            for key in CONTEXT_FIELDS
        )
        or context.get("docType") != "AssemblyDocument"
    ):
        report_issues.append(
            {"status": "unverified", "reason": "当前装配文档或阶段上下文不完整"}
        )
    if not _evidence_files(
        [context.get("scriptFile"), context.get("responseFile")], context
    ):
        report_issues.append(
            {"status": "unverified", "reason": "本阶段脚本或执行响应文件缺失"}
        )
    rows = []
    for req in selected:
        findings = [
            _review_check(req, c, context)
            for c in checks
            if c["requirementId"] == req["id"]
        ]
        status = (
            "failed"
            if any(c["status"] == "failed" for c in findings)
            else "unverified"
            if not findings or any(c["status"] == "unverified" for c in findings)
            else "passed"
        )
        rows.append(
            {
                "id": req["id"],
                "title": req.get("title", req["id"]),
                "kind": req.get("kind"),
                "required": req["required"],
                "target": req.get("target"),
                "expected": req.get("expected"),
                "status": status,
                "findings": findings,
                "reason": "缺少本次有效结果"
                if not findings
                else "；".join(c["reason"] for c in findings),
            }
        )
    statuses = [r["status"] for r in rows if r["required"]] + [
        i["status"] for i in report_issues
    ]
    overall = (
        "failed"
        if "failed" in statuses
        else "unverified"
        if not statuses or "unverified" in statuses
        else "passed"
    )
    return {
        "scope": "assembly_requirements_check",
        "context": deepcopy(context),
        "final": final,
        "overall": overall,
        "rows": rows,
        "issues": report_issues,
    }


def _cell(value):
    text = (
        value
        if isinstance(value, str)
        else json.dumps(value, ensure_ascii=False, allow_nan=False)
    )
    return (
        text.replace("|", "\\|")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "<br>")
    )


def write_assembly_report(report, output_dir):
    """Write independent reports. Refuse replacing any previous report."""
    # Serialize before creating files so nonfinite values cannot produce a partial JSON report.
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    lines = [
        "# 装配检查报告",
        "",
        f"结论：{report['overall']}",
        "",
        "本报告比较当前要求与资料；不单独证明实际模型已完成全部验收。",
        "",
        "| 检查 | 对象 | 预期 | 实际 | 状态 | 原因 | 证据 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["rows"]:
        values = [
            row["title"],
            row["target"],
            row["expected"],
            [f.get("actual") for f in row["findings"]],
            row["status"],
            row["reason"],
            [f.get("evidence", []) for f in row["findings"]],
        ]
        lines.append("| " + " | ".join(_cell(v) for v in values) + " |")
    lines += ["", "## 问题", ""] + [f"- {_cell(i)}" for i in report["issues"]]
    output = Path(output_dir)
    paths = [output / "assembly-verification.json", output / "assembly-verification.md"]
    if any(path.exists() for path in paths):
        raise FileExistsError("报告已存在，请使用新的阶段输出目录")
    output.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, (payload + "\n", "\n".join(lines) + "\n")):
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
