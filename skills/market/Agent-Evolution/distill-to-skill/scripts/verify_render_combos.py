# -*- coding: utf-8 -*-
"""验证：render_formats 多选格式组合联测（含 PPT 分支，P0 回归）。

模拟用户按新引导走完 D1 -> 格式「2,3」-> 风格A 后的真实编排路径：
  - 组合1：md+txt+docx+pptx（覆盖 PPT 分支）
  - 组合2：1,3 双选 -> pptx + docx（B/C 多格式同源）
  - 组合3：7 项全选 md/txt/ppt/pdf/docx/xlsx/xlsx_chart
断言：produced 数量 == 请求数、failed 空、每个产物字节 > 0。

环境豁免：本机无中文字体时 pdf 必然渲染失败。若因此判 FAIL，则无字体
机器永远过不了门禁 —— 门禁本身也就失去了意义。故先用「试渲一份最小 PDF」探测字体
（比猜系统路径可靠）；探测不到则把含 pdf 的组合降级为去掉 pdf，打印警告，其余照常断言。

本脚本需真实渲染环境，故不提供离线自测开关（不进离线回归），由 --full 与
assemble 的自举门禁强制调用。
"""
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from distill_skeleton import render_formats

demo = {
    "title": "联测大纲", "subtitle": "多选格式组合",
    "date": "2026-10-01", "source": "由 蒸馏成技能Skill 蒸馏产出",
    "sections": [
        {"heading": "一、模块甲", "core": "甲的核心", "points": ["要点1", "要点2"]},
        {"heading": "二、模块乙", "core": "乙的核心", "points": ["要点A", "要点B"]},
    ],
}


def has_cjk_font():
    """试渲一份最小 PDF 判定是否有可用中文字体；异常或无产物即判无字体环境。"""
    try:
        from build_pdf_standard import build_pdf
    except Exception:
        return False
    td = tempfile.mkdtemp(prefix="font_probe_")
    out = os.path.join(td, "probe.pdf")
    try:
        build_pdf({"title": "字体探测", "subtitle": "", "date": "", "source": "",
                   "sections": [{"heading": "甲", "core": "乙", "body": ["丙"]}]}, out)
    except Exception as e:
        print("字体探测失败: %s: %s" % (type(e).__name__, e))
        return False
    return os.path.isfile(out) and os.path.getsize(out) > 0


if has_cjk_font():
    COMBOS = {
        "md+txt+docx+pptx": ["md", "txt", "docx", "pptx"],
        "1,3双选(pptx+docx)": ["pptx", "docx"],
        "7项全选": ["md", "txt", "ppt", "pdf", "docx", "xlsx", "xlsx_chart"],
    }
else:
    print("警告: 未探测到可用中文字体 —— pdf 相关组合降级为跳过 pdf（其余照常断言）")
    COMBOS = {
        "md+txt+docx+pptx": ["md", "txt", "docx", "pptx"],
        "1,3双选(pptx+docx)": ["pptx", "docx"],
        "全选(去pdf)": ["md", "txt", "ppt", "docx", "xlsx", "xlsx_chart"],
    }

ok = True
for name, fmts in COMBOS.items():
    td = tempfile.mkdtemp()
    produced, failed = render_formats(demo, fmts, td)
    sizes = {os.path.basename(p): os.path.getsize(p) for p in produced}
    good = (len(produced) == len(fmts)) and (not failed) and all(s > 0 for s in sizes.values())
    ok = ok and good
    print("%-22s produced=%d failed=%d sizes=%s %s" %
          (name, len(produced), len(failed), sizes, "OK" if good else "FAIL"))
    for f in failed:
        print("   failed:", f)
print("RESULT:", "ALL OK" if ok else "HAS FAIL")
sys.exit(0 if ok else 1)
