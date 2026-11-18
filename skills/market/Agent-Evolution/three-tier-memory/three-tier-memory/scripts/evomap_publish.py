#!/usr/bin/env python3
"""
EvoMap 发布工具

用法:
    python evomap_publish.py --capsule capsule.json
    python evomap_publish.py --gene gene.json --capsule capsule.json
"""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

EVOMAP_HUB = "https://evomap.ai"
NODE_ID_FILE = Path.home() / ".evomap_node_id"


def canonical_json(obj: dict) -> str:
    """生成规范 JSON 字符串（排序键）"""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def compute_asset_id(asset: dict) -> str:
    """计算资产 ID (SHA256)"""
    # 移除 asset_id 字段后计算
    asset_copy = {k: v for k, v in asset.items() if k != "asset_id"}
    canonical = canonical_json(asset_copy)
    return "sha256:" + hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def get_node_id() -> str:
    """获取 Node ID"""
    if NODE_ID_FILE.exists():
        return NODE_ID_FILE.read_text().strip()
    raise ValueError("未找到 Node ID，请先运行 hello 注册")


def publish_bundle(gene: dict = None, capsule: dict = None, event: dict = None) -> dict:
    """发布资产包到 EvoMap"""

    node_id = get_node_id()
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    message_id = f"msg_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}"

    assets = []

    if gene:
        gene["asset_id"] = compute_asset_id(gene)
        assets.append(gene)

    if capsule:
        if gene:
            capsule["gene"] = gene["asset_id"]
        capsule["asset_id"] = compute_asset_id(capsule)
        assets.append(capsule)

    if event:
        if capsule:
            event["capsule_id"] = capsule["asset_id"]
        if gene:
            event["genes_used"] = [gene["asset_id"]]
        event["asset_id"] = compute_asset_id(event)
        assets.append(event)

    envelope = {
        "protocol": "gep-a2a",
        "protocol_version": "1.0.0",
        "message_type": "publish",
        "message_id": message_id,
        "sender_id": node_id,
        "timestamp": timestamp,
        "payload": {
            "assets": assets
        }
    }

    # 发送请求
    import urllib.request
    import urllib.error

    url = f"{EVOMAP_HUB}/a2a/publish"
    data = json.dumps(envelope).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"ok": False, "error": f"HTTP {e.code}: {error_body}"}


def main():
    parser = argparse.ArgumentParser(description="发布资产到 EvoMap")
    parser.add_argument("--gene", "-g", help="Gene JSON 文件路径")
    parser.add_argument("--capsule", "-c", required=True, help="Capsule JSON 文件路径")
    parser.add_argument("--event", "-e", help="EvolutionEvent JSON 文件路径")

    args = parser.parse_args()

    gene = None
    capsule = None
    event = None

    if args.gene:
        with open(args.gene, "r", encoding="utf-8") as f:
            gene = json.load(f)

    with open(args.capsule, "r", encoding="utf-8") as f:
        capsule = json.load(f)

    if args.event:
        with open(args.event, "r", encoding="utf-8") as f:
            event = json.load(f)

    print("🚀 发布到 EvoMap...")
    print(f"   Node: {get_node_id()}")

    result = publish_bundle(gene, capsule, event)

    if result.get("ok") or result.get("status") == "acknowledged":
        print("✅ 发布成功!")
        if "payload" in result:
            for asset in result["payload"].get("assets", []):
                print(f"   {asset.get('type')}: {asset.get('asset_id', 'N/A')}")
    else:
        print(f"❌ 发布失败: {result.get('error', result)}")


if __name__ == "__main__":
    main()
