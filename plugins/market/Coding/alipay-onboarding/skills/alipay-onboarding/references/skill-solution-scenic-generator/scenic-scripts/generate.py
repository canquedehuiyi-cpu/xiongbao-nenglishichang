#!/usr/bin/env python3
"""Skill Solution 生成器 - 节点②：生成（加载模板+裁剪+替换）"""

import argparse
import json
import os
import re

from common import load_json, load_text, find_template_dir, emit_success, emit_error, emit_warning, output_dir


def clip_template(text, switches_spec, switches_config):
    """
    CLIP 标记裁剪
    switch=false → 删除 <!-- CLIP:{id} START -->...<!-- CLIP:{id} END --> 整段
    switch=true  → 仅删除标记行，保留内容
    """
    clipped_steps = []
    kept_steps = []

    for sw in switches_spec:
        clip_id = sw.get("clip_id")
        if not clip_id:
            continue

        sw_name = sw["name"]
        sw_value = switches_config.get(sw_name, sw.get("default", True))

        # 匹配 CLIP 标记块
        pattern = re.compile(
            r'<!--\s*CLIP:' + re.escape(clip_id) + r'\s+START\s*-->\n'
            r'(.*?)'
            r'<!--\s*CLIP:' + re.escape(clip_id) + r'\s+END\s*-->\n',
            re.DOTALL
        )

        match = pattern.search(text)
        if not match:
            continue

        if sw_value is False:
            # 删除整段（含标记行）
            text = pattern.sub('', text)
            clipped_steps.append({
                "clip_id": clip_id,
                "step_name": sw.get("description", clip_id),
                "value": False
            })
        else:
            # 仅删除标记行，保留中间内容
            content = match.group(1)
            text = text[:match.start()] + content + text[match.end():]
            kept_steps.append({
                "clip_id": clip_id,
                "step_name": sw.get("description", clip_id),
                "value": True
            })

    # 清理连续空行（3个及以上连续空行 → 2个）
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text, clipped_steps, kept_steps


def build_replacement_map(config, detail, switches_config, switches_spec):
    """
    构建占位符替换映射表（工具兜底权威：detail.mcpToolList）
    顺序：global → mcp 顶层(mcpPrefix) → mcp.tools
    switches 布尔值不进映射
    """
    replacements = []

    # 1. global 级
    global_config = config.get("global", {})
    for key, value in global_config.items():
        replacements.append({
            "placeholder": key,
            "value": str(value) if value is not None else ""
        })

    # 2. mcp 顶层级 - mcpPrefix
    mcp_prefix = config.get("mcp", {}).get("server", {}).get("mcpPrefix", "")
    if mcp_prefix:
        replacements.append({
            "placeholder": "mcpPrefix",
            "value": mcp_prefix
        })

    # 3. mcp.tools 级 - config 优先，detail.mcpToolList 兜底
    config_tools = config.get("mcp", {}).get("tools", [])
    config_tool_map = {t.get("name", ""): t for t in config_tools if t.get("name")}

    # 工具兜底权威：detail.mcpToolList（toolName）
    spec_tools = [{"name": t.get("toolName", "")} for t in detail.get("mcpToolList", [])]
    for tool_spec in spec_tools:
        tool_name = tool_spec.get("name", "")
        if not tool_name:
            continue
        if tool_name in config_tool_map:
            # config 有传 → 用 config 的 value
            tool_value = config_tool_map[tool_name].get("value", tool_name)
        else:
            # config 没传 → 用模板 name 兜底
            tool_value = tool_name
        replacements.append({
            "placeholder": tool_name,
            "value": str(tool_value) if tool_value is not None else tool_name
        })

    return replacements


def replace_placeholders(text, replacements):
    """
    执行占位符替换
    【{{name}}】 → value
    空值 → 空字符串
    未找到映射 → 保留原样
    """
    replaced_count = 0

    for rep in replacements:
        placeholder = rep["placeholder"]
        value = rep["value"]
        pattern = re.compile(r'【\{\{' + re.escape(placeholder) + r'\}\}】')
        matches = pattern.findall(text)
        if matches:
            text = pattern.sub(value, text)
            replaced_count += len(matches)

    return text, replaced_count


def scan_unresolved_placeholders(text):
    """扫描未替换的占位符 【{{xxx}}】（原 revise.py 逻辑）"""
    unresolved = []
    lines = text.split('\n')
    pattern = re.compile(r'【\{\{([^}]+)\}\}】')

    for line_num, line in enumerate(lines, 1):
        for match in pattern.finditer(line):
            placeholder = match.group(1)
            context = line.strip()
            if len(context) > 80:
                context = context[:77] + "..."
            unresolved.append({
                "placeholder": placeholder,
                "line": line_num,
                "context": context
            })

    return unresolved


def check_mcp_format(text):
    """检查 MCP 工具调用格式正确性（原 revise.py 逻辑）"""
    format_errors = []

    lines = text.split('\n')
    for line_num, line in enumerate(lines, 1):
        if '$' in line and '【{{' in line:
            context = line.strip()
            if len(context) > 80:
                context = context[:77] + "..."
            format_errors.append({
                "line": line_num,
                "context": context,
                "issue": "MCP 工具调用中存在未替换的占位符"
            })

    return format_errors


