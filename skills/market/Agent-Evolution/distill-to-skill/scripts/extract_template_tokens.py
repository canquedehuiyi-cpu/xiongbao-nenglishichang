#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_template_tokens.py —— 参考模板设计令牌提取器（纯标准库，无第三方依赖）

用途（见 SKILL.md「PPT 标准版规格 · 参考模板机制」）：
  用户给自有 PPT 作风格参考时，运行本脚本提取其「设计特征」，
  引擎据此对齐版式/配色/字体产出标准版。只取设计特征，不取文字内容（不把模板内文当源材料）。

用法：
  python extract_template_tokens.py <模板.pptx> [输出.json]
  不传输出路径则打印到 stdout（JSON）。

输出字段：
  palette        主色/辅色候选（按出现频次排序，去重，过滤纯黑纯白）
  fonts          字体（latin 西文 + ea 中文/东亚，去重）
  page_fingerprint 每页版式指纹（形状数/是否有图/是否有图表/文字量/是否有大标题），用于判断页型库覆盖
  stats          汇总（页数/平均形状数/含图比例/含图表比例）
"""
import zipfile
import re
import sys
import os
import json
import argparse
from collections import Counter

NS_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'

def read_zip(path):
    return zipfile.ZipFile(path)

def all_slides(z):
    i = 1
    out = []
    while True:
        try:
            out.append(z.read(f'ppt/slides/slide{i}.xml'))
        except KeyError:
            break
        i += 1
    return out

def collect_colors(z):
    """从主题 + 全部 slide 收集 srgbClr，按频次排序，过滤纯黑纯白纯灰极端值。"""
    cnt = Counter()
    names = z.namelist()
    targets = [n for n in names if n.endswith('.xml')]
    for n in targets:
        try:
            data = z.read(n).decode('utf-8', 'ignore')
        except Exception:
            continue
        for m in re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', data):
            cnt[m.upper()] += 1
    # 过滤纯黑/纯白/常见无彩色噪声，但保留作为候选（标注）
    def is_near_gray(c):
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return max(r, g, b) - min(r, g, b) < 18
    ranked = []
    for c, n in cnt.most_common(40):
        if c in ('000000', 'FFFFFF', '000001', 'FFFFFE'):
            continue
        ranked.append({'hex': '#' + c, 'freq': n, 'neutral': is_near_gray(c)})
    return ranked[:10]

def collect_fonts(z):
    latin, ea = Counter(), Counter()
    for n in z.namelist():
        if not n.endswith('.xml'):
            continue
        try:
            data = z.read(n).decode('utf-8', 'ignore')
        except Exception:
            continue
        for m in re.findall(r'<a:latin typeface="([^"]+)"', data):
            if m and m != '':
                latin[m] += 1
        for m in re.findall(r'<a:ea typeface="([^"]+)"', data):
            if m and m != '':
                ea[m] += 1
    return {
        'latin': [f for f, _ in latin.most_common(6)],
        'ea': [f for f, _ in ea.most_common(6)],
    }

def slide_fingerprint(xml):
    if isinstance(xml, bytes):
        xml = xml.decode('utf-8', 'ignore')
    txts = re.findall(r'<a:t>(.*?)</a:t>', xml, re.S)
    full = ' '.join(t for t in txts)
    sp = len(re.findall(r'<p:sp>', xml))
    pic = 1 if '<p:pic>' in xml else 0
    chart = 1 if 'chart' in xml or '<c:' in xml else 0
    # 大标题启发：首段文字较短且后续形状少
    title = next((t.strip() for t in txts if t.strip()), '')
    return {
        'shapes': sp,
        'has_pic': pic,
        'has_chart': chart,
        'text_len': len(full),
        'title_len': len(title),
    }

def has_media(z):
    return any('media/' in n for n in z.namelist())

def _self_test():
    """离线自测：标准库手工造最小 pptx 模板，断言配色/字体/版式指纹均可抽。"""
    import tempfile
    td = tempfile.mkdtemp()
    p = os.path.join(td, "tpl.pptx")
    slide = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:sp><p:spPr>'
        '<a:solidFill><a:srgbClr val="16335B"/></a:solidFill>'
        '</p:spPr><p:txBody>'
        '<a:p><a:r><a:rPr><a:latin typeface="Arial"/><a:ea typeface="SimHei"/></a:rPr>'
        '<a:t>模板标题</a:t></a:r></a:p>'
        '</p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
    )
    theme = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
             '<a:srgbClr val="E0A33E"/></a:theme>')
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("ppt/slides/slide1.xml", slide.encode("utf-8"))
        zf.writestr("ppt/theme/theme1.xml", theme.encode("utf-8"))
    z = read_zip(p)
    slides = all_slides(z)
    assert len(slides) == 1, "页数应为 1，实得 %d" % len(slides)
    hexes = [c["hex"] for c in collect_colors(z)]
    assert "#16335B" in hexes, "主色未抽出: %s" % hexes
    assert "#E0A33E" in hexes, "辅色未抽出: %s" % hexes
    assert "#FFFFFF" not in hexes and "#000000" not in hexes, "纯黑纯白未过滤: %s" % hexes
    fonts = collect_fonts(z)
    assert "Arial" in fonts["latin"], "西文字体未抽出: %s" % fonts
    assert "SimHei" in fonts["ea"], "中文字体未抽出: %s" % fonts
    fp = slide_fingerprint(z.read("ppt/slides/slide1.xml"))
    assert fp["shapes"] >= 1 and fp["text_len"] > 0, "版式指纹异常: %s" % fp
    print("PASS extract_template_tokens：配色=%d 字体 latin/ea 齐 指纹正常" % len(hexes))
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="extract_template_tokens.py",
        description="从用户自有 PPT 提取设计令牌（配色/字体/页型指纹），只取设计特征、不取文字内容。",
    )
    ap.add_argument("pptx", nargs="?", help="用户模板 .pptx")
    ap.add_argument("out", nargs="?", default=None, help="输出 JSON 路径（不传则打印到 stdout）")
    ap.add_argument("--self-test", action="store_true", help="离线自测（无需外部输入）")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if not args.pptx:
        ap.error("缺少模板文件：<模板.pptx>")
    path = args.pptx
    out_path = args.out
    try:
        z = read_zip(path)
    except Exception as e:
        print(f'[ERR] 无法读取 {path}: {e}', file=sys.stderr)
        sys.exit(1)
    slides = all_slides(z)
    palette = collect_colors(z)
    fonts = collect_fonts(z)
    fps = [slide_fingerprint(z.read(f'ppt/slides/slide{i}.xml')) for i in range(1, len(slides) + 1)]
    n = len(slides)
    avg_shapes = round(sum(f['shapes'] for f in fps) / n, 1) if n else 0
    pic_rate = round(sum(f['has_pic'] for f in fps) / n, 2) if n else 0
    chart_rate = round(sum(f['has_chart'] for f in fps) / n, 2) if n else 0
    result = {
        'source': path,
        'palette': palette,
        'fonts': fonts,
        'page_fingerprint': fps,
        'stats': {
            'slides': n,
            'avg_shapes': avg_shapes,
            'pic_rate': pic_rate,
            'chart_rate': chart_rate,
            'has_media': has_media(z),
        },
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'[OK] 已写出 {out_path}（{n} 页）')
    else:
        print(text)

if __name__ == '__main__':
    main()
