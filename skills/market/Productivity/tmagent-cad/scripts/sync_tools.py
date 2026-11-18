#!/usr/bin/env python3
"""
sync_tools.py — 从 TmAgent MCP 端口实时生成技能工具清单。

TmAgent 把全部 CAD 命令通过 MCP 连接器 `tm-cad` 暴露为 `mcp__tm-cad__*` 工具。
本脚本对接同一后端的标准 MCP Streamable-HTTP 端点，调用 `tools/list`，
自动生成 `references/tool-inventory.md`，保证技能文档与端口实际暴露的工具一致。

前置：
    - TmAgent.dll 已在 ZWCAD 中 NETLOAD（否则 /api/mcp 不存在）
    - 默认端点 http://localhost:9876/api/mcp （可用 --base 覆盖）

用法：
    python scripts/sync_tools.py            # 生成到 references/tool-inventory.md
    python scripts/sync_tools.py --base URL # 指定端点
    python scripts/sync_tools.py --check    # 仅打印数量，不写文件
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

DEFAULT_BASE = "http://localhost:9876/api/mcp"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "references", "tool-inventory.md")

CAT_RE = re.compile(r"\[([^\]]+)\]")


def post(base, payload, session=None, timeout=20):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base, data=data, headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.headers, resp.read().decode("utf-8", "replace")


def parse_sse(text):
    out = None
    for line in text.splitlines():
        if line.startswith("data:"):
            chunk = line[5:].strip()
            try:
                out = json.loads(chunk)
            except Exception:
                pass
    if out is None:
        try:
            out = json.loads(text)
        except Exception:
            pass
    return out


def fetch_tools(base):
    h, body = post(base, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "tmagent-skill-sync", "version": "3.6.0"},
        },
    })
    sid = h.get("Mcp-Session-Id")
    init = parse_sse(body)
    server = init.get("result", {}).get("serverInfo", {}) if init else {}
    post(base, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, sid)

    tools = []
    cursor = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        _, b = post(base, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": params}, sid)
        res = parse_sse(b)
        if not res or "result" not in res:
            raise RuntimeError("tools/list 失败: " + b[:400])
        tools.extend(res["result"].get("tools", []))
        cursor = res["result"].get("nextCursor")
        if not cursor:
            break
    return server, tools


def categorize(tools):
    groups = {}
    for t in tools:
        m = CAT_RE.search(t.get("description", ""))
        cat = m.group(1) if m else "其他"
        groups.setdefault(cat, []).append(t)
    return groups


def render(server, tools):
    groups = categorize(tools)
    lines = []
    server_name = server.get("name", "TmAgent-ZWCAD")
    server_ver = server.get("version", "")
    lines.append("# TmAgent MCP 工具清单（自动生成）\n")
    lines.append(
        f"> 由 `scripts/sync_tools.py` 从 MCP 端口 (`{DEFAULT_BASE}`) 实时生成。\n"
        f"> 服务：{server_name} v{server_ver} · 共 **{len(tools)}** 个工具 / "
        f"**{len(groups)}** 个类别。\n"
        f"> 调用方式：连接器信任后直接调 `mcp__tm-cad__<工具名>`；"
        f"未连上时用 REST `GET /api/help?command=<名>` 取参数详情。\n"
    )
    # 类别概览
    lines.append("## 类别概览\n")
    lines.append("| 类别 | 工具数 |")
    lines.append("|------|------:|")
    for cat in sorted(groups, key=lambda c: -len(groups[c])):
        lines.append(f"| {cat} | {len(groups[cat])} |")
    lines.append("")

    # 逐类别详表
    for cat in sorted(groups, key=lambda c: -len(groups[c])):
        lines.append(f"## {cat}（{len(groups[cat])}）\n")
        lines.append("| 工具 | 说明 | 必填参数 |")
        lines.append("|------|------|----------|")
        for t in groups[cat]:
            name = t["name"]
            desc = CAT_RE.sub("", t.get("description", "")).strip()
            props = t.get("inputSchema", {}).get("properties", {})
            req = t.get("inputSchema", {}).get("required", [])
            if req:
                params = "、".join(f"`{p}`" for p in req)
            elif props:
                params = "（无必填）"
            else:
                params = "—"
            desc_escaped = desc.replace("|", "\\|")
            lines.append(f"| `{name}` | {desc_escaped} | {params} |")
        lines.append("")
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    base = DEFAULT_BASE
    check_only = False
    if "--base" in args:
        i = args.index("--base")
        base = args[i + 1]
    if "--check" in args:
        check_only = True
    try:
        server, tools = fetch_tools(base)
    except Exception as e:
        print(f"[sync_tools] 无法从 {base} 获取工具列表：{e}", file=sys.stderr)
        print("请确认 TmAgent.dll 已 NETLOAD 且 ZWCAD 已打开。", file=sys.stderr)
        sys.exit(1)

    print(f"服务 {server.get('name')} v{server.get('version')} · 工具数 {len(tools)}")
    if check_only:
        return
    md = render(server, tools)
    out = os.path.normpath(OUT_PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"已写入 {out}")


if __name__ == "__main__":
    main()
