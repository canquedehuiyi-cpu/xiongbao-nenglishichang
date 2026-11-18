#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deliverable_competitor_scan.py — 交付物竞品平台名零命中扫描（fail-closed · 目标渠道×词表）

用途：
    按「目标渠道词表」对交付物文本文件扫描竞品分发平台名；
    命中即 fail-closed（exit 1），不过此闸不准分发。
    这些名字仅用于创作者后台路由与支付识别（内部配置），不得外溢到交付物，
    否则对应分发平台官方审核会卡审、无法上架。

词表：
    外置 scripts/competitor_lexicon.json（channels: default / tencent / aliyun ...）。
    default 为全量口径（客户交付物零平台名）。
    词表缺失或目标渠道不在词表内 → exit 2（fail-closed，不静默放行）。
    时效口径：各渠道审核规则一切以官方最新公告为准；维护者发现规则变化后更新词表并重扫。

用法：
    python deliverable_competitor_scan.py <目录> [--target tencent] [--include-factory] [--quiet]
    --target <渠道名>   按词表内该渠道词表扫描（缺省 default 全量）
    --include-factory   显式扫描工厂自身根目录（工厂包上架前自检用；缺省跳过防自命中）
退出码：
    0 = 零命中（可出包）
    1 = 命中（不准出包，清掉分发平台名后重扫）
    2 = 参数 / 路径 / 词表错误
"""
import json
import os
import sys

# 工厂自身根目录标记：含 _meta.json 且 references/ 下有 REF- 文件。
# 缺省只服务「客户交付物」：扫到工厂根目录直接跳过，避免自命中误判为 FAIL；
# 工厂包上架前自检用 --include-factory 显式开启。
FACTORY_MARKERS = ("_meta.json",)

TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js",
            ".sh", ".html", ".css", ".toml", ".cfg", ".ini"}

# 扫描器自身文件不参与命中统计（词表文件与本脚本天然含品牌词）。
SELF_FILES = ("deliverable_competitor_scan.py", "competitor_lexicon.json")


def _is_factory_root(root):
    if not os.path.isfile(os.path.join(root, "_meta.json")):
        return False
    ref_dir = os.path.join(root, "references")
    if os.path.isdir(ref_dir):
        for fn in os.listdir(ref_dir):
            if fn.startswith("REF-") and fn.endswith(".md"):
                return True
    return False


def load_words(lexicon_path, target):
    """按目标渠道取词表；缺失 / 渠道不存在一律 exit 2（fail-closed）。"""
    if not os.path.isfile(lexicon_path):
        print("词表缺失: %s（fail-closed，不静默放行）" % lexicon_path)
        sys.exit(2)
    try:
        data = json.load(open(lexicon_path, encoding="utf-8"))
    except Exception as e:
        print("词表解析失败: %s（%s）" % (lexicon_path, e))
        sys.exit(2)
    channels = data.get("channels", {})
    if target not in channels:
        print("词表内无该渠道: %s（可用: %s）" % (target, ", ".join(sorted(channels))))
        sys.exit(2)
    return [w for w in channels[target] if w]


def scan_file(path, words):
    hits = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                low = line.lower()
                for tok in words:
                    if tok.lower() in low:
                        hits.append((i, tok))
    except Exception:
        pass
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    quiet = "--quiet" in flags
    target = "default"
    if "--target" in flags:
        i = flags.index("--target")
        if i + 1 >= len(flags) or flags[i + 1].startswith("--"):
            print("--target 需要渠道名参数")
            sys.exit(2)
        target = flags[i + 1]
    include_factory = "--include-factory" in flags

    if len(args) < 1:
        print("usage: deliverable_competitor_scan.py <目录> [--target tencent] [--include-factory] [--quiet]")
        sys.exit(2)
    root = args[0]
    if not os.path.isdir(root):
        print("not a dir:", root)
        sys.exit(2)

    lexicon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "competitor_lexicon.json")
    words = load_words(lexicon_path, target)

    # 护栏：缺省扫到工厂自身根目录直接跳过；--include-factory 显式开启才扫。
    if _is_factory_root(root) and not include_factory:
        if not quiet:
            print("检测到工厂自身根目录；缺省跳过（工厂包上架前自检请加 --include-factory）。")
        sys.exit(0)

    self_abs = set(os.path.abspath(p) for p in
                   [os.path.join(os.path.dirname(os.path.abspath(__file__)), f) for f in SELF_FILES])

    total = 0
    report = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("logs", "__pycache__")]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            fp = os.path.join(dirpath, fn)
            if os.path.abspath(fp) in self_abs:
                continue
            hits = scan_file(fp, words)
            if hits:
                rel = os.path.relpath(fp, root)
                report.append((rel, hits))
                total += len(hits)

    if total == 0:
        if not quiet:
            print("竞品平台名零命中 PASS（目标渠道=%s，交付物可出包）" % target)
        sys.exit(0)

    if not quiet:
        print("竞品平台名命中 %d 处（目标渠道=%s）→ FAIL（不准出包，清掉后重扫）：" % (total, target))
        for rel, hits in report:
            for (ln, tok) in hits:
                print("  %s:%d  命中[%s]" % (rel, ln, tok))
    sys.exit(1)


if __name__ == "__main__":
    main()
