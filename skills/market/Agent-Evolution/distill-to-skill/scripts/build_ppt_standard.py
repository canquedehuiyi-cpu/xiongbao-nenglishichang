# -*- coding: utf-8 -*-
"""
build_ppt_standard.py —— 蒸馏成技能Skill · B模式 PPT 标准版「可执行生成器」
================================================================================
纯标准库（zipfile + xml）生成符合引擎「PPT 标准版规格」的 .pptx。
不依赖 python-pptx，任何托管环境都能跑；各平台 Agent 直接调用本脚本，
不要再手搓 pptx 代码（手搓易出重叠/字号反/一页一意破等格式错误）。

设计令牌（与 SKILL.md PPT 标准版规格一致）：
  主色 MAIN=#16335B  强调 ACCENT=#E0A33E  辅助 AUX=#2E6E9E
  浅底 LIGHT=#F4F6F9 正文 BODY=#1F2733 注释 ANNOT=#6B7480 边框 BORDER=#D8DEE6
层级字号（统一，杜绝字号反）：
  封面主标题 40 / 章节大编号 54 / 页标题 24 / 卡片标题 18
  正文 15 / 金句洞察 18(粗,ACCENT或MAIN) / 导航 11 / 注释 11
纪律：导航不重叠（内容页只用一行路线图，当前章高亮，不重复 running header）
      一页一意（章节分隔页独立成页）  行距 1.2  留白>=20%  配色<=3主色
================================================================================
"""
import zipfile, os, datetime, math, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_tokens
import constants

EMU = 914400
def emu(inch): return int(round(inch * EMU))

# ---- 幻灯片画布硬规格（16:9，内容不得溢出安全区）----
SLIDE_W = 13.333   # 英寸
SLIDE_H = 7.5      # 英寸
SAFE_BOTTOM = 6.85 # 内容安全区下沿；页脚固定在 SAFE_BOTTOM 以下

# ---- 设计令牌（默认 biz，与 SKILL.md PPT 标准版规格一致；build_ppt 按所选模式覆盖）----
MAIN   = "16335B"
ACCENT = "E0A33E"
AUX    = "2E6E9E"
LIGHT  = "F4F6F9"
BODY   = "1F2733"
ANNOT  = "6B7480"
BORDER = "D8DEE6"
WHITE  = "FFFFFF"
FONT   = "微软雅黑"
# 版式风格（由所选版本/布局驱动；默认 balanced，与 biz 一致不回归）
LAYOUT = {"cover_align": "ctr", "card_bar": 0.07, "gap": 1.00, "accent_card": False}

# ---- 底层 XML 构件 ----
def _clr(hexv): return f'<a:srgbClr val="{hexv}"/>'
def _run(text, size, bold, hexv, align=None):
    b = ' b="1"' if bold else ''
    al = f' algn="{align}"' if align else ''
    return (f'<a:p{al}><a:pPr><a:lnSpc><a:spcPct val="120000"/></a:lnSpc>'
            f'<a:spcBef><a:spcPts val="600"/></a:spcBef></a:pPr>'
            f'<a:r><a:rPr lang="zh-CN" sz="{int(size*100)}"{b}>'
            f'<a:solidFill>{_clr(hexv)}</a:solidFill>'
            f'<a:latin typeface="{FONT}"/><a:ea typeface="{FONT}"/></a:rPr>'
            f'<a:t>{_xml(text)}</a:t></a:r></a:p>')

def _xml(t): return (t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))

def rect(l,t,w,h,fill=None,line=None,line_w=1):
    fillxml = f'<a:solidFill>{_clr(fill)}</a:solidFill>' if fill else '<a:noFill/>'
    if line:
        linexml = f'<a:ln w="{line_w*12700}"><a:solidFill>{_clr(line)}</a:solidFill></a:ln>'
    else:
        linexml = '<a:ln><a:noFill/></a:ln>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="1" name="r"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(l)}" y="{emu(t)}"/>'
            f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fillxml}{linexml}</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/></p:txBody></p:sp>')

