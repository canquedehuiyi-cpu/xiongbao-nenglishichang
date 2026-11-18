# 超级设计工坊 (Super Design Studio)

百亿补贴频道 UX 设计全链路 AI 工具箱，集设计大脑、生产引擎、资产扩展于一体。包含 7 个 Skill，覆盖从需求分析、设计策略、界面生产、竞品分析、动效生成、图形素材到设计交付的完整设计链路。内置电商频道专属设计评审标准、百亿补贴视觉约束和 Galacean Effects 动效引擎集成。

> **Disclaimer:** 本插件辅助专业设计工作流程，不替代专业设计判断。所有设计产出应在上线前经过设计团队评审确认。

## Target Roles

- **电商频道 UX/体验设计负责人** — 全链路设计管理，从策略制定到方案评审到交付
- **体验设计师** — 独立产出设计方案，从需求分析到高保真界面到交互标注
- **视觉设计师** — 高质量视觉执行，界面打磨、图形资产、动效制作
- **产品经理（设计协同）** — 理解设计方案、查看评审报告、获取交付文档

## Quick Commands

| Command | Description |
|---------|-------------|
| `/super-design-studio:impeccable craft` | 从描述或线框生成高保真 UI 代码 |
| `/super-design-studio:impeccable critique` | 结构化 UX/设计评审（含评分） |
| `/super-design-studio:impeccable live` | 浏览器实时迭代（HMR） |
| `/super-design-studio:ux-expert analyze` | 需求分析 → 项目背景+目标+场景+体验目标 |
| `/super-design-studio:ux-expert strategize` | 设计策略制定 + 多方案输出 |
| `/super-design-studio:ux-expert generate` | 高保真 HTML 方案生成（委派 impeccable） |
| `/super-design-studio:ux-expert review` | 扣分制设计评审（委派 impeccable critique） |
| `/super-design-studio:compete` | 竞品分析（URL → 长截图 → 对比报告） |
| `/super-design-studio:deliver` | 从设计方案生成技术交付文档 |
| `/super-design-studio:graphic` | 图形资产生成（SVG / AI 生图 / 混合） |
| `/super-design-studio:motion` | 动效生成（Galacean Effects JSON + Demo） |
| `/super-design-studio:onboarding` | 首次使用引导（10-15 分钟配置） |

## Skills

| Skill | Description |
|-------|-------------|
| **impeccable（界面工坊）** | 25 个命令的通用 UI 生产引擎。覆盖 craft（创建）、critique（评审）、audit（审计）、polish（打磨）、live（实时迭代）、animate（动效）、colorize（配色）等全品类界面设计与优化。内置 WCAG 无障碍标准、反模式检测、设计规范系统。 |
| **ux-expert（体验设计专家）** | 百亿补贴 UX 全链路编排器。6 个 MVP 命令：analyze（需求分析）、strategize（策略制定）、generate（方案生成）、live（实时微调）、polish（上线打磨）、review（设计评审）。自动路由到 impeccable 执行并注入百补业务约束。 |
| **compete（竞品分析）** | 接收竞品 URL 列表，通过浏览器自动化截取长截图，从配色/布局/交互/信息架构四维度分析，生成含截图和差异分析的竞品对比报告（HTML + MD）。 |
| **deliver（设计交付）** | 从 HTML 原型和设计策略文档提取设计决策，生成交互链路图（Mermaid）、页面详细说明（模块/状态/异常）和视觉标注（颜色/字号/间距 Token），组装为技术交付文档。 |
| **graphic（图形生成）** | 三条生成路径：SVG 代码图形（图标/简单插画）、AI 生图（写实素材/纹理背景）、混合模式（AI 底图 + SVG 叠加文字/品牌元素）。适用于图标、Banner、插画、装饰元素。 |
| **motion（动效生成）** | 基于 Galacean Effects API 生成动效 JSON 配置和预览 Demo。覆盖开屏品牌动效、微交互、Demo 演示、转场动效四种类型。输出前端可直接集成的代码包。 |
| **onboarding（首次引导）** | 10-15 分钟访谈，了解团队设计流程、评审标准、设计规范、协作方式，写入 QODERWORK.md 让所有 Skill 按团队标准执行。支持 --quick（2分钟极简）和 --redo（重做某段）。 |

## Connectors (Optional Enhancement)

| Connector | Enhanced Capability |
|-----------|-------------------|
| **浏览器自动化** | 竞品分析自动截取长截图；live mode HMR 实时预览迭代；generate 后自动打开浏览器验证效果 |
| **钉钉文档** | analyze 直接读取钉钉文档中的 PRD/需求文档；deliver 自动推送交付文档到钉钉文档空间 |
| **AI 生图** | graphic 调用 AI 生成素材图/背景图；generate 生成辅助视觉素材 |

> 不连接任何外部工具也可完整使用。浏览器自动化未连接时竞品分析改为手动截图上传，AI 生图未连接时图形生成切换为纯 SVG 路径。详见各 Skill 的 MCP 依赖说明。

## First Run

安装后首次使用前，请运行 onboarding 配置：

```
/super-design-studio:onboarding
```

或极简版（2 分钟）：

```
/super-design-studio:onboarding --quick
```

配置完成前，所有 Skill 会暂停并提示你先完成 onboarding —— 这是为了防止产出脱离团队实际标准的通用内容。
