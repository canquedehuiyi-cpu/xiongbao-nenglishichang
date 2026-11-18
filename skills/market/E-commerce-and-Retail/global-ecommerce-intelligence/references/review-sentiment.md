# AI评价情感分析引擎
> 版本：1.0.7
> 最后更新：2026-09-02
> 最后核实：2026-09-02
> 核实周期：每年
> 下次核实：2027-09-02

> 多维度评价情感分析+用户痛点提取+竞品弱点识别
> 支持中文/英文评价分析

---

## 分析维度

| 维度 | 方法 | 输出 |
|------|------|------|
| 好评关键词 | 提取高频正面词+频率统计 | 用户认可点TOP5+提及率 |
| 差评关键词 | 提取高频负面词+频率统计 | 用户痛点TOP5+改进机会 |
| 情感倾向 | 正面/中立/负面占比计算 | 评分分布+趋势 |
| 功能需求 | 识别"希望""如果能""要是"类表达 | 产品改进方向TOP3 |
| 竞品提及 | 识别评价中提及竞品的频次 | 竞品弱点+用户流失原因 |

---

## 情感评分算法 (0-100)

> 实际评分公式以 `references/scripts/sentiment_analyzer.py` 为准（文档与脚本一致）：

```
基础分 50
  + 正面关键词命中数 × 8   （上限 +40）
  - 负面关键词命中数 × 12  （下限 -50）
  + 正负占比修正 (正面占比 - 0.5) × 20  （范围 -10 ~ +10）
最终截断到 [0, 100]

评级:
  80-100: 极好 ★★★★★
  60-79:  良好 ★★★★
  40-59:  一般 ★★★
  20-39:  较差 ★★
  0-19:   极差 ★
```

> 注意：本引擎为关键词匹配，非 AI 语义分析。否定短语（如"不好用"）先于正面词识别，避免被"好用"覆盖。

---

## 中文评价关键词库

> 词库与 references/scripts/sentiment_analyzer.py 保持一致（代码为单一数据源）。

### 正面关键词

| 类别 | 关键词 |
|------|--------|
| 品质 | 质量好、质量不错、做工精细、做工好、用料考究、耐用、结实、厚实 |
| 外观 | 外观漂亮、颜值高、设计感、精致、时尚、好看、漂亮 |
| 价值 | 性价比高、物超所值、超值、划算、便宜好用 |
| 体验 | 好用、方便、舒适、顺手、人性化 |
| 服务 | 发货快、物流快、包装好、客服好、售后好 |
| 情感 | 喜欢、满意、惊喜、推荐、回购、已买多次 |
| 程度副词组 | 很好、很好用、很不错、很棒、很快、非常好、特别好 |

### 负面关键词

| 类别 | 关键词 |
|------|--------|
| 品质 | 质量差、容易坏、做工粗糙、廉价感、用一次就坏、做工差 |
| 外观 | 色差大、与图片不符、实物难看 |
| 价值 | 不值、坑人、割韭菜、智商税、太贵 |
| 体验 | 难用、设计缺陷、尺寸不对、尺寸偏小、尺寸偏大 |
| 服务 | 发货慢、物流差、包装破损、客服不理、退货难 |
| 情感 | 失望、后悔、差评、被坑 |
| 程度副词组 | 很差、很烂、很慢、非常差、特别差 |

### 否定短语（先于正面词识别并从文本移除）

`不好用, 不好看, 不舒服, 不方便, 不满意, 不喜欢, 不推荐, 质量不好, 质量不行, 做工不好, 性价比不高, 不划算, 没用, 没效果, 没反应, 不工作, 不能用`

---

## 英文评价关键词库

> 词库与 references/scripts/sentiment_analyzer.py 保持一致（代码为单一数据源）。

### Positive Keywords

| Category | Keywords |
|----------|----------|
| Quality | great quality, well-made, well made, durable, sturdy, solid, good quality |
| Value | great value, worth every penny, bang for buck, affordable |
| Experience | easy to use, works great, perfect fit, highly recommend |
| Service | fast shipping, well packaged, great customer service |
| Emotion | love it, amazing, awesome, exceeded expectations |