def text(l,t,w,h,paras,anchor="t",wrap="square",autofit=False):
    """paras: list of dict(text,size,bold,color,align)

    autofit=True → 文字超框时由渲染器自动缩排（`<a:normAutofit/>`），用于卡片标题 / 正文盒，
    防长文本溢出固定盒高。默认 False 时输出与既有完全一致（不自闭合改写法，避免影响基线）。
    """
    body = "".join(_run(p.get('text',''), p.get('size',15), p.get('bold',False),
                         p.get('color',BODY), p.get('align')) for p in paras)
    _bp = (f'wrap="{wrap}" lIns="91440" tIns="45720" rIns="91440" bIns="45720" anchor="{anchor}"')
    if autofit:
        bp = f'<a:bodyPr {_bp}><a:normAutofit/></a:bodyPr>'
    else:
        bp = f'<a:bodyPr {_bp}/>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="1" name="tx"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(l)}" y="{emu(t)}"/>'
            f'<a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody>{bp}'
            f'<a:lstStyle/>{body}</p:txBody></p:sp>')

# ---- 页型库（标准组件）----
def footer(sb, page, total, attr=None):
    attr = attr or constants.FOOTER
    # 溯源落款：每页固定左下；页码固定右下；均放在安全区内，防止平台裁切导致消失
    sb.append(text(0.5, 6.95, 8.5, 0.35, [{'text':attr,'size':11,'color':ANNOT}]))
    sb.append(text(10.8, 6.95, 2.0, 0.35, [{'text':f'{page} / {total}','size':11,'color':ANNOT,'align':'r'}]))

def roadmap(sb, chapters, cur):
    # 一行路线图放顶部，当前章高亮；内容页只用此，不重复 running header（防重叠）
    x = 0.5
    for i, ch in enumerate(chapters):
        c = ACCENT if i == cur else ANNOT
        b = (i == cur)
        label = f'{ch[0]} {ch[1]}' if isinstance(ch, tuple) else ch
        sb.append(text(x, 0.18, 3.0, 0.35,
                       [{'text':label,'size':11,'bold':b,'color':c}]))
        x += 3.0

def slide_blank(): return ['<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>']

def slide_close():
    return ('</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping '
    'bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
    'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sld>')

# ---- 各页型渲染（通用版式原语）----
# 通用版式原语（跨题材可复用，不含任何特定来源特征）：
#   ① 标题带：左上标题 + 其下强调短横
#   ② 编号徽章：实心方块嵌白字编号
#   ③ 卡片模块：浅底方块 + 顶部强调条 + 标题 + 要点
#   ④ 图标圈：等大同色圆/方块 + 短标签成排
#   ⑤ 分隔大编号：左色块 + 巨大编号水印 + 右侧标题引言
#   ⑥ 对比双栏 / 步骤横排 / 金句块：把"一大段字"拆成结构化视觉模块
# 以下原语内容无关，任何材料都能套；layout_* 按内容自动选版式。

def cover(sb, title, subtitle, attr_tag="精华萃取 · 完整原生浓缩"):
    sb.append(rect(0,0,13.333,7.5,fill=MAIN))
    if LAYOUT.get("cover_align") == "left":
        sb.append(rect(0,3.05,4.2,0.09,fill=ACCENT))     # 左侧短强调条
        sb.append(text(1.2,2.0,11,1.2,[{'text':title,'size':40,'bold':True,'color':WHITE,'align':'l'}],anchor="ctr"))
        sb.append(text(1.2,3.35,11,0.8,[{'text':subtitle,'size':24,'color':ACCENT,'align':'l'}],anchor="ctr"))
        sb.append(text(1.2,4.4,11,0.6,[{'text':attr_tag,'size':14,'color':'C9D3DF','align':'l'}],anchor="ctr"))
    else:
        sb.append(rect(0,3.05,13.333,0.09,fill=ACCENT))
        sb.append(text(1.5,2.0,10,1.2,[{'text':title,'size':40,'bold':True,'color':WHITE,'align':'ctr'}],anchor="ctr"))
        sb.append(text(1.5,3.35,10,0.8,[{'text':subtitle,'size':24,'color':ACCENT,'align':'ctr'}],anchor="ctr"))
        sb.append(text(2.0,4.4,9,0.6,[{'text':attr_tag,'size':14,'color':'C9D3DF','align':'ctr'}],anchor="ctr"))
    # 封面溯源落款只在此处出现一次；footer() 不在封面页调用，避免重复

