#!/usr/bin/env python3
"""Skill Solution 生成器 - 节点①：参数校验"""

import argparse
import json
import os
import re

from common import load_json, find_template_dir, emit_success, emit_error, run_dir


# transport 默认值：服务端 detail 不返回 transport，由脚本常量提供（与 SKILL.md 既有约定一致）
DEFAULT_TRANSPORT = "Streamable HTTP"


def validate_industry_scene(industry_code, scene_code, templates_dir,
                            industry=None, scene=None):
    """校验行业和场景是否支持"""
    errors = []

    template_dir = find_template_dir(
        templates_dir, industry_code, scene_code, industry, scene
    )

    if template_dir is None:
        # 确定错误类型
        if industry_code:
            # 检查行业是否存在
            industry_dir = os.path.join(templates_dir, industry_code)
            if not os.path.isdir(industry_dir):
                errors.append({
                    "code": "VALIDATE_ERR_INVALID_INDUSTRY",
                    "message": f"不支持的行业编码: {industry_code}",
                    "fields": [f"industryCode={industry_code}"]
                })
                return errors
            else:
                errors.append({
                    "code": "VALIDATE_ERR_INVALID_SCENE",
                    "message": f"行业[{industry_code}]下不支持的场景编码: {scene_code}",
                    "fields": [f"sceneCode={scene_code}"]
                })
                return errors
        elif industry:
            # 中文兼容模式
            has_industry = os.path.isdir(os.path.join(templates_dir, industry)) or \
                          os.path.isdir(os.path.join(templates_dir, f"{industry}{scene}"))
            if not has_industry:
                if os.path.isdir(templates_dir):
                    for entry in os.listdir(templates_dir):
                        entry_path = os.path.join(templates_dir, entry)
                        if os.path.isdir(entry_path) and industry in entry:
                            has_industry = True
                            break
            if not has_industry:
                errors.append({
                    "code": "VALIDATE_ERR_INVALID_INDUSTRY",
                    "message": f"不支持的行业: {industry}",
                    "fields": [f"industry={industry}"]
                })
                return errors
            errors.append({
                "code": "VALIDATE_ERR_INVALID_SCENE",
                "message": f"行业[{industry}]下不支持的场景: {scene}",
                "fields": [f"scene={scene}"]
            })

    return errors


def validate_config(config, detail, switches_config=None):
    """
    校验 config 完整性（参数定义权威来源：服务端 detail = queryTemplateDetail 返回的 data）
    返回 (missing_fields, type_errors, filled_defaults, updated_config)
    """
    missing_fields = []
    type_errors = []
    filled_defaults = []

    # 深拷贝 config 避免修改原始数据
    updated_config = json.loads(json.dumps(config))

    # 确保 config 结构完整
    if "global" not in updated_config:
        updated_config["global"] = {}
    if "mcp" not in updated_config:
        updated_config["mcp"] = {}
    if "server" not in updated_config["mcp"]:
        updated_config["mcp"]["server"] = {}
    if "tools" not in updated_config["mcp"]:
        updated_config["mcp"]["tools"] = []
    if "switches" not in updated_config:
        updated_config["switches"] = {}

    # switches：服务端 detail 当前不返回 switches，恒为空（clip/switch 机制保留为预留死代码）
    switches_spec = detail.get("switches", []) or []
    if switches_config is None:
        switches_config = updated_config.get("switches", {})

    # 构建 switches 关闭时可跳过的工具集合（目前恒为空集）
    skippable_tools = set()
    for sw in switches_spec:
        sw_name = sw.get("name")
        sw_value = switches_config.get(sw_name, sw.get("default", True))
        if sw_value is False and "affects_tools" in sw:
            for tool_name in sw["affects_tools"]:
                skippable_tools.add(tool_name)

    # 校验 global 项（权威：detail.globalParamList）
    for item in detail.get("globalParamList", []):
        name = item.get("paramName")
        if not name:
            continue
        value = updated_config["global"].get(name)
        if value is None or (isinstance(value, str) and value == ""):
            default = item.get("defaultValue")
            if default is not None:
                # 自动填充默认值
                updated_config["global"][name] = default
                filled_defaults.append({"field": name, "default": default})
            elif item.get("required") == 1:
                missing_fields.append(f"config.global.{name}")
        # BOOLEAN 类型校验
        if item.get("paramValueType") == "BOOLEAN" and name in updated_config["global"]:
            val = updated_config["global"][name]
            if not isinstance(val, bool):
                type_errors.append(f"config.global.{name}")

    # 校验 mcp.server（权威：detail.mcpServerParamList）
    server_config = updated_config["mcp"]["server"]
    for item in detail.get("mcpServerParamList", []):
        name = item.get("paramName")
        if not name:
            continue
        value = server_config.get(name)
        if value is None or (isinstance(value, str) and value == ""):
            default = item.get("defaultValue")
            if default is not None:
                server_config[name] = default
                filled_defaults.append({"field": f"server.{name}", "default": default})
            elif item.get("required") == 1:
                missing_fields.append(f"config.mcp.server.{name}")

    # transport 默认值（脚本常量，服务端 detail 不返回 transport）
    if not server_config.get("transport"):
        server_config["transport"] = DEFAULT_TRANSPORT
        filled_defaults.append({"field": "server.transport", "default": DEFAULT_TRANSPORT})

    # 校验 mcp.tools（权威：detail.mcpToolList）
    config_tools = updated_config["mcp"]["tools"]
    config_tool_map = {t.get("name"): t for t in config_tools if "name" in t}
    for tool_spec in detail.get("mcpToolList", []):
        tool_name = tool_spec.get("toolName")
        if not tool_name:
            continue
        is_skippable = tool_name in skippable_tools
        if tool_name not in config_tool_map:
            # MCP_TOOL 未在 config 中提供 → 自动填充默认值（value=toolName）
            updated_config["mcp"]["tools"].append({"name": tool_name, "value": tool_name})
            filled_defaults.append({"field": f"mcp.tools[{tool_name}]", "default": tool_name})
        else:
            # MCP 工具名格式校验（仅对已提供的工具）
            name_val = str(config_tool_map[tool_name].get("name", ""))
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name_val):
                type_errors.append(f"config.mcp.tools[{tool_name}].name")

    # 校验 switches 类型 + 默认值填充（恒空，预留）
    for sw in switches_spec:
        sw_name = sw.get("name")
        sw_value = updated_config["switches"].get(sw_name)
        if sw_value is None:
            if sw.get("default") is not None:
                updated_config["switches"][sw_name] = sw["default"]
                filled_defaults.append({"field": f"switches.{sw_name}", "default": sw["default"]})
        elif sw.get("type") == "boolean":
            if not isinstance(sw_value, bool):
                type_errors.append(f"config.switches.{sw_name}")

    return missing_fields, type_errors, filled_defaults, updated_config


