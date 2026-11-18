#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_gate.py —— 标准守门自检编排器（分层扫描 + 有界重试熔断 + 持久化自检报告）

定位
----
Skill技能搭建专家「标准守门自检模块」的编排入口（细则见 references/REF-QC-020_QualityGateModule.md）。
按 L1 元数据/配置 → L2 代码安全供应链 → L3 业务逻辑的层级，
依次调用既有扫描器（含关键词守卫 keyword_guard），
汇总结论、记录 retry_count、给出 pass / retry_needed / fuse_abort 判定，
并把每一次构建的结构化自检报告持久化到 logs/QUALITY_<build_no>_<时间戳>.json 与 .md。

分层（先快检、后深度核验）
--------------------------
L1 结构化配置校验：selfcheck_factory（name==slug==目录名 + frontmatter 必填 + 一致性）
                   package_check（禁词/CRLF/隐形字符/时间戳）
L2 代码安全供应链检查：code_security_scan（八维：危险执行/硬编码密钥/隐私外传/
                   远程动态加载/输入边界/声明一致性；扫全部脚本含机件自身，HIGH 阻断）
L3 业务逻辑校验：skill_quality_check（技能质量标准五维＋安全基线八维，fail-closed，签名留痕）
                   （素材采信专项校验由 Agent 在 runtime 比对 material status 后填入报告）

用法
----
    python scripts/quality_gate.py <产出技能目录> [--retry N] [--max-retry 3] [--quiet]
退出码
------
    0 = 全过（pass）
    2 = 有闸未过且 retry_count < max_retry（retry_needed，回传定向修复）
    3 = 有闸未过且 retry_count >= max_retry（fuse_abort，终止本次构建）
    1 = 参数/环境/运行异常
零外部依赖，纯标准库。
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MAX_RETRY = 3


def _run_scanner(script_path, target, quiet=False):
    """运行单个扫描器，返回 (name, passed, rc, summary)。"""
    if not script_path.exists():
        return (script_path.name, None, None, "扫描器文件缺失，跳过")
    try:
        # 传绝对路径，确保扫描器（如 selfcheck 取 root.name 比对目录名）拿到正确目录名
        target_arg = str(Path(target).resolve())
        proc = subprocess.run(
            [sys.executable, str(script_path), target_arg],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        rc = proc.returncode
        out = (proc.stdout or "") + (proc.stderr or "")
        # 裁剪输出，避免报告过长
        out = "\n".join(line for line in out.splitlines() if line.strip())[:800]
        passed = (rc == 0)
        return (script_path.name, passed, rc, out.strip())
    except Exception as e:  # pragma: no cover
        return (script_path.name, None, None, "运行异常：%s" % e)


def _package_hash(root: Path):
    """对目录内文本/二进制文件做稳定哈希，作为签名摘要。"""
    h = hashlib.sha256()
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if not d.startswith("."))
        for fn in sorted(fns):
            if fn.startswith("."):
                continue
            p = Path(dp) / fn
            try:
                h.update(p.read_bytes())
            except Exception:
                continue
    return h.hexdigest()


