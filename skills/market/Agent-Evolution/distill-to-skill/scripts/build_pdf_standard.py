# -*- coding: utf-8 -*-
"""
build_pdf_standard.py —— B/C 模式 PDF 标准生成器（纯标准库·零第三方依赖·内嵌中文子集·跨平台字体探测）

本生成器锁定（不混排西文字体、版式/字重统一）：
  - 单一 CJK 字体（默认 SimHei），全篇统一，绝不混排西文字体；
  - A4 + 固定页边距（20mm）；层级标题用主色；每节一句话核心用强调色；
  - 自动分页（不漂移、不随机断行）；页码；封面信息行；落款页；
  - 内嵌字体子集（Identity-H + ToUnicode），跨设备不乱码。

设计令牌（与 PPT/DOCX/XLSX 同源）：
  MAIN=#16335B  ACCENT=#E0A33E  BODY=#1F2733  GRAY=#6B7480

输入大纲 outline（dict）：
{
  "title":   "总标题",
  "subtitle":"副标题/口径（可选）",
  "date":    "2026-09-30",
  "source":  "由 蒸馏成技能Skill 蒸馏产出",
  "sections":[ {"heading":..,"core":..,"body":[..],
                "paragraphs":[..]},  # 可选·成段正文，渲染为不加符号的独立段落
               ... ]
}

用法：
  from build_pdf_standard import build_pdf
  build_pdf(outline, "输出.pdf")

硬规：
  - 找不到 CJK 字体时明确抛错（列出候选路径），绝不产出缺字/乱码 PDF。
  - 严禁 Agent 手搓 PDF 渲染或用平台「自由生成」PDF。
"""
import struct, zlib, datetime, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_tokens
import constants

# ---------- 设计令牌（RGB 0-1）----------
def _rgb(hex6):
    h = hex6
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)

MAIN = _rgb("16335B")
ACCENT = _rgb("E0A33E")
BODY = _rgb("1F2733")
GRAY = _rgb("6B7480")
WHITE = (1.0, 1.0, 1.0)

# 中文字体走跨平台探测（见 _find_font），不硬编码任何系统专用绝对路径。


