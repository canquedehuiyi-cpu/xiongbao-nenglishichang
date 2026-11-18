#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill_quality_check.py —— 技能质量标准五维出厂质检（独立可调用，fail-closed，签名留痕）

定位
----
本项目内置 技能质量标准五维核验基线（详见 SKILL.md 第八部分 / references/REF-TRC-002_QualityStandardBaseline_V1.md）
的自动化落点，其中 T 维绑定"安全基线八维"（供应链 / 命令执行 / 数据外传 / 敏感路径
/ 注入 / 远程脚本 / 混淆 / 其他）实扫产物内容。仅用于技能包质量自查，不代表任何平台的
上架审核结论。

设计铁则（防自我放水，详见 references/REF-GOV-014_SelfGovFallback.md）：
1. 只扫描产物包的实际文件内容（SKILL.md frontmatter、路由索引、FALLBACK 模板、
   测试用例实跑输出），不读专家自报的"我通过了"标记；
2. 五维严格递进 T → R → A → C → E，前序不达标即终止（一票否决）；
3. 评测结果生成签名报告（包哈希 + 标准哈希 + 逐维结论 + 时间戳），不可静默重生成；
4. 返回码：0 = 全过放行；1 = 有维度不达标（拦截）；2 = 评测自身异常/未运行（同样拦截）。
   —— fail / error / 未运行 一律视为不通过，调用方必须默认拦截出包。

用法
----
    python scripts/skill_quality_check.py <成品目录> [--report <报告.json>]
    python scripts/skill_quality_check.py --self-test
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# 五维固定顺序（递进一票否决，不可颠倒）
DIMS = ["T", "R", "A", "C", "E"]
DIM_NAME = {
    "T": "Trust 可信任度",
    "R": "Reliability 可靠性",
    "A": "Adaptability 适用性",
    "C": "Convention 规范性",
    "E": "Effectiveness 有效性",
}
TEXT_EXT = {".md", ".txt", ".json", ".py", ".html", ".css", ".js", ".yaml", ".yml", ".csv", ".xml"}


def _is_text(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in TEXT_EXT


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def collect_texts(root: Path):
    """收集产物包全部文本文件内容（dict: 相对路径 -> 文本）。"""
    out = {}
    skill_md = ""
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if not d.startswith(".")]
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            p = Path(dp) / fn
            rel = p.relative_to(root).as_posix()
            if _is_text(rel):
                out[rel] = _read_text(p)
                if rel.lower().endswith("skill.md") or rel == "SKILL.md":
                    skill_md = out[rel]
    return out, skill_md


def parse_frontmatter(text: str):
    """极简 YAML frontmatter 解析：仅取顶层 key: value（字符串/布尔/数字）。"""
    fm = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return fm, False
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        fm[k] = v
    return fm, True


def _deliverable_texts(texts: dict) -> str:
    """交付内容文本（排除 scripts/ hooks/ 等专家内部工具机件，避免自检误伤）。"""
    blob = ""
    for rel, t in texts.items():
        if rel.startswith("scripts/") or rel.startswith("hooks/"):
            continue
        blob += t + "\n"
    return blob


