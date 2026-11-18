# -*- coding: utf-8 -*-
"""
build_txt_standard.py —— B/C 模式 TXT 纯文本标准生成器（纯标准库·零第三方依赖）

设计令牌：源材料溯源落款 + 层级结构 + 每节一句话核心（与 MD/DOCX/PDF 同源）。

输入大纲 outline（dict）：
{
  "title":   "总标题",
  "subtitle":"副标题/口径（可选）",
  "date":    "2026-09-30",
  "source":  "由 蒸馏成技能Skill 蒸馏产出",   # 顶部溯源落款
  "sections":[
     {"heading":"一、章节名", "core":"本章一句话核心", "body":["要点1","要点2",...],
      "paragraphs":["成段正文…"]},   # 可选·成段的话渲染为不加符号的独立段落（讲稿/口播载体）
     ...
  ]
}

用法：
  from build_txt_standard import build_txt
  build_txt(outline, "输出.txt")

硬规：
  - 顶部一行溯源落款（规格强制）——平台自由生成常把落款挪到底部或省去，本生成器锁死顶部。
  - 每节必须有「一句话核心」，否则不产出（core 为空时给占位并提示）。
  - UTF-8 无 BOM，纯文本、可进知识库/轻量搬运。
  - 严禁 Agent 手搓 TXT 排版。
"""
import datetime, os
import design_tokens
import constants

SEP = "=" * 40
SUBSEP = "-" * 40


def _clean(s):
    return "" if s is None else str(s).replace("\r\n", "\n").replace("\r", "\n")


def build_txt(outline, out_path, mode=None, palette=None, font=None, scale=None, number=None):
    title = _clean(outline.get("title", "蒸馏精华"))
    subtitle = _clean(outline.get("subtitle", ""))
    date = _clean(outline.get("date") or datetime.date.today().isoformat())
    source = _clean(outline.get("source", constants.FOOTER))
    sections = outline.get("sections", [])
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font,
                                scale=scale, number=number, fmt="txt")
    num_fn = tok["number"] if number else None  # number 未显式指定时保留原标题（不回归）

    L = []
    # 顶部溯源落款（规格强制）
    L.append(source)
    L.append("")
    L.append(title)
    if subtitle:
        L.append(subtitle)
    L.append("（%s）" % date)
    L.append(SEP)
    L.append("")

    for i, sec in enumerate(sections, 1):
        heading = design_tokens.number_heading(sec.get("heading", "章节"), 1, i, 0, num_fn)
        heading = _clean(heading)
        core = _clean(sec.get("core", ""))
        body = sec.get("body", []) or []
        L.append(heading)
        L.append(SUBSEP)
        if core:
            L.append("一句话核心：" + core)
        else:
            L.append("一句话核心：（待补——萃取时须给出本章核心）")
        L.append("")
        # 成段正文（讲稿体/口播体的载体）——与要点列表职责不同：段落不加 "- " 前缀。
        for para in sec.get("paragraphs", []) or []:
            L.append(_clean(para))
            L.append("")
        for item in body:
            it = _clean(item)
            if it.startswith("- ") or it.startswith("• "):
                L.append(it)
            else:
                L.append("- " + it)
        L.append("")

    L.append(SEP)
    L.append(constants.FOOTER)
    ov = constants.sources_overview(outline.get("sources"))
    if ov:
        L.append(ov)
    L.append("（%s）" % constants.disclaimer(outline.get("topic")))
    # 交付回执（闭环·反馈口）：紧随免责之后，是全篇最后一行
    L.append(constants.receipt_line(outline.get("receipt_tags")))
    text = "\n".join(L).rstrip() + "\n"

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return out_path


def _self_test():
    """最小自测：渲染一次并断言**要点真写入**。走临时目录，不写 scripts/。"""
    import tempfile
    demo = {
        "title": "自测标题",
        "subtitle": "自测副标题",
        "date": "2026-01-01",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sections": [
            {"heading": "一、甲模块", "core": "甲的核心句",
             "body": ["甲要点一", "甲要点二"]},
        ],
    }
    p = os.path.join(tempfile.mkdtemp(), "self.txt")
    build_txt(demo, p)
    assert os.path.getsize(p) > 0, "产物为空: %s" % p
    t = open(p, encoding="utf-8").read()
    for must in ("自测标题", "一、甲模块", "甲的核心句", "甲要点一", "甲要点二",
                 constants.RECEIPT_PREFIX, constants.RECEIPT_BOUND):
        assert must in t, "txt 产物缺内容: %s" % must
    print("self-test PASS: %s (%d B)" % (os.path.basename(p), os.path.getsize(p)))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=None)
    ap.add_argument("--palette", default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--scale", default=None)
    ap.add_argument("--number", default=None,
                    help="序号系统：arabic/cn/circle/none（不填=保留原标题，向后兼容）")
    ap.add_argument("--self-test", action="store_true",
                    help="最小自测：渲染一次并断言要点真写入（走临时目录，不写包内）")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        raise SystemExit(0)

    demo = {
        "title": "SkillHub 新功能精华萃取",
        "subtitle": "GitHub 一键导入 Skill · ClawHub 镜像 Skill 一键认领",
        "date": "2026-09-30",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sections": [
            {"heading": "一、本次更新解决的两个核心痛点",
             "core": "把 GitHub/ClawHub 的 Skill 迁移从手工搬运变成一键操作。",
             "body": ["痛点一：GitHub 的 Skill 迁到 SkillHub 需手动打 zip、拖拽、抄字段。",
                      "痛点二：ClawHub 镜像 Skill 无法声明所有权、无法平台管理。"]},
            {"heading": "二、绑定 GitHub 账号——一切功能的入场券",
             "core": "绑定是导入与认领两项功能的前置条件。",
             "body": ["入口：个人中心左侧栏底部或「我的 Skills」顶部蓝卡。",
                      "结果：显示 GitHub 头像 + 「已绑定」绿标。"]},
        ],
    }
    suffix = ("_%s" % args.mode) if args.mode else ""
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "SkillHub_精华萃取%s.txt" % suffix)
    build_txt(demo, out, mode=args.mode, palette=args.palette,
              font=args.font, scale=args.scale, number=args.number)
    print("生成:", out, "|", os.path.getsize(out), "bytes")
