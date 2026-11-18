# 执行层协议
> 版本：1.0.7

> 本skill集成19个可执行脚本：环境验证/实时汇率/利润/BSR/情感/价格弹性/知识过滤/时效巡检/竞品清单/合规扫描/Listing评分/价格监控/税费试算/库存计算/意图路由/编排执行/用户分层引导/类官方事实核实/Agent就绪度评分。
> 调用脚本必须遵循本协议，确保如实转达、优雅降级、不编造结果。

---

## 一、三级降级架构

```
脚本调用请求
  ├── Level 1: 脚本可用 → 正常执行，如实转达结果
  ├── Level 2: 脚本缺失/报错 → 降级到纯知识模式（用references里的方法论手动分析）
  └── Level 3: 纯知识模式也不足 → 明示"无法精确计算，给框架性建议"
```

**核心原则**：脚本失败不阻塞主流程，但必须如实告知用户"用了降级模式"，不能假装算了。

---

## 二、环境前置检查

首次调用任何脚本前，先跑环境验证：

```bash
node references/scripts/env-check.mjs --json
```

返回 Python/Node 可用性、各脚本状态。Python脚本缺失Python时降级到Level 2。

---

## 三、脚本调用规则

### 通用规则

1. **路径确认**：调用前确认所需参数齐全（如profit_calculator必须price+cost）
2. **JSON优先**：所有脚本调用加 `--json` 参数，输出结构化数据
3. **如实转达**：脚本输出原样转述，不美化、不编造成功
4. **失败诊断**：脚本失败时分析原因并给修复建议，不静默吞错

### 脚本清单与调用方式

| 脚本 | 语言 | 用途 | 调用示例 |
|------|:---:|------|---------|
| env-check.mjs | Node | 环境验证 | `node references/scripts/env-check.mjs --json` |
| fetch-rates.mjs | Node | 实时汇率抓取(多源并行+缓存) | `node references/scripts/fetch-rates.mjs --json` |
| profit_calculator.py | Python | 利润计算 | `python3 references/scripts/profit_calculator.py --price 199 --cost 80 --commission 15 --json` |
| bsr_analyzer.py | Python | BSR销量估算 | `python3 references/scripts/bsr_analyzer.py --bsr 1500 --category home --json` |
| sentiment_analyzer.py | Python | 评价情感分析 | `python3 references/scripts/sentiment_analyzer.py --text "评价文本" --lang zh --json` |
| price-elasticity.mjs | Node | 价格弹性计算 | `node references/scripts/price-elasticity.mjs --p1 29.99 --q1 1000 --p2 27.99 --q2 1200 --json` |
| knowledge-filter.mjs | Node | 知识加载过滤+全文检索 | `node references/scripts/knowledge-filter.mjs --entry selection --json` |
| sop-timeliness-check.mjs | Node | 数据+SOP时效巡检 | `node references/scripts/sop-timeliness-check.mjs --json` |
| competitor-checklist.mjs | Node | 竞品+Listing检查清单 | `node references/scripts/competitor-checklist.mjs --product B0XXXXXX --json` |
| compliance-scan.mjs | Node | 文案合规扫描(违禁词) | `node references/scripts/compliance-scan.mjs --text "文案" --platform amazon --json` |
| listing-scorer.mjs | Node | Listing质量评分(0-100) | `node references/scripts/listing-scorer.mjs --title "标题" --bullets "a\|b" --json` |
| price-monitor.mjs | Node | 竞品价格快照与异动 | `node references/scripts/price-monitor.mjs --product B0XXX --price 29.99 --json` |
| tax_calculator.py | Python | 跨境税费试算 | `python3 references/scripts/tax_calculator.py --country DE --price 100 --json` |
| inventory_calculator.py | Python | 库存补货计算 | `python3 references/scripts/inventory_calculator.py --daily-sales 10 --lead-time 15 --on-hand 100 --json` |
| router.mjs | Node | 意图路由(入口/工具推荐) | `node references/scripts/router.mjs --intent "算利润" --json` |
| orchestrator.mjs | Node | 工具链编排执行 | `node references/scripts/orchestrator.mjs --tool profit -- --price 199 --cost 80 --json` |
| guidance.mjs | Node | 用户分层引导(画像识别/偏好进度记忆/下一步推荐) | `node references/scripts/guidance.mjs --detect "新手第一次开店" --json` |