def ellipse(l,t,w,h,fill,line=None,line_w=1):
    fillxml = f'<a:solidFill>{_clr(fill)}</a:solidFill>' if fill else '<a:noFill/>'
    linexml = f'<a:ln w="{int(line_w*12700)}"><a:solidFill>{_clr(line)}</a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="1" name="e"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(l)}" y="{emu(t)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>{fillxml}{linexml}</p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/></p:txBody></p:sp>')

def title_band(sb, title, subtitle=None, cur=None, chapters=None):
    """通用标题带：顶部路线图(可选) + 左强调竖条 + 标题 + 强调横 + 细分隔线"""
    if chapters is not None and cur is not None:
        roadmap(sb, chapters, cur)
    sb.append(rect(0.8,0.62,0.13,0.52,fill=ACCENT))
    sb.append(text(1.12,0.55,11.2,0.66,[{'text':title,'size':26,'bold':True,'color':MAIN}]))
    if subtitle:
        sb.append(text(1.12,1.22,11.2,0.42,[{'text':subtitle,'size':14,'color':ANNOT}]))
    sb.append(rect(0.8,1.46,11.73,0.018,fill=BORDER))

def card_module(sb, x, y, w, h, heading, lines, bar=None, head_color=None):
    # ⚠️ 默认参数不得直接写 ACCENT / MAIN —— 函数默认值在「定义时」求值，会绑死模块导入时的
    # 初始配色；resolve() 换配色后卡片仍是旧色 = 配色串台。故用 None + 函数内取当前全局值。
    bar = bar or ACCENT
    head_color = head_color or MAIN
    if isinstance(lines, str): lines=[lines]   # 容错：要点写成字符串也自动转列表
    # 标题盒按 17pt 可容 2 行预留（≈0.62in），修正原固定 0.5in 导致长标题压字 / 溢出
    head_y, head_h = y + 0.18, 0.62
    body_y = head_y + head_h + 0.02
    # 正文 13pt 实际行高 ≈0.22in（原按 0.18 估会多算行数 → 溢出）
    body_h = max(0.4, h - (body_y - y) - 0.18)
    max_lines = max(1, int(body_h / 0.22))
    lines = (lines or [])[:max_lines]
    sb.append(rect(x,y,w,h,fill=LIGHT))
    sb.append(rect(x,y,w,LAYOUT.get("card_bar",0.07),fill=bar))
    sb.append(text(x+0.25,head_y,w-0.5,head_h,
                   [{'text':heading,'size':17,'bold':True,'color':head_color}],autofit=True))
    paras=[{'text':'· '+ln,'size':13,'color':BODY} for ln in lines] if lines else []
    sb.append(text(x+0.25,body_y,w-0.5,body_h,paras,autofit=True))

def badge_rows(sb, x, y, w, items, size=14):
    # 调用方已按 5 项拆页；这里再硬切一道保险
    items = items[:5]
    n=len(items); avail=6.5-y
    rh=min(0.95, avail/max(n,1))
    for i,it in enumerate(items):
        yy=y+i*rh
        sb.append(rect(x,yy+0.06,0.52,0.52,fill=MAIN))
        sb.append(text(x,yy+0.06,0.52,0.52,[{'text':str(i+1),'size':16,'bold':True,'color':WHITE,'align':'ctr'}],anchor="ctr"))
        sb.append(text(x+0.72,yy+0.02,w-0.72,rh-0.05,[{'text':it,'size':size,'color':BODY}],anchor="ctr"))
        if i<n-1:
            sb.append(rect(x+0.72,yy+rh,w-0.72,0.012,fill=BORDER))

def icon_circle(sb, x, y, d, label, fill):
    sb.append(ellipse(x,y,d,d,fill=fill))
    sb.append(text(x,y,d,d,[{'text':label,'size':13,'bold':True,'color':WHITE,'align':'ctr'}],anchor="ctr"))

