# 模块协同指南（内部）

> 模块G参考文档：本技能内部各模块之间的协同工作方式
> 无外部依赖：所有协同均发生在本技能内部，不引用任何外部 skill 或第三方接口。

---

## 一、协同概述

本技能的 14 大模块（A去AI味 / B润色 / C蒸馏 / D仿写 / E日韩适配 / F自进化 / G协同 / H安全合规 / H-2专家会诊 / I深度检测 / J创作引擎 / K合规引擎 / L原创自查 / M补充引擎 / N统一工作流）全部为内置资源，模块间通过以下方式协同：

| 协同环节 | 模块 | 说明 |
|----------|------|------|
| 诊断 → 处理 | 诊断模块 → A/B/C/D/E/J | 内置诊断节点 前置诊断决定处理路径 |
| 处理 → 质检 | A/B/C/D/E/J → 专家会诊/I | 处理后文本进入 EX1-EX7 逐项质检与深度检测 |
| 去AI → 润色 | A → B/J(PL) | 去AI味后自动衔接润色 |
| 蒸馏 → 仿写 | C → D/J(ST→IM) | 蒸馏出的风格参数用于仿写 |
| 创作引擎内部 | ST→IM/CO/PL/DL | 蒸馏档案作为仿写/续写/润色/对白的底座 |
| 自进化 → 全部 | F → A/质检 | 黑名单是去AI引擎与 quality_check.py 的唯一数据源 |
| 安全 → 全部 | H → 所有处理 | 前置内容安全过滤先于所有模块 |
| 全流程 → 全部 | N → A~M | pipeline.py 一键串起所有可执行模块 |
| 合规 → 原创 | K → L | 合规体检与原创自查在统一流水线中顺序执行 |

---

## 二、共享数据源（单一数据源）

| 数据 | 位置 | 使用方 |
|------|------|--------|
| 反AI黑名单 | `references/antiai_blacklist.json`（唯一，含 rules/engine_rules/平台策略/类别映射） | de-ai-engine 替换、quality_check.py 检测、evolve_blacklist.py 管理、schema_check.py 校验 |
| 作家风格库 | `references/writer-styles.md` | 仿写模块 |
| 专家检查标准 | `references/expert-verification.md` | 专家会诊 |
| 安全红线 | `references/content-safety.md` | 前置过滤 |
| 版本 | `scripts/common.py`（VERSION） | 全部脚本统一导入 |

> 原则：任何模块需要词表/规则时，一律从上述唯一数据源读取，不在模块内硬编码第二份。

---

## 三、风格参数传递（模块内部）

### 3.1 YAML格式规范

```yaml
style_params:
  version: 1.0.7
  source_module: 蒸馏引擎    # 或 去AI引擎 / 润色引擎
  target_module: 润色引擎        # 或 蒸馏引擎 / 去AI引擎
  timestamp: "YYYY-MM-DDTHH:MM:SS"

  vocabulary:
    高频词: [词1, 词2, 词3, ...]          # TOP20
    指纹词: [词1, 词2, 词3, ...]          # 独特用词
    口语书面比: 0.6                        # 0=全书面 1=全口语

  syntax:
    平均句长: 25                           # 字
    句长标准差: 15
    句式分布:
      短句_3_8字: 30%
      中句_9_30字: 50%
      长句_31_60字: 20%

  paragraph:
    开头类型: "冲突切入"                   # 冲突/氛围/对话/细节
    段落分布: "长短交错"                   # 均匀/长短交错/极短为主
    结尾类型: "钩子"                       # 钩子/收束/开放式

  tone:
    情感色调: "中性"                       # 中性/积极/消极
    判断力: "强断"                         # 强断/建议/中性
    幽默度: 0.3                            # 0=无 1=极高

  punctuation:
    逗号密度: 0.15                         # 逗号数/总字数
    引号频率: 0.05
    破折号频率: 0.02

  anti_ai:
    黑名单版本: "v1.0.7"
    自定义规则: []
    人工质感评分: 85

  genre:
    类型: "玄幻"                           # 或 Romance/Fantasy/異世界/로판 等
    语言: "zh"                             # zh/en/ja/ko
    平台: "起点"                           # 可选
```

### 3.2 传递场景

| 场景 | 方向 | 说明 |
|------|------|------|
| 蒸馏 → 仿写 | 蒸馏引擎 → 仿写 | 蒸馏用户风格后按参数仿写 |
| 去AI → 润色 | 去AI引擎 → 润色引擎 | 去AI化后按风格参数精修 |
| 蒸馏 → 润色 | 蒸馏引擎 → 润色引擎 | 蒸馏风格参数用于润色保风格 |

---

## 四、标准工作流（全流程）

