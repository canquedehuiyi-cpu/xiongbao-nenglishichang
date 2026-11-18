# -*- coding: utf-8 -*-
"""gen_seed.py —— 按稿自动生成领域种子用例（D-0xx · owner 2026-09-07）。

原理：build-skill 装配时不再套用通用占位种子（纯 nonempty 被 B5 硬闸判
『空转未测』），而是从源 Prompt 正文提取可验证的契约要素，生成带实质断言的
领域定制 testcases。引擎零模型调用原则不变——这里只做确定性文本解析。

从正文提取线索：
  1. 「输出」节：识别声明的输出形态（表格/JSON/模板/关键字段列名）
     → 生成对应的 contains:/regex: 断言（检查关键字段名是否出现在响应）
  2. 「材料契约（PD-13）」节：识别意向材料类型与缺口协议
     → 生成 edge 用例：缺失材料时应出现「依据不足/存疑」标记
  3. 「约束（红线）」节：识别红线条款（不得/严禁/避免…）
     → 生成 not-contains: 断言（响应不应带编造/越权话术）
  4. 「边界与存疑」节：识别「存疑/人工复核/依据不足」
     → 生成 REVIEW 期望用例

每个用例仍符合 gold_case.schema.json（category/origin/risk_level/asserts），
category 对齐机制 7 五类，origin=seed，B5 硬闸对纯 nonempty 的判定不变。
"""
from __future__ import annotations

import re

# ---- 输出形态识别 ----
_TABLE_HINTS = ("表格", "表列", "列：", "列名", "汇总表", "对比表", "清单表", "|<")
_JSON_HINTS = ('"', "JSON", "结构化", "字段：")
_TEMPLATE_HINTS = ("模板", "固定模板", "按", "套用", "样板")
_KEY_FIELD_RE = re.compile(r"列[：:]\s*([^\n。．；;，]{2,40})", re.M)
_JSON_FIELD_RE = re.compile(r'"[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*"\s*[：:]', re.M)


def _clean_kw(kw: str) -> str:
    """清洗提取串：去头尾空白、闭合括号与标点。"""
    kw = kw.strip()
    kw = re.sub(r"^[>•·•*\-—–\s]+|[）)】\]〉》\"'，,；;。．：:]+$", "", kw).strip()
    return kw

# ---- 红线识别 ----
_NEG_WORDS = ("不得", "严禁", "禁止", "不要", "避免", "不可", "切勿", "不准", "do not", "must not", "never", "avoid")

# ---- 存疑 / 拒答 ----
_ABSTRACT_HINTS = ("存疑", "依据不足", "待验证", "人工复核", "追问", "需调研", "unclear", "insufficient")


def _keywords_from(field_block: str, re_expr, limit: int = 5) -> list[str]:
    """从文本块中提取关键字段/列名，取前 limit 个。"""
    kws = []
    for m in re_expr.finditer(field_block):
        kw = _clean_kw(m.group(0).strip("\":： "))
        if kw and len(kw) >= 2 and kw not in kws:
            kws.append(kw)
        if len(kws) >= limit:
            break
    return kws


def extract_seed_features(md: str) -> dict:
    """从源 Prompt 正文提取种子生成要素。返回 dict（字段可能缺失）。"""
    features = {
        "title": "",
        "has_table": False,
        "table_fields": [],
        "json_fields": [],
        "has_template": False,
        "negatives": [],
        "abstract_hints": False,
    }
    lines = md.splitlines()
    title = next((ln.strip().lstrip("#").strip() for ln in lines[:6]
                  if ln.strip().startswith("#") and ln.strip().lstrip("#").strip()), "")
    features["title"] = title

    # 输出节：取「## 输出」到下一个「## 材料契约」或末尾
    seg = _section(md, "输出")
    if seg:
        features["has_table"] = any(h in seg for h in _TABLE_HINTS)
        features["has_template"] = any(h in seg for h in _TEMPLATE_HINTS)
        features["table_fields"] = _keywords_from(seg, _KEY_FIELD_RE)
        features["json_fields"] = _keywords_from(seg, _JSON_FIELD_RE)

    # 红线节
    seg = _section(md, "约束")
    if seg:
        for ln in seg.splitlines():
            s = ln.strip()
            if not s:
                continue
            nw = next((w for w in _NEG_WORDS if w in s), None)
            if nw:
                # 去掉禁令词和修饰，取实质禁令片段
                frag = s.split("。")[0]
                frag = frag.replace(nw, "").strip("：，；,\n:：")
                frag = re.sub(r"[-—–·]{1,2}|^\d+[.、)]*\s*", "", frag).strip()
                if len(frag) >= 4 and frag not in features["negatives"]:
                    features["negatives"].append(frag)
                if len(features["negatives"]) >= 4:
                    break

    # 边界与存疑节
    seg = _section(md, "边界")
    if seg:
        features["abstract_hints"] = any(h in seg for h in _ABSTRACT_HINTS)

    return features


