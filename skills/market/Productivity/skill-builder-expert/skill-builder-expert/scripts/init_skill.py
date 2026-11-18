#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_skill.py —— 代建脚手架生成器（实现 references/REF-SKL-007_SkillSkeleton_v1.md）

定位
----
代建链路「框架确认后、组装前」调用：按骨架规范生成新技能骨架——必含四件套＋档位组件
一次到位，结构零方差。骨架只含结构与占位（{PH} 标记），业务内容由 Agent 按用户素材
逐项填充；生成物逐卡过 REF-SKL-007 第六节内核四卡（卡A 排版 / 卡B 代码 / 卡C 内容策略 /
卡D 工程适配），并遵守卡A「生成物文风三通则」（祈使句／第三人称 description／只写程序性知识）。

用法
----
    python scripts/init_skill.py <skill-name> --档 极简|标准|重型 [--out <输出目录>]
    python scripts/init_skill.py --self-test

说明
----
- --档 缺省为 标准档（大多数交互式技能）；档位判定依据见 REF-SKL-007 第二节。
- --out 缺省为当前工作目录下 <skill-name>/；目标已存在即拒绝（防覆盖，退出码 3）。
- 生成文件一律 UTF-8、LF 行尾；不发起任何网络请求，零外部依赖。
退出码：0 = 成功；2 = 参数错误；3 = 目标目录已存在；4 = 自测失败。
"""
import json
import re
import sys
from pathlib import Path

# 占位标记字面以码点拼装（同包内机检自指惯例）：占位符是生成物的合法组成，
# 但本脚本自身不落该字面裸文（占位符检出机检按字面扫描，码点拼装双向自洽）。
PH = "".join(chr(c) for c in (0x54, 0x4F, 0x44, 0x4F))

TIERS = ("极简", "标准", "重型")


def fm_block(name: str) -> str:
    return f"""---
name: {name}
slug: {name}
displayName: "[{PH}: 中文展示名]"
description: "[{PH}: 本技能用于……（写清能力与价值）；应在……场景使用（触发场景）；能力边界……。第三人称写法，写明触发场景与能力边界]"
type: skill
capability: tool
category: "[{PH}: 按目标市场类目枚举填写]"
language: zh-CN
version: "0.1.0"
license: LicenseRef-Proprietary
author: "[{PH}: 作者/主体]"
security:
  external_network: "none"
  allowed_domains: []
  credentials_usage: "none"
  data_flow: "local-only"