def compare_two(sb, x, y, w, h, lh, ll, rh, rl):
    cw=(w-0.4)/2
    sb.append(rect(x,y,cw,h,fill=LIGHT)); sb.append(rect(x,y,cw,0.07,fill=ACCENT))
    sb.append(text(x+0.25,y+0.2,cw-0.5,0.5,[{'text':lh,'size':17,'bold':True,'color':MAIN}]))
    sb.append(text(x+0.25,y+0.85,cw-0.5,h-1.05,[{'text':'· '+ln,'size':13,'color':BODY} for ln in ll]))
    rx=x+cw+0.4
    sb.append(rect(rx,y,cw,h,fill='FBF1E0')); sb.append(rect(rx,y,cw,0.07,fill=MAIN))
    sb.append(text(rx+0.25,y+0.2,cw-0.5,0.5,[{'text':rh,'size':17,'bold':True,'color':MAIN}]))
    sb.append(text(rx+0.25,y+0.85,cw-0.5,h-1.05,[{'text':'· '+ln,'size':13,'color':BODY} for ln in rl]))

def steps_h(sb, x, y, w, items):
    # 调用方已按 4 项拆页；这里再硬切一道保险
    items = items[:4]
    n=len(items); gap=0.35; cw=(w-(n-1)*gap)/n
    for i,it in enumerate(items):
        cx=x+i*(cw+gap)
        sb.append(rect(cx,y,cw,1.05,fill=MAIN))
        sb.append(text(cx,y,cw,1.05,[{'text':str(i+1),'size':30,'bold':True,'color':ACCENT,'align':'ctr'}],anchor="ctr"))
        sb.append(text(cx,y+1.15,cw,0.9,[{'text':it,'size':13,'color':BODY,'align':'ctr'}],anchor="ctr"))
        if i<n-1:
            sb.append(text(cx+cw,y+0.3,gap,0.5,[{'text':'→','size':22,'bold':True,'color':ACCENT,'align':'ctr'}],anchor="ctr"))

def quote_block(sb, x, y, w, h, quote, points):
    sb.append(rect(x,y,w,h,fill=LIGHT))
    sb.append(rect(x,y,0.13,h,fill=ACCENT))
    sb.append(text(x+0.45,y+0.35,w-0.9,1.5,[{'text':'“'+quote+'”','size':22,'bold':True,'color':MAIN}],anchor="ctr"))
    if points:
        # 14pt 行高约 0.20；正文区 h-2.1，最多行数
        max_pts = max(1, int((h-2.1-0.2) / 0.20))
        sb.append(text(x+0.7,y+1.95,w-1.4,h-2.1,[{'text':'· '+p,'size':14,'color':BODY} for p in points[:max_pts]]))

def divider(sb, chapters, cur, num, title, lead):
    sb.append(rect(0,0,4.8,7.5,fill=MAIN))
    sb.append(rect(0,0,0.2,7.5,fill=ACCENT))
    sb.append(text(0.7,2.3,3.7,1.8,[{'text':num,'size':96,'bold':True,'color':ACCENT}],anchor="ctr"))
    sb.append(text(5.5,2.7,7.0,1.2,[{'text':title,'size':38,'bold':True,'color':MAIN}],anchor="ctr"))
    sb.append(text(5.5,3.95,7.0,1.5,[{'text':lead,'size':16,'color':ANNOT}],anchor="ctr"))

def toc_list(sb, chapters):
    sb.append(rect(0,0,13.333,1.1,fill=MAIN))
    sb.append(text(0.8,0.26,6,0.6,[{'text':'目录','size':26,'bold':True,'color':WHITE}]))
    # 6 项目录需 5 个间隔，总高度 ≤ 5.15，故间隔 1.0
    gap=1.0; y=1.7
    for i,(num,title,desc) in enumerate(chapters[:6]):
        sb.append(rect(0.9,y,0.72,0.72,fill=ACCENT))
        sb.append(text(0.9,y,0.72,0.72,[{'text':num,'size':22,'bold':True,'color':MAIN,'align':'ctr'}],anchor="ctr"))
        sb.append(text(1.85,y+0.04,5.0,0.45,[{'text':title,'size':19,'bold':True,'color':MAIN}]))
        sb.append(text(1.85,y+0.48,10.8,0.35,[{'text':desc,'size':12,'color':ANNOT}]))
        y+=gap