# ============================================================
#  TTF 解析 + 子集化（仅保留正文用到的字形）
# ============================================================
class TTFSubset:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        self.off = 0
        # 处理 TTC（字体集合）：'ttcf'(4) + version(4) + numFonts(4) + offsetTable[0](4)…
        # 第一个字体偏移在 byte 12，不是 byte 8（byte 8 是 numFonts 字段，取错会读歪表目录）
        if self.data[:4] == b"ttcf":
            self.off = struct.unpack(">I", self.data[12:16])[0]  # 取第 0 个字体偏移
        self._read_dir()

    def _read_dir(self):
        d = self.data
        o = self.off
        (self.sfnt,) = struct.unpack(">I", d[o:o + 4])
        (numTables,) = struct.unpack(">H", d[o + 4:o + 6])
        self.tables = {}
        p = o + 12
        for _ in range(numTables):
            tag = d[p:p + 4].decode("latin1")
            (checksum,) = struct.unpack(">I", d[p + 4:p + 8])
            (offset,) = struct.unpack(">I", d[p + 8:p + 12])
            (length,) = struct.unpack(">I", d[p + 12:p + 16])
            self.tables[tag] = (offset, length)
            p += 16

    def _t(self, tag):
        off, ln = self.tables[tag]
        return self.data[off:off + ln]

    def _u16(self, b, p):
        return struct.unpack(">H", b[p:p + 2])[0]

    def _i16(self, b, p):
        return struct.unpack(">h", b[p:p + 2])[0]

    def _u32(self, b, p):
        return struct.unpack(">I", b[p:p + 4])[0]

    def parse(self, chars):
        """返回 (font_bytes, char2gid) 其中 char2gid: unicode -> 子集内 GID(0-based)"""
        head = self._t("head")
        unitsPerEm = self._u16(head, 18)
        indexToLocFormat = self._u16(head, 50)
        maxp = self._t("maxp")
        numGlyphs = self._u16(maxp, 4)
        loca = self._t("loca")
        glyf = self._t("glyf")
        hhea = self._t("hhea")
        numHMetrics = self._u16(hhea, 34)
        hmtx = self._t("hmtx")

        def glyph_offset(gid):
            if indexToLocFormat == 0:
                return self._u16(loca, gid * 2) * 2
            return self._u32(loca, gid * 4)

        def advance(gid):
            if gid < numHMetrics:
                return self._u16(hmtx, gid * 4)
            # 余下用最后一个 advance + lsb 数组
            last = self._u16(hmtx, (numHMetrics - 1) * 4)
            lsb_start = numHMetrics * 4
            return last  # 简化：用最后 advance

        # cmap
        cmap = self._t("cmap")
        nsub = self._u16(cmap, 2)
        best = None
        p = 4
        for _ in range(nsub):
            plat = self._u16(cmap, p)
            enc = self._u16(cmap, p + 2)
            off = self._u32(cmap, p + 4)
            p += 8
            if (plat, enc) in [(3, 1), (0, 3), (3, 10), (0, 4)]:
                if best is None:
                    best = off
        if best is None:
            raise RuntimeError("cmap 无 Unicode 子表")
        subt = cmap[best:best + 8]
        fmt = self._u16(subt, 0)
        if fmt == 4:
            char2old = self._cmap4(cmap[best:])
        elif fmt == 12:
            char2old = self._cmap12(cmap[best:])
        else:
            raise RuntimeError("不支持的 cmap 格式 %d" % fmt)

        # 收集需要的 old gid（含递归 composite）
        need = set()
        char2oldgid = {}
        for ch in chars:
            g = char2old.get(ord(ch))
            if g is None:
                g = 0
            char2oldgid[ch] = g
            need.add(g)
        # 递归 composite 组件
        stack = list(need)
        while stack:
            g = stack.pop()
            go = glyph_offset(g)
            ncont = self._i16(glyf, go)
            if ncont == -1:
                comps = self._composite_components(glyf, go)
                for cg in comps:
                    if cg not in need:
                        need.add(cg)
                        stack.append(cg)
        # 排序：0 在前，其余升序
        ordered = sorted(need)
        old2new = {g: i for i, g in enumerate(ordered)}

        # 重建 glyf（含 composite 组件重映射）
        new_glyf_parts = []
        new_offsets = [0]
        for g in ordered:
            go = glyph_offset(g)
            gn = glyph_offset(g + 1) if g + 1 < numGlyphs else len(glyf)
            raw = glyf[go:gn]
            if len(raw) < 12:  # 空字形（如 .notdef），原样保留
                new_glyf_parts.append(raw)
                new_offsets.append(new_offsets[-1] + len(raw))
                continue
            ncont = self._i16(raw, 0)
            if ncont == -1:
                raw = self._remap_composite(raw, old2new)
            new_glyf_parts.append(raw)
            new_offsets.append(new_offsets[-1] + len(raw))
        new_glyf = b"".join(new_glyf_parts)
        # 4 字节对齐
        pad = (-len(new_glyf)) % 4
        new_glyf += b"\x00" * pad
        # loca
        if new_offsets[-1] + pad > 0xFFFF * 2:
            indexToLocFormat = 1
        loca_out = b""
        if indexToLocFormat == 0:
            for off in new_offsets:
                loca_out += struct.pack(">H", off // 2)
        else:
            for off in new_offsets:
                loca_out += struct.pack(">I", off)

        # hmtx
        hmtx_out = b""
        for g in ordered:
            if g < numHMetrics:
                adv = self._u16(hmtx, g * 4)
                lsb = self._i16(hmtx, g * 4 + 2)
            else:
                adv = self._u16(hmtx, (numHMetrics - 1) * 4)
                lsb = self._i16(hmtx, numHMetrics * 4 + (g - numHMetrics) * 2)
            hmtx_out += struct.pack(">Hh", adv, lsb)

        # cmap format4（platform 3 / enc 1）
        cmap_out = self._build_cmap4(char2oldgid, old2new)

        # maxp 更新 numGlyphs
        maxp_out = bytearray(maxp)
        maxp_out[4:6] = struct.pack(">H", len(ordered))

        # head 更新 indexToLocFormat + checkSumAdjustment
        head_out = bytearray(head)
        head_out[50:52] = struct.pack(">H", indexToLocFormat)
        head_out[8:12] = b"\x00\x00\x00\x00"

        # hhea 保留；OS/2 保留原样；post 写 format3；name 保留原样
        os2 = self._t("os2") if "os2" in self.tables else None
        name = self._t("name") if "name" in self.tables else None
        post = self._build_post3()
        extra = {}
        for t in ("fpgm", "prep", "cvt ", "gasp"):
            if t in self.tables:
                extra[t] = self._t(t)

        font = self._assemble({
            "head": bytes(head_out), "hhea": hhea, "maxp": bytes(maxp_out),
            "loca": loca_out, "glyf": new_glyf, "hmtx": hmtx_out,
            "cmap": cmap_out, "post": post,
            "OS/2": os2, "name": name, **extra,
        })
        char2gid = {ch: old2new[g] for ch, g in char2oldgid.items()}
        return font, char2gid, unitsPerEm

    def _cmap4(self, b):
        # b 以 subtable 起始
        segX2 = self._u16(b, 6)
        segCount = segX2 // 2
        eofs = 14
        end = [self._u16(b, eofs + i * 2) for i in range(segCount)]
        sstart = eofs + segCount * 2 + 2
        start = [self._u16(b, sstart + i * 2) for i in range(segCount)]
        didx = sstart + segCount * 2
        delta = [self._u16(b, didx + i * 2) for i in range(segCount)]
        iro = didx + segCount * 2
        idRange = [self._u16(b, iro + i * 2) for i in range(segCount)]
        gidmap = {}
        glyphDataStart = iro + segCount * 2
        for i in range(segCount):
            if start[i] == 0xFFFF:
                continue
            for ch in range(start[i], end[i] + 1):
                if idRange[i] == 0:
                    g = (ch + delta[i]) & 0xFFFF
                else:
                    addr = glyphDataStart + (ch - start[i]) * 2 + idRange[i]
                    g = self._u16(b, addr)
                    if g != 0:
                        g = (g + delta[i]) & 0xFFFF
                if g != 0:
                    gidmap[ch] = g
        return gidmap

    def _cmap12(self, b):
        ngrp = self._u32(b, 12)
        gidmap = {}
        p = 16
        for _ in range(ngrp):
            s = self._u32(b, p)
            e = self._u32(b, p + 4)
            g = self._u32(b, p + 8)
            for ch in range(s, e + 1):
                gidmap[ch] = g + (ch - s)
            p += 12
        return gidmap

    def _composite_components(self, glyf, go):
        comps = []
        if go + 12 > len(glyf):
            return comps
        p = 10
        while True:
            flags = self._u16(glyf, go + p)
            cg = self._u16(glyf, go + p + 2)
            comps.append(cg)
            p += 4
            if flags & 0x0001:
                p += 4
            else:
                p += 2
            if flags & 0x0008:
                p += 2
            elif flags & 0x0040:
                p += 4
            elif flags & 0x0080:
                p += 8
            if flags & 0x0100:
                # 指令在全部组件之后
                pass
            if not (flags & 0x0020):
                break
        return comps

    def _remap_composite(self, raw, old2new):
        if len(raw) < 12:
            return raw
        out = bytearray(raw[:10])
        p = 10
        has_instr = False
        comp_bytes = []
        while True:
            flags = self._u16(raw, p)
            cg = self._u16(raw, p + 2)
            comp_bytes.append(struct.pack(">H", flags))
            comp_bytes.append(struct.pack(">H", old2new.get(cg, 0)))
            p += 4
            if flags & 0x0001:
                comp_bytes.append(raw[p:p + 4]); p += 4
            else:
                comp_bytes.append(raw[p:p + 2]); p += 2
            if flags & 0x0008:
                comp_bytes.append(raw[p:p + 2]); p += 2
            elif flags & 0x0040:
                comp_bytes.append(raw[p:p + 4]); p += 4
            elif flags & 0x0080:
                comp_bytes.append(raw[p:p + 8]); p += 8
            if flags & 0x0100:
                has_instr = True
            if not (flags & 0x0020):
                break
        if has_instr:
            comp_bytes.append(raw[p:p + 2])
            ilen = self._u16(raw, p)
            p += 2
            comp_bytes.append(raw[p:p + ilen])
        out.extend(b"".join(comp_bytes))
        return bytes(out)

    def _build_cmap4(self, char2oldgid, old2new):
        # 构建 char -> new_gid
        pairs = sorted(set((ord(ch), old2new[g]) for ch, g in char2oldgid.items()))
        # 合并连续 char 且连续 new_gid 的段
        segs = []
        for ch, ng in pairs:
            if segs and segs[-1][1] + 1 == ch and segs[-1][3] + 1 == ng:
                segs[-1][1] = ch
                segs[-1][3] = ng
            else:
                segs.append([ch, ch, ng, ng])
        segCount = len(segs) + 1  # + 末尾 0xFFFF
        endCode = [s[1] for s in segs] + [0xFFFF]
        startCode = [s[0] for s in segs] + [0xFFFF]
        idDelta = []
        for s in segs:
            idDelta.append((s[3] - s[1]) & 0xFFFF)
        idDelta.append(1)  # 末尾 0xFFFF -> 0
        idRangeOffset = [0] * segCount
        searchRange = (1 << (segCount - 1).bit_length() - 1) * 2 if segCount else 0
        entrySelector = (segCount - 1).bit_length() - 1 if segCount else 0
        rangeShift = segCount * 2 - searchRange
        subt = b""
        subt += struct.pack(">H", 4)
        subt += struct.pack(">H", 0)  # length placeholder
        subt += struct.pack(">H", 0)  # language
        subt += struct.pack(">H", segCount * 2)
        subt += struct.pack(">H", searchRange)
        subt += struct.pack(">H", entrySelector)
        subt += struct.pack(">H", rangeShift)
        for e in endCode:
            subt += struct.pack(">H", e)
        subt += struct.pack(">H", 0)  # reserved
        for s in startCode:
            subt += struct.pack(">H", s)
        for d in idDelta:
            subt += struct.pack(">H", d)
        for r in idRangeOffset:
            subt += struct.pack(">H", r)
        subt = subt[:2] + struct.pack(">H", len(subt)) + subt[4:]
        cmap = b"\x00\x00\x00\x01"  # version, numSubtables=1
        cmap += struct.pack(">H", 3) + struct.pack(">H", 1) + struct.pack(">I", 4)
        cmap += subt
        return cmap

    def _build_post3(self):
        return struct.pack(">I", 0x00030000) + struct.pack(">i", 0) + \
               struct.pack(">h", -100) + struct.pack(">h", 0) + \
               struct.pack(">I", 0) * 4

    def _table_checksum(self, b):
        s = 0
        n = len(b) // 4
        for i in range(n):
            s = (s + struct.unpack(">I", b[i * 4:i * 4 + 4])[0]) & 0xFFFFFFFF
        if len(b) % 4:
            rem = b[n * 4:] + b"\x00" * (4 - len(b) % 4)
            s = (s + struct.unpack(">I", rem)[0]) & 0xFFFFFFFF
        return s

    def _assemble(self, tables):
        # 过滤 None
        tabs = {k: v for k, v in tables.items() if v is not None}
        tags = sorted(tabs.keys())
        # 计算各表（head 的 checksumAdjustment 先置 0 已处理）
        # 先写 head 的 checksum 用 0 调整
        recs = {}
        for t in tags:
            recs[t] = (self._table_checksum(tabs[t]), tabs[t])
        # 计算 head checksum 占位（已置0），整体 checkSumAdjustment
        total = 0
        for t in tags:
            total = (total + recs[t][0]) & 0xFFFFFFFF
        # 重新算 head 的 checksum（head 内 checkSumAdjustment=0）
        head_cs = recs["head"][0]
        adjust = (0xB1B0AFBA - total) & 0xFFFFFFFF
        # 写回 head 的 checkSumAdjustment
        head_bytes = bytearray(recs["head"][1])
        head_bytes[8:12] = struct.pack(">I", adjust)
        recs["head"] = (self._table_checksum(bytes(head_bytes)), bytes(head_bytes))
        # 重新累加（head 变了）
        total = 0
        for t in tags:
            total = (total + recs[t][0]) & 0xFFFFFFFF
        # 组装
        numTables = len(tags)
        header = b"\x00\x01\x00\x00"  # TrueType sfnt
        header += struct.pack(">H", numTables)
        searchRange = (1 << (numTables - 1).bit_length() - 1) * 16 if numTables else 0
        entrySelector = (numTables - 1).bit_length() - 1 if numTables else 0
        rangeShift = numTables * 16 - searchRange
        header += struct.pack(">H", searchRange)
        header += struct.pack(">H", entrySelector)
        header += struct.pack(">H", rangeShift)
        body = b""
        offsets = {}
        # 对齐表顺序：按 tag
        # 先计算起始偏移
        cur = 12 + numTables * 16
        rec_entries = b""
        for t in tags:
            ln = len(recs[t][1])
            pad = (-ln) % 4
            offsets[t] = cur
            rec_entries += t.encode("latin1") + struct.pack(">I", recs[t][0]) + \
                          struct.pack(">I", cur) + struct.pack(">I", ln)
            body += recs[t][1] + b"\x00" * pad
            cur += ln + pad
        return header + rec_entries + body


# ============================================================
#  PDF 写入
# ============================================================
# 中文字体候选文件名（按文件名匹配，不硬编码任何系统绝对路径）
_CJK_FONT_NAMES = [
    "simhei.ttf", "msyh.ttc", "msyh.ttf", "simsun.ttc", "simsun.ttf",
    "NotoSansSC-Regular.ttf", "NotoSansSC-VF.ttf", "NotoSansCJK-Regular.ttc",
    "NotoSansCJKsc-Regular.otf", "SourceHanSansSC-Regular.otf",
    "wqy-zenhei.ttc", "wqy-microhei.ttc",
    "PingFang.ttc", "STHeiti Light.ttc", "STHeiti Medium.ttc",
    "Hiragino Sans GB.ttc", "Songti.ttc", "Heiti SC.ttc",
]

def _font_search_dirs():
    """返回当前系统的字体搜索目录（按优先级），不依赖硬编码绝对路径。"""
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        windir = os.environ.get("SystemRoot", r"C:\Windows")
        return [os.path.join(windir, "Fonts")]
    if sys.platform == "darwin":
        return ["/System/Library/Fonts", "/Library/Fonts",
                os.path.join(home, "Library", "Fonts")]
    # linux / other
    return ["/usr/share/fonts", "/usr/local/share/fonts",
            os.path.join(home, ".fonts"),
            os.path.join(home, ".local", "share", "fonts")]

def _find_font(family=None):
    # ① 显式环境变量优先（运行环境可传入字体路径，跨平台通用）
    env = os.environ.get("AI_DISTILL_FONT")
    if env and os.path.exists(env):
        return env
    # ② 按所选字体族（hei/song/kai/deng）取候选文件名列表；缺省用全量候选
    if family:
        cand = design_tokens.FONTS.get(family, {}).get("pdf") or _CJK_FONT_NAMES
    else:
        cand = _CJK_FONT_NAMES
    names = set(n.lower() for n in cand)
    for d in _font_search_dirs():
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):                      # 平级目录
            if fn.lower() in names:
                return os.path.join(d, fn)
        try:                                          # 一层子目录（truetype/opentype/CJK…）
            subs = [os.path.join(d, s) for s in os.listdir(d)
                    if os.path.isdir(os.path.join(d, s))][:200]
        except OSError:
            subs = []
        for sd in subs:
            for fn in os.listdir(sd):
                if fn.lower() in names:
                    return os.path.join(sd, fn)
    raise RuntimeError(
        "未找到中文字体（已按当前系统 %s 探测常见字体目录）。\n"
        "请安装任一含中文的 TTF/TTC（如 Noto Sans CJK / 思源黑体 / 黑体），"
        "或调用 build_pdf(..., font_path=<字体绝对路径>) 显式传入；"
        "亦可用环境变量 AI_DISTILL_FONT 指定路径。" % sys.platform
    )