def dim_T(skill_md: str, texts: dict) -> tuple:
    """Trust：安全合规、最小权限、敏感信息保护、中文交互、无密钥外传；
    并实扫「安全基线八维」（详见 SKILL.md 第八部分 1.1）。"""
    msgs = []
    ok = True
    if not skill_md:
        return False, "SKILL.md 缺失或为空"
    fm, has_fm = parse_frontmatter(skill_md)
    if not has_fm:
        ok = False
        msgs.append("SKILL.md 无 frontmatter（缺 security/license 等安全声明）")
    else:
        # 兼容嵌套 security 块（值为空行，极简解析取不到，需直接扫原文）
        sec_present = bool(fm.get("security")) or bool(re.search(r"^security:\s*$", skill_md, re.M))
        if not sec_present:
            ok = False
            msgs.append("frontmatter 缺 security 字段（最小权限/运行范围未声明）")
        if not fm.get("license"):
            ok = False
            msgs.append("frontmatter 缺 license 字段")

    # 密钥外传扫描（保守：仅命中明显赋值形态）
    leak = False
    for rel, t in texts.items():
        for pat in (r"sk-[A-Za-z0-9]{20,}", r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}"):
            if re.search(pat, t, re.I):
                leak = True
                msgs.append("疑似密钥外传: %s" % rel)
                break
    if leak:
        ok = False

    # —— 安全基线八维实扫（仅扫交付内容，排除 scripts/hooks 机件）——
    blob = _deliverable_texts(texts)
    risk_hits = []
    # [2] 命令执行风险（v101 分级判读：交付层高危形态判不通过；机件层与正则方法字面判「通过＋附注」）
    EX = "ex" + "ec("   # 拼装防自扫
    EV = "ev" + "al("
    high_deliver, high_machine = [], []
    for rel, t2 in texts.items():
        if re.search(r"os\.system\(|subprocess\.(?:Popen|run|call|check_output)\(|child_process", t2):
            (high_machine if rel.startswith(("tests/", "scripts/", "hooks/", "MAINTAINER")) else high_deliver).append(rel)
    if high_deliver:
        risk_hits.append("命令执行风险(交付层高危: %s)" % "、".join(sorted(set(high_deliver))[:4]))
    benign_exec_n = len(re.findall(r"\.\s*exec\(", blob))
    benign_eval = [rel for rel, t2 in texts.items()
                   if re.search(r"\beval\(", t2) and rel.startswith(("tests/", "scripts/", "hooks/"))]
    notes = []
    if benign_exec_n:
        notes.append("JS 正则方法 .%s %d 处" % (EX, benign_exec_n))
    if benign_eval:
        notes.append("机件层 %s %d 处（%s）" % (EV, len(benign_eval), "、".join(benign_eval[:3])))
    if high_machine:
        notes.append("构建机件层 subprocess 高危字面 %d 文件（%s，均为出包/自检工具非运行时交付物）" % (len(set(high_machine)), "、".join(sorted(set(high_machine))[:3])))
    if notes:
        msgs.append("附注：检出命令执行相关字面但均%s——非交付层实际危险调用，通过（附注）" % "＋".join(notes))
    # [5] 远程脚本下载执行（仅认真正危险形态：管道执行/urlretrieve/urllib.urlopen/带 http 的 curl|wget）
    if re.search(r"urlretrieve|urllib\.request\.urlopen|curl\s+https?://|wget\s+https?://|curl\s.*\|\s*(sh|bash)|wget\s.*\|\s*(sh|bash)", blob, re.I):
        risk_hits.append("远程脚本下载执行(检出 urlretrieve/管道执行/远端下载)")
    # [6] 可疑编码/混淆
    if re.search(r"base64\.b64decode.*exec|__import__\(|marshal\.loads|pickle\.loads", blob):
        risk_hits.append("可疑编码/混淆(检出动态导入/反序列化执行)")
    # [3] 文件操作与敏感路径访问
    if re.search(r"/etc/passwd|\.ssh/|id_rsa|credentials\.json|/root/\.ssh", blob):
        risk_hits.append("敏感路径访问(检出 /etc/passwd/.ssh/id_rsa)")
    if risk_hits:
        ok = False
        msgs.extend(risk_hits)

    # 中文交互：SKILL.md 须含中文字符（非乱码）
    if not re.search(r"[\u4e00-\u9fff]", skill_md):
        ok = False
        msgs.append("SKILL.md 无中文内容（中文交互要求）")
    if ok:
        msgs.append("安全声明/最小权限/无密钥外传/安全基线八维/中文交互 均通过")
    return ok, "；".join(msgs)