def _split_sections(sections):
    """密度保护：把会溢出的长列表/卡片/步骤拆成多页，避免内容跑出安全区。"""
    out=[]
    for s in sections:
        t=s.get('type')
        if t=='cards':
            items=s.get('items',[])
            # 单页卡片上限 6（3列x2行），超量拆页
            if len(items)>6:
                for i in range(0,len(items),6):
                    chunk=items[i:i+6]
                    suffix=f" ({i//6+1}/{(len(items)-1)//6+1})"
                    out.append({**s,'title':s.get('title','')+suffix,'items':chunk})
                continue
        elif t=='list':
            items=s.get('items',[])
            if len(items)>5:
                for i in range(0,len(items),5):
                    chunk=items[i:i+5]
                    suffix=f" ({i//5+1}/{(len(items)-1)//5+1})"
                    out.append({**s,'title':s.get('title','')+suffix,'items':chunk})
                continue
        elif t=='steps':
            items=s.get('items',[])
            if len(items)>4:
                for i in range(0,len(items),4):
                    chunk=items[i:i+4]
                    suffix=f" ({i//4+1}/{(len(items)-1)//4+1})"
                    out.append({**s,'title':s.get('title','')+suffix,'items':chunk})
                continue
        elif t=='quote':
            pts=s.get('points',[])
            if len(pts)>4:
                for i in range(0,len(pts),4):
                    chunk=pts[i:i+4]
                    suffix=f" ({i//4+1}/{(len(pts)-1)//4+1})"
                    out.append({**s,'title':s.get('title','')+suffix,'points':chunk})
                continue
        out.append(s)
    return out

def auto_cards(sb, items, x0=0.8, y0=1.85, x1=12.53, y1=SAFE_BOTTOM-0.3):
    """把 (标题,要点列表) 列表自动排成卡片网格（1/2/3/4 一行 或 3x2）。调用方须控制 items≤6，超量由 _split_sections 拆页。"""
    n=len(items)
    cols = 1 if n<=1 else (2 if n==2 else (n if n<=4 else 3))
    rows = math.ceil(n/cols)
    gw=0.35; gh=0.35
    cw=(x1-x0-(cols-1)*gw)/cols
    ch=(y1-y0-(rows-1)*gh)/rows
    for i,(h,lines) in enumerate(items):
        r=i//cols; c=i%cols
        x=x0+c*(cw+gw); y=y0+r*(ch+gh)
        card_module(sb,x,y,cw,ch,h,lines)

