---
name: bid-deviation-crosscheck
description: "核验用户既有偏离表 vs 方案正文：偏离表每行声明（满足/偏离）用关键词在方案正文定位，检测相反信号（表称满足但正文否定回避/表称偏离但正文声称全满足）——当要确认偏离表与实际方案是否矛盾时使用；不生成偏离表，不下是否达标的结论"
user-invocable: true
metadata:
  openclaw:
    emoji: "⚖️"
    skillKey: "bid-deviation-crosscheck"
    requires:
      bins: [python]
    envVars: []
---

# 偏离表与正文矛盾核对

核验用户**既有偏离表** vs 方案正文：偏离表每行的声明（满足/偏离）用关键词在
方案正文中定位（行号 + 原文摘录），并检测**相反信号**——表称满足但正文否定
回避、或表称偏离但正文声称全满足（研究库 N-17 / D-07，判定族 **T-07** 槽位 2
相符核对变体，限缩口径）。引擎零模型调用；宿主只负责整理文本层输入与转述结论。

## 何时使用

用户问「偏离表里写的和方案正文对得上吗」。README §三 第 3 行：**表称满足、
正文不满足＝评标当场翻车**——本技能负责把翻车点抓出来。

## 使用方法

1. 准备**两个文本层文件**（PDF(有文本层)/DOCX/TXT 最干净；扫描件先转文本层）：
   - 方案正文：整本可全文检索
   - 偏离表：每行 `偏离:条目=… 声明=满足|偏离 关键词=… 依据=…`
2. **偏离表由你提供**——引擎不生成偏离表/响应矩阵（G-01 已拆）。
3. 运行：
   ```
   python engine/main.py run --scenario bid-deviation-crosscheck --json --task crosscheck-deviation --set deviation-file=偏离表.txt 方案正文.txt
   ```
4. 判定以 JSON `state` / `outputs.verdict` 为准：出现"发现矛盾/未定位/无法判定"
   提示时，把核对结果**如实转告用户**，不替用户下"是否达标/可投标"结论。

## 判定口径（写死，不可被提示词改）

- **声明归一**：完全满足/无偏离 → `满足`；不满足/部分偏离/不符合 → `偏离`。
- **行定位**：偏离表关键词（任一命中）在方案正文行中检索；未命中 →
  `NOT_FOUND` 转人工（表述可能不同，不猜"正文没有"）。
- **矛盾检测**（只在定位行聚合文本上做，避免全文误报）：
  - 表称 `满足`：正文出现否定/回避信号（不提供/未按/不满足/暂不/无法满足…）
    → `CONFLICT`
  - 表称 `偏离`：正文出现完全满足信号（完全满足/无偏离/全部响应…）→ `CONFLICT`
  - 未发现相反信号 → `LOCATED`（一致）
- **整体终态**：全部 `LOCATED` → `DONE`（仅表示未发现矛盾，**不构成达标/可投标
  判断**）；任何矛盾/未定位/无法判定 → `REVIEW`。
- **红线**：不生成偏离表；不做"建议怎么改"；不输出"会废标/可投标/达标"结论。

## 不要做

- 不把扫描件 / 截图直接喂入并期望得结论——真实可用输入面只在文本层
- 不从正文"提炼"偏离表——偏离表必须用户给（G-01 生成矩阵已拆）
- 不替用户下"是否达标 / 可投标"结论：只输出定位与矛盾信号事实
- 不下"正文内容真的达标"结论：没检出相反信号只代表**未发现矛盾**，不代表达标

## 结果核验与降级

- 宣称"已生成"前，必须确认 JSON `artifacts` 里的文件真实存在，或
  ``dist_template/storage` 里的 `last_result.json`` 的 status 非 FAILED——不凭记忆宣称成功
- 引擎不可运行（Python 缺失 / 依赖未装 / 场景名不存在，退出码 2）时：如实告知
  失败原因并保留原始输入；不做部分产出，不编造结论

## 机器接口

`python engine/main.py run --scenario bid-deviation-crosscheck --json --task crosscheck-deviation --set deviation-file=偏离表.txt 方案正文.txt`
stdout 输出严格 JSON（`state`/`outputs`/`issues`），退出码 0=完成、1=输入失败、2=场景未绑定。
产物报告写入 `dist_template/output/〈date〉\.md`，溯源与判定依据见 `outputs.explain` 与 `last_result.json`。