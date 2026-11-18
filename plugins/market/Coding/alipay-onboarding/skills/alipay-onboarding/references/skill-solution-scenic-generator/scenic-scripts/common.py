#!/usr/bin/env python3
"""Skill Solution 生成器 - 公共工具模块

提供各脚本共用的文件加载、模板目录定位与 JSON 响应构造能力。
所有脚本通过 `from common import ...` 引用，避免重复代码。
"""

import json
import os
import sys

# 确保可以 from common import ... （脚本与 common.py 同目录）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_json(path):
    """加载 JSON 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path):
    """加载文本文件"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def find_template_dir(templates_dir, industry_code=None, scene_code=None,
                      industry=None, scene=None):
    """查找行业+场景对应的模板目录，优先使用编码查找

    查找顺序：
    1. 编码: templates/{industryCode}/{sceneCode}/
    2. 中文: templates/{industry}{scene}/ 或 templates/{industry}/{scene}/
    3. 兜底: 遍历 template.json 按 industryCode/sceneCode 匹配
    """
    # 优先使用编码: templates/{industryCode}/{sceneCode}/
    if industry_code and scene_code:
        dir_code = os.path.join(templates_dir, industry_code, scene_code)
        if os.path.isdir(dir_code):
            return dir_code

    # 兼容中文
    if industry and scene:
        dir1 = os.path.join(templates_dir, f"{industry}{scene}")
        if os.path.isdir(dir1):
            return dir1
        dir2 = os.path.join(templates_dir, industry, scene)
        if os.path.isdir(dir2):
            return dir2
        industry_dir = os.path.join(templates_dir, industry)
        if os.path.isdir(industry_dir):
            for entry in os.listdir(industry_dir):
                entry_path = os.path.join(industry_dir, entry)
                if os.path.isdir(entry_path) and scene in entry:
                    return entry_path

    # 兜底: 遍历 template.json 按 industryCode/sceneCode 匹配
    if industry_code and scene_code:
        for root, dirs, files in os.walk(templates_dir):
            if "template.json" in files:
                try:
                    t = load_json(os.path.join(root, "template.json"))
                    if (t.get("industryCode") == industry_code and
                            t.get("sceneCode") == scene_code):
                        return root
                except Exception:
                    pass

    return None


def run_dir():
    """返回运行时中间产物目录 {SKILL_ROOT}/dist/run/，不存在则创建。

    中间产物（template_detail.json / validated_config.json）统一落此目录，
    避免污染 skill 源码根目录。最终产物 SKILL.md 由 generate.py 写到 output_dir()；
    打包 zip 由 package.py 写到 dist/output/。
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "run"
    )
    os.makedirs(path, exist_ok=True)
    return path


def output_dir():
    """返回最终产物 SKILL.md 的输出根目录 {SKILL_ROOT}/dist/output/skills/，不存在则创建。

    最终产物与中间产物统一收敛到 dist/ 下，便于一次性清理；持久能力档案在 skill 包之外
    （环境变量 SKILL_ABILITIES_DIR / ../skill-abilities/），不受 dist 清理影响。
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "output", "skills"
    )
    os.makedirs(path, exist_ok=True)
    return path


def dist_root():
    """返回 {SKILL_ROOT}/dist 根目录"""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist"
    )


def cleanup_temp():
    """清理 dist 下全部临时产物（dist/run 中间产物 + dist/output 最终产物与 zip）。

    在步骤14 上传成功且能力档案写入后调用。**不触碰持久能力档案目录**
    （SKILL_ABILITIES_DIR / ../skill-abilities/，位于 skill 包外，重装不丢）。
    返回已删除的顶层条目列表。
    """
    import shutil
    removed = []
    root = dist_root()
    if not os.path.isdir(root):
        return removed
    for sub in ("run", "output"):
        sub_path = os.path.join(root, sub)
        if os.path.isdir(sub_path):
            shutil.rmtree(sub_path, ignore_errors=True)
            removed.append(sub_path)
    return removed


def make_response(node, status, data=None, errors=None):
    """构造统一的 JSON 响应输出到 stdout

    Args:
        node: 节点名称（如 "validate", "generate" 等）
        status: "success" / "error" / "warning"
        data: 业务数据字典
        errors: 错误/警告列表
    """
    react = {
        "node": node,
        "status": status,
        "data": data or {},
        "errors": errors or []
    }
    print(json.dumps(react, ensure_ascii=False, indent=2))


def emit_success(node, data=None):
    """输出成功响应并退出"""
    make_response(node, "success", data)
    sys.exit(0)


def emit_error(node, errors, data=None):
    """输出错误响应并退出"""
    make_response(node, "error", data, errors)
    sys.exit(1)


def emit_warning(node, data=None, errors=None):
    """输出警告响应并退出（退出码 0，不阻塞）"""
    make_response(node, "warning", data, errors)
    sys.exit(0)
