#!/usr/bin/env python3
"""sentiment_analyzer.py — 评价情感分析 (v1.0.7)

说明:
  - 关键词规则匹配,非AI语义分析(输出中明示)
  - 中文容差匹配: 评论口语常在词中插入虚词("用了一次就坏"/"质量真不好"),
    词条相邻字之间允许插入0-2个虚词以召回这类表达
  - 区间去重: 同一段文字被多个词条命中时合并计一处,代表词取最长
  - 否定短语优先识别并从文本剔除,不被正面词覆盖
  - 支持单条/文件/批量与 --json 输出

用法:
    python3 sentiment_analyzer.py --text "这个产品很好用" --lang zh
    python3 sentiment_analyzer.py --text "great quality" --lang en --json
    python3 sentiment_analyzer.py --file reviews.txt --lang en --output report.json
    python3 sentiment_analyzer.py --batch products/ --lang zh

参数:
    --text    单条评价文本
    --file    评价文件路径(每行一条)
    --batch   批量分析目录
    --lang    语言: zh/en（仅支持中文/英文）
    --output  输出文件(可选,JSON格式)
    --json    输出JSON到stdout
"""

import argparse
import datetime
import json
import os
import re
import sys

VERSION = "1.0.7"

# 中文虚词容差类: 词条相邻字之间允许插入的可选虚词。
# 刻意排除否定词(不/没/无/非)——否则"好用"会误匹配"不好用",造成语义反转;
# 亦排除"得/地/吗/呢"等改变语法或语气的字。
ZH_FILLER_CLASS = "了的者是也都还真挺太过很就才又再过着"
ZH_FILLER_MAX = 2

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def meta_fields(tool):
    return {
        "ok": True,
        "tool": tool,
        "version": VERSION,
        "schema": "global-ecommerce-intelligence/" + tool,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


# ─────────────────────────────────────────────────────────────
# 关键词库
# 设计原则:
#   - 短语优先(多字短语先匹配),避免单字误匹配
#   - 否定短语单独列(如"不好用"≠"好用")
#   - 不放单字"薄"(会误匹配"薄荷")
# ─────────────────────────────────────────────────────────────

# 否定短语(优先识别,识别后从文本剔除避免被正面词覆盖)
# 注意: 不能与 ZH_NEGATIVE 重复收录同一短语,否则会在原文匹配+合并计数中双重计分
# (如"质量差"已在 ZH_NEGATIVE,此处不重复收录)
ZH_NEGATION_PHRASES = [
    "不好用", "不好看", "不舒服", "不方便", "不满意", "不喜欢", "不推荐",
    "质量不好", "质量不行", "做工不好", "性价比不高", "不划算",
    "没用", "没效果", "没反应", "不工作", "不能用",
]

ZH_POSITIVE = [
    # 品质
    "质量好", "质量不错", "做工精细", "做工好", "用料考究", "耐用", "结实", "厚实",
    # 外观
    "外观漂亮", "颜值高", "设计感", "精致", "时尚", "好看", "漂亮",
    # 价值
    "性价比高", "物超所值", "超值", "划算", "便宜好用",
    # 体验
    "好用", "方便", "舒适", "顺手", "人性化",
    # 服务
    "发货快", "物流快", "包装好", "客服好", "售后好",
    # 情感
    "喜欢", "满意", "惊喜", "推荐", "回购", "已买多次",
    # 程度副词 + 形容词(高频评价口语,"质量很好/物流很快"等)
    "很好", "很好用", "很不错", "很棒", "很快", "非常好", "特别好",
]

ZH_NEGATIVE = [
    # 品质
    "质量差", "容易坏", "做工粗糙", "廉价感", "用一次就坏", "做工差",
    # 外观
    "色差大", "与图片不符", "实物难看",
    # 价值
    "不值", "坑人", "割韭菜", "智商税", "太贵",
    # 体验
    "难用", "设计缺陷", "尺寸不对", "尺寸偏小", "尺寸偏大",
    # 服务
    "发货慢", "物流差", "包装破损", "客服不理", "退货难",
    # 情感
    "失望", "后悔", "差评", "被坑",
    # 程度副词 + 形容词(高频评价口语,"很差/很烂/很慢"等)
    "很差", "很烂", "很慢", "非常差", "特别差",
]

ZH_WISH = ["希望", "如果能", "要是", "建议", "可以改进", "最好", "期待"]

EN_POSITIVE = [
    "great quality", "well-made", "well made", "durable", "sturdy", "solid",
    "great value", "worth every penny", "bang for buck", "affordable",
    "easy to use", "works great", "perfect fit", "highly recommend",
    "fast shipping", "well packaged", "great customer service",
    "love it", "amazing", "awesome", "exceeded expectations", "good quality",
]

EN_NEGATIVE = [
    "poor quality", "cheaply made", "broke after", "flimsy", "fell apart",
    "overpriced", "not worth", "waste of money", "ripoff",
    "difficult to use", "doesn't work", "misleading", "not as described",
    "slow shipping", "damaged", "no response", "return hassle",
    "disappointed", "regret buying", "would not recommend", "waste",
]

EN_WISH = ["wish", "hope", "could", "would be better", "should", "improve", "suggest"]

# 英文否定短语 — 优先识别并从文本剔除,避免被正面词误判
# 注意: 已存在于 EN_NEGATIVE 的短语(not worth/doesn't work/not as described等)不重复收录,
#       否则会双重计数; 这里只收"会被正面词覆盖"的否定构造
EN_NEGATION_PHRASES = [
    "not good quality", "not well made", "not durable", "not sturdy",
    "not easy to use", "not as good", "not what i expected",
    "does not work", "did not work", "not working",
    "not fast", "not satisfied", "not happy", "not recommended",
]


def _has_cjk(term):
    return bool(_CJK_RE.search(term))


def _tolerant_zh(term):
    """把中文词条编译为容差正则: 相邻字之间允许插入 0~ZH_FILLER_MAX 个虚词"""
    chars = list(term)
    parts = []
    for i, ch in enumerate(chars):
        parts.append(re.escape(ch))
        if i < len(chars) - 1:
            parts.append("[" + ZH_FILLER_CLASS + "]{0," + str(ZH_FILLER_MAX) + "}")
    return "".join(parts)


def build_pattern(keywords, flags=0, zh_tolerant=False):
    """构建正则: 按长度降序,最长匹配优先

    flags        用于英文大小写不敏感
    zh_tolerant  中文词条启用虚词容差(英文不适用,英文靠空格分词)
    """
    sorted_kw = sorted(set(keywords), key=len, reverse=True)
    parts = []
    for k in sorted_kw:
        if zh_tolerant and _has_cjk(k):
            parts.append(_tolerant_zh(k))
        else:
            parts.append(re.escape(k))
    return re.compile("|".join(parts), flags) if parts else None


def count_keywords(text, pattern):
    """返回 {命中文本: 次数}; 重叠区间合并计一处,代表取最长命中"""
    spans = match_spans(text, pattern)
    result = {}
    for _, _, matched in spans:
        result[matched] = result.get(matched, 0) + 1
    return result


def match_spans(text, pattern):
    """返回去重后的匹配 [(start, end, matched_text)]

    重叠区间合并为一个,保留其中最长的一段,避免同一段文字被多个词条重复计分
    (例: "用了一次就坏" 同时被 "用一次就坏" 与 "一次" 类词条命中时只计一处)
    """
    if not pattern:
        return []
    raw = [(m.start(), m.end(), m.group(0)) for m in pattern.finditer(text)]
    if not raw:
        return []
    raw.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    kept = [raw[0]]
    for start, end, matched in raw[1:]:
        last_start, last_end, last_matched = kept[-1]
        if start < last_end:
            if (end - start) > (last_end - last_start):
                kept[-1] = (start, end, matched)
            continue
        kept.append((start, end, matched))
    return kept


def blank_spans(text, spans):
    """把给定区间替换为空格(长度不变,索引稳定),用于剔除已识别的否定短语"""
    chars = list(text)
    for start, end, _ in spans:
        for i in range(start, end):
            chars[i] = " "
    return "".join(chars)


def find_wishes(text, wish_list):
    found = []
    for w in wish_list:
        idx = text.find(w)
        if idx >= 0:
            start = max(0, idx - 5)
            end = min(len(text), idx + len(w) + 20)
            found.append(text[start:end])
    return found


def calculate_sentiment_score(pos_count, neg_count):
    """情感评分(0-100)

    规则:
      - 基础分50(中性)
      - 正面词加分(每个+8,上限+40)
      - 负面词减分(每个-12,下限-50)
      - 正负比修正: 正面占比高再加分
    """
    base = 50
    pos_bonus = min(pos_count * 8, 40)
    neg_penalty = max(neg_count * -12, -50)
    total = pos_count + neg_count
    if total > 0:
        ratio_bonus = round((pos_count / total - 0.5) * 20)  # -10 ~ +10
    else:
        ratio_bonus = 0
    score = base + pos_bonus + neg_penalty + ratio_bonus
    return max(0, min(100, score))


def analyze_single(text, lang="zh"):
    if lang == "zh":
        pos_list = ZH_POSITIVE
        neg_list = ZH_NEGATIVE
        wish_list = ZH_WISH
        neg_phrases = ZH_NEGATION_PHRASES
        tolerant = True
    else:
        pos_list = EN_POSITIVE
        neg_list = EN_NEGATIVE
        wish_list = EN_WISH
        neg_phrases = EN_NEGATION_PHRASES
        tolerant = False

    # 英文忽略大小写以覆盖 "Great quality" 等写法
    en_ci = re.IGNORECASE if lang == "en" else 0

    # 1) 先识别否定短语并剔除,避免被正面词误判
    #    ("不好用"被"好用"匹配 / "not good quality"被"good quality"匹配)
    negation_spans = match_spans(text, build_pattern(neg_phrases, en_ci, tolerant))
    neg_keywords = {}
    for _, _, matched in negation_spans:
        neg_keywords[matched] = neg_keywords.get(matched, 0) + 1
    cleaned_text = blank_spans(text, negation_spans)

    # 2) 正/负面词库在剔除否定后的文本上匹配,重叠区间合并计一处
    pos_keywords = count_keywords(cleaned_text, build_pattern(pos_list, en_ci, tolerant))
    neg_spans = match_spans(cleaned_text, build_pattern(neg_list, en_ci, tolerant))
    for _, _, matched in neg_spans:
        neg_keywords[matched] = neg_keywords.get(matched, 0) + 1

    pos_count = sum(pos_keywords.values())
    neg_count = sum(neg_keywords.values())

    score = calculate_sentiment_score(pos_count, neg_count)

    if score >= 80:
        rating = "5星 极好"
    elif score >= 60:
        rating = "4星 良好"
    elif score >= 40:
        rating = "3星 一般"
    elif score >= 20:
        rating = "2星 较差"
    else:
        rating = "1星 极差"

    return {
        "text_preview": text[:100],
        "method": "关键词规则匹配(非AI语义分析)",
        "sentiment_score": score,
        "rating": rating,
        "positive_keywords": sorted(pos_keywords.items(), key=lambda x: x[1], reverse=True)[:5],
        "negative_keywords": sorted(neg_keywords.items(), key=lambda x: x[1], reverse=True)[:5],
        "wish_list": find_wishes(text, wish_list)[:3],
        "pos_count": pos_count,
        "neg_count": neg_count,
    }


def analyze_file(filepath, lang="zh"):
    if not os.path.isfile(filepath):
        raise FileNotFoundError("评价文件不存在: " + filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return [analyze_single(line, lang) for line in lines]


def batch_analyze(directory, lang="zh"):
    if not os.path.isdir(directory):
        raise FileNotFoundError("批量目录不存在: " + directory)
    all_results = {}
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath) and fname.endswith((".txt", ".csv")):
            all_results[fname] = analyze_file(fpath, lang)
    return all_results


def print_report(result):
    print("\n评价情感分析报告")
    print("=" * 40)
    print(f"  文本: {result['text_preview']}...")
    print(f"  方法: {result['method']}")
    print(f"  情感评分: {result['sentiment_score']}/100 {result['rating']}")
    print(f"  正面关键词数: {result['pos_count']}")
    if result['positive_keywords']:
        print("  好评关键词:")
        for kw, cnt in result['positive_keywords']:
            print(f"    - \"{kw}\" (×{cnt})")
    print(f"  负面关键词数: {result['neg_count']}")
    if result['negative_keywords']:
        print("  差评关键词:")
        for kw, cnt in result['negative_keywords']:
            print(f"    - \"{kw}\" (×{cnt})")
    if result['wish_list']:
        print("  功能需求:")
        for w in result['wish_list']:
            print(f"    - \"{w}\"")
    print("=" * 40)


def main():
    parser = argparse.ArgumentParser(description="评价情感分析 v" + VERSION)
    parser.add_argument("--text", type=str, help="单条评价文本")
    parser.add_argument("--file", type=str, help="评价文件路径")
    parser.add_argument("--batch", type=str, help="批量分析目录")
    parser.add_argument("--lang", type=str, default="zh", choices=["zh", "en"], help="语言")
    parser.add_argument("--output", type=str, help="输出JSON文件路径")
    parser.add_argument("--json", action="store_true", help="输出JSON到stdout")
    parser.add_argument("--version", action="version", version=VERSION, help="输出版本")
    args = parser.parse_args()

    def emit(obj):
        if args.json:
            print(json.dumps(obj, ensure_ascii=False, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            if not args.json:
                print(f"  已保存至 {args.output}")

    def wrap(payload):
        m = meta_fields("sentiment_analyzer")
        m.update(payload)
        return m

    if args.text is not None:
        if not args.text.strip():
            print("错误: --text 不能为空", file=sys.stderr)
            sys.exit(1)
        result = analyze_single(args.text, args.lang)
        if args.json:
            emit(wrap({"result": result}))
        else:
            print_report(result)
            if args.output:
                emit(wrap({"result": result}))
    elif args.file:
        try:
            results = analyze_file(args.file, args.lang)
        except FileNotFoundError as e:
            print("错误: " + str(e), file=sys.stderr)
            sys.exit(1)
        if args.json:
            emit(wrap({"results": results}))
        else:
            for r in results[:5]:
                print_report(r)
            if len(results) > 5:
                print(f"  ... 还有 {len(results) - 5} 条评价(省略)")
            if args.output:
                emit(wrap({"results": results}))
    elif args.batch:
        try:
            all_results = batch_analyze(args.batch, args.lang)
        except FileNotFoundError as e:
            print("错误: " + str(e), file=sys.stderr)
            sys.exit(1)
        if args.json:
            emit(wrap({"results": all_results}))
        else:
            print("\n批量评价情感分析汇总")
            print("=" * 50)
            for fname, results in all_results.items():
                if not results:
                    continue
                scores = [r["sentiment_score"] for r in results]
                avg_score = round(sum(scores) / len(scores), 1)
                total_pos = sum(r["pos_count"] for r in results)
                total_neg = sum(r["neg_count"] for r in results)
                print(f"  {fname}: 评分{avg_score} | 正面{total_pos} | 负面{total_neg} | 样本{len(results)}")
            print("=" * 50)
            if args.output:
                emit(wrap({"results": all_results}))
    else:
        parser.error("需要 --text, --file 或 --batch")


if __name__ == "__main__":
    main()