# 行首禁则（不得出现在行首的字符）与行尾禁则（不得出现在行尾的字符）——中文避头尾规则
_NO_LINE_START = "、。，．！？；：）〕］｝〉》」』】”’%‰℃°·…—～!?,.;:)]}"
_NO_LINE_END = "（〔［｛〈《「『【“‘([{"


def _fix_kinsoku(lines):
    """中文避头尾：行首禁则字符拉回上一行行尾；开引号等行尾禁则字符推到下一行行首。
    防「标点孤行」——末行只剩一个 `）` / `。` / `”` 这类违反行首禁则的排版。"""
    lines = [l for l in lines if l]
    if len(lines) <= 1:
        return lines or [""]
    out = [lines[0]]
    for ln in lines[1:]:
        # 行首禁则：把行首的禁则字符挪回上一行末尾
        while ln and ln[0] in _NO_LINE_START and out:
            out[-1] += ln[0]
            ln = ln[1:]
        # 行尾禁则：上一行末尾是开引号/开括号 → 挪到本行行首
        while ln and out and out[-1] and out[-1][-1] in _NO_LINE_END:
            ln = out[-1][-1] + ln
            out[-1] = out[-1][:-1]
        out = [l for l in out if l]
        if ln:
            out.append(ln)
    return out or [""]


