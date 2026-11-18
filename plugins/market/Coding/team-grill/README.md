# Team Grill

面向研发团队的 Qoder 技能集，帮助团队澄清需求、拆解任务、实现功能、排查问题并审查代码。

包含 **39 个技能**，以 Matt Pocock 的工程实践技能为基础，补充项目协作规范初始化能力。团队可以按任务选择单个技能，也可以组合使用。

## 功能亮点

- **需求对齐**：通过分轮提问明确目标、约束和待决事项。
- **工程协作**：将已讨论的需求整理为规格和任务，支持实现、TDD、审查与交接。
- **问题排查**：围绕复现、验证和回归测试定位复杂问题。
- **项目规范**：根据真实项目生成或精简 `AGENTS.md`，将详细规则改为按需读取。
- **知识与表达**：维护领域术语和决策，辅助调研、教学、技术写作。

## 安装

### 从团队插件市场安装

当团队管理员将 Team Grill 发布到组织可访问的插件市场后：

1. 打开 Qoder 的插件市场，选择团队提供的扩展来源。
2. 搜索 **Team Grill**，确认插件标识为 `team-grill`。
3. 查看版本及包含的技能，选择安装；跨项目使用时选择用户级范围。
4. 新建会话，在 `/` 菜单中确认插件技能可见。

市场中的可见范围和安装权限由团队配置决定。当前仓库提供插件发布包，尚未指定市场地址。

### 从发布包导入

获取团队提供的 `team-grill.zip`，通过 Qoder 的插件导入入口选择该文件。ZIP 可用于导入；导入当前设备不会自动将插件发布到团队或公共市场。

## 快速开始

安装后，在对话中输入 `/`，选择 Team Grill 中的对应技能，再描述任务。插件内技能可能显示为 `team-grill:技能名`，以当前客户端菜单为准。

| 目标 | 建议选择 | 示例输入 |
| --- | --- | --- |
| 澄清需求 | `grill-me` | 帮我明确批量导入功能的目标和边界，每轮给出推荐选项。 |
| 不知道该选哪个技能 | `ask-matt` | 我已经有需求说明，接下来应该使用哪个技能？ |
| 将讨论整理成规格 | `to-spec` | 把已经确认的内容整理为规格，不新增需求。 |
| 测试驱动实现 | `tdd` | 为金额计算规则补充测试，再完成实现。 |
| 排查复杂问题 | `diagnosing-bugs` | 根据这份复现步骤定位问题，并验证修复结果。 |
| 审查变更 | `code-review` | 审查相对于指定提交的变更，检查规范和需求符合性。 |
| 建立项目协作约定 | `init-agents-md` | 根据当前代码初始化精简的 AGENTS.md。 |

`grill-me` 使用同包内的 `grilling` 完成访谈，两者已经一起打包。技能之间的调用仍需在团队实际使用的客户端及模型环境中验证。

## 技能目录

