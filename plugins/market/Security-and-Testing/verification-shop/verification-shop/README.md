# 插件发布前核对质检团（verification-shop）

一个发布前核对质检专家套件（Qoder Plugin / 专家套件形态）：以虚拟团队对技能包/插件做上线前核对，**只核不修**，最后给出 PASS / REVIEW / BLOCKED 放行裁决。

## 它解决什么问题

技能包/插件在提交到市场（Qoder、WorkBuddy 或双平台）之前，经常因为一些「平台会查但本地不知道」的规则被打回：简介字数超限、快捷提示词与默认开场白不一致、名称被占用、引用了未上架的 Connector、头像缺失……本套件把这些打回点沉淀成一套分平台口径的核对流程，在提交前一次核完。

## 团队成员（6 人）

| 角色 | 岗位 | 分工 |
|---|---|---|
| 经理 | 质检总监（主理人） | 接单、定平台口径、分派、汇总裁决 |
| 主管 | 结构核对员 | 包结构、元数据清单、双平台格式差异 |
| 员工A | 功能核对员 | 能力声明与实现一致性、可执行性、失败路径 |
| 员工B | 文档与引用核对员 | 简介与正文一致、引用可解析、硬校验项 |
| 员工C | 合规与安全核对员 | 密钥泄露、越权指令、Connector 上架状态 |
| 员工D | 发布裁决员 | 按严重度给 PASS / REVIEW / BLOCKED |

## 内嵌技能

- **release-verification**：四维核对方法（结构 / 功能 / 文档与引用 / 合规与安全），分平台口径表，三态裁决规则，`references/checklist.md` 逐项清单。

## 用法示例

- 「帮我发布前核对一个插件包」（自动判断目标平台）
- 「这个 Qoder 插件包结构对吗？和 WorkBuddy 版本有什么差异？」
- 「这个插件能发布吗？把四个核对维度的问题按严重度列出来。」

## 分平台口径（摘要）

- **Qoder**：`.qoder-plugin/plugin.json` + `skills/`（每个技能一个文件夹含 SKILL.md）；name 小写字母/数字/连字符；引用的 Connector 须已上架。
- **WorkBuddy**：`.codebuddy-plugin/plugin.json` + `agents/` + `settings.json`；zh 简介 40–50 字；tags / quickPrompts 各 3 个；`defaultInitPrompt` 与 `quickPrompts[0]` 逐字一致。
- **双平台**：两套口径分别核，分别出结论。

## 作者

LinkSaaS · 咨询可发邮件：linksass@126.com
