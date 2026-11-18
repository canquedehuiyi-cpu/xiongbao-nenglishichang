"""
validator_presence.py —— 投标资料完整度（文件/应然项存在性核对）判定规则

判定族 T-05（N-16 / N-46）限缩口径（U-28 裁决）：对照**应然清单**逐项核对
**存在性**（在标书目录/文件列表中定位）。不做签章位置/图像版面（D-23 拆掉），
不做投标文件数字一致性（B-38 归脚本）。

本文件作为 bid_disqualification_terms 场景的第二个任务（check-completeness）
的判定引擎；与主任务 validator.py（条款+材料存在性）业务语义不同但原理同族。

核心动作（存在性核对）：
1. 应然清单：每行一个应提交项（名称 + 关键词 + 是否必备）。
2. 标书目录/文件列表：每行一个实际条目。
3. 逐项核对：应然项关键词（任一）在目录条目中命中 -> 存在（行号+原文摘录）；
   未命中 -> 缺失。必备项缺失 -> REVIEW；可缺项缺失 -> 仅提示不阻塞。

输出态：PRESENT（存在）/ MISSING（必备项缺失）/ OPTIONAL_MISSING（可缺项缺失）/
UNKNOWN（无法判定）。整体终态只分 DONE 与 REVIEW。
"""

from __future__ import annotations

import re
import unicodedata

from scenario_api import Issue, IssueLevel

# ---- 输出态（模块内独立命名空间，外部以别名导入避免与主任务符号冲突） ---------

PRESENT = "PRESENT"
MISSING = "MISSING"
OPTIONAL_MISSING = "OPTIONAL_MISSING"
UNKNOWN = "UNKNOWN"

_SCAN_HINTS = (
    "image", "png", "jpg", "jpeg", "bmp", "tif", "tiff", "scan", "扫描",
    "[图片", "[扫描", "不可解析", "ocr",
)

# ---- 字段识别 --------------------------------------------------------------

REQUIRED_FIELDS = {
    "名称": "name",
    "文件": "name",
    "项目": "name",
    "关键词": "keywords",
    "关键字": "keywords",
    "必须": "required",
    "必备": "required",
    "强制": "required",
}

# ---- 归一化 ----------------------------------------------------------------

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def _norm_lite(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "").replace("\u3000", "")


# ---- 行解析 ----------------------------------------------------------------

def _split_pairs(body: str) -> list[tuple[str, str]]:
    keys = list(re.finditer(r"[^=\s]+=", body))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(keys):
        key = m.group(0)[:-1]
        end = keys[i + 1].start() if i + 1 < len(keys) else len(body)
        val = body[m.end():end].strip()
        if key and val:
            out.append((key, val))
    return out


def _values(raw: str) -> list[str]:
    return [t for t in re.split(r"[,，、;；]", _norm(raw)) if t]


def _norm_required(raw: str | None) -> bool:
    return _norm(raw or "是") not in ("否", "可选", "非必备", "不强制")


def parse_required_line(line: str) -> dict | None:
    """解析应然清单一行：{name, keywords[], required} 或 None。"""
    if not line:
        return None
    if any(h in line.lower() for h in _SCAN_HINTS):
        return None
    body = line.split(":", 1)
    if len(body) != 2:
        return None
    fields: dict = {}
    for key, val in _split_pairs(body[1]):
        fid = REQUIRED_FIELDS.get(_norm(key))
        if fid is None:
            continue
        fields.setdefault(fid, _norm(val))
    if "name" not in fields:
        return None
    keywords = _values(fields.get("keywords", "")) or [fields["name"]]
    return {
        "name": fields["name"],
        "keywords": keywords,
        "required": _norm_required(fields.get("required", "是")),
    }


# ---- 判定 ----------------------------------------------------------------

def check_item(item: dict, toc_lines: list[str], max_hits: int = 3) -> dict:
    """单项存在性核对：应然项关键词在标书目录条目中检索。

    返回 {**item, located, hits[], status}
    """
    norm_lines = [_norm_lite(ln) for ln in toc_lines]
    kws = [_norm_lite(k) for k in item["keywords"]]
    hits = []
    for idx, nl in enumerate(norm_lines):
        if any(kw and kw in nl for kw in kws):
            hits.append({"line_no": idx + 1, "excerpt": toc_lines[idx][:120]})
            if len(hits) >= max_hits:
                break

    if hits:
        return {**item, "located": True, "hits": hits, "status": PRESENT}
    if not item["required"]:
        return {**item, "located": False, "hits": [], "status": OPTIONAL_MISSING}
    return {**item, "located": False, "hits": [], "status": MISSING}


def evaluate(toc_lines: list[str], required_list: list[dict]) -> dict:
    """全量判定，返回 {items:[…], summary, verdict}。

    整体终态只分 DONE / REVIEW：
      - 任何必备项 MISSING / UNKNOWN -> REVIEW
      - 全部存在（可缺项缺失不阻塞）-> DONE
    """
    items = [check_item(it, toc_lines) for it in required_list]
    n_present = sum(1 for i in items if i["status"] == PRESENT)
    n_missing = sum(1 for i in items if i["status"] == MISSING)
    n_optional = sum(1 for i in items if i["status"] == OPTIONAL_MISSING)
    n_unknown = sum(1 for i in items if i["status"] == UNKNOWN)
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "present": n_present,
            "missing": n_missing,
            "optional_missing": n_optional,
            "unknown": n_unknown,
        },
        "verdict": "REVIEW" if (n_missing or n_unknown) else "DONE",
    }


# ---- 对外判定（步骤层调用） ------------------------------------------------

def evaluate_issues(result: dict) -> list[Issue]:
    issues: list[Issue] = []
    summ = result["summary"]
    for it in result["items"]:
        st = it["status"]
        if st == MISSING:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"必备项「{it['name']}」未在标书目录/文件列表中定位到，"
                "转人工确认是否漏装或改名",
            ))
        elif st == UNKNOWN:
            issues.append(Issue(
                IssueLevel.REVIEW,
                f"应然项「{it['name']}」无法判定（条目无法解析/疑似扫描件），转人工",
            ))
    if summ["total"] == 0:
        issues.append(Issue(IssueLevel.ERROR, "应然清单为空或无法解析"))
    elif summ["optional_missing"] and not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"{summ['optional_missing']} 个可缺项未提供（不阻塞，按招标文件口径确认即可）",
        ))
    elif not issues:
        issues.append(Issue(
            IssueLevel.INFO,
            f"全部 {summ['present']} 个必备项均已在标书目录中定位到"
            "（仅核对存在性，不核数字一致性/签章位置）",
        ))
    return issues