def _wrap(text, adv_fn, size, units, max_w):
    """按字符宽度换行。CJK 按字符硬断；ASCII 优先在空格断；保证每行不超出 max_w。"""
    def cw(c):
        return adv_fn(ord(c)) * size / units

    lines = []
    cur = ""
    cur_w = 0.0
    last_space_idx = -1
    for ch in text:
        w = cw(ch)
        if cur_w + w > max_w and cur:
            # 有 ASCII 空格时，回退到最后一个空格处换行。
            # 边界：last_space_idx==1 时回退会只剩一个项目符号（"- " 的空格在索引 1）
            # → 产生「项目符号孤行」。故要求回退点 >1，否则走硬断（整行保留）。
            if last_space_idx > 1:
                line = cur[:last_space_idx]
                nxt = cur[last_space_idx + 1:]
                lines.append(line)
                cur = nxt + ch
                cur_w = sum(cw(c) for c in cur)
            else:
                lines.append(cur)
                cur = ch
                cur_w = w
            # 重新计算最后一个空格位置
            if " " in cur:
                last_space_idx = cur.rindex(" ")
            else:
                last_space_idx = -1
        else:
            cur += ch
            cur_w += w
            if ch == " ":
                last_space_idx = len(cur) - 1
    if cur:
        lines.append(cur)
    return _fix_kinsoku(lines or [""])