### Negative Keywords

| Category | Keywords |
|----------|----------|
| Quality | poor quality, cheaply made, broke after, flimsy, fell apart |
| Value | overpriced, not worth, waste of money, ripoff |
| Experience | difficult to use, doesn't work, misleading, not as described |
| Service | slow shipping, damaged, no response, return hassle |
| Emotion | disappointed, regret buying, would not recommend, waste |

### Negation Phrases

> 与中文"不好用"同理：以下否定构造会被优先识别并从文本移除，避免被正面词覆盖
> （如 "not good quality" 不再被 "good quality" 误判为正面）。已收录在 Negative 的
> 短语（not worth / doesn't work / not as described 等）不重复计数。

`not good quality, not well made, not durable, not sturdy, not easy to use, not as good,
 not what i expected, does not work, did not work, not working, not fast, not satisfied,
 not happy, not recommended`

### Wish / 期望词

| 语言 | 关键词 |
|------|--------|
| 中文 | 希望、如果能、要是、建议、可以改进、最好、期待 |
| 英文 | wish, hope, could, would be better, should, improve, suggest |

---
## 平台评价分析特点

| 平台 | 评价特点 | 分析要点 |
|------|----------|----------|
| Amazon | 评价详细+Verified Purchase标记+图片/视频 | 重点关注Verified评价，过滤虚假/操纵性评价 |
| 淘宝/天猫 | 评价短+追评体系+问大家 | 关注追评（更真实）和问大家 |
| Shopee | 评价简短+星级评分为主 | 星级分布比文字更有价值 |
| JD京东 | 评价质量高+晒单+视频 | 重点关注晒单评价 |
| 拼多多 | 评价极短+质量参差 | 需要大样本量才有价值 |
| eBay | 评价偏正面+Feedback体系 | 关注Neutral/Negative反馈 |
| AliExpress | 多语言评价+评价质量参差 | 需分语言分析 |

---

## 评价分析输出模板

```
【评价情感分析报告 - 产品名】
━━━━━━━━━━━━━━━━━━━━━━━━━━

 总览
  总评价数: 2,450
  情感评分: 78/100 ★★★★
  评分分布: 5★(45%) 4★(25%) 3★(15%) 2★(8%) 1★(7%)

 好评焦点 (用户认可点)
  1. "质量好" — 35%好评提及 → 核心卖点
  2. "性价比高" — 28%好评提及 → 定价优势
  3. "外观漂亮" — 22%好评提及 → 视觉吸引力
  4. "发货快" — 15%好评提及 → 物流体验
  5. "包装精美" — 10%好评提及 → 开箱体验

 差评焦点 (改进机会)
  1. "容易坏" — 25%差评提及 → 品控升级
  2. "尺寸不准" — 20%差评提及 → 尺码指南
  3. "客服差" — 15%差评提及 → 客服培训
  4. "与图片不符" — 12%差评提及 → 图片优化
  5. "物流慢" — 8%差评提及 → 物流升级

 功能需求 (用户期待)
  1. "希望能有XX颜色" → 增加SKU
  2. "如果能更轻便" → 材料升级
  3. "希望出XX版本" → 产品线扩展

 竞品提及
  1. "比XX品牌好" — 被比较12次 → 优于竞品
  2. "不如YY品牌" — 被比较5次 → 劣势点

 情绪趋势
  近30天: 正面↑3% 负面↓1% → 趋势向好
```

---

## 批量分析模式

支持同时分析多个产品的评价，生成对比报告：

```
【多产品评价对比】
━━━━━━━━━━━━━━━━━━━━
产品A: 情感评分 82 ★★★★★
产品B: 情感评分 65 ★★★★
产品C: 情感评分 48 ★★★

推荐排序: A > B > C
关键差异: A品控最好，B性价比高，C差评集中在质量
```

---

## 脚本使用

```bash
python3 sentiment_analyzer.py --text "这个产品很好用，质量超出预期" --lang zh
python3 sentiment_analyzer.py --file reviews.txt --lang en --output report.json
python3 sentiment_analyzer.py --batch products/ --lang zh
```
