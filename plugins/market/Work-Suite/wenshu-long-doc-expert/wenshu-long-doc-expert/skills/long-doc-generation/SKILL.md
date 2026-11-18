---
name: long-doc-generation
description: >-
  Six-stage enterprise long-document generation workflow. Coordinates four specialist roles
  (editor-in-chief, standards researcher, content author, quality corrector) through orientation,
  evidence gathering, drafting, collation, binding and release to produce publication-ready
  long documents with traceable regulation citations and cross-chapter parameter consistency.
version: 1.0.0
tags:
  - long-document
  - multi-agent
  - workflow
---

# 长文档生成（Long Document Generation）

六段成书流程，统筹四位专业角色，从 bare topic 到可交付长文档。

---

## 适用场景

- 建筑装饰：装修施工图设计说明、方案设计说明
- 工程与 IT：技术方案、API 文档、系统运维手册
- 招投标：投标文件、技术规格书
- 通用：需求规格说明书、标准化作业程序（SOP）

---

## 六段流程

| 段 | 名 | 角色 | 产出 |
|---|---|---|---|
| 一 | **定向** | 总编辑（宗秉衡） | 题目、体裁、篇目骨架、卷宗提要初版 |
| 二 | **采撷** | 文献检索员（殷溯典） | 检索凭据（规范条文 + 出处 + 置信度） |
| 三 | **织辞** | 内容生成员（谢敷文） | 完整篇稿 |
| 四 | **校雠** | 质量审核员（邢绳谬） | 校雠结论（放行 / 须改）+ 必改清单 |
| 五 | **合卷** | 总编辑 | 完整书稿（目录、跨篇互引、格式统一） |
| 六 | **付梓** | 总编辑 | 交付版 Markdown + 免责声明 |

---

## 质量门禁

第三段（织辞）与第四段（校雠）构成**闭环**：

- 校雠判「须改」→ 退回织辞重写
- **最多退回两轮**
- 第三轮仍不过 → 强制放行，篇末加「校勘未竟」标注

---

## 卷宗提要

全队共用的唯一事实源，贯穿全程：

| 字段 | 内容 |
|------|------|
| 题目 | 文档正式名称 |
| 体裁 | 决定引用规范与章节骨架 |
| 行业 | 建筑装饰 / 机电 / 市政 / 信息化… |
| 篇幅 | 预估篇数与单篇字数区间 |
| 核心参数 | 面积、层数、等级、设防等 |
| 必引规范 | 已确认须引用的规范清单 |
| 禁用项 | 明确不写的内容 |
| 已成篇目 | 每完成一篇追加 ≤60 字摘要 |
| 待决问题 | 尚未定论的事项 |

---

## 协作机制

- **总编辑建队**：调用 `TeamCreate`，队名形如 `wenshu-<体裁简称>`
- **派工**：调用 Agent 工具，`name` 填成员 Agent ID
- **中转**：成员产出经 `SendMessage` 回传总编辑，不得直连
- **采信**：专业判断必须由对应成员产出后才采信

---

## 交付格式

完整 Markdown：封面信息 → 目录 → 全部正文 → 附录 → 待完善事项 → 免责声明

**免责声明**：本文档由「文枢」文档工坊编制，规范条文引用须经专业人员核验，重要决策以现行有效规范原文为准。
