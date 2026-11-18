#!/usr/bin/env python3
"""Skill Solution 生成器 - 节点⑥-C 辅助：把用户实例化参数组装成 createSkillAbility.configParamList

仅输出模板定义的配置参数：GLOBAL + MCP_SERVER。MCP_TOOL 不进 configParamList
（服务端会报 "param[xxx] is not defined in template"），MCP 工具绑定由 mcpRelList 承担。

数据来源：
  - paramType / paramName / paramValueType / description / sortOrder ← template_detail.json（服务端 queryTemplateDetail 返回权威）
  - paramValue ← validated_config.json（阶段0-D 用户填写，节点① 校验补全后）
"""

import argparse
import json
import os

from common import load_json, emit_success


def build_config_param_list(detail, validated_config):
    """从 detail + validated_config 组装 configParamList"""
    config_param_list = []

    # 1. GLOBAL 参数
    for item in detail.get("globalParamList", []):
        param_name = item.get("paramName")
        if not param_name:
            continue
        value = (validated_config.get("global") or {}).get(param_name)
        config_param_list.append({
            "paramType": item.get("paramType", "GLOBAL"),
            "paramName": param_name,
            "paramValueType": item.get("paramValueType", "STRING"),
            "paramValue": value if value is not None else "",
            "description": item.get("description", ""),
            "sortOrder": item.get("sortOrder", len(config_param_list) + 1)
        })

    # 2. MCP_SERVER 参数
    for item in detail.get("mcpServerParamList", []):
        param_name = item.get("paramName")
        if not param_name:
            continue
        value = (validated_config.get("mcp", {}).get("server") or {}).get(param_name)
        config_param_list.append({
            "paramType": item.get("paramType", "MCP_SERVER"),
            "paramName": param_name,
            "paramValueType": item.get("paramValueType", "STRING"),
            "paramValue": value if value is not None else "",
            "description": item.get("description", ""),
            "sortOrder": item.get("sortOrder", len(config_param_list) + 1)
        })

    # 3. MCP_TOOL 不进 configParamList：服务端 createSkillAbility 只认模板定义的配置参数
    #    （GLOBAL + MCP_SERVER）。工具属 mcpToolList、非配置参数，传入会报
    #    "param[xxx] is not defined in template"。MCP 工具绑定改由 mcpRelList
    #    （mcpAbilityCode + serverDiscoveryCode）承担，故此处不输出 MCP_TOOL。

    return config_param_list


def main():
    parser = argparse.ArgumentParser(description="组装 createSkillAbility.configParamList")
    parser.add_argument("--config", required=True, help="validated_config.json 路径（节点① 输出）")
    parser.add_argument("--template-detail", required=True, help="template_detail.json 路径（阶段0-C 落盘）")
    args = parser.parse_args()

    validated_config = load_json(args.config)
    detail = load_json(args.template_detail)

    config_param_list = build_config_param_list(detail, validated_config)

    emit_success("to_config_param", {
        "count": len(config_param_list),
        "configParamList": config_param_list,
        "summary": {
            "global": sum(1 for x in config_param_list if x["paramType"] == "GLOBAL"),
            "mcp_server": sum(1 for x in config_param_list if x["paramType"] == "MCP_SERVER")
        }
    })


if __name__ == "__main__":
    main()
