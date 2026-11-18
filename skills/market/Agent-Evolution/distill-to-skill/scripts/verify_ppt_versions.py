# -*- coding: utf-8 -*-
"""验证：7 版本 PPT 各自配色不同、版式风格生效、零厂商标识。

产物落临时目录（tempfile），不写进 scripts/ —— 避免
「验证脚本把产物留在包内、下次打包被一并压进 zip」。
本脚本可离线自测（仅标准库 + 本地渲染，无网络依赖），支持 --self-test。

用法：
  python verify_ppt_versions.py            # 跑冒烟（exit 0 = ALL OK）
  python verify_ppt_versions.py --self-test
"""
import os
import sys
import shutil
import tempfile
import zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_ppt_standard as P

# 构造一份含各页型的小大纲
# 大纲结构须匹配 render_outline API：
#   chapters = [(num,title,desc), ...]（目录页自动生成）
#   sections 仅含有效页型 divider/cards/list/compare/steps/quote（cover/toc 自动生成）
#   closing 走 o["closing"]（结尾页自动生成）
o = {
    "title": "演示萃取", "subtitle": "验证 7 版本观感差异",
    "attr": "由 蒸馏成技能Skill 蒸馏产出",
    "chapters": [("1", "背景", "一句话"), ("2", "做法", "一句话")],
    "sections": [
        {"type": "divider", "cur": 1, "num": "1", "title": "第一章 背景", "lead": "要点"},
        {"type": "cards", "title": "核心做法", "items": [("做法A", ["说明"]), ("做法B", ["说明"]),
                                                    ("做法C", ["说明"]), ("做法D", ["说明"])]},
        {"type": "compare", "title": "方案对比", "lh": "方案甲", "ll": ["优点1", "优点2"],
         "rh": "方案乙", "rl": ["优点1", "优点2"]},
        {"type": "steps", "title": "操作步骤", "items": ["第一步", "第二步", "第三步"]},
        {"type": "quote", "title": "关键结论", "quote": "关键结论金句", "points": ["支撑点"]},
    ],
    "closing": {"title": "谢谢", "points": ["收尾一", "收尾二"]},
}

EXPECT = {  # 封面底 MAIN 色
    "standard": "16335B", "minimal": "04AEDA", "classic": "1F4E3D",
    "premium": "4B3F72", "summary": "E8730C", "course": "0E7FB7", "data": "C00000",
}


def run():
    td = tempfile.mkdtemp(prefix="ppt_ver_")
    ok = True
    try:
        for v, exp in EXPECT.items():
            out = os.path.join(td, "t_v_%s.pptx" % v)
            try:
                P.render_outline(o, out, version=v)
            except Exception as e:
                print("FAIL %s: %s" % (v, e))
                ok = False
                continue
            z = zipfile.ZipFile(out)
            # 扫所有 slide xml 是否含厂商标识
            blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
            bad = [w for w in ("京东", "阿里", "字节", "腾讯", "jdred") if w.encode("utf-8") in blob]
            x = z.read("ppt/slides/slide1.xml").decode("utf-8", "ignore")
            has = exp in x
            print("%-8s cover=%s expect=%s %s | vendor=%s" %
                  (v, ("OK" if has else "WRONG"), exp, ("OK" if has else "X"), bad or "none"))
            if not has or bad:
                ok = False
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print("RESULT:", "ALL OK" if ok else "HAS FAIL")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("--self-test",):
        sys.stderr.write("用法: python verify_ppt_versions.py [--self-test]\n")
        sys.exit(2)
    sys.exit(0 if run() else 1)