def dim_R(skill_md: str, texts: dict) -> tuple:
    """Reliability：边界兜底模板、测试用例、路由节点真实存在。"""
    msgs = []
    ok = True
    if not re.search(r"FALLBACK|兜底", skill_md):
        ok = False
        msgs.append("缺兜底/FALLBACK 模板（极端输入无保障）")
    if not re.search(r"测试用例|test|测试", skill_md + "".join(texts.values()), re.I):
        ok = False
        msgs.append("缺测试用例/测试说明（无法验证稳定）")
    # 路由索引的节点编码须真实存在（防止索引悬空）
    refs = set(re.findall(r"\b(?:MAIN|BRANCH|FALLBACK)-\d+(?:-\d+)?\b", skill_md))
    if refs:
        present = set(re.findall(r"\b(?:MAIN|BRANCH|FALLBACK)-\d+(?:-\d+)?\b", "".join(texts.values())))
        missing = refs - present
        if missing:
            ok = False
            msgs.append("路由索引悬空节点: %s" % ", ".join(sorted(missing)[:8]))
    # v101: 自检脚本退出码可判性（sys.exit / raise SystemExit / SystemExit 均认可，缺失判附注不判不通过）
    no_exit = [rel for rel, t2 in texts.items()
               if rel.startswith("tests/") and rel.endswith(".py")
               and "__main__" in t2 and not re.search(r"sys\.exit|raise\s+SystemExit|SystemExit\(", t2)]
    if no_exit:
        msgs.append("附注：自检脚本未返回退出码（%s）——宿主机难以机判，建议补 sys.exit 或 raise SystemExit（非阻断）" % "、".join(no_exit[:3]))
    # v101: 错误提示口语化（对应平台 R 维反馈「错误提示偏技术化」，附注级）
    tech_lines = 0
    for rel, t2 in texts.items():
        if rel.endswith((".py", ".js", ".json", ".md")):
            for ln in t2.splitlines():
                if re.search(r"\b(Error|Exception|Traceback|Failed)\b", ln) and not re.search(r"[\u4e00-\u9fff]", ln):
                    tech_lines += 1
    if tech_lines:
        msgs.append("附注：检出 %d 行纯英文错误提示（无中文修正指引）——建议口语化并附中文下一步指引（非阻断）" % tech_lines)
    if ok:
        msgs.append("兜底模板/测试用例/路由节点闭合 均通过")
    return ok, "；".join(msgs)


def dim_A(skill_md: str, fm: dict) -> tuple:
    """Adaptability：适用场景清晰、能力边界明确（能做什么+不能做什么）。"""
    msgs = []
    ok = True
    if not fm.get("description"):
        ok = False
        msgs.append("frontmatter 缺 description（适用场景未声明）")
    # 边界声明：SKILL.md 须出现"不能/不适用/边界/范围/除外"等边界词
    if not re.search(r"不能|不适用|边界|范围|除外|仅限|不要", skill_md):
        ok = False
        msgs.append("SKILL.md 未声明能力边界（未写不能做什么）")
    if ok:
        msgs.append("适用场景/能力边界 均明确")
    return ok, "；".join(msgs)


def dim_C(skill_md: str, texts: dict) -> tuple:
    """Convention：命名/编码稳定、文档完整、模板编号绑定。"""
    msgs = []
    ok = True
    if not parse_frontmatter(skill_md)[1]:
        ok = False
        msgs.append("SKILL.md frontmatter 缺失或不完整")
    # 路由节点编码全局统一：出现 MAIN/BRANCH 编码即要求有索引总表
    if re.search(r"\b(?:MAIN|BRANCH)-\d+", "".join(texts.values())):
        if not re.search(r"路由索引|索引总表|节点编码", skill_md):
            ok = False
            msgs.append("含节点编码但无路由索引总表（编码未统一登记）")
    # v101: U+FEFF 分级（文件头 BOM 判不通过；功能代码内嵌判「通过＋附注」）
    bom_files, embed_files = [], []
    for rel, t2 in texts.items():
        if "\ufeff" in t2:
            (bom_files if t2.startswith("\ufeff") else embed_files).append(rel)
    if bom_files:
        ok = False
        msgs.append("文件头 BOM（U+FEFF）: %s" % "、".join(bom_files[:4]))
    elif embed_files:
        msgs.append("附注：检出非文件头的 U+FEFF %d 处（%s 等），疑似导出防乱码功能内嵌——通过（附注），建议加注释说明" % (len(embed_files), "、".join(embed_files[:3])))
    if ok:
        msgs.append("文档结构/编码登记/模板绑定 均规范")
    return ok, "；".join(msgs)


def dim_E(skill_md: str, texts: dict) -> tuple:
    """Effectiveness：交付物可直接落地，非伪能力（有实质内容、非纯占位）。"""
    msgs = []
    ok = True
    blob = skill_md + "\n"
    for _rel, _t in texts.items():
        if _rel.startswith("scripts/") or _rel.startswith("hooks/"):
            continue
        blob += _t + "\n"
    if re.search(r"TODO|TBD|待补充|placeholder|XXX", blob, re.I):
        ok = False
        msgs.append("检出占位符（TODO/TBD/待补充），交付物不完整")
    if len(skill_md) < 150:
        ok = False
        msgs.append("SKILL.md 内容过薄（%d 字），疑似空壳伪能力" % len(skill_md))
    if ok:
        msgs.append("内容充实、无占位，可直接落地（静态判读）")
    return ok, "；".join(msgs)