### Python脚本降级规则

| 场景 | 降级行为 |
|------|---------|
| python3可用 | 正常执行 |
| python3缺失但python可用 | 用python替代 |
| Python完全缺失 | 告知用户"利润计算需Python，当前环境不可用"，改用references/pricing-analysis.md方法论手动算 |
| 脚本报错 | 转达错误信息+给修复建议 |

---

## 四、自动调用触发

| 用户信号 | 自动执行 | 说明 |
|---------|---------|------|
| "算利润"/"能赚多少" | profit_calculator.py | 必须先确认price/cost/commission参数 |
| "BSR"/"销量多少"/"排名" | bsr_analyzer.py | 标注"经验模型估算" |
| "评价分析"/"评价情感" | sentiment_analyzer.py | 标注"关键词匹配" |
| "提价"/"降价"/"弹性" | price-elasticity.mjs | 需两组价格-销量数据 |
| "这个阶段该看什么" | knowledge-filter.mjs | 按入口精准加载(`--entry`)或`--search`检索 |
| "数据过时没"/"核实" | sop-timeliness-check.mjs | 扫描数据文件时效 |
| "违禁词"/"文案合规" | compliance-scan.mjs | 标注"关键词启发式初筛" |
| "Listing评分"/"质量分" | listing-scorer.mjs | 标注"人工项需确认" |
| "监控竞品价格"/"盯价" | price-monitor.mjs | 快照对比+异动阈值 |
| "税费"/"关税"/"VAT" | tax_calculator.py | 标注"估算,以官方为准" |
| "补货"/"安全库存" | inventory_calculator.py | 标注"模型估算" |
| "做什么/入口" | router.mjs | 意图→入口→工具推荐 |
| "一键编排" | orchestrator.mjs | 环境门禁+链式执行 |

---

## 五、输出转达规范

脚本输出必须如实转达，格式：

```
[脚本名] 执行结果
─────────────────
[脚本原始输出]

可靠性提示：[如有]
─────────────────
解读：[基于结果的业务建议]
```

**禁止**：
- 把脚本失败说成成功
- 把估算结果说成精确值
- 隐藏脚本的置信度/可靠性提示
- 用"系统分析"包装脚本结果（应明示用的哪个脚本）

---

## 六、参数缺失处理

用户给的参数不全时：

1. **必填参数缺失** → 询问用户，不猜（如profit_calculator的price/cost）
2. **可选参数缺失** → 用默认值并告知（如commission默认15%）
3. **参数可疑** → 提示用户核实（如cost>price时警告）

---

## 七、并发与性能

- 单次交互最多调用2个脚本，避免阻塞
- 脚本超时(30秒；实时汇率/编排类可放宽)自动终止，降级到知识模式
- 批量分析(如批量情感分析)提示用户耗时，不默认执行


---

## 八、错误输出与退出码约定（统一）

所有脚本遵循同一错误契约，转达时据此判断：

| 项 | 约定 |
|----|------|
| 错误输出 | 文本模式一律输出到 **stderr**；`--json` 模式下错误作为结构化结果输出到 **stdout**（`{ ok:false, error, hint }`），退出码仍非 0 |
| 成功输出 | 文本模式 stdout 只承载结果；`--json` 模式 stdout 输出结构化 JSON |
| 退出码 | `0` = 成功；`1` = 执行/参数值/运行错误、核实冲突、合规命中 |
| 退出码 `2` | 脚本特定的"需注意"状态，按脚本语义解读：env-check = 关键工具缺失（仅知识模式可用）；fact-check = 离线模式存在未核实项（需 `--online`）；Python 脚本 = argparse 命令行格式错误 |
| JSON 错误 | 输出 `{ ok:false, error, hint }` 且退出码非 0 |
| 参数校验 | 数值参数按语义校验（如利润率/百分比 0-100、价格非负、排名为正整数），校验失败报错不静默 |

> 编排层（orchestrator）依据本约定判断子工具成败；Python 相关工具不可用时按一级降级到知识模式。