```
Step 1: 前置诊断（内置诊断节点）
  输入：用户文本 + 需求
  输出：诊断报告（语言/句长/连接词/情感标签）
    │
    ▼
Step 2: EX6 安全合规官 前置过滤（H）
  命中红线 → 拒绝；通过 → 继续
    │
    ▼
Step 3: 按用户需求分流
  A 去AI味 → 去AI引擎（黑名单替换 + 人味注入）
  B 润色   → 润色引擎（5原则/6灵魂/术语锁定）
  C 蒸馏   → 蒸馏引擎（8维参数）
  D 仿写   → 蒸馏引擎（作家风格）
  E 日韩   → 对应语言规则
    │
    ▼
Step 4: 模拟专家团会诊（H-2）
  EX1结构 → EX2语言 → EX3对话 → EX4/EX5日韩 → EX7评分
    │
    ▼
Step 5: 交付（通过）或 回退重处理（<70分）
```

---

## 五、决策树

```
用户需求
    │
    ├── 需要质量检测/深度维度？ ──→ 模块I（quality_check.py / quality_depth.py / opening_check.py）
    │
    ├── 需要去AI味？ ──→ 模块A（deai_loop.py，三档模式）
    │
    ├── 需要润色？ ──→ 模块B/J(PL)（creation_engine.py polish）
    │
    ├── 需要提取风格/仿写/续写/对白？ ──→ 模块C/D/J（creation_engine.py distill/imitate/continue/dialogue）
    │
    ├── 日韩小说适配？ ──→ 模块E
    │
    ├── 进化反AI词库？ ──→ 模块F（脚本 evolve_blacklist.py，adopt/rollback）
    │
    ├── 需要专家把关？ ──→ 模块H-2（脚本 quality_check.py）
    │
    ├── 需要合规申报/体检/标识？ ──→ 模块K（compliance_engine.py）
    │
    ├── 需要原创/洗稿自查？ ──→ 模块L（originality_check.py）
    │
    ├── 需要大纲对照/标题/编辑视角？ ──→ 模块M（editor_insight.py）
    │
    ├── 需要全流程一条链？ ──→ 模块N（pipeline.py --chapters）
    │
    └── 不确定？ ──→ 先诊断（模块H-2 前置CT），按结果分流
```

---

## 六、协同接口规范（模块内部）

### 6.1 处理模块 → 质检

```yaml
quality_input:
  text: "处理后的文本"
  style_params:
    version: 1.0.7
    # ... 完整风格参数
  options:
    de_ai: true           # 是否已执行去AI味
    polish: true          # 是否已执行润色
    anti_ai_threshold: 80 # 人工质感评分阈值
    language: "zh"        # 语言
    genre: "玄幻"         # 体裁
    locked_terms: [...]   # 术语锁定列表
```

### 6.2 质检 → 交付

```yaml
quality_output:
  text: "精修文本"
  quality_report:
    anti_ai_score: 85
    checks_passed: 8/8
    issues: []
  style_params:
    version: 1.0.7
    # ... 可能微调后的风格参数
  evolution:
    new_rules_added: 0
    blacklist_version: "v1.0.7"
```

### 6.3 风格蒸馏输出

```yaml
distillation_output:
  style_params:
    version: 1.0.7
    # ... 完整8维风格参数
  cross_validation:
    - feature: "思维特征1"
      evidence: "写作物证1"
      status: "已验证"
  compatibility:
    genre_match: "玄幻"
    language: "zh"
```

---

## 六、跨 skill 协作接口（W-3，统一输出协议 A-2）

本技能 1.0.7 起所有脚本的 `--json` 出口统一为 `{status, version, ...}` 信封结构：
- `status`: `ok` / `blocked` / `skip` / `error`
- `version`: 版本单一来源（`scripts/common.py` 的 VERSION）
- 其余字段为各模块专属结果（`checks[]`/`score`/`summary` 等）

其他 skill（如新媒体写作、剧本、漫画脚本）如需复用本技能产物，直接消费任一脚本的 JSON 信封即可，无需解析特定文本格式。典型场景：
- 剧本/漫画 skill 将台词稿传给 `quality_check.py --json` 做对白质量体检；
- 新媒体写作 skill 将正文传给 `compliance_engine.py manifest` 生成 AI 辅助申报清单；
- 长文 skill 将分章文本传给 `pipeline.py --chapters --json` 获取章节级质量聚合。

所有跨 skill 场景保持"只读消费 + 本地运行"原则，不引入外部依赖。

---

## 七、版本

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.6 | 2026-08-31 | 新增 I 深度检测/J 创作引擎/K 合规引擎/L 原创自查/M 补充引擎/N 统一工作流模块；统一输出协议（A-2）；跨 skill 消费 JSON 信封；全流程与决策树更新 |
| 1.0.4 | 2026-08-15 | 移除全部外部依赖，改为纯内部模块协同；风格参数格式对齐 1.0.4 |
| 1.0.3 | 2026-08-11 | 历史版本（含外部依赖声明，已废弃） |
