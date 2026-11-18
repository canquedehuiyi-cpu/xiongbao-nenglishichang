#!/usr/bin/env python3
"""Skill Solution 生成器 - 步骤14-E：上传成功后清理临时产物

在步骤14-C（create/updateSkillAbility）返回 SUCCESS 且步骤14-D 能力档案写入后调用。
清理 dist 下全部临时产物（dist/run 中间产物 + dist/output 最终产物与 zip）。
**不触碰持久能力档案目录**（SKILL_ABILITIES_DIR / ../skill-abilities/）。
"""

from common import emit_success, emit_error, cleanup_temp


def main():
    try:
        removed = cleanup_temp()
    except Exception as e:
        emit_error("cleanup", [{
            "code": "CLEANUP_ERR_FAILED",
            "message": f"清理临时产物失败: {e}",
            "fields": []
        }])
    emit_success("cleanup", {
        "removed": removed,
        "kept": "持久能力档案目录（skill 包外）不受影响"
    })


if __name__ == "__main__":
    main()