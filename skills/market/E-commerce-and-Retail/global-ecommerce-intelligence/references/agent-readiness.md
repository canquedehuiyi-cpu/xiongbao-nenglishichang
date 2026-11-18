# 智能体就绪度（Agentic Commerce / AEO）

> 最后更新：2026-09-02
> 最后核实：2026-09-02
> 核实周期：每季度（AI 检索 / 电商 Agent 演化快）
> 下次核实：2026-12-01

> 当消费者用 ChatGPT / Gemini / Perplexity / Shopify Agent 等 AI 助手"帮我在 X 场景选一个耐用又适合送人的 Y"时，
> 你的 listing 能否被检索到、被正确理解、被优先推荐？本模块用可机检的真实特征给 listing 打分。

## 为什么重要

2025 年 Cyber Week 期间，AI 与 Agent 影响了约 20% 的全球订单（来源：Salesforce 2025-12-05 官方新闻稿，覆盖 15 亿+ 购物者数据；[置信度:中，第三方数据]）。搜索电商 → 推荐/智能体电商的迁移中，
"产品信息机器可读 + 意图可命中"成为新的流量入口（AEO, Answer Engine Optimization）。

## 五个评分维度（脚本 `agent-readiness.mjs`）

| 维度 | 含义 | 满分条件 |
|------|------|----------|
| schema | 结构化数据完整度 | 提供 JSON-LD，含 @type:Product + Offer.price + availability + priceCurrency |
| specs | 规格可解析性 | 规格为结构化键值对（≥3 项），而非纯文本 |
| returnPolicy | 退货政策清晰度 | 明确退货天数 + 运费/责任方 |
| price | 价格实时性 | 含 price + priceCurrency + 库存/availability |
| aeo | 意图词覆盖 | 标题/描述含自然语言购买意图词（适合/耐用/送礼/场景 等） |

## 评分与改进

- 总分 = 五维加权（schema 0.25 / specs 0.2 / returnPolicy 0.15 / price 0.2 / aeo 0.2）。
- 任一维度 <100 会给出**具体改进动作**（补哪个字段）。
- 总分 <60：在 AI Agent 链路中极易被漏掉或误读。

## 用法

```bash
# 自带样例(好 listing)
node scripts/agent-readiness.mjs --demo --json

# 用 JSON 文件评估
node scripts/agent-readiness.mjs --input listing.json

# 直接传参
node scripts/agent-readiness.mjs --title "..." --description "..." --specs "材质:棉;尺寸:M" \
     --price 19.9 --currency USD --stock 100 --return-policy "30天无理由退货,运费卖家承担" --json
```

listing.json 示例字段：`title / description / specs(对象或"键:值;键:值") / price / currency / stock / returnPolicy / structuredData(JSON-LD 字符串)`。