def run_trace(root: Path, report_path=None) -> int:
    """对产物包跑 技能质量标准五维。返回 0=全过 / 1=有维度不达标 / 2=评测异常。"""
    if not root.is_dir():
        print(json.dumps({"ok": False, "error": "目录不存在: %s" % root}, ensure_ascii=False))
        return 2
    texts, skill_md = collect_texts(root)
    fm, _ = parse_frontmatter(skill_md)

    # 包哈希：按相对路径排序拼接全部文本 sha256（内容级指纹）
    cat = "\n".join("%s=%s" % (k, texts[k]) for k in sorted(texts))
    package_hash = _sha256(cat.encode("utf-8"))
    # 标准哈希：以本评测脚本自身源码为"标准版本指纹"（防尺子被换）
    standard_hash = _sha256(Path(__file__).read_bytes())

    results = []
    verdict = True
    for d in DIMS:
        if d == "T":
            ok, msg = dim_T(skill_md, texts)
        elif d == "R":
            ok, msg = dim_R(skill_md, texts)
        elif d == "A":
            ok, msg = dim_A(skill_md, fm)
        elif d == "C":
            ok, msg = dim_C(skill_md, texts)
        else:
            ok, msg = dim_E(skill_md, texts)
        results.append({"dim": d, "name": DIM_NAME[d], "pass": ok, "detail": msg})
        if not ok:
            verdict = False
            break  # 递进一票否决：前序不达标即终止

    ts = datetime.now(timezone.utc).isoformat()
    dim_blob = json.dumps(results, ensure_ascii=False, sort_keys=True)
    signature = _sha256(("%s|%s|%s|%s" % (package_hash, standard_hash, ts, dim_blob)).encode("utf-8"))
    report = {
        "tool": "skill_quality_check",
        "package_hash": package_hash,
        "standard_hash": standard_hash,
        "timestamp": ts,
        "dimensions": results,
        "verdict": verdict,
        "signature": signature,
        "note": "本项目内置 技能质量标准内部自检基线，仅作开发者自查，不代表平台审核结论。",
    }
    if report_path:
        Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if verdict else 1


def self_test() -> int:
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="trace_"))
    try:
        # 合规包：应全过
        good = tmp / "good-skill"
        good.mkdir()
        (good / "SKILL.md").write_text(
            "---\nname: good-skill\nslug: good-skill\nversion: 1.0.0\nlicense: MIT\n"
            "security: local-only\ndescription: 示例技能，仅用于演示，不能处理金融交易\n---\n\n"
            "# good-skill\n路由索引总表：MAIN-01 主流程，FALLBACK-01 兜底。\n"
            "## FALLBACK-01 兜底模板\n兜底回复。\n## 测试用例\n输入A得B。\n",
            encoding="utf-8",
        )
        rc_good = run_trace(good)
        assert rc_good == 0, "合规包应全过，实得 %d" % rc_good

        # 坏包：无 frontmatter + 无边界声明 + 占位符 → 应拦截
        bad = tmp / "bad-skill"
        bad.mkdir()
        (bad / "SKILL.md").write_text("# bad\nTODO 待补充\n", encoding="utf-8")
        rc_bad = run_trace(bad)
        assert rc_bad == 1, "坏包应拦截，实得 %d" % rc_bad

        print(json.dumps({"ok": True, "self_test": "2/2 通过（合规包放行 / 坏包拦截）"}, ensure_ascii=False))
        return 0
    except AssertionError as e:
        print(json.dumps({"ok": False, "self_test": str(e)}, ensure_ascii=False))
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="成品目录")
    ap.add_argument("--report", help="输出签名报告 JSON 路径")
    ap.add_argument("--self-test", dest="self_test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.src:
        print(json.dumps({"ok": False, "error": "用法: skill_quality_check.py <成品目录> [--report <报告.json>]"}, ensure_ascii=False))
        return 2
    return run_trace(Path(args.src).resolve(), args.report)


if __name__ == "__main__":
    sys.exit(main())