def main():
    parser = argparse.ArgumentParser(description="Skill Solution 生成器 - 生成节点")
    parser.add_argument("--industry-code", default=None, help="行业编码")
    parser.add_argument("--scene-code", default=None, help="场景编码")
    parser.add_argument("--industry", default=None, help="行业名称（兼容）")
    parser.add_argument("--scene", default=None, help="场景名称（兼容）")
    parser.add_argument("--templates-dir", required=True, help="模板仓库根目录")
    parser.add_argument("--config", required=True, help="品牌配置 JSON 文件路径（校验后）")
    parser.add_argument("--template-detail", required=True, help="queryTemplateDetail 返回 data 落盘 JSON 路径（参数定义权威）")
    parser.add_argument("--ability-en-name", required=True, help="能力英文名称（节点②确认后生成）")
    parser.add_argument("--output-dir", default=None, help="最终产物输出根目录（默认 dist/output/skills）")
    args, _ = parser.parse_known_args()

    config = load_json(args.config)
    detail = load_json(args.template_detail)

    # 从 config 中也尝试取 industryCode/sceneCode
    industry_code = args.industry_code or config.get("industryCode", "")
    scene_code = args.scene_code or config.get("sceneCode", "")
    industry = args.industry or config.get("industry", "")
    scene = args.scene or config.get("scene", "")

    # 查找模板目录
    template_dir = find_template_dir(
        args.templates_dir, industry_code, scene_code, industry, scene
    )
    if not template_dir:
        loc_info = f"industryCode={industry_code}" if industry_code else f"industry={industry}"
        scene_info = f"sceneCode={scene_code}" if scene_code else f"scene={scene}"
        emit_error("generate", [{
            "code": "GENERATE_ERR_TEMPLATE_NOT_FOUND",
            "message": f"未找到模板目录: {loc_info}, {scene_info}",
            "fields": [loc_info, scene_info]
        }])

    # 加载 template.json
    template_json_path = os.path.join(template_dir, "template.json")
    if not os.path.isfile(template_json_path):
        emit_error("generate", [{
            "code": "GENERATE_ERR_TEMPLATE_NOT_FOUND",
            "message": f"模板目录中缺少 template.json",
            "fields": [template_dir]
        }])

    spec_data = load_json(template_json_path)

    # 加载 Skill 模板
    skill_template_name = spec_data.get("skillTemplate", spec_data.get("skill_template", "SKILL.md"))
    skill_template_path = os.path.join(template_dir, skill_template_name)
    if not os.path.isfile(skill_template_path):
        emit_error("generate", [{
            "code": "GENERATE_ERR_TEMPLATE_NOT_FOUND",
            "message": f"未找到 Skill 模板文件: {skill_template_path}",
            "fields": [skill_template_name]
        }])

    skill_text = load_text(skill_template_path)
    if not skill_text.strip():
        emit_error("generate", [{
            "code": "GENERATE_ERR_TEMPLATE_INVALID",
            "message": "Skill 模板文件为空",
            "fields": [skill_template_path]
        }])

    # CLIP 裁剪（switches 权威：detail；服务端当前不返回 switches，恒为空，clip 为预留死代码）
    switches_spec = detail.get("switches", []) or []
    switches_config = config.get("switches", {})
    skill_text, clipped_steps, kept_steps = clip_template(
        skill_text, switches_spec, switches_config
    )

    # 构建替换映射
    replacements = build_replacement_map(config, detail, switches_config, switches_spec)

    # 注入 skillName 占位符（来自节点②确认后的 abilityEnName，非 bizParam 传入）
    if args.ability_en_name:
        replacements.insert(0, {
            "placeholder": "skillName",
            "value": args.ability_en_name
        })

    # 执行占位符替换
    skill_text, replaced_count = replace_placeholders(skill_text, replacements)

    # 扫描未替换占位符（原 revise.py 逻辑，合入此步）
    unresolved = scan_unresolved_placeholders(skill_text)
    mcp_format_errors = check_mcp_format(skill_text)

    # 写入最终产物目录（原 output.py 逻辑，合入此步）
    out_root = args.output_dir or output_dir()
    target_dir = os.path.join(out_root, args.ability_en_name)
    target_path = os.path.join(target_dir, "SKILL.md")
    os.makedirs(target_dir, exist_ok=True)
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(skill_text)
    except OSError as e:
        emit_error("generate", [{
            "code": "GENERATE_ERR_WRITE_FAILED",
            "message": f"写入产物失败: {e}",
            "fields": [target_dir]
        }])

    # 构建替换详情（去重显示）
    replacement_details = []
    for rep in replacements:
        replacement_details.append({
            "placeholder": rep["placeholder"],
            "value": rep["value"]
        })

    # 构建警告列表（不阻塞，仅记录）
    errors = []
    if unresolved:
        placeholder_names = list(set(u["placeholder"] for u in unresolved))
        errors.append({
            "code": "REVISE_WARN_PLACEHOLDER_REMAIN",
            "message": f"存在{len(placeholder_names)}个未替换的占位符",
            "fields": placeholder_names
        })
    if mcp_format_errors:
        errors.append({
            "code": "REVISE_WARN_MCP_FORMAT",
            "message": f"存在{len(mcp_format_errors)}个MCP格式异常",
            "fields": [f"line {e['line']}" for e in mcp_format_errors]
        })

    data = {
        "output_path": target_path,
        "content_size": len(skill_text.encode("utf-8")),
        "version": detail.get("templateVersion", spec_data.get("version", "1.0.0")),
        "templateCode": detail.get("templateCode", spec_data.get("templateCode", "")),
        "flow_description": [
            {"step": s.get("stepOrder"), "name": s.get("stepName"), "description": s.get("stepDesc")}
            for s in detail.get("previewFlow", [])
        ],
        "clipped_steps": clipped_steps,
        "kept_steps": kept_steps,
        "replaced_count": replaced_count,
        "replacements": replacement_details,
        "unresolved": unresolved,
        "mcp_format_errors": mcp_format_errors
    }

    if errors:
        emit_warning("generate", data, errors)
    else:
        emit_success("generate", data)


if __name__ == "__main__":
    main()
