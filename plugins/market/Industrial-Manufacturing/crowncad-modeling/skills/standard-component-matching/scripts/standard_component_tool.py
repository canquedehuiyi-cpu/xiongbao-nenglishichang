"""Offline standard-component name matching over MCP-supplied catalog items."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


class ToolInputError(ValueError):
    """Raised when a local matching request does not satisfy its input contract."""


def _validate_condition_groups(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ToolInputError("nameConditionGroups 必须是非空数组")

    groups: List[Dict[str, Any]] = []
    for index, group in enumerate(value):
        if not isinstance(group, Mapping):
            raise ToolInputError(f"nameConditionGroups[{index}] 必须是对象")
        label = group.get("label")
        aliases = group.get("aliases")
        if not isinstance(label, str) or not label.strip():
            raise ToolInputError(f"nameConditionGroups[{index}].label 必须是非空文本")
        if not isinstance(aliases, list) or not aliases:
            raise ToolInputError(f"nameConditionGroups[{index}].aliases 必须是非空数组")
        if any(not isinstance(alias, str) or not alias.strip() for alias in aliases):
            raise ToolInputError(
                f"nameConditionGroups[{index}].aliases 中每项都必须是非空文本"
            )
        groups.append({"label": label, "aliases": list(aliases)})
    return groups


def _validate_catalog_items(items: Any) -> List[Mapping[str, Any]]:
    if not isinstance(items, list):
        raise ToolInputError("catalogItems 必须是扁平数组")

    validated: List[Mapping[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ToolInputError(f"catalogItems[{index}] 必须是对象")
        name = item.get("name")
        item_id = item.get("id")
        valid_id = isinstance(item_id, str) and bool(item_id.strip())
        valid_id = valid_id or (isinstance(item_id, int) and not isinstance(item_id, bool))
        if not isinstance(name, str) or not name:
            raise ToolInputError(f"catalogItems[{index}].name 必须是非空文本")
        if not valid_id:
            raise ToolInputError(f"catalogItems[{index}].id 必须是非空文本或整数")
        validated.append(item)
    return validated


def build_name_regex(condition_groups: Sequence[Mapping[str, Any]]) -> re.Pattern[str]:
    """Build an AND-across-groups / OR-within-group regex over literal text."""

    lookaheads: List[str] = []
    for group in condition_groups:
        alternatives = "|".join(re.escape(alias) for alias in group["aliases"])
        lookaheads.append(f"(?=.*(?:{alternatives}))")
    return re.compile("".join(lookaheads) + ".*", flags=re.DOTALL)


def _format_condition_summary(drawing_item: str, groups: Sequence[Mapping[str, Any]]) -> str:
    conditions = [
        f"{group['label']}={' / '.join(group['aliases'])}" for group in groups
    ]
    if drawing_item:
        return f"{drawing_item}；名称条件：" + "；".join(conditions)
    return "；".join(conditions)


def _markdown_cell(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|")


def _render_mapping_table(rows: Sequence[Mapping[str, Any]]) -> str:
    header = "| 图纸项目及名称条件 | 清单中对应的名称 | ID |\n| --- | --- | --- |"
    if not rows:
        return header + "\n| - | 未匹配 | - |"
    body = [
        "| "
        + " | ".join(
            _markdown_cell(row.get(key, ""))
            for key in ("drawingRequirement", "catalogName", "id")
        )
        + " |"
        for row in rows
    ]
    return "\n".join([header, *body])


def match_catalog_items(request: Mapping[str, Any], items: Any) -> Dict[str, Any]:
    """Filter list entries by their raw ``name`` field using generated regex."""

    groups = _validate_condition_groups(request.get("nameConditionGroups"))
    catalog_items = _validate_catalog_items(items)
    drawing_item = request.get("drawingItem", "")
    if not isinstance(drawing_item, str):
        raise ToolInputError("drawingItem 必须是文本")

    pattern = build_name_regex(groups)
    matches = [item for item in catalog_items if pattern.search(item["name"])]
    if len(matches) == 1:
        status = "unique_match"
    elif len(matches) == 0:
        status = "no_match"
    else:
        status = "ambiguous"

    drawing_requirement = _format_condition_summary(drawing_item, groups)
    rows = [
        {
            "drawingRequirement": drawing_requirement,
            "catalogName": item["name"],
            "id": item["id"],
        }
        for item in matches
    ]
    if not matches:
        rows = [
            {
                "drawingRequirement": drawing_requirement,
                "catalogName": "未匹配",
                "id": "-",
            }
        ]

    result: Dict[str, Any] = {
        "status": status,
        "standardType": request.get("standardType"),
        "drawingItem": drawing_item,
        "nameConditionGroups": groups,
        "criteriaRegex": pattern.pattern,
        "matchCount": len(matches),
        "matches": [dict(item) for item in matches],
        "mappingRows": rows,
        "mappingTableMarkdown": _render_mapping_table(rows),
        "parameters": request.get("parameters"),
        "quantity": request.get("quantity"),
    }
    if status == "unique_match":
        result["catalogItemId"] = matches[0]["id"]
        result["nextStage"] = "get_standard_component_parameters"
    elif status == "ambiguous":
        result["nextStage"] = "human_review_or_more_drawing_evidence"
    else:
        result["nextStage"] = "review_conditions_and_catalog_type"
    return result


def call_tool(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Match caller-supplied catalog items; network access belongs to MCP."""

    try:
        if request.get("operation") != "match_catalog_items":
            raise ToolInputError("operation 必须是 match_catalog_items")
        return match_catalog_items(request, request.get("catalogItems"))
    except ToolInputError as error:
        return {"status": "invalid_request", "message": str(error)}


def _read_request(path: str | None) -> Mapping[str, Any]:
    if path:
        raw = Path(path).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ToolInputError(f"输入不是有效 JSON: {error.msg}") from error
    if not isinstance(request, Mapping):
        raise ToolInputError("输入 JSON 顶层必须是对象")
    return request


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="离线标准件目录名称匹配工具")
    parser.add_argument("--input", help="输入 JSON 文件；省略时从 stdin 读取")
    args = parser.parse_args(argv)
    try:
        request = _read_request(args.input)
        result = call_tool(request)
    except (OSError, ToolInputError) as error:
        result = {"status": "invalid_request", "message": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") not in {"invalid_request"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
