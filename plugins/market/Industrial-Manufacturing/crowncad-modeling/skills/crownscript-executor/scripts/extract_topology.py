"""离线提取 CrownCAD 业务 JSON；不连接 CAD，不推断缺失关系。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

COLLECTIONS = {"entities": "solid", "shells": "shell", "faces": "face",
               "edges": "edge", "vertices": "vertex", "curves": "curve"}
KINDS = tuple(COLLECTIONS.values())


def records(data):
    if not isinstance(data, dict):
        raise ValueError("输入必须是业务 JSON 对象")
    result = []
    if "items" in data:
        if not isinstance(data["items"], list) or not isinstance(data.get("objects", []), list):
            raise ValueError("items/objects 必须是数组")
        groups = [("element", data["items"]), ("object", data.get("objects", []))]
        for scope, rows in groups:
            for row in rows:
                identity = "id" if scope == "element" else "entityId"
                if not isinstance(row, dict) or row.get("kind") not in KINDS or identity not in row:
                    raise ValueError("记录缺少有效 kind 或身份字段")
                result.append((scope, dict(row)))
    elif "documentId" in data and any(key in data for key in COLLECTIONS):
        for collection, kind in COLLECTIONS.items():
            rows = data.get(collection, {})
            if not isinstance(rows, dict):
                raise ValueError(f"{collection} 必须是对象")
            for key, row in rows.items():
                if not isinstance(row, dict):
                    raise ValueError(f"{collection} 记录必须是对象")
                identity = int(key)
                scope = "object" if collection in ("entities", "shells") else "element"
                identity_field = "entityId" if scope == "object" else "id"
                if identity_field in row and row[identity_field] != identity:
                    raise ValueError(f"{collection} 身份字段与索引不一致")
                normalized = dict(row, kind=kind)
                normalized[identity_field] = identity
                result.append((scope, normalized))
                if collection == "curves" and "entityId" in row:
                    result.append(("object", dict(row, kind=kind)))
    else:
        raise ValueError("不支持的业务格式；需要 topology-compact/full 或 geometry JSON")
    for scope, row in result:
        value = row["id" if scope == "element" else "entityId"]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("身份字段必须是整数")
    return result


def extract(data, *, kinds=(), ids=(), owner_ids=(), fields=(), summary=False, scope="element"):
    rows = records(data)
    if set(kinds) - set(KINDS):
        raise ValueError("不支持的类别")
    if scope not in ("element", "object"):
        raise ValueError("scope 必须是 element 或 object")
    output = {"counts": dict(Counter(f"{s}:{r['kind']}" for s, r in rows)),
              "sourceMetadata": {k: data[k] for k in (
                  "document", "documentId", "versionId", "docType", "level", "coverage",
                  "requestedKinds", "requestedEntityIds", "requestedElements", "missingCollections"
              ) if k in data},
              "sourceIssues": data.get("issues", []), "recordIssues": [],
              "missingIds": [], "missingFields": [], "unknownOwners": []}
    for s, row in rows:
        if (row.get("status") not in (None, "available") or row.get("parseError")
                or row.get("elementInfoParseStatus") not in (None, "parsed")):
            output["recordIssues"].append({"scope": s, **{k: row[k] for k in (
                "kind", "id", "entityId", "status", "parseError", "elementInfoParseStatus"
            ) if k in row}})
    if summary or not any((kinds, ids, owner_ids, fields)):
        output["mode"] = "summary"
        return output
    selected = []
    identity_key = "id" if scope == "element" else "entityId"
    seen_ids = set()
    for s, row in rows:
        if s != scope or kinds and row["kind"] not in kinds:
            continue
        identity = row[identity_key]
        if ids and identity not in ids:
            continue
        seen_ids.add(identity)
        if owner_ids:
            owners = row.get("owners")
            if s == "object":
                owners = [{"entityId": identity}]
            if not isinstance(owners, list) or any(
                not isinstance(v, dict) or isinstance(v.get("entityId"), bool)
                or not isinstance(v.get("entityId"), int) for v in owners
            ):
                output["unknownOwners"].append({"kind": row["kind"], identity_key: identity})
                continue
            if not set(owner_ids).intersection(v["entityId"] for v in owners):
                continue
        if fields:
            projected = {"kind": row["kind"], identity_key: identity}
            for field in fields:
                if field in row:
                    projected[field] = row[field]
                else:
                    output["missingFields"].append({"kind": row["kind"], identity_key: identity, "field": field})
            selected.append(projected)
        else:
            selected.append(row)
    output.update(mode="selection", scope=scope, matchedCount=len(selected), items=selected,
                  missingIds=sorted(set(ids) - seen_ids))
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog="默认仅概况；不截断。退出码：0=提取完成（仍需检查缺失/异常），2=输入或参数错误。--fields 选择顶层字段，完整保留嵌套值。")
    parser.add_argument("file", type=Path)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--scope", choices=("element", "object"), default="element")
    parser.add_argument("--kind", choices=KINDS, action="append", default=[])
    parser.add_argument("--id", type=int, action="append", default=[])
    parser.add_argument("--owner-id", type=int, action="append", default=[])
    parser.add_argument("--fields", default="")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.file.read_text(encoding="utf-8-sig"),
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"非法数值 {value}")))
        result = extract(data, kinds=args.kind, ids=args.id, owner_ids=args.owner_id,
                         fields=[f.strip() for f in args.fields.split(",") if f.strip()],
                         summary=args.summary, scope=args.scope)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
