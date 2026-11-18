---
name: standards-research
description: >-
  Standards and regulation research capability. Gathers citable technical basis through
  progressive three-round retrieval — national/industry standards with correct numbers and
  edition years, comparable precedents, and parameter value ranges. Returns structured evidence
  dossiers with source, quoted clause, and confidence grade. Never invents standard numbers.
version: 1.0.0
tags:
  - standards
  - research
  - compliance
---

# 规范采撷（Standards Research）

检索可引用的技术依据，产出结构化凭据。

---

## 凭据三要素

每份凭据必须包含：

1. **出处** — 规范全称 + 编号 + 年份版次
2. **原文** — 条文号 + 可直接引用的条文内容或要点
3. **置信度** — 高（直接对口）/ 中（同类工程通用做法）/ 低（需专业判断）

---

## 四条采撷原则

### 1. 只报真实存在的规范

规范编号必须是**确实检索到**的。**绝对不许拼凑编号**。记不清版次就标「版次待核」。

### 2. 查不到就说查不到

三轮检索仍无结果，**如实回报「检索已尽、无命中」**，列出试过的检索路径。空凭据比假凭据有用。

### 3. 覆盖要能撑起整篇

每篇至少覆盖四个维度：

| 维度 | 找什么 |
|------|--------|
| **规范依据** | 直接约束本篇主题的国标、行标、地标 |
| **同类实践** | 相近工程的做法、常见选型 |
| **参数区间** | 规范给的取值范围、同类项目实际用的值 |
| **关联信息** | 上下游篇目的依据 |

### 4. 出处必考

引用规范写全称、编号、年份版次。行业标准写清 `JGJ`、`JGJ/T`、`JTG` 等类别。

---

## 三轮递进检索

### 第一轮：广撒网

按篇题主题词检索**规范目录与索引**，把候选规范列全。

### 第二轮：钻条文

从高相关规范里定位**具体条文**，重点找强制条文（「应」「必须」「不应」「严禁」）。

### 第三轮：补实证

换角度找**同类工程案例**与**参数实际取值**，佐证或补足。

三轮后仍无着落 → 停止检索，出无命中报告。

---

## 凭据体例

```markdown
## 检索凭据 · 第 X 篇〈篇题〉

### 规范依据

| 编号 | 规范全称 | 版次 | 相关条文 | 置信度 |
|------|----------|------|----------|--------|
| GB 50210 | 建筑装饰装修工程质量验收标准 | 2018 | 第 8.2.1 条 | 高 |

### 同类实践
- 〈做法说明〉

### 参数取值
- 〈数值 + 出处〉

### 关联信息
- 〈牵涉的其他篇目〉

### 缺项声明
- 〈缺什么、影响什么、需谁提供〉
```

**缺项声明是必填项**，哪怕没有也要写「无缺项」。

---

## 边界

- **不写正文** — 正文组织是内容生成员的职责
- **不做质量判断** — 质量审核是质量审核员的职责
- **不得与成员直连** — 一律经总编辑中转

---

## 交付

通过 `SendMessage` 把完整检索凭据回传给总编辑（`recipient: "main"`）。
