# UX Expert References Index

ux-expert 原始完整版本包含丰富的 domain/ 目录和 9 个 reference/ 文件。
本插件保留核心编排逻辑，以下为参考文件的索引说明。

## Domain Knowledge Directory

### 业务基础
| 文件 | 说明 |
|---|---|
| `domain/业务概况.md` | 百亿补贴频道业务概况：定位、用户画像、核心指标、竞争格局 |
| `domain/业务术语.md` | 百补领域术语表：GMV、UV 价值、坑产、曝光点击率等业务概念定义 |

### 设计原则
| 文件 | 说明 |
|---|---|
| `domain/principles/视觉构成.md` | 百补频道视觉构成原则：信息层级、价格突出、利益点展示、促销氛围 |

### 策略模板
| 文件 | 说明 |
|---|---|
| `domain/strategy/*.md` | 设计策略模板库：不同场景（大促/日常/品类专场）的策略框架 |

### 设计规则
| 文件 | 说明 |
|---|---|
| `domain/rules/*.md` | 百补设计规则集：平台规范、合规要求、品牌约束 |

### UX 工作流
| 文件 | 说明 |
|---|---|
| `domain/ux-workflow/*.md` | UX 工作流模板：不同设计阶段的方法论和操作指南 |

### 案例库
| 文件 | 说明 |
|---|---|
| `domain/cases/*.md` | 历史设计案例：成功案例和踩坑记录 |

## Command References (9 files)

| 文件 | 行数 | 说明 |
|---|---|---|
| `reference/analyze.md` | ~147 行 | analyze 命令详细执行逻辑：需求解析框架、上下文提取、目标设定 |
| `reference/strategize.md` | ~373 行 | strategize 命令详细执行逻辑：洞察提炼、策略框架、多方案对比 |
| `reference/generate.md` | ~426 行 | generate 命令详细执行逻辑：线框到高保真转化、impeccable craft 委派协议 |
| `reference/live.md` | — | live 命令：浏览器实时微调和 impeccable live 委派 |
| `reference/polish.md` | — | polish 命令：上线前视觉检查和 impeccable polish 委派 |
| `reference/review.md` | — | review 命令：扣分制评审规则和 impeccable critique 委派 |
| `reference/research.md` | — | research 扩展位（未启用） |
| `reference/compete.md` | — | compete 扩展位（已迁移为独立 skill） |
| `reference/collect.md` | — | collect 扩展位（未启用） |

## Context Files

| 文件 | 说明 |
|---|---|
| `PRODUCT.md` | 项目产品信息文档（按命令分档：轻档/全档） |
| `DESIGN.md` | 设计系统和规范文档 |

---

**注：** 完整 domain/ 和 reference/ 文件内容请参考 ux-expert 原始安装包。
本插件中的 ux-expert skill 保留了所有路由规则、Shared Laws 和编排逻辑。
执行具体命令时会按需加载对应的 domain/ 和 reference/ 文件。
