#!/usr/bin/env python3
"""common.py — 全库共享基础层（版本单一来源 / 统一输出协议 / 可选依赖增强）

1. VERSION: 全库唯一版本号（A-3：所有脚本从本模块读取，不再各自硬编码）
2. read_text: 统一文件读取（UTF-8 BOM 安全，防止 \ufeff 残留）
3. make_result: 统一结果信封（A-2：{status, checks, score, compliance, provenance}）
4. 可选依赖层（A-4）：jieba 已安装则启用词汇级分词，未安装自动降级字符级（零依赖兜底）
"""

from pathlib import Path

VERSION = "1.0.7"


def read_text(path, errors="replace"):
    """读取文本文件，UTF-8 BOM 安全（有 BOM 则自动去除，无 BOM 不影响）。"""
    return Path(path).read_text(encoding="utf-8-sig", errors=errors)


def make_result(status="ok", checks=None, score=None, compliance=None, provenance=None):
    """统一输出信封（A-2 统一输出协议）。

    status: ok / fail / skipped
    checks: [{name, pass, detail}]
    score: {name, value, threshold, pass}
    compliance: 合规提示（字符串或对象）
    provenance: 处理留痕（版本/语言/时间戳等）
    """
    return {
        "status": status,
        "checks": checks or [],
        "score": score,
        "compliance": compliance,
        "provenance": provenance,
    }


def tokenize(text, lang="zh"):
    """词汇级分词（可选依赖层）。

    - jieba 已安装且文本为中文：返回 jieba 词列表（更准确的词汇级分析）
    - 其他情况：回退字符级 2-gram（零依赖，纯标准库）
    """
    if lang == "zh" and len(text) > 0:
        try:
            import jieba  # 可选依赖，未安装时 ImportError 触发降级

            return [w for w in jieba.lcut(text) if w.strip()]
        except ImportError:
            pass
    # 字符级 2-gram 兜底（全语言通用）
    clean = re_sub_noise(text)
    return [clean[i:i + 2] for i in range(max(0, len(clean) - 1)) if clean[i:i + 2].strip()]


def re_sub_noise(text):
    """去除标点/空白噪音，返回干净文本（用于 n-gram 兜底）。"""
    import re

    return re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’（）()\[\]{}]", "", text)