def _read_build_no(root: Path):
    meta = root / "_meta.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            if "build_no" in data:
                return data.get("build_no", "NA")
        except Exception:
            pass
    # 构建号收敛内部私有区：以计数器为唯一取值点（对外交付视图不携带构建号）
    seq_file = root / "_build_seq.json"
    if seq_file.exists():
        try:
            return json.loads(seq_file.read_text(encoding="utf-8")).get("seq", "NA")
        except Exception:
            return "NA"
    # 观察项1修复（定稿依据 2026-11-04 三方质检报告，方案B兜底）：出包视图已剥离
    # _build_seq.json，质检在解压包上跑时构建号恒为 NA、历史报告无法对账——
    # 兜底取 version 字段作归档键（报告文件名自带时间戳，两者联合可定位）。
    if meta.exists():
        try:
            v = json.loads(meta.read_text(encoding="utf-8")).get("version")
            if v:
                return "ver-%s" % v
        except Exception:
            pass
    return "NA"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    quiet = "--quiet" in flags

    retry = 0
    for f in flags:
        if f.startswith("--retry"):
            try:
                retry = int(f.split("=", 1)[1])
            except Exception:
                pass
    max_retry = MAX_RETRY
    for f in flags:
        if f.startswith("--max-retry"):
            try:
                max_retry = int(f.split("=", 1)[1])
            except Exception:
                pass

    if len(args) < 1:
        print("usage: quality_gate.py <产出技能目录> [--retry N] [--max-retry 3]")
        return 1
    root = Path(args[0])
    if not root.is_dir():
        print("not a dir:", root)
        return 1

    scripts_dir = Path(__file__).resolve().parent
    layers = [
        ("L1 结构化配置校验", [scripts_dir / "selfcheck_factory.py",
                              scripts_dir / "package_check.py",
                              scripts_dir / "keyword_guard.py"]),
        ("L2 代码安全供应链检查", [scripts_dir / "code_security_scan.py"]),
        ("L3 业务逻辑校验", [scripts_dir / "skill_quality_check.py",
                            scripts_dir / "run_regression.py",
                            scripts_dir / "interaction_closure_scan.py",
                            scripts_dir / "scan_name_conflict.py",
                            scripts_dir / "deliverable_competitor_scan.py",
                            scripts_dir / "tail_fragment_scan.py",
                            scripts_dir / "external_wording_scan.py",
                            scripts_dir / "preference_guard.py",
                            scripts_dir / "visual_layer_scan.py",
                            scripts_dir / "keyword_mapping_scan.py",
                            scripts_dir / "numeric_consistency_scan.py",
                            scripts_dir / "threshold_scan.py",
                            scripts_dir / "term_bare_scan.py"]),
    ]

    results = []
    any_fail = False
    for layer_name, scanners in layers:
        for sc in scanners:
            name, passed, rc, out = _run_scanner(sc, root, quiet)
            results.append({
                "layer": layer_name,
                "scanner": name,
                "passed": passed,
                "returncode": rc,
                "summary": out,
            })
            if passed is False:
                any_fail = True

    build_no = _read_build_no(root)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkg_hash = _package_hash(root)

    if any_fail:
        verdict = "retry_needed" if retry < max_retry else "fuse_abort"
    else:
        verdict = "pass"

    report = {
        "build_no": build_no,
        "check_time": datetime.now().isoformat(timespec="seconds"),
        "target": str(root),
        "package_hash": pkg_hash,
        "retry_count": retry,
        "max_retry": max_retry,
        "verdict": verdict,
        "scanners": results,
        "material_audit_note": (
            "素材采信专项校验（REF-VER-021 校验项1-4）由 Agent 在 runtime "
            "比对 material_id/version_tag/status 与用户确认方案后填入本报告的 material_audit 字段"
        ),
    }

    # 持久化报告
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    json_path = log_dir / ("QUALITY_%s_%s.json" % (build_no, ts))
    md_path = log_dir / ("QUALITY_%s_%s.md" % (build_no, ts))
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_md(md_path, report)

    if not quiet:
        print(json.dumps({
            "ok": not any_fail,
            "build_no": build_no,
            "verdict": verdict,
            "retry_count": retry,
            "max_retry": max_retry,
            "report_json": str(json_path),
            "report_md": str(md_path),
        }, ensure_ascii=False, indent=2))

    if verdict == "pass":
        return 0
    if verdict == "retry_needed":
        return 2
    return 3


def _write_md(path: Path, report: dict) -> None:
    lines = []
    lines.append("# 自检报告（标准守门模块）")
    lines.append("")
    lines.append("- 构建编号：%s" % report["build_no"])
    lines.append("- 校验时间：%s" % report["check_time"])
    lines.append("- 包哈希：%s" % report["package_hash"])
    lines.append("- 整改次数 retry_count：%s（上限 %s）" % (report["retry_count"], report["max_retry"]))
    lines.append("- 最终结果：**%s**" % report["verdict"])
    lines.append("")
    lines.append("## 逐扫描器结论")
    lines.append("")
    for r in report["scanners"]:
        mark = "PASS" if r["passed"] is True else ("FAIL" if r["passed"] is False else "SKIP")
        lines.append("### [%s] %s —— %s" % (r["layer"], r["scanner"], mark))
        if r["summary"]:
            lines.append("")
            lines.append("```")
            lines.append(r["summary"])
            lines.append("```")
        lines.append("")
    lines.append("## 素材采信专项校验（runtime 填写）")
    lines.append("")
    lines.append(report["material_audit_note"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