def build_config_from_biz_param(biz_param, detail):
    """从 bizParam 数组构建 config 结构（消除 AI 手写 config.json）

    bizParam 格式: [{"paramType":"GLOBAL","paramName":"xxx","paramValue":"yyy"}, ...]
    config 格式: {"global":{...}, "mcp":{"server":{...}, "tools":[...]}, "switches":{...}}
    """
    config = {"global": {}, "mcp": {"server": {}, "tools": []}, "switches": {}}

    for item in biz_param:
        param_type = item.get("paramType", "")
        name = item.get("paramName", "")
        value = item.get("paramValue", "")

        if param_type == "GLOBAL":
            config["global"][name] = value
        elif param_type == "MCP_SERVER":
            config["mcp"]["server"][name] = value
        elif param_type == "MCP_TOOL":
            config["mcp"]["tools"].append({"name": name, "value": value})
        elif param_type == "SWITCH":
            config["switches"][name] = value == "true"

    # 保留 industryCode/sceneCode 便于后续脚本定位模板
    config["industryCode"] = detail.get("industryCode", "")
    config["sceneCode"] = detail.get("sceneCode", "")

    return config


def main():
    parser = argparse.ArgumentParser(description="Skill Solution 生成器 - 参数校验")
    parser.add_argument("--config", default=None, help="品牌配置 JSON 文件路径（与 --biz-param 二选一）")
    parser.add_argument("--biz-param", default=None, help="bizParam JSON 数组（交互式模式，替代 --config）")
    parser.add_argument("--template-detail", required=True, help="queryTemplateDetail 返回 data 落盘 JSON 路径（参数定义权威）")
    parser.add_argument("--templates-dir", required=True, help="模板仓库根目录（用于定位本地 .md 模板）")
    parser.add_argument("--industry-code", default=None, help="本地行业编码（定位模板目录）")
    parser.add_argument("--scene-code", default=None, help="本地场景编码（定位模板目录）")
    parser.add_argument("--industry", default=None, help="行业名称（兼容）")
    parser.add_argument("--scene", default=None, help="场景名称（兼容）")
    parser.add_argument("--output", default=None, help="校验后配置输出路径")
    args = parser.parse_args()

    if not args.config and not args.biz_param:
        parser.error("必须提供 --config 或 --biz-param")

    detail = load_json(args.template_detail)

    if args.biz_param:
        biz_param = json.loads(args.biz_param)
        config = build_config_from_biz_param(biz_param, detail)
    else:
        config = load_json(args.config)

    # 本地目录定位编码：仅从入参/config 取（detail.industryCode/sceneCode 仅作回显，不覆盖入参，
    # 避免服务端编码与本地目录编码不一致时找不到模板目录）
    industry_code = args.industry_code or config.get("industryCode", "")
    scene_code = args.scene_code or config.get("sceneCode", "")
    industry = args.industry or config.get("industry", "")
    scene = args.scene or config.get("scene", "")

    # 行业/场景校验（本地模板目录存在性）
    all_errors = validate_industry_scene(
        industry_code, scene_code, args.templates_dir, industry, scene
    )

    # 参数校验（权威来源：服务端 detail）
    missing_fields, type_errors, filled_defaults, updated_config = validate_config(
        config, detail
    )

    if missing_fields:
        all_errors.append({
            "code": "VALIDATE_ERR_MISSING_REQUIRED",
            "message": "必填字段缺失",
            "fields": missing_fields
        })

    if type_errors:
        all_errors.append({
            "code": "VALIDATE_ERR_TYPE_MISMATCH",
            "message": "类型不匹配",
            "fields": type_errors
        })

    if all_errors:
        emit_error("validate", all_errors)

    # 输出校验后的完整配置
    output_path = args.output
    if not output_path:
        output_path = os.path.join(run_dir(), "validated_config.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(updated_config, f, ensure_ascii=False, indent=2)

    emit_success("validate", {
        "filled_defaults": filled_defaults,
        "template_info": {
            "templateCode": detail.get("templateCode", ""),
            "templateVersion": detail.get("templateVersion", ""),
            "industryCode": detail.get("industryCode", ""),
            "sceneCode": detail.get("sceneCode", ""),
            "localIndustryCode": industry_code,
            "localSceneCode": scene_code
        }
    })


if __name__ == "__main__":
    main()
