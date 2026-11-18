#!/usr/bin/env python3
"""schema_check.py — 反AI黑名单数据 Schema 校验（A-1）

校验 antiai_blacklist.json 的结构与数据质量：
    1. 顶层字段齐全（version/last_updated/rules/evolution_log/engine_rules/category_aliases
       + 1.0.7 规则分区 entity_rules/behavior_features/semantic_features）
    2. 规则必填字段齐全（id/category/pattern/language/source/confidence/usage_count）
    3. ID 全局唯一
    4. pattern 为正则且编译通过（英文忽略大小写）
    5. 无完全重复的 (language, pattern)
    6. engine_rules 分区关键字段存在
    7. 1.0.7 规则分区（entity_rules/behavior_features/semantic_features）字段齐全
    8. 输出覆盖对（同一语言内被其他 pattern 子串/正则覆盖的规则，供人工判断，不视为错误）

用法:
    python3 schema_check.py            # 校验唯一数据源
    python3 schema_check.py <json路径>  # 校验指定文件
退出码: 0=通过  1=发现问题
"""

import json
import re
import sys
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "references" / "antiai_blacklist.json"

REQUIRED_TOP = {"version", "last_updated", "rules", "evolution_log", "engine_rules", "category_aliases",
                "entity_rules", "behavior_features", "semantic_features"}
REQUIRED_RULE = {"id", "category", "pattern", "language", "source", "confidence", "usage_count"}
REQUIRED_ENGINE = {"connector_drop", "cliche_open", "emotion_to_action", "hard_residue_keep", "context_words"}
REQUIRED_SECTIONS = {
    "entity_rules": {"state_death", "state_coma", "state_gone", "state_arrive", "state_hold",
                     "time_words", "time_marks", "foreshadow_hit", "payoff_hit"},
    "behavior_features": {"dialogue_action_words", "event_words", "sense_words",
                          "event_density_threshold", "sense_density_threshold", "min_text_len"},
    "semantic_features": {"overlap_ngram", "overlap_min_count", "same_sentence_len_delta", "overlap_ratio_high"},
}
SUPPORTED_LANGS = {"zh", "en", "ja", "ko"}


def compile_pattern(pattern, lang):
    return re.compile(pattern, re.IGNORECASE if lang == "en" else 0)


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = Path(argv[0]) if argv else DEFAULT_FILE
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        return 1

    errors = []
    warnings = []

    # 1. 顶层字段
    for k in REQUIRED_TOP:
        if k not in data:
            errors.append(f"缺少顶层字段: {k}")

    rules = data.get("rules", [])
    if not isinstance(rules, list):
        errors.append("rules 必须为列表")
        rules = []

    # 2/3. 必填字段 + ID 唯一
    seen_ids = {}
    for r in rules:
        if not isinstance(r, dict):
            errors.append("rules 中存在非对象条目")
            continue
        missing = REQUIRED_RULE - set(r.keys())
        if missing:
            errors.append(f"规则 {r.get('id', '?')} 缺少字段: {sorted(missing)}")
        rid = r.get("id")
        if rid:
            if rid in seen_ids:
                errors.append(f"重复 ID: {rid}")
            seen_ids[rid] = True
        if r.get("language") not in SUPPORTED_LANGS:
            errors.append(f"规则 {rid} 语言不支持: {r.get('language')}")

    # 4. pattern 正则合法性
    for r in rules:
        try:
            compile_pattern(r.get("pattern", ""), r.get("language", "zh"))
        except re.error as e:
            errors.append(f"规则 {r.get('id')} 非法正则: {e}")

    # 5. 无完全重复 (language, pattern)
    seen_pat = {}
    for r in rules:
        key = (r.get("language"), r.get("pattern"))
        if key in seen_pat:
            errors.append(f"完全重复规则: {seen_pat[key]} 与 {r.get('id')} 相同 (lang={key[0]})")
        seen_pat[key] = r.get("id")

    # 6. engine_rules 关键字段
    er = data.get("engine_rules")
    if isinstance(er, dict):
        for k in REQUIRED_ENGINE:
            if k not in er:
                errors.append(f"engine_rules 缺少字段: {k}")
    elif "engine_rules" in data:
        errors.append("engine_rules 必须为对象")

    # 7. 1.0.7 规则分区字段齐全
    for section, fields in REQUIRED_SECTIONS.items():
        sec = data.get(section)
        if not isinstance(sec, dict):
            if section in data:
                errors.append(f"{section} 必须为对象")
            continue
        for k in fields:
            if k not in sec:
                errors.append(f"{section} 缺少字段: {k}")

    # 8. 覆盖对（提示性，不视为错误）
    for i, a in enumerate(rules):
        for j, b in enumerate(rules):
            if i >= j or a.get("language") != b.get("language"):
                continue
            pa, pb = a.get("pattern", ""), b.get("pattern", "")
            if not pa or pa == pb:
                continue
            try:
                if pa in pb or compile_pattern(pb, a.get("language", "zh")).search(pa):
                    warnings.append(f"{a.get('id')} 被 {b.get('id')} 覆盖（{a.get('category')} ⊂ {b.get('category')}）")
            except re.error:
                pass

    print(f"📋 Schema 校验: {path}")
    print(f"   版本: {data.get('version')} | 规则数: {len(rules)} | 顶层字段: {len(data)}")
    print()
    if errors:
        print(f"  ❌ 发现 {len(errors)} 个问题:")
        for e in errors:
            print(f"     - {e}")
        print(f"\n  结果: 未通过")
        return 1
    print("  ✅ 必填字段/ID唯一/正则合法/无完全重复 全部通过")
    if warnings:
        print(f"  ⚠️ 覆盖对 {len(warnings)} 条（跨类别关键词归属，属正常结构，供人工参考）:")
        for w in warnings[:10]:
            print(f"     - {w}")
        if len(warnings) > 10:
            print(f"     ... 及其他 {len(warnings) - 10} 条")
    print("\n  结果: 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
