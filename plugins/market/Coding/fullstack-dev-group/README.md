# 全栈开发组 (Fullstack Dev Group)

一个把 **18 人软硬件交付团队** 装进 Qoder 的插件。用户提需求，团队**智能派单**到对应角色，复杂需求自动**多角色会诊**；工程类任务直接下沉到插件**内置**的《运维专家》和《P8 全栈开发》两项成熟技能（随插件打包、不依赖全局环境）。每位成员的**详细角色配置**见 `agents/*.md`。

## 团队成员（18 人 / 19 个席位）

| 角色 | 姓名 | 一句话职责 |
| --- | --- | --- |
| 技术总监 / 主理人 | 钟帷幄 | 技术战略、架构裁决、交付拍板（两席位同一人） |
| 产品经理 | 蓝图画 | 需求、优先级、验收标准 |
| 前端开发组长 | 颜可见 | 前端架构与排期、跨端协调 |
| 后端开发组长 | 石磐安 | 后端架构与契约、接口治理、统筹五位后端 |
| Java 后端工程师 | 贾巍然 | Java / Spring Boot |
| Python 后端工程师 | 彭森宇 | Python / FastAPI |
| Go 后端工程师 | 郭轻舟 | Go / Gin |
| .NET 后端工程师 | 范承码 | C# / .NET / ASP.NET Core |
| C/C++ 工程师 | 凌彻底 | C/C++ 高性能 / 系统编程 |
| React 前端工程师 | 李响应 | React 体系 |
| Vue 前端工程师 | 韦悠然 | Vue 3 / Element Plus |
| 跨端前端工程师 | 唐端阳 | uni-app / 微信小程序 |
| UI 设计师 | 涂悦目 | 交互与视觉、设计规范 |
| 测试工程师 | 查无漏 | 用例、质量门禁、回归 |
| 运维工程师 | 常守恒 | 部署、监控、发布安全闸门 |
| 硬件组组长 | 路通远 | 硬件架构与联调 |
| 硬件工程师 | 易图安 | 电路 / 器件 / PCB |
| 嵌入式开发工程师 | 褚固行 | 固件 / 驱动 / RTOS |

> 嵌入式、硬件、跨端、运维、UI 等工程细节分别下沉到各角色卡与内置技能，主技能只负责**派单与编排**。

## 两种触发方式

1. **斜杠命令**：输入 `/全栈开发组` 或 `/delivery-team`，后接你的需求，例如：
   `/全栈开发组 给登录接口加限流，后端和运维一起看下`
2. **语义自动触发**：当消息明显属于开发 / 交付 / 软硬件协作场景（写代码、修 bug、画原型、评审方案、部署上线、硬件联调等），团队会自动以对应角色介入。

## 运作规则

- **派单**：技能按团队名册把单条需求路由到 1 个主责角色 + 若干协同角色，并以该角色口吻回应。
- **会诊**：涉及跨角色（如「性能」「安全」「上线」「排期」）时，依次让相关角色表态，最后由技术总监 / 主理人拍板并给出统一结论与下一步。
- **工程下沉**：Vue/Element Plus、Go/Gin、Spring Boot、FastAPI、.NET、C/C++、uni-app、微信小程序、Linux 运维、部署监控、硬件联调、产品/测试/流水线/接口契约等具体实现，直接调用内置技能，不重复造轮子。

## 内置技能

| Skill | 说明 |
| --- | --- |
| `delivery-team` | 团队编排主技能（派单 + 会诊），总入口 |
| `team-p8-full-stack` | P8 全栈开发：文档优先门禁、前后端编码、单元测试、反复打磨（插件内置） |
| `team-ops-expert` | 运维专家：Linux 全生命周期运维、部署监控、安全闸门（插件内置） |
| `hardware-embedded` | 硬件与嵌入式交付：硬件架构/PCB、固件驱动 RTOS、设备协议、软硬联调 |
| `product-design` | 产品与交互设计：需求拆解/PRD、验收标准、交互原型、设计规范 |
| `qa-quality` | 测试与质量门禁：测试策略/用例、覆盖率与劣化门槛、发布验证 |
| `devops-pipeline` | CI/CD 与发布流水线：构建编排、灰度/蓝绿/滚动发布与回滚剧本 |
| `api-contract` | 接口契约治理：OpenAPI 先行、契约评审与 Mock、版本兼容与幂等 |
| `design-diagrams` | 设计图：架构/时序/状态/C4/ER/部署图，统一 mermaid(≤8.8.3) 并经校验 |
| `drawio` | Draw.io 可编辑图：流程图/拓扑/架构/部署图，产出 `.drawio`（mxGraph XML，可在 draw.io 二次编辑） |
| `network-topology` | 网络拓扑：VPC/子网/网关/LB/链路，标注带宽延迟与故障域 |
| `high-fidelity-prototype` | 高保真原型：可点击 HTML/CSS + 设计令牌，覆盖多状态 |
| `test-case` | 测试用例：用例模板/边界矩阵/参数化，可追溯验收标准 |
| `effect-image` | 效果图生成：用 ImageGen 直接出图（头像/渲染/视觉稿），不走 HTML 截图 |
| `canvas-studio` | 交互式画布：委派 Qoder 内置 /canvas 生成看板/架构全景/作战室 |

## 目录结构

```text
fullstack-dev-group/
  .qoder-plugin/plugin.json
  README.md
  qoder.md                # 角色指令总入口（agents/ 目录下 18 张角色卡的索引与运作规则）
  assets/avatar256.png    # 插件图标（含 avatar512.png、avatar.svg 矢量源）
  skills/
    delivery-team/        # 团队编排主技能
      SKILL.md
      references/team-roster.md
    ...（其余 11 项团队技能；team-p8-full-stack / team-ops-expert 为插件内置，随包自包含）
  agents/                 # 18 位成员的详细角色配置（qoder.md 索引到此目录）
```

## 安装

将 `fullstack-dev-group/` 目录放入 Qoder 的插件目录（或市场），重启 / 刷新即可。插件名与目录名均为 `fullstack-dev-group`。