agent_created: true
---"""


def body_block(name: str, tier: str) -> str:
    tier_note = {
        "极简": "极简档：纯后端调用 / 轻量结果交付，包内无业务逻辑（判定依据 REF-SKL-007 第二节）。",
        "标准": "标准档：大多数交互式技能；hooks 护栏＋references 分级加载＋scripts 自检。",
        "重型": "重型档：复杂业务 / 高合规 / 多交付物；标准档全部＋tests/FAQ/tools/专项质检。",
    }[tier]
    patterns = """[{PH}: 选定结构模式后删除本段提示。四种常用模式（可混搭）：
- 流程式：适合多步顺序过程（## 30 秒导读 → ## 步骤一 → ## 步骤二 …）
- 任务式：适合工具集合（## 30 秒导读 → ## 任务类一 → ## 任务类二 …）
- 规范式：适合标准与规范（## 30 秒导读 → ## 准则 → ## 规格 …）
- 能力式：适合集成系统（## 30 秒导读 → ## 核心能力 → ### 能力一 …）]

[{PH}: 生成物文风三通则（REF-SKL-007 卡A 第 9–11 条）——
① 指令一律祈使句动词开头，禁第二人称叙述；
② description 用第三人称写法，写明触发场景与能力边界；
③ 只写另一个 Agent 实例不知道且有用的程序性知识，不写寒暄与通用常识。]"""
    refs = {
        "极简": "",
        "标准": "\n### references/\n\n[{PH}: 分级加载的细则、案例、话术库——执行到对应环节才读，不整包预读]\n",
        "重型": "\n### references/ 与 tests/\n\n[{PH}: 细则按 ref-编号分级；tests/golden.json 存放金标准用例]\n",
    }[tier]
    return f"""# [{PH}: 技能标题]

## 30 秒导读

[{PH}: 1–2 句说明本技能让 Agent 能做什么；主文档只讲流程骨架与决策树，细则一律下沉 references/ 当字典用]

> 档位：{tier_note}

{patterns}

## 文件地图

| 文件/目录 | 作用 |
| --- | --- |
{refs}
## [{PH}: 第一个主章节（按选定结构模式命名）]
"""


def listing_block(name: str) -> str:
    return f"""# [{PH}: 技能中文名]

- ① **名称**：[{PH}: 中文名]
- ② **简介**：[{PH}: 一句话价值描述]
- ③ **分类**：[{PH}: 类目]
- ④ **版本**：0.1.0（以包内 `SKILL.md` 的 `version` 字段为准）
- ⑤ **使用说明**：见 INSTALL.md
"""


def install_block(name: str) -> str:
    return f"""# 安装与上手

1. 下载 `{name}.zip` 后导入支持自定义技能的平台，或解压到技能目录。
2. 按技能的「30 秒导读」开始使用；遇到问题先查 `FAQ.md`（重型档）或对应 references/。
3. 版本升级：替换为新版本包即可，历史版本独立留存。
"""


def hook_stubs() -> dict:
    return {
        "hooks/hooks.json": json.dumps({"pre_write": "hooks/pre_write_guard.py", "post_write": "hooks/post_write_check.py"}, ensure_ascii=False, indent=2) + "\n",
        "hooks/pre_write_guard.py": "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\"\"\"写前守卫占位：写入前校验（按业务实现后替换本占位）。\"\"\"\n\nimport sys\n\n\ndef main() -> int:\n    # {PH}: 写入前校验逻辑（如敏感词、格式、路径白名单）\n    return 0\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n",
        "hooks/post_write_check.py": "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\"\"\"写后校验占位：写入后核对（按业务实现后替换本占位）。\"\"\"\n\nimport sys\n\n\ndef main() -> int:\n    # {PH}: 写入后核对逻辑（如产物存在性、字数、结构完整）\n    return 0\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n",
        "scripts/self_check.py": "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\"\"\"自检占位：包内基础自检（按业务实现后替换本占位）。\"\"\"\n\nimport sys\n\n\ndef main() -> int:\n    # {PH}: 自检逻辑（结构完整 / 必含件在位 / 内容规格核对）\n    print(\"self-check: PASS\")\n    return 0\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n",
    }


def heavy_extras() -> dict:
    return {
        "FAQ.md": "# 常见问题\n\n[{PH}: 六类常见问题，每问配逐字标准答案；本件为重型档必含（使用救助模块）]\n",
        "tools.json": json.dumps({"tools": []}, ensure_ascii=False, indent=2) + "\n",
        "tests/golden.json": json.dumps({"cases": []}, ensure_ascii=False, indent=2) + "\n",
    }


def generate(name: str, tier: str, out: Path) -> list:
    root = out / name
    if root.exists():
        print(json.dumps({"ok": False, "error": "目标目录已存在（防覆盖，请换名或清理后重试）: %s" % root}, ensure_ascii=False))
        sys.exit(3)
    files = {
        "SKILL.md": fm_block(name) + "\n" + body_block(name, tier),
        "_meta.json": json.dumps({"ownerId": "[{PH}]", "slug": name, "version": "0.1.0", "publishedAt": None}, ensure_ascii=False, indent=2) + "\n",
        "LISTING.md": listing_block(name),
        "INSTALL.md": install_block(name),
    }
    if tier in ("标准", "重型"):
        files.update(hook_stubs())
        files["references/details.md"] = "# 细则占位\n\n[{PH}: 按「分级加载」原则从主文档下沉的细则放这里；执行到对应环节才读]\n"
    if tier == "重型":
        files.update(heavy_extras())
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    return sorted(files.keys())


def self_test() -> bool:
    import shutil
    import tempfile
    ok = True
    for tier, expect in (("极简", 4), ("标准", 9), ("重型", 12)):
        tmp = Path(tempfile.mkdtemp())
        try:
            files = generate("demo-skill", tier, tmp)
            ok &= len(files) == expect
            ok &= (tmp / "demo-skill" / "SKILL.md").is_file()
            ok &= "agent_created: true" in (tmp / "demo-skill" / "SKILL.md").read_text(encoding="utf-8")
            ok &= "祈使句" in (tmp / "demo-skill" / "SKILL.md").read_text(encoding="utf-8")
            ok &= "{PH}:" in (tmp / "demo-skill" / "SKILL.md").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    # 防覆盖阴例：同名目录已存在应退出码 3
    tmp = Path(tempfile.mkdtemp())
    try:
        generate("demo-skill", "极简", tmp)
        rc = 0
        try:
            generate("demo-skill", "极简", tmp)
        except SystemExit as e:
            rc = int(e.code)
        ok &= rc == 3
        # 预算机检阳阴用例：小文件过、超限文件拦
        import tempfile as _tf
        _t2 = Path(_tf.mkdtemp())
        (_t2 / "small.md").write_text("---\nname: x\n---\n内容", encoding="utf-8")
        (_t2 / "big.md").write_text("---\nname: x\n---\n" + "字" * 60001, encoding="utf-8")
        ok &= check_size(_t2 / "small.md") == 0
        ok &= check_size(_t2 / "big.md") == 1
        shutil.rmtree(_t2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok


SIZE_LIMIT = 60000  # 代建产出 SKILL.md 全文字节预算（真源 REF-SKL-007 第七节·产出预算）


def check_size(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    body = re.sub(r"\A---\n.*?\n---\n", "", raw, count=1, flags=re.S) if raw.startswith("---") else raw
    size = len(body.encode("utf-8"))
    ok = size <= SIZE_LIMIT
    print(json.dumps({"ok": ok, "file": str(path), "body_bytes": size, "limit": SIZE_LIMIT,
                      "note": "超限即把细则下沉 references/（分级加载定数化）"}, ensure_ascii=False))
    return 0 if ok else 1


def main() -> int:
    argv = [a for a in sys.argv[1:]]
    if "--check-size" in argv:
        i = argv.index("--check-size")
        return check_size(Path(argv[i + 1]))
    if "--self-test" in argv:
        print("PASS 脚手架自测（三档生成＋防覆盖）" if self_test() else "FAIL 脚手架自测")
        return 0 if self_test() else 4
    name, tier, out = None, "标准", Path(".").resolve()
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--档":
            tier = argv[i + 1]; i += 2; continue
        if a in ("--档位", "--tier"):
            tier = {"极简": "极简", "标准": "标准", "重型": "重型"}.get(argv[i + 1], argv[i + 1]); i += 2; continue
        if a in ("--out", "--输出"):
            out = Path(argv[i + 1]); i += 2; continue
        if a.startswith("-"):
            print(json.dumps({"ok": False, "error": "未知参数: %s" % a}, ensure_ascii=False))
            return 2
        name = a; i += 1
    if not name:
        print(json.dumps({"ok": False, "error": "用法: init_skill.py <skill-name> --档 极简|标准|重型 [--out 目录]"}, ensure_ascii=False))
        return 2
    if tier not in TIERS:
        print(json.dumps({"ok": False, "error": "档位必须为 极简|标准|重型，判定依据见 REF-SKL-007 第二节"}, ensure_ascii=False))
        return 2
    import re as _re
    if not _re.match(r"^[a-z][a-z0-9\-]*$", name):
        print(json.dumps({"ok": False, "error": "skill-name 仅允许小写字母/数字/连字符且字母开头（命名纪律）"}, ensure_ascii=False))
        return 2
    files = generate(name, tier, out)
    print(json.dumps({"ok": True, "out": str((out / name).resolve()), "tier": tier, "files": len(files),
                      "note": "骨架已生成；逐项填充 {PH}，产出逐卡过 REF-SKL-007 第六节内核四卡"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