| 技能 | 用途 |
| --- | --- |
| [ask-matt](skills/ask-matt/SKILL.md) | 根据当前任务选择技能或工作流 |
| [chief-of-staff](skills/chief-of-staff/SKILL.md) | 协调子代理推进长期目标 |
| [claude-handoff](skills/claude-handoff/SKILL.md) | 将上下文移交给新的后台代理，面向支持该能力的环境 |
| [code-review](skills/code-review/SKILL.md) | 从编码规范和需求两个维度审查变更 |
| [codebase-design](skills/codebase-design/SKILL.md) | 分析模块接口、职责和测试边界 |
| [diagnosing-bugs](skills/diagnosing-bugs/SKILL.md) | 为复杂缺陷建立复现与验证流程 |
| [domain-modeling](skills/domain-modeling/SKILL.md) | 维护领域术语与架构决策 |
| [git-guardrails-claude-code](skills/git-guardrails-claude-code/SKILL.md) | 为 Claude Code 配置 Git 操作保护 |
| [grill-me](skills/grill-me/SKILL.md) | 通过持续提问打磨计划或想法 |
| [grill-with-docs](skills/grill-with-docs/SKILL.md) | 在需求访谈中同步维护领域文档 |
| [grilling](skills/grilling/SKILL.md) | 分轮访谈的基础能力 |
| [handoff](skills/handoff/SKILL.md) | 整理供后续代理使用的交接文档 |
| [implement](skills/implement/SKILL.md) | 按规格或任务完成实现 |
| [implement-spec](skills/implement-spec/SKILL.md) | 按规格和任务依赖组织实现工作 |
| [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) | 识别并讨论架构改进机会 |
| [init-agents-md](skills/init-agents-md/SKILL.md) | 检查、初始化或精简 AGENTS.md |
| [loop-me](skills/loop-me/SKILL.md) | 讨论要建立的工作流规格 |
| [migrate-to-shoehorn](skills/migrate-to-shoehorn/SKILL.md) | 迁移 TypeScript 测试中的类型断言 |
| [pr](skills/pr/SKILL.md) | 编写 PR 描述 |
| [prototype](skills/prototype/SKILL.md) | 制作低成本原型以验证想法 |
| [research](skills/research/SKILL.md) | 依据可靠一手来源调研并记录发现 |
| [retro](skills/retro/SKILL.md) | 复盘一次开发协作 |
| [scaffold-exercises](skills/scaffold-exercises/SKILL.md) | 创建教学练习目录结构 |
| [setup-matt-pocock-skills](skills/setup-matt-pocock-skills/SKILL.md) | 配置项目工单、分类和领域文档约定 |
| [setup-pre-commit](skills/setup-pre-commit/SKILL.md) | 为适用项目设置提交前检查 |
| [setup-ts-deep-modules](skills/setup-ts-deep-modules/SKILL.md) | 配置 TypeScript 模块依赖边界检查 |
| [tdd](skills/tdd/SKILL.md) | 使用测试驱动开发实现功能或修复缺陷 |
| [teach](skills/teach/SKILL.md) | 引导学习指定技能或概念 |
| [to-questionnaire](skills/to-questionnaire/SKILL.md) | 将待决问题整理成问卷 |
| [to-spec](skills/to-spec/SKILL.md) | 将已讨论内容整理成规格 |
| [to-tickets](skills/to-tickets/SKILL.md) | 将计划或规格拆解成有依赖关系的任务 |
| [triage](skills/triage/SKILL.md) | 分类并推进工单处理 |
| [wait-what](skills/wait-what/SKILL.md) | 要求重新清楚地解释上一段内容 |
| [wayfinder](skills/wayfinder/SKILL.md) | 为大型目标梳理决策路径 |
| [wizard](skills/wizard/SKILL.md) | 为需要人工参与的操作创建交互式引导 |
| [writing-beats](skills/writing-beats/SKILL.md) | 将素材组织成连贯的表达结构 |
| [writing-for-agents](skills/writing-for-agents/SKILL.md) | 编写供 AI 代理使用的文档 |
| [writing-fragments](skills/writing-fragments/SKILL.md) | 探索和收集写作素材 |
| [writing-shape](skills/writing-shape/SKILL.md) | 打磨文章的整体结构 |

## 依赖与适用范围

- 插件提供工作方法，不包含模型服务、外部账号或工具安装。技能提及的 Git、MCP、数据库、构建工具等按任务在使用环境中配置。
- 工单相关技能需要目标业务项目的跟踪方式、分类标签和领域文档约定。已有配置可继续复用；缺少时可使用 `setup-matt-pocock-skills`。
- 部分技能面向 Claude Code、TypeScript 等特定环境；安装到 Qoder 不代表其平台专用能力已经适配。
- 包含完整排查或任务编排的技能适用于对应复杂任务；日常小改动可以直接描述需求。
- `init-agents-md` 默认按实际变化维护 API 和 SQL 资料，设计文档及图示仅在用户明确要求时生成。该约定不自动改写其他技能的原始工作流。

## 常见问题

**安装后找不到技能？**

确认插件已启用，检查安装范围及当前工作区，再新建会话查看 `/` 菜单。

**为什么一次会问很多问题？**

`grill-me` 用于澄清决策和需求。提供明确的任务范围、已确认事项及期望的访谈深度，有助于控制讨论范围。

**安装后会自动配置数据库或 Hook 吗？**

不会。本插件仅声明 Skills 组件；各技能的辅助文件随包提供，不作为 Qoder Hook、MCP 或 Agent 自动注册。

## 来源与致谢

工程和协作技能主要来自 [Matt Pocock / skills](https://github.com/mattpocock/skills)，保留原始技能内容和支持资源。`init-agents-md` 为团队维护的项目规范初始化技能。

上游原始 MIT 许可证见 [LICENSE](LICENSE)。团队打包维护者为开心一本；原始技能作者保留其署名。

插件版本：`0.1.0`。结构校验已通过；全部技能的实际模型执行效果尚未逐一验证。

## 维护与发布

插件维护、验证、打包及来源快照信息见 [CONTRIBUTING.md](CONTRIBUTING.md)。
