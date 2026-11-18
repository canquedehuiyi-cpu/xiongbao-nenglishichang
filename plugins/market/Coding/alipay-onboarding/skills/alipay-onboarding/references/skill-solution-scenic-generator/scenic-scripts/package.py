#!/usr/bin/env python3
"""Skill Solution 生成器 - 节点⑥-A：产物打包为 zip（顶层目录为 abilityEnName）"""

import argparse
import os
import zipfile

from common import emit_success, emit_error


def zip_directory(src_dir, ability_en_name, zip_path):
    """把 src_dir 下所有文件打包到 zip_path，zip 内顶层目录为 ability_en_name"""
    file_count = 0
    included_files = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            dirs.sort()
            for fname in sorted(files):
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, src_dir)
                # zip 内顶层目录为 abilityEnName，解压即得 {abilityEnName}/SKILL.md 及子文件
                arcname = os.path.join(ability_en_name, rel_path)
                zf.write(abs_path, arcname)
                included_files.append(arcname)
                file_count += 1
    return file_count, included_files


def main():
    parser = argparse.ArgumentParser(description="Skill Solution 生成器 - 产物打包为 zip")
    parser.add_argument("--skill-dir", required=True, help="节点⑤ 产物目录 {output-dir}/{abilityEnName}")
    parser.add_argument("--ability-en-name", required=True, help="能力英文名称（zip 内顶层目录名）")
    parser.add_argument("--output", default=None, help="zip 输出路径，默认 {SKILL_ROOT}/dist/output/{abilityEnName}.zip")
    args = parser.parse_args()

    skill_dir = args.skill_dir
    ability_en_name = args.ability_en_name

    # 校验产物目录存在
    if not os.path.isdir(skill_dir):
        emit_error("package", [{
            "code": "PACKAGE_ERR_SKILL_DIR_MISSING",
            "message": f"产物目录不存在: {skill_dir}",
            "fields": [skill_dir]
        }])

    # 校验 SKILL.md 存在
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        emit_error("package", [{
            "code": "PACKAGE_ERR_SKILL_MD_MISSING",
            "message": f"产物目录中缺少 SKILL.md: {skill_md}",
            "fields": [skill_md]
        }])

    # 默认输出路径 {SKILL_ROOT}/dist/output/{abilityEnName}.zip
    output_path = args.output
    if not output_path:
        skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(skill_root, "dist", "output", f"{ability_en_name}.zip")

    # 创建输出目录
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # 打包
    try:
        file_count, included_files = zip_directory(skill_dir, ability_en_name, output_path)
    except Exception as e:
        emit_error("package", [{
            "code": "PACKAGE_ERR_ZIP_FAILED",
            "message": f"打包失败: {e}",
            "fields": [output_path]
        }])

    emit_success("package", {
        "zip_path": output_path,
        "ability_en_name": ability_en_name,
        "file_count": file_count,
        "skill_md_included": os.path.join(ability_en_name, "SKILL.md") in included_files,
        "included_files": included_files
    })


if __name__ == "__main__":
    main()