# ---- 组装 ----
CT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'''
def build_ppt(slides, out_path, total_override=None, mode=None, palette=None,
              font=None, scale=None, version=None, layout=None):
    """slides: list of list-of-xml-string (每页已含 footer 等)。本函数只负责打包。
    可选 token 参数（前置设计令牌库）：mode/palette/font/scale 自由组合，
    或 version（用户可选版本：standard/minimal/classic/premium/summary/course/data）+ layout（版式风格）。
    不选则默认 biz（与既有默认值一致）。
    """
    global MAIN, ACCENT, AUX, LIGHT, BODY, ANNOT, BORDER, WHITE, FONT, LAYOUT
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font, scale=scale,
                                version=version, layout=layout, fmt="ppt")
    LAYOUT = tok["layout"]
    MAIN   = tok["palette"]["MAIN"]
    ACCENT = tok["palette"]["ACCENT"]
    AUX    = tok["palette"]["AUX"]
    LIGHT  = tok["palette"]["LIGHT"]
    BODY   = tok["palette"]["BODY"]
    ANNOT  = tok["palette"]["ANNOT"]
    BORDER = tok["palette"]["BORDER"]
    WHITE  = "FFFFFF"
    FONT   = tok["font_office"]
    total = total_override or len(slides)
    total = total_override or len(slides)
    # 写入总页数到每页 footer 占位
    z = zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED)
    # Content_Types
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
          '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
          '<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>',
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>']
    for i in range(1,total+1):
        ct.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    ct.append('</Types>')
    z.writestr('[Content_Types].xml', ''.join(ct))

    z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>')

    # presentation.xml
    sldIds = "".join(f'<p:sldId id="{256+i}" r:id="rId{3+i}"/>' for i in range(total))
    z.writestr('ppt/presentation.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        f'<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f'<p:sldIdLst>{sldIds}</p:sldIdLst>'
        '<p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')

    prels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>']
    for i in range(total):
        prels.append(f'<Relationship Id="rId{3+i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>')
    prels.append('</Relationships>')
    z.writestr('ppt/_rels/presentation.xml.rels', ''.join(prels))

    z.writestr('ppt/presProps.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentationPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')

    # slideMaster
    z.writestr('ppt/slideMasters/slideMaster1.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>'
        '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>'
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
        'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        '<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>')
    z.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
        '</Relationships>')
    # slideLayout (blank)
    z.writestr('ppt/slideLayouts/slideLayout1.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">'
        '<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>'
        '<p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
        'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sldLayout>')
    z.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
        '</Relationships>')
    # theme
    z.writestr('ppt/theme/theme1.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office">'
        '<a:themeElements><a:clrScheme name="Office">'
        '<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="%s"/></a:dk2><a:lt2><a:srgbClr val="%s"/></a:lt2>'
        '<a:accent1><a:srgbClr val="%s"/></a:accent1><a:accent2><a:srgbClr val="%s"/></a:accent2>'
        '<a:accent3><a:srgbClr val="%s"/></a:accent3><a:accent4><a:srgbClr val="%s"/></a:accent4>'
        '<a:accent5><a:srgbClr val="%s"/></a:accent5><a:accent6><a:srgbClr val="%s"/></a:accent6>'
        '<a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink>'
        '</a:clrScheme><a:fontScheme name="Office"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:majorFont>'
        '<a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme>'
        '<a:fmtScheme name="Office"/></a:themeElements></a:theme>' % (
        MAIN, LIGHT, ACCENT, AUX, MAIN, LIGHT, MAIN, LIGHT))
    # slides
    for i, sb in enumerate(slides):
        xml = slide_blank()[0] + "".join(sb) + slide_close()
        z.writestr(f'ppt/slides/slide{i+1}.xml', xml)
        z.writestr(f'ppt/slides/_rels/slide{i+1}.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
            '</Relationships>')
    # docProps（用 timezone-aware UTC 取时：utcnow() 已弃用，未来 Python 会移除）
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    z.writestr('docProps/core.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>蒸馏成技能Skill</dc:creator><cp:lastModifiedBy>蒸馏成技能Skill</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    z.writestr('docProps/app.xml',
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        '<Application>蒸馏成技能Skill</Application></Properties>')
    z.close()
    return out_path

def render_outline(o, out_path, attr=None,
                   mode=None, palette=None, font=None, scale=None,
                   version=None, layout=None):
    """大纲驱动渲染——内容无关，任何材料皆可。
    o = dict:
      title / subtitle
      chapters: [(num,title,desc), ...]            # 目录 + 顶部路线图
      sections: [ {type, ...}, ... ]               # 每节一页，type 自动选版式
      closing:  {title, points:[...]}
    section.type ∈ divider / cards / list / compare / steps / quote：
      divider : {type,cur,num,title,lead}
      cards   : {type,cur,title,subtitle,items:[(小标题,[要点...]), ...]}
      list    : {type,cur,title,subtitle,items:[文本,...]}
      compare : {type,cur,title,lh,ll,rh,rl}        # 左标题/左要点 / 右标题/右要点
      steps   : {type,cur,title,items:[文本,...]}
      quote   : {type,cur,title,quote,points:[...]}
    蒸馏步骤负责把源材料拆成 concise 要点；本函数只负责结构化排版。"""
    global MAIN, ACCENT, AUX, LIGHT, BODY, ANNOT, BORDER, WHITE, FONT, LAYOUT
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font, scale=scale,
                                version=version, layout=layout, fmt="ppt")
    MAIN   = tok["palette"]["MAIN"]
    ACCENT = tok["palette"]["ACCENT"]
    AUX    = tok["palette"]["AUX"]
    LIGHT  = tok["palette"]["LIGHT"]
    BODY   = tok["palette"]["BODY"]
    ANNOT  = tok["palette"]["ANNOT"]
    BORDER = tok["palette"]["BORDER"]
    WHITE  = "FFFFFF"
    FONT   = tok["font_office"]
    LAYOUT = tok["layout"]
    chapters=o.get('chapters',[])
    # 目录项超过 6 个会溢出，压缩描述或拆页由调用方控制；生成器只保证 6 项以内安全
    chapters=chapters[:6]
    sections=_split_sections(o.get('sections',[]))
    specs=[('cover',None)]
    if chapters: specs.append(('toc',None))
    for s in sections: specs.append(('sec',s))
    if o.get('closing'): specs.append(('closing',o['closing']))
    total=len(specs)
    slides=[]
    for idx,(kind,data) in enumerate(specs,1):
        sb=[]
        if kind=='cover':
            cover(sb,o['title'],o.get('subtitle',''))
        elif kind=='toc':
            toc_list(sb,chapters)
        elif kind=='sec':
            t=data['type']
            if t=='divider':
                divider(sb,chapters,data.get('cur',0),data['num'],data['title'],data.get('lead',''))
            else:
                title_band(sb,data['title'],data.get('subtitle'),data.get('cur'),chapters)
                if t=='cards': auto_cards(sb,data['items'])
                elif t=='list': badge_rows(sb,1.0,1.95,11.3,data['items'])
                elif t=='compare': compare_two(sb,0.9,1.95,11.5,4.5,data['lh'],data['ll'],data['rh'],data['rl'])
                elif t=='steps': steps_h(sb,0.9,2.5,11.5,data['items'])
                elif t=='quote': quote_block(sb,0.9,1.95,11.5,4.5,data['quote'],data.get('points'))
        elif kind=='closing':
            c=data
            sb.append(rect(0,0,13.333,7.5,fill=MAIN))
            sb.append(rect(0,3.0,13.333,0.09,fill=ACCENT))
            sb.append(text(1.5,2.0,10,1.0,[{'text':c['title'],'size':34,'bold':True,'color':WHITE,'align':'ctr'}],anchor="ctr"))
            y=3.6
            # 结尾页要点 ≤ 6，防溢出；落款由页脚统一承载，此处过滤掉重复落款（乙-4：末页落款重复）
            pts=[p for p in c.get('points',[]) if str(p).strip() != constants.FOOTER][:6]
            for p in pts:
                sb.append(text(2.0,y,9,0.5,[{'text':'· '+p,'size':16,'color':'C9D3DF','align':'ctr'}],anchor="ctr"))
                y+=0.62
        if idx == total:
            # 末页补来源总览（多份材料时）：贴免责之上，只报份数/来源，正文不逐条插页码
            ov = constants.sources_overview(o.get('sources'))
            if ov:
                sb.append(text(0.5, 6.24, 12.3, 0.2,
                               [{'text': ov, 'size': 8,
                                 'color': ('C9D3DF' if kind in ('closing', 'cover') else ANNOT),
                                 'align': 'ctr'}]))
            # 末页补免责声明（合规）：与页脚溯源落款是两句两处，不合并
            sb.append(text(0.5, 6.48, 12.3, 0.3,
                           [{'text': constants.disclaimer(o.get('topic')), 'size': 9,
                             'color': ('C9D3DF' if kind in ('closing', 'cover') else ANNOT),
                             'align': 'ctr'}]))
            # 末页补交付回执（闭环·反馈口）：贴免责之下、页脚之上，一行不换行
            sb.append(text(0.5, 6.70, 12.3, 0.2,
                           [{'text': constants.receipt_line(o.get('receipt_tags')), 'size': 8,
                             'color': ('C9D3DF' if kind in ('closing', 'cover') else ANNOT),
                             'align': 'ctr'}]))
        footer(sb,idx,total,attr=attr)
        slides.append(sb)
    return build_ppt(slides,out_path,total_override=total,
                      mode=mode,palette=palette,font=font,scale=scale,
                      version=version,layout=layout)

def _self_test():
    """最小自测：渲染一页 divider + 一页 cards，断言**要点真写入**。走临时目录。"""
    import tempfile, zipfile
    o = {
        "title": "自测演示",
        "subtitle": "自测副标题",
        "attr": "由 蒸馏成技能Skill 蒸馏产出",
        "chapters": [("1", "一、甲模块", "甲的核心句")],
        "sections": [
            {"type": "divider", "cur": 1, "num": "1",
             "title": "一、甲模块", "lead": "甲的核心句"},
            {"type": "cards", "title": "一、甲模块",
             "items": [("甲要点一", []), ("甲要点二", [])]},
        ],
        "closing": {"title": "谢谢", "points": ["由 蒸馏成技能Skill 蒸馏产出"]},
    }
    p = os.path.join(tempfile.mkdtemp(), "self.pptx")
    render_outline(o, p)
    assert os.path.getsize(p) > 0, "产物为空: %s" % p
    z = zipfile.ZipFile(p)
    blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
    for must in ("自测演示", "一、甲模块", "甲的核心句", "甲要点一", "甲要点二",
                 constants.RECEIPT_PREFIX, constants.RECEIPT_BOUND):
        assert must.encode("utf-8") in blob, "pptx 未写入内容: %s" % must
    slides = [n for n in z.namelist() if n.startswith("ppt/slides/slide")]
    assert len(slides) >= 2, "页数不足: %s" % slides
    # 乙-4：末页落款只准出现 1 次（页脚承载；结尾页要点若写落款，须被过滤掉）
    _sn = sorted((n for n in z.namelist()
                  if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
                 key=lambda n: int(n[len("ppt/slides/slide"):-len(".xml")]))
    _last = z.read(_sn[-1]).decode("utf-8")
    _n_foot = _last.count(constants.FOOTER)
    assert _n_foot == 1, "末页落款重复（乙-4）：出现 %d 次" % _n_foot
    print("self-test PASS: %s (%d B, %d slides)"
          % (os.path.basename(p), os.path.getsize(p), len(slides)))


if __name__ == '__main__':
    import argparse, json
    ap = argparse.ArgumentParser(description="生成 PPT 标准版（前置设计令牌库）")
    ap.add_argument("outline", nargs="?", help="大纲 JSON 路径")
    ap.add_argument("out", nargs="?", help="输出 .pptx 路径")
    ap.add_argument("--mode", help="模板模式: biz/lean/report/warm/red/sky/teal/violet")
    ap.add_argument("--palette", help="配色族: amber/red/sky/teal/warm/ink/violet")
    ap.add_argument("--font", help="字体族: hei/song/kai/deng")
    ap.add_argument("--scale", help="字号规格: standard/compact/report")
    ap.add_argument("--version", help="用户可选版本: standard/minimal/classic/premium/summary/course/data")
    ap.add_argument("--layout", help="版式风格: balanced/airy/formal/elegant")
    ap.add_argument("--self-test", action="store_true",
                    help="最小自测：渲染 divider+cards 两页并断言要点真写入（走临时目录）")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        raise SystemExit(0)
    if args.outline and args.out:
        with open(args.outline, "r", encoding="utf-8") as f:
            o = json.load(f)
        render_outline(o, args.out, mode=args.mode, palette=args.palette,
                       font=args.font, scale=args.scale,
                       version=args.version, layout=args.layout)
        print("生成:", args.out, "| 版本:", args.version or args.mode or "biz(默认)")
    else:
        print("build_ppt_standard: 引擎可执行 PPT 标准生成器（纯标准库，内容无关）。"
              "各平台 Agent 调用 render_outline(outline, out_path) 生成标准版 PPT，勿手搓。")
