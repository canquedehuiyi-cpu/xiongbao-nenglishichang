#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vuln_report_parse.py — 解析漏洞扫描结果 Word(.docx) 报告，提取结构化漏洞清单并排序

仅依赖 Python 标准库（.docx 本质是 zip + XML）。适用 ops-expert skill
(references/vuln-remediation.md)：把漏扫 Word 报告转为"严重度统计 + CVE 清单 + 资产清单
+ 按严重度排序的候选漏洞条目"，供模型/人工研判后制定修复方案。

用法:
  python3 vuln_report_parse.py --in 漏扫报告.docx
  python3 vuln_report_parse.py --in 漏扫报告.docx --out findings.md
  python3 vuln_report_parse.py --in 漏扫报告.docx --raw raw.txt

输出:
  - 控制台 与 (可选) findings.md：报告元信息、严重度统计、资产清单、CVE 清单、
    按严重度排序的候选漏洞条目（含原文片段）。
  - 可选 --raw：导出报告全文纯文本，供模型/人工二次研判。

注意: 本脚本是基于关键词 + 正则的初步抽取，可能漏报/误报，必须结合全文与原始报告人工核对。
"""
import argparse
import datetime
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def w(tag):
    return "{%s}%s" % (W, tag)


# ---------------------------------------------------------------------------
# 1. docx 文本抽取（标准库实现）
# ---------------------------------------------------------------------------
def extract_blocks(path):
    """返回 [(text, kind)]，kind ∈ 'paragraph' | 'cell'。保留表格单元格行。"""
    if not zipfile.is_zipfile(path):
        raise ValueError("不是有效的 .docx（zip）文件，请确认后缀与文件完整性")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "word/document.xml" not in names:
            raise ValueError("缺少 word/document.xml，可能并非 Word 文档")
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(w("body"))
    if body is None:
        return []
    blocks = []
    for child in body:
        if child.tag == w("tbl"):
            for row in child.iter(w("tr")):
                cells = []
                for tc in row.findall(w("tc")):
                    cells.append(_text_of(tc).strip())
                line = " | ".join(c for c in cells if c)
                if line:
                    blocks.append((line, "cell"))
        elif child.tag == w("p"):
            txt = _text_of(child).strip()
            if txt:
                blocks.append((txt, "paragraph"))
    return blocks


def _text_of(el):
    return "".join(t.text or "" for t in el.iter(w("t")))


# ---------------------------------------------------------------------------
# 2. 启发式抽取
# ---------------------------------------------------------------------------
CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
CVSS_RE = re.compile(r"CVSS\s*[:：]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PORT_RE = re.compile(r"(?:端口|port)\s*[:：]?\s*(\d{1,5})", re.IGNORECASE)

# 严重度关键词 -> 等级（数值越大越紧急）；用负向 lookahead 避免误匹配"严重度/中危度/低危度"
SEVERITY_PATTERNS = [
    (re.compile(r"严重(?!度)|危急|critical|fatal", re.IGNORECASE), 4, "严重"),
    (re.compile(r"高危(?!度)|高风险|high", re.IGNORECASE), 3, "高危"),
    (re.compile(r"中危(?!度)|中风险|medium|moderate", re.IGNORECASE), 2, "中危"),
    (re.compile(r"低危(?!度)|低风险|low|informational", re.IGNORECASE), 1, "低危"),
]

# 表格表头常见标记：命中且非真实漏洞行时跳过，降低噪声
HEADER_MARKERS = ["漏洞名称", "资产IP", "资产 ip", "风险等级", "扫描时间", "序号", "编号"]

# 漏洞名称信号：命中即视为"候选漏洞行"
VULN_SIGNALS = [
    "SQL 注入", "SQL注入", "XSS", "跨站脚本", "CSRF", "SSRF", "命令注入",
    "代码注入", "文件上传", "任意文件", "目录遍历", "路径遍历", "信息泄露",
    "反序列化", "XXE", "XML 外部实体", "弱口令", "弱密码", "空口令", "默认口令",
    "未授权访问", "越权", "提权", "权限提升", "缓冲区溢出", "拒绝服务", "DoS",
    "远程代码执行", "RCE", "勒索", "钓鱼", "中间人", "MITM", "不安全", "明文",
    "OpenSSL", "OpenSSH", "glibc", "Ghost", "Heartbleed", "Log4j", "Log4Shell",
    "Shellshock", "Nginx", "Apache", "Tomcat", "Redis", "MySQL", "漏洞",
]


def detect_severity(text):
    best = (0, "")
    for pat, rank, label in SEVERITY_PATTERNS:
        if pat.search(text):
            if rank > best[0]:
                best = (rank, label)
    return best  # (rank, label)


def is_header_row(text):
    low = text.lower()
    return any(m.lower() in low for m in HEADER_MARKERS) and not CVE_RE.search(text)


def is_vuln_line(text):
    if is_header_row(text):
        return False
    if CVE_RE.search(text):
        return True
    low = text.lower()
    return any(s.lower() in low for s in VULN_SIGNALS)


def extract(blocks):
    cves = set()
    ips = set()
    ports = set()
    cvss_scores = []
    severity_counter = Counter()
    candidates = []  # (line_no, rank, label, cve, text)

    for i, (text, _kind) in enumerate(blocks, start=1):
        for m in CVE_RE.finditer(text):
            cves.add(m.group(0).upper())
        for m in IP_RE.finditer(text):
            ip = m.group(0)
            # 过滤明显非 IP（如 999.999）
            if all(0 <= int(p) <= 255 for p in ip.split(".")):
                ips.add(ip)
        for m in PORT_RE.finditer(text):
            ports.add(m.group(1))
        for m in CVSS_RE.finditer(text):
            try:
                cvss_scores.append(float(m.group(1)))
            except ValueError:
                pass
        if is_vuln_line(text):
            rank, label = detect_severity(text)
            cv = CVE_RE.search(text)
            candidates.append((i, rank, label or "未分级", cv.group(0).upper() if cv else "", text))

    # 严重度分布（统计全文关键词出现，不局限于候选行）
    for text, _ in blocks:
        _r, label = detect_severity(text)
        if label:
            severity_counter[label] += 1

    # 排序：严重度降序 -> CVE 优先 -> 行号
    rank_order = {"严重": 4, "高危": 3, "中危": 2, "低危": 1, "未分级": 0}
    candidates.sort(key=lambda c: (-rank_order.get(c[2], 0), 0 if c[3] else 1, c[0]))

    return {
        "cves": sorted(cves),
        "ips": sorted(ips),
        "ports": sorted(ports, key=lambda x: int(x)),
        "cvss": cvss_scores,
        "severity": severity_counter,
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# 3. 渲染
# ---------------------------------------------------------------------------
def render(path, data, full_text):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# 漏洞报告解析结果\n")
    lines.append("- 来源文件：`%s`" % path)
    lines.append("- 解析时间：%s" % now)
    lines.append("")

    lines.append("## 一、概览统计")
    lines.append("- 候选漏洞条目（命中关键词行）：**%d**" % len(data["candidates"]))
    lines.append("- 识别 CVE 编号：**%d** 个" % len(data["cves"]))
    sev = data["severity"]
    lines.append("- 严重度关键词分布：严重 %d / 高危 %d / 中危 %d / 低危 %d"
                 % (sev.get("严重", 0), sev.get("高危", 0),
                    sev.get("中危", 0), sev.get("低危", 0)))
    if data["cvss"]:
        lines.append("- 抽取到的 CVSS 分值：%s" % ", ".join(str(s) for s in data["cvss"][:20]))
    if data["ports"]:
        lines.append("- 涉及端口（候选）：%s" % ", ".join(data["ports"][:30]))
    lines.append("")

    lines.append("## 二、资产清单（IP / 主机）")
    if data["ips"]:
        for ip in data["ips"]:
            lines.append("- %s" % ip)
    else:
        lines.append("- （未识别到 IP，请结合全文核对资产列）")
    lines.append("")

    lines.append("## 三、CVE 清单")
    if data["cves"]:
        for c in data["cves"]:
            lines.append("- %s" % c)
    else:
        lines.append("- （未识别到 CVE 编号）")
    lines.append("")

    lines.append("## 四、漏洞条目（按严重度排序，待模型/人工研判）")
    if data["candidates"]:
        lines.append("| # | 严重度 | CVE | 原文片段 |")
        lines.append("|---|--------|-----|----------|")
        for idx, (lno, _r, label, cve, text) in enumerate(data["candidates"], start=1):
            snippet = text if len(text) <= 120 else text[:117] + "..."
            snippet = snippet.replace("|", "/").replace("\n", " ")
            lines.append("| %d | %s | %s | %s |" % (idx, label, cve or "-", snippet))
    else:
        lines.append("- （未命中关键词，请使用 --raw 导出全文人工研判）")
    lines.append("")

    lines.append("> 注意：本清单为脚本基于关键词+正则的初步抽取，可能漏报/误报。"
                 "请结合 --raw 全文与原始报告人工核对，再进入修复方案制定"
                 "（见 references/vuln-remediation.md）。")
    lines.append("")

    lines.append("## 五、下一步")
    lines.append("按 references/vuln-remediation.md 流程，对上表逐条给出："
                 "影响面 → 修复动作 → 回滚路径 → 验证方式 → 业务窗口，"
                 "并复用生产安全闸门（方案+回滚+授权）。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="解析漏洞扫描 Word(.docx) 报告，提取结构化漏洞清单")
    ap.add_argument("--in", dest="inp", required=True, help="漏扫报告 .docx 路径")
    ap.add_argument("--out", default="", help="结构化清单输出 .md（可选）")
    ap.add_argument("--raw", default="", help="报告全文纯文本导出路径（可选）")
    args = ap.parse_args()

    if not os.path.exists(args.inp):
        print("错误：文件不存在 -> %s" % args.inp, file=sys.stderr)
        sys.exit(2)

    try:
        blocks = extract_blocks(args.inp)
    except ValueError as e:
        print("错误：%s" % e, file=sys.stderr)
        sys.exit(2)

    if not blocks:
        print("警告：未从文档中提取到任何文本，请确认文件内容或格式。", file=sys.stderr)

    data = extract(blocks)
    full_text = "\n".join(t for t, _ in blocks)
    md = render(args.inp, data, full_text)

    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print("\n[已写出结构化清单] %s" % args.out, file=sys.stderr)
    if args.raw:
        with open(args.raw, "w", encoding="utf-8") as f:
            f.write(full_text + "\n")
        print("[已导出报告全文] %s" % args.raw, file=sys.stderr)


if __name__ == "__main__":
    main()