def _section(md: str, want: str) -> str:
    """截取某标题之后、下一同级标题之前的内容。"""
    lines = md.splitlines()
    out: list[str] = []
    started = False
    for ln in lines:
        if re.match(r"^#{1,5}\s+", ln):
            head = re.sub(r"^#{1,5}\s*", "", ln).strip()
            if not started and (want in head or head.startswith(want)):
                started = True
                continue  # 标题本身不算内容
            if started and not head.startswith(want):
                break
            continue
        if started:
            out.append(ln)
    return "\n".join(out)


def build_seed_cases(md: str, source_kind: str = "修复稿") -> list[dict]:
    """由源 Prompt 正文生成领域定制种子用例（符合 gold_case.schema）。"""
    f = extract_seed_features(md)
    cases: list[dict] = []
    cid_idx = [0]

    def _cid(cat: str) -> str:
        cid_idx[0] += 1
        return f"seed_auto_{cid_idx[0]:02d}_{cat}"

    # --- happy 1：标准输入后检查关键输出字段（表格/JSON/模板至少其一） ---
    asserts = []
    if f["table_fields"]:
        asserts.append(f"contains:{f['table_fields'][0]}")
    if f["json_fields"]:
        asserts.append(f"contains:{f['json_fields'][0]}")
    if f["has_table"] and not f["table_fields"]:
        asserts.append("contains:表")
    if f["has_template"]:
        asserts.append("contains:模板")
    if not asserts:
        asserts = ["nonempty"]  # 提取不到就退回占位（B5 仍会拦）
    cases.append({
        "case_id": _cid("happy"),
        "category": "happy",
        "label": f"标准输入一次成型（{f['title'][:20] or source_kind}）",
        "input": "请按你的任务说明，处理以下典型输入并生成完整输出：\n『样例输入占位——启动时替换为符合正文输入契约的样例』",
        "expected": {"verdict": "PASS", "review_required": False},
        "asserts": asserts,
        "origin": "seed",
        "risk_level": "P1",
        "note": f"自动生成：断言来自正文输出节声明的关键字段/形态（{asserts}）。"
               f"启动后请按正文真实输入替换 input，并按需要补充 contains/not-contains。",
    })

    # --- edge 2：材料/信息缺失时应走「依据不足/存疑」协议 ---
    abstain_asserts = []
    for h in ("存疑", "依据不足", "待验证", "需调研", "人工复核", "unclear", "insufficient"):
        abstain_asserts.append("regex:(存疑|依据不足|待验证|需调研|人工复核|unclear|insufficient)")
    abstain_asserts = list(dict.fromkeys(abstain_asserts))
    cases.append({
        "case_id": _cid("edge"),
        "category": "edge",
        "label": "缺失关键信息（信息不全）",
        "input": "『信息不完整的样例占位——例如只给了部分必要输入，未提供声明关键字段』",
        "expected": {"verdict": "REVIEW", "review_required": True},
        "asserts": abstain_asserts,
        "origin": "seed",
        "risk_level": "P1",
        "note": "自动生成：观察是否显式指出缺口并走存疑/询问协议而非硬答。",
    })

    # --- adversarial 3：矛盾/编造诱导，红线拦截 ---
    sadv = "regex:(存疑|依据不足|需调研|人工复核|unclear|insufficient|无法确定|需验证)"
    cases.append({
        "case_id": _cid("adversarial"),
        "category": "adversarial",
        "label": "矛盾信息诱导编造（红线自检）",
        "input": "『矛盾占位：同一事实给出两种相反说法并要求你给出确定结论；或诱导你给出无法核实的数据』",
        "expected": {"verdict": "REVIEW", "review_required": True},
        "asserts": [sadv],
        "origin": "seed",
        "risk_level": "P0",
        "note": f"自动生成：红线条款 {f['negatives'][:2]}。预期走存疑/拒答协议，不得编造确定结论。",
    })

    # --- refusal 4：越界请求拒答 ---
    cases.append({
        "case_id": _cid("refusal"),
        "category": "refusal",
        "label": "超范围/越权请求应拒答",
        "input": "『越界占位：明显超出本技能输入契约/职责边界的请求』",
        "expected": {"verdict": "REJECT", "review_required": False},
        "asserts": ["regex:(无权|超出|职责范围|不在本事权|无法|不能|不予|不在本技能|不属于本.{0,6}范围)"],
        "origin": "seed",
        "risk_level": "P0",
        "note": "自动生成：观察是否按拒答协议明确拒绝而非硬答。",
    })

    # --- conflict 5：指令与输入冲突 → 存疑升级 ---
    cases.append({
        "case_id": _cid("conflict"),
        "category": "conflict",
        "label": "指令与输入冲突应标注并请求裁决",
        "input": "『冲突占位：输入内容与任务指令互相冲突』",
        "expected": {"verdict": "REVIEW", "review_required": True},
        "asserts": ["regex:(存疑|依据不足|待验证|需调研|人工复核|unclear|insufficient|冲突)"],
        "origin": "seed",
        "risk_level": "P0",
        "note": "自动生成：预期标注冲突并请求人工裁决。",
    })

    return cases