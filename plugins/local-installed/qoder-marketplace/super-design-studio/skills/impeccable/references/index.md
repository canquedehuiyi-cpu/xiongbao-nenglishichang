# Impeccable References Index

impeccable 原始完整版本包含 27 个 reference 文件、40+ Node.js scripts 和 3 个 agents。
本插件保留核心 SKILL.md 逻辑，以下为 reference 文件的索引说明。

## Command References (27 files)

### Build Commands
| 文件 | 说明 |
|---|---|
| `reference/craft.md` | craft 命令详细执行逻辑：从描述/线框/截图生成高保真 UI 的完整流程 |
| `reference/shape.md` | shape 命令：对已有界面进行结构性改进 |
| `reference/init.md` | init 命令：新项目设计系统脚手架初始化 |
| `reference/document.md` | document 命令：设计文档和规范生成 |
| `reference/extract.md` | extract 命令：从已有代码提取设计 tokens/模式/组件 |

### Evaluate Commands
| 文件 | 说明 |
|---|---|
| `reference/critique.md` | critique 命令：结构化 UX/设计评审，含评分维度和扣分规则 |
| `reference/audit.md` | audit 命令：全面设计和无障碍审计 |

### Refine Commands
| 文件 | 说明 |
|---|---|
| `reference/polish.md` | polish 命令：上线前视觉质量检查清单 |
| `reference/bolder.md` | bolder 命令：让平淡设计更鲜明有力的技法 |
| `reference/quieter.md` | quieter 命令：降噪和简化过载界面 |
| `reference/distill.md` | distill 命令：精简复杂度同时保留功能 |
| `reference/harden.md` | harden 命令：加固边界场景和错误状态 |
| `reference/onboard.md` | onboard 命令：引导流程设计 |

### Enhance Commands
| 文件 | 说明 |
|---|---|
| `reference/animate.md` | animate 命令：目的性动效设计原则和实现 |
| `reference/colorize.md` | colorize 命令：配色方案优化和色彩系统 |
| `reference/typeset.md` | typeset 命令：排版优化和层级调整 |
| `reference/layout.md` | layout 命令：布局重构和空间节奏 |
| `reference/delight.md` | delight 命令：愉悦细节和微时刻 |
| `reference/overdrive.md` | overdrive 命令：视觉野心最大化 |

### Fix Commands
| 文件 | 说明 |
|---|---|
| `reference/clarify.md` | clarify 命令：信息清晰度提升 |
| `reference/adapt.md` | adapt 命令：响应式适配 |
| `reference/optimize.md` | optimize 命令：性能优化 |

### Iterate Commands
| 文件 | 说明 |
|---|---|
| `reference/live.md` | live 命令：浏览器 HMR 实时迭代工作流 |

### Register Files
| 文件 | 说明 |
|---|---|
| `reference/brand.md` | 品牌/营销/落地页的设计注册规范 |
| `reference/product.md` | 应用/仪表盘/工具类的设计注册规范 |

## Scripts (40+)
impeccable 包含大量 Node.js 脚本辅助执行：
- `context.mjs` — 会话上下文初始化
- `palette.mjs` — 品牌种子色生成
- 其他辅助脚本用于颜色计算、排版验证、无障碍检查等

## Agents (3)
impeccable 使用 3 个专用 agents 分别处理不同类型的任务编排。

---

**注：** 完整 reference 文件内容请参考 impeccable 原始安装包的 `reference/` 目录。
本插件中的 impeccable skill 保留了所有路由规则和设计指导核心逻辑，
具体命令执行时会按需加载对应的 reference 文件。
