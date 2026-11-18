---
name: bid-disqualification-terms
description: "对投标文件中的应然要求做确定性存在性核对，两任务共享一个宿主：① check-completeness 对照应然清单核对封标前文件完整度（N-16/N-46）；② check-terms 把废标/硬性资格条款在招标文件全文中定位并逐项核对要求材料（N-18）。均只给存在性/定位状态，不出会否废标/能否投标结论——封标前自查投标文件完整度、或核对废标/硬性资格条款要求材料时使用"
user-invocable: true
metadata:
  openclaw:
    emoji: "⚠️"
    skillKey: "bid-disqualification-terms"
    requires:
      bins: [python]
    envVars: []
---

# 投标应然要求存在性核对

本场景把投标文件的**应然要求**做成确定性存在性核对，两个任务共享同一宿主：

- **check-completeness（完整度）**：对照应然清单在标书目录中核对文件齐不齐（N-16/N-46）。
- **check-terms（条款/材料）**：把废标/硬性资格条款在招标文件全文定位，并逐项核对要求材料（N-18）。

引擎零模型调用；宿主只负责整理文本层输入与转述结论。

---

## 任务一：check-completeness（封标前完整度与漏项）

### 何时使用
用户问「封标前该交的文件齐不齐、有没有漏项」。

### 使用方法
1. 准备两个文本层文件（PDF(有文本层)/DOCX/TXT 最干净；扫描件先转文本层）：
   - 标书目录/文件列表：每行一个目录条目或文件名
   - 应然清单：每行 `文件:名称=… 关键词=… 必须=是|否`
2. **应然清单由用户提供**——引擎不"猜"招标要求。
3. 运行：
   ```
   python engine/main.py run --scenario bid-disqualification-terms --json --task check-completeness --set required-file=应然清单.txt 标书目录.txt
   ```

### 判定口径（写死）
- 应然项关键词（任一）在目录条目命中 → `PRESENT`（行号+摘录）
- 必备项未命中 → `MISSING` 转人工；可缺项未命中 → `OPTIONAL_MISSING` 仅提示不阻塞
- 任一必备缺失/无法判定 → `REVIEW`；全部定位 → `DONE`
- **红线**：只核对文件"有没有"（存在性），不核数字一致性/签章位置，不输出任何结论性判词

---

## 任务二：check-terms（废标条款与硬性资格打标）

### 何时使用
用户问「这次招标的硬性资格/废标条款散在哪几页、我方材料齐不齐」。

### 使用方法
1. 准备**三个文本层文件**（PDF(有文本层)/DOCX/TXT 最干净；扫描件先转文本层）：
   - 招标文件：几十页可全文检索
   - 条款检查清单：每行 `条款:名称=… 关键词=… 材料=… 类别=废标|硬性资格`
   - 我方材料清单（可选）：每行 `材料:名称=… 关键词=…`
2. **检查清单由你提供**——引擎不做"从招标文件提炼条款"（那是生成半边，已拆）。
3. 运行：
   ```
   python engine/main.py run --scenario bid-disqualification-terms --json --task check-terms --set checklist-file=<清单> [--set materials-file=<材料>] 招标文件.txt
   ```
4. 判定以 JSON `state` / `outputs.verdict` 为准：出现"未定位 / 材料缺失 / 无法判定"
   提示时，把清单**如实转告用户**，不替用户下"会废标/可投标"结论。

### 判定口径（写死，不可被提示词改）
- **条款定位**：检查清单关键词（任一命中）在招标文件行中检索；未命中 →
  `NOT_FOUND` 转人工（表述可能不同，不猜"条款不存在"）。
- **要件核对**：条款要求的材料 vs 材料清单（名称/关键词归一化子串互含）；
  命中 → 已提供；缺失 → `MISSING`；未提供材料清单 → `UNKNOWN` 转人工。
- **整体终态**：全部 `LOCATED` → `DONE`（仅表示核对完成，**不构成可投标判断**）；
  任何未定位/缺失/无法判定 → `REVIEW`。
- **红线**：不输出"会废标/不会废标/可投标"结论；不生成废标风险摘要。

## 通用红线

- 不把扫描件 / 截图直接喂入并期望得结论——真实可用输入面只在文本层
- 不从招标文件/应然要求"提炼"清单（清单必须用户给）
- 不替用户下"会废标 / 可投标"结论：只输出存在性/定位/要件核对事实

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

```
# 完整度（N-16/N-46）
python engine/main.py run --scenario bid-disqualification-terms --json --task check-completeness --set required-file=应然清单.txt 标书目录.txt

# 条款/材料（N-18）
python engine/main.py run --scenario bid-disqualification-terms --json --task check-terms --set checklist-file=<清单> [--set materials-file=<材料>] 招标文件.txt
```
stdout 输出严格 JSON（`state`/`outputs`/`issues`），退出码 0=完成、1=输入失败、2=场景未绑定。
产物报告写入 `dist_template/output/〈date〉\*.md`（完整度 `bid-completeness-*.md`、条款 `bid-terms-*.md`），
溯源与判定依据见 `outputs.explain` 与 `last_result.json`。