def build_pdf(outline, out_path, font_path=None, mode=None, palette=None, font=None, scale=None, number=None):
    """入口：outline 为结构化大纲（与题材无关），驱动生成标准 .pdf。
    可选 token 参数（前置设计令牌库）：
      mode=预设模式(biz/lean/report/warm/red/sky/teal/violet)，或自由组合
      palette=配色族 / font=字体族(hei/song/kai/deng) / scale=字号规格(standard/compact/report)
      number=序号系统(arabic/cn/circle/none·不填=保留原标题，向后兼容)
    不选则用默认 biz（与既有默认值一致）。
    """
    global MAIN, ACCENT, BODY, GRAY, SCALE
    tok = design_tokens.resolve(mode=mode, palette=palette, font=font, scale=scale, number=number, fmt="pdf")
    num_fn = tok["number"] if number else None  # number 未显式指定→保留原标题（不回归）
    # 覆盖模块级配色（PDF 用 RGB 元组）
    MAIN = _rgb(tok["palette"]["MAIN"])
    ACCENT = _rgb(tok["palette"]["ACCENT"])
    BODY = _rgb(tok["palette"]["BODY"])
    GRAY = _rgb(tok["palette"]["GRAY"])
    SCALE = tok["scale"]["pdf"]
    # 字体
    if font_path is None:
        font_path = _find_font(family=tok["font_name"])
    title = outline.get("title", "蒸馏精华")
    subtitle = outline.get("subtitle", "")
    date = outline.get("date") or datetime.date.today().isoformat()
    source = outline.get("source", constants.FOOTER)
    sections = outline.get("sections", [])
    disclaimer_text = "（%s）" % constants.disclaimer(outline.get("topic"))
    receipt_text = constants.receipt_line(outline.get("receipt_tags"))
    ov_text = constants.sources_overview(outline.get("sources"))

    # 收集所有字符（含硬编码 UI 前缀，否则会渲染成空白框）
    chars = set()
    for s in (title, subtitle, date, source, constants.FOOTER, disclaimer_text,
              receipt_text, ov_text, "第 页",
              "一句话核心：", "- ", "0123456789",
              "一二三四五六七八九十百零、（）①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"):
        chars.update(s)
    for sec in sections:
        chars.update(sec.get("heading", ""))
        chars.update(sec.get("core", ""))
        for it in sec.get("body", []):
            chars.update(it)
        # 成段正文同样要进字形子集 —— 只加渲染不加子集，段落会渲染成空白框。
        for p in sec.get("paragraphs", []) or []:
            chars.update(p)

    font_bytes, char2gid, units = TTFSubset(font_path).parse(chars)
    # 缺失字形宽（用 gid0 或默认 500）
    gid0_adv = 500

    def adv(unicode_char):
        g = char2gid.get(chr(unicode_char))
        if g is None:
            return gid0_adv
        # 从字体取 advance：通过 cmap 反查后读 hmtx 太重，直接用近似 1000 单位
        return 1000  # 简单近似：等宽按 1000 单位估算（视觉可接受）

    # 排版宽度近似（按字体 unitsPerEm 归一化）：CJK 近似全角，ASCII 近似半角
    def adv2(unicode_char):
        c = chr(unicode_char)
        if ord(c) < 128:
            return int(units * 0.55)
        return int(units * 1.05)

    # 文本编码为 GID 十六进制
    def enc(text):
        out = bytearray()
        for ch in text:
            g = char2gid.get(ch, 0)
            out += b"%04X" % g
        return bytes(out)

    # 页面与版式
    PW, PH = 595.28, 841.89
    ML = MR = 56.7
    MT = 56.7
    MB = 56.7
    avail = PW - ML - MR

    # 颜色
    def col(c):
        return "%.3f %.3f %.3f rg" % c

    # 构建内容流（分页）
    pages_content = []
    ops = []
    y = PH - MT

    def newpage():
        nonlocal ops, y
        if ops:
            pages_content.append(ops)
        ops = []
        y = PH - MT

    def line_gap(h):
        nonlocal y
        y -= h
        if y < MB + 20:
            newpage()

    def draw_text(txt, size, color, lh, bold=False, indent=0):
        nonlocal y
        lines = _wrap(txt, adv2, size, units, avail - indent)
        # 整个文本块绘制前先看是否跨页：第一行连一行都放不下就换页
        if y - size < MB + 10:
            newpage()
        for ln in lines:
            if y - size < MB + 10:
                newpage()
            x = ML + indent
            ops.append("BT /F1 %g Tf %s 1 0 0 1 %g %g Tm <%s> Tj ET" %
                       (size, col(color), x, y - size, enc(ln).decode("ascii")))
            # 行距不得小于字号本身（防相邻两行叠压）；调用方传的 lh 只作下限参考
            y -= max(lh, size * 1.25)

    def draw_rule():
        nonlocal y
        if y < MB + 14:
            newpage()
        ops.append("%.3f %.3f %.3f RG 0.6 w %g %g m %g %g l S" %
                   (MAIN[0], MAIN[1], MAIN[2], ML, y, PW - MR, y))
        y -= 12

    def draw_table(headers, rows, col_widths=None):
        """绘制简单表格：表头深蓝底白字，数据行白底深灰字，细边框"""
        nonlocal y
        ncols = len(headers)
        if col_widths is None:
            cw = (PW - ML - MR - (ncols - 1) * 4) / ncols
            col_widths = [cw] * ncols
        row_h = 18
        # 表头
        if y - row_h < MB + 10:
            newpage()
        x = ML
        for i, h in enumerate(headers):
            ops.append("%.3f %.3f %.3f rg %g %g %g %g re f" %
                       (MAIN[0], MAIN[1], MAIN[2], x, y - row_h, col_widths[i], row_h))
            ops.append("BT /F1 10 Tf 1 0 0 1 %g %g Tm <%s> Tj ET" %
                       (x + 2, y - row_h + 5, enc(h).decode("ascii")))
            x += col_widths[i] + 4
        y -= row_h
        # 数据行
        for row in rows:
            if y - row_h < MB + 10:
                newpage()
            x = ML
            for i, v in enumerate(row[:ncols]):
                text_v = str(v)
                ops.append("BT /F1 9 Tf %.3f %.3f %.3f rg 1 0 0 1 %g %g Tm <%s> Tj ET" %
                           (BODY[0], BODY[1], BODY[2], x + 2, y - row_h + 5, enc(text_v).decode("ascii")))
                # 边框
                ops.append("%.3f %.3f %.3f RG 0.4 w %g %g m %g %g l %g %g l %g %g l %g %g l S" %
                           (0.85, 0.87, 0.90, x, y - row_h, x + col_widths[i], y - row_h,
                            x + col_widths[i], y, x, y, x, y - row_h))
                x += col_widths[i] + 4
            y -= row_h
        y -= 6

    def draw_page_number(pno):
        s = "第 %d 页" % pno
        ops.append("BT /F1 %g Tf %s 1 0 0 1 %g %g Tm <%s> Tj ET" %
                   (SCALE["page"], col(GRAY), PW / 2 - 20, MB - 14, enc(s).decode("ascii")))

    # 封面信息行 + 标题
    draw_text(source, SCALE["annot"], GRAY, 14)
    line_gap(4)
    draw_text(title, SCALE["cover"], MAIN, 28, bold=True)
    if subtitle:
        draw_text(subtitle, SCALE["h2"], GRAY, 18)
    draw_text("（%s）" % date, SCALE["annot"], GRAY, 16)
    draw_rule()
    line_gap(6)

    for i, sec in enumerate(sections, 1):
        heading = design_tokens.number_heading(sec.get("heading", ""), 1, i, 0, num_fn)
        draw_text(heading, SCALE["h1"], MAIN, 22, bold=True)
        core = sec.get("core", "")
        if core:
            draw_text("一句话核心：" + core, SCALE["core"], ACCENT, 17)
        line_gap(2)
        # 成段正文（讲稿体/口播体的载体）——与要点列表职责不同：段落不加 "- " 前缀。
        for p in sec.get("paragraphs", []) or []:
            draw_text(p, SCALE["body"], BODY, 16)
            line_gap(1)
        for it in sec.get("body", []):
            body = it if (it.startswith("- ") or it.startswith("• ")) else "- " + it
            draw_text(body, SCALE["body"], BODY, 16, indent=4)
        tbl = sec.get("table")
        if tbl:
            draw_table(tbl.get("headers", []), tbl.get("rows", []))
        line_gap(8)

    # 落款页
    draw_rule()
    draw_text(source, SCALE["annot"], GRAY, 16)
    if ov_text:
        draw_text(ov_text, SCALE["annot"], GRAY, 14)
    draw_text(disclaimer_text, SCALE["annot"], GRAY, 14)
    draw_text(receipt_text, SCALE["annot"], GRAY, 12)
    newpage()

    # 补页码（追加到每页内容流末尾）
    final_pages = []
    for i, ops_p in enumerate(pages_content):
        pg = list(ops_p)
        s = "第 %d 页" % (i + 1)
        pg.append("BT /F1 %g Tf %s 1 0 0 1 %g %g Tm <%s> Tj ET" %
                   (SCALE["page"], col(GRAY), PW / 2 - 20, MB - 14, enc(s).decode("ascii")))
        final_pages.append("\n".join(pg).encode("latin1"))
    pages_content = final_pages

    # 组装 PDF 对象
    objs = []
    # 1 Catalog, 2 Pages, 3 Font, 4 ToUnicode, then per page: Page + Content
    font_res_name = "F1"
    # Font 对象
    subset_tag = "DSTILL"
    _FAMILY_NAME = {"hei": "SimHei", "song": "SimSun", "kai": "KaiTi", "deng": "Deng"}
    family = _FAMILY_NAME.get(tok["font_name"], "SimHei")
    base = "%s+%s" % (subset_tag, family)
    # FontDescriptor
    fd = ("<< /Type /FontDescriptor /FontName /%s "
          "/Flags 4 /FontBBox [-100 -100 1200 900] /ItalicAngle 0 "
          "/Ascent 800 /Descent -200 /CapHeight 800 /StemV 80 "
          "/FontFile2 %d 0 R >>" % (base, 0))  # FontFile2 ref 占位
    # 先排对象编号
    # 1: Catalog, 2: Pages, 3: Font(Type0), 4: CIDFontType2, 5: FontDescriptor, 6: ToUnicode
    # 7..: 每页 Page, Content
    n_pages_real = len(pages_content)
    # 对象编号
    CATALOG, PAGES, TYPE0, CIDFONT, FD, TOUNI = 1, 2, 3, 4, 5, 6
    page_obj_start = 7
    content_obj_start = page_obj_start + n_pages_real

    # FontFile2 ref = 最后一个对象之后新建
    fontfile_obj = content_obj_start + n_pages_real

    fd = ("<< /Type /FontDescriptor /FontName /%s "
          "/Flags 4 /FontBBox [-100 -100 1200 900] /ItalicAngle 0 "
          "/Ascent 800 /Descent -200 /CapHeight 800 /StemV 80 "
          "/FontFile2 %d 0 R >>" % (base, fontfile_obj))

    cidfont = ("<< /Type /Font /Subtype /CIDFontType2 /BaseFont /%s "
               "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
               "/FontDescriptor %d 0 R /CIDToGIDMap /Identity >>" % (base, FD))
    type0 = ("<< /Type /Font /Subtype /Type0 /BaseFont /%s "
             "/Encoding /Identity-H /DescendantFonts [%d 0 R] /ToUnicode %d 0 R >>"
             % (base, CIDFONT, TOUNI))

    # ToUnicode CMap
    bf = []
    for ch, g in sorted(char2gid.items()):
        bf.append("<%04X> <%04X>" % (g, ord(ch)))
    bftext = "\n".join(bf)
    touc = ("/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
             "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> def\n"
             "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
             "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
             "%d beginbfchar\n%s\nendbfchar\nendcmap\n"
             "CMapName currentdict /CMap defineresource pop\nend end" %
             (len(bf), bftext)).encode("latin1")

    # Pages 对象引用
    kids = " ".join("%d 0 R" % (page_obj_start + i) for i in range(n_pages_real))
    pages_obj = "<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n_pages_real)
    catalog = "<< /Type /Catalog /Pages %d 0 R >>" % PAGES

    objs = {}
    objs[CATALOG] = catalog
    objs[PAGES] = pages_obj
    objs[TYPE0] = type0
    objs[CIDFONT] = cidfont
    objs[FD] = fd
    objs[TOUNI] = touc
    for i in range(n_pages_real):
        page = ("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %g %g] "
                "/Resources << /Font << /%s %d 0 R >> >> /Contents %d 0 R >>"
                % (PAGES, PW, PH, font_res_name, TYPE0, content_obj_start + i))
        objs[page_obj_start + i] = page
        content = pages_content[i]
        objs[content_obj_start + i] = content
    objs[fontfile_obj] = font_bytes  # 二进制流

    # 写文件
    out = []
    out.append(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    buf = b""
    # 按顺序写对象 1..max
    max_obj = max(objs.keys())
    body = b""
    for num in range(1, max_obj + 1):
        offsets[num] = len(body)
        val = objs[num]
        if isinstance(val, bytes):
            body += ("%d 0 obj\n" % num).encode("latin1")
            body += b"<< /Length %d >>\nstream\n" % len(val)
            body += val
            body += b"\nendstream\nendobj\n"
        else:
            body += ("%d 0 obj\n%s\nendobj\n" % (num, val)).encode("latin1")
    xref_pos = len(body)
    n = max_obj + 1
    xref = b"xref\n0 %d\n" % n
    xref += b"0000000000 65535 f \n"
    for num in range(1, max_obj + 1):
        xref += ("%010d 00000 n \n" % offsets[num]).encode("latin1")
    trailer = ("trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
               % (n, CATALOG, xref_pos))
    out = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n" + body + xref + trailer.encode("latin1")
    with open(out_path, "wb") as f:
        f.write(out)
    return out_path


def _self_test():
    """离线自测：试渲一份最小 PDF，做**内容级结构断言**（不只"字节>0"）。

    无中文字体时 SKIP（exit=0）。断言点：PDF 头标记 / 尾标记 / 内嵌
    ToUnicode（文本可抽取、跨设备不乱码）/ 体积下限。
    """
    import tempfile
    demo = {
        "title": "自测 PDF",
        "subtitle": "内容级断言",
        "date": "2026-01-01",
        "source": "由 蒸馏成技能Skill 蒸馏产出",
        "sections": [
            {"heading": "一、模块甲", "core": "甲核心文本",
             "body": ["甲要点一", "甲要点二"]},
            {"heading": "二、模块乙", "core": "乙核心文本",
             "body": ["乙要点一"]},
        ],
    }
    td = tempfile.mkdtemp()
    out = os.path.join(td, "selftest.pdf")
    try:
        build_pdf(demo, out)
    except RuntimeError as e:
        print("SKIP build_pdf：未找到中文字体（%s）" % str(e).strip().splitlines()[0][:70])
        return 0
    assert os.path.exists(out), "未产出 PDF"
    raw = open(out, "rb").read()
    assert raw[:5] == b"%PDF-", "PDF 头标记缺失"
    assert b"%%EOF" in raw[-128:], "PDF 尾标记缺失"
    assert b"ToUnicode" in raw, "未内嵌 ToUnicode（文本不可抽取/跨设备乱码风险）"
    assert len(raw) > 1000, "PDF 体积异常：%d B" % len(raw)
    # 丙-4：页码必须走令牌字号（SCALE["page"]），不得硬编码 9
    assert ("/F1 %g Tf" % SCALE["page"]).encode("ascii") in raw, \
        "页码未使用令牌字号 SCALE['page']"
    # 丙-2 / 丙-3：折行器内容级断言（纯逻辑，不依赖字体）
    _adv = (lambda _i: 1000)                       # 等宽假字宽
    _long = "这是一句足够长的中文测试文本用来触发折行并且把标点推到下一行看看会不会出现标点孤行。"
    for _l in _wrap(_long, _adv, 10, 1000, 30):    # 每行约 3 字，强制多行
        assert _l != "", "折行产生了空行"
        assert _l[0] not in _NO_LINE_START, "行首出现禁则字符（标点孤行）：%r" % _l
    _bullet = _wrap("- 这是第一条足够长的要点用于验证项目符号不会被单独留在某一行", _adv, 10, 1000, 30)
    assert all(_l.strip() not in ("-", "•", "") for _l in _bullet), \
        "项目符号独占一行：%r" % _bullet
    # 交付回执必须进字体子集（漏进 chars 会渲染成空白框）
    import re as _re
    _cm = set(_re.findall(rb"<[0-9A-F]{4}> <([0-9A-F]{4})>", raw))
    for _c in constants.RECEIPT_PREFIX + constants.RECEIPT_BOUND:
        assert ("%04X" % ord(_c)).encode("ascii") in _cm, \
            "PDF 未子集化交付回执字符（会渲染成空白框）: %r" % _c
    print("PASS build_pdf：%d B，头/尾/ToUnicode 齐 + 禁则/孤行/页码令牌/回执 过" % len(raw))
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="生成 PDF 标准版（前置设计令牌库）")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="离线自测：试渲最小 PDF 做内容级结构断言（无中文字体则 SKIP）")
    ap.add_argument("outline", nargs="?", help="大纲 JSON 路径")
    ap.add_argument("out", nargs="?", help="输出 .pdf 路径")
    ap.add_argument("--mode", help="模板模式: biz/lean/report/warm/red/sky/teal/violet")
    ap.add_argument("--palette", help="配色族: amber/red/sky/teal/warm/ink/violet")
    ap.add_argument("--font", help="字体族: hei/song/kai/deng")
    ap.add_argument("--scale", help="字号规格: standard/compact/report")
    ap.add_argument("--number", help="序号系统: arabic/cn/circle/none（不填=保留原标题）")
    args = ap.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    if args.outline and args.out:
        with open(args.outline, "r", encoding="utf-8") as f:
            demo = json.load(f)
        build_pdf(demo, args.out, mode=args.mode, palette=args.palette,
                  font=args.font, scale=args.scale, number=args.number)
        print("生成:", args.out, "| 模式:", args.mode or "biz(默认)",
              "| 序号:", args.number or "保留原标题")
        raise SystemExit
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
            {"heading": "三、GitHub 仓库 Skill 一键批量导入",
             "core": "60 秒内完成公开仓库 Skill 的批量发布。",
             "body": ["旧流程繁琐：打 zip → 拖拽 → 抄 slug/名称/版本号。",
                      "新流程：发布页选导入 → 勾选 → 确认 → 一键发布。",
                      "关键规则：单次≤5 个；自动扫 SKILL.md；Slug 实时查重。"]},
        ],
    }
    suffix = ("_%s" % (args.mode or "biz")) + ("_num%s" % args.number if args.number else "")
    import tempfile as _tf
    out = os.path.join(_tf.mkdtemp(), "SkillHub_精华萃取%s.pdf" % suffix)
    build_pdf(demo, out, mode=args.mode, palette=args.palette,
              font=args.font, scale=args.scale, number=args.number)
    print("生成:", out, "|", os.path.getsize(out), "bytes", "| 模式:", args.mode or "biz(默认)",
          "| 序号:", args.number or "保留原标题")
