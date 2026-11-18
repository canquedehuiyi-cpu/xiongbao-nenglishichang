---
name: three-tier-memory
description: AI Agent 三层记忆系统。L1 工作记忆（当前对话）、L2 会话记忆（每日事件）、L3 长期记忆（核心知识 + EvoMap）。实现跨会话记忆连续性、知识进化、EvoMap 集成。触发场景：(1) 会话启动加载记忆 (2) 记录重要事件 (3) 查询历史知识 (4) 发布 Capsule 到 EvoMap。
---

# 三层记忆系统

## 快速开始

### 会话启动

每次会话启动时自动加载：

```
L3 (长期) → MEMORY.md + Genes
L2 (会话) → recent-events.md + 今日日记
L1 (工作) → 当前对话上下文
```

### 记录事件

```bash
# 记录到 L2
echo "- $(date '+%H:%M') 重要决策: xxx" >> memory/daily/$(date +%Y-%m-%d).md

# 记录到事件数据库
sqlite3 memory/events.db "INSERT INTO events (type, content, importance) VALUES ('decision', 'xxx', 5)"
```

### 压缩到 L3

每日 00:00 自动执行：
1. 读取昨日 daily note
2. 提取重要事件
3. 更新 MEMORY.md
4. 清理过期 L2 数据

## 三层架构

| 层级 | 存储 | 容量 | 持久性 |
|------|------|------|--------|
| L1 工作记忆 | LLM Context | 200K tokens | 会话内 |
| L2 会话记忆 | SQLite + 文件 | 7 天 | 可配置 |
| L3 长期记忆 | 文件 + EvoMap | 无限 | 永久 |

## 文件结构

```
memory/
├── daily/              # 每日记忆
│   └── YYYY-MM-DD.md
├── events.db           # 事件数据库
├── recent-events.md    # 滚动事件 (24h)
└── evolution-events/   # 进化事件

genes/                  # 策略模板
capsules/               # 解决方案
MEMORY.md              # 核心知识
```

## EvoMap 集成

### 发布 Capsule

当解决了一个有价值的问题：

```json
{
  "type": "Capsule",
  "trigger": ["ErrorType"],
  "summary": "解决方案摘要",
  "content": "详细内容",
  "confidence": 0.85,
  "blast_radius": { "files": 1, "lines": 10 },
  "outcome": { "status": "success", "score": 0.85 }
}
```

### 获取 Capsule

遇到问题时：

```bash
curl -X POST https://evomap.ai/a2a/fetch \
  -H "Content-Type: application/json" \
  -d '{"payload": {"asset_type": "Capsule"}}'
```

## 事件类型

| 类型 | 说明 | L2 保留 | L3 归档 |
|------|------|---------|---------|
| decision | 重要决策 | 7 天 | ✅ |
| insight | 学习心得 | 7 天 | ✅ |
| task | 任务完成 | 3 天 | ❌ |
| error | 错误修复 | 7 天 | 转 Capsule |
| evolution | 能力进化 | 30 天 | ✅ + EvoMap |

## API

### 写入

```bash
# 添加事件
memory_add <type> <content> [--importance 1-5]

# 发布 Capsule
memory_publish_capsule <capsule.json>
```

### 读取

```bash
# 搜索记忆
memory_search <query>

# 获取今日事件
memory_today

# 获取最近事件
memory_recent [--hours 24]
```

## Cron 配置

```bash
# 心跳 (每 15 分钟)
*/15 * * * * curl -X POST https://evomap.ai/a2a/heartbeat -d '{"node_id":"xxx"}'

# 每日压缩 (每天 00:00)
0 0 * * * memory_compress

# 获取 Capsule (每 4 小时)
0 */4 * * * memory_fetch_capsules
```

## 最佳实践

1. **即时记录** — 事件发生立即写入 L2
2. **定期压缩** — 避免无限增长
3. **发布 Capsule** — 高质量解决方案分享到 EvoMap
4. **查询优先** — 遇到问题先查 EvoMap

## 参考

- EvoMap 文档: https://evomap.ai/skill.md
- MEMORY.md 模板: workspace/memory/MEMORY.md
