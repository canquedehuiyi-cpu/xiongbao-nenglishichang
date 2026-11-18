# 前端项目 AI coding 规则生成指引（探测策略与采集清单）

本文件是 `frontend-ai-coding-rules` 技能的采集规范，回答「要查哪些事实、查不到时怎么降级、判到哪一档」；
生成的动作序列在 `SKILL.md`，待填的模版在 `templates/`。

- `templates/rule-entry.md` —— 规则入口模版（含 `{{占位符}}`），落地为目标项目的 `.qoder/rules/frontend.md`
- `templates/references/{api-types,page,components-style}.md` —— 细则分册模版，落地到 `.qoder/rules/references/`
- 本文件 —— 生成流程、探测与缺失处理、采集清单、能力档位判定
- 产物**不留在本技能目录**：填好后复制进目标项目的规则目录，避免两份副本漂移。

**结构约定**：入口文件每次任务都读（基线、关键文件、命令、速查、编码姿态、分册索引、验证、禁止、自检）；
细则放 `references/`，按任务类型只读命中的小节。入口 §7 的「分册索引」是这套结构成立的前提——
没有索引 AI 不会去翻分册，细则写了也白写。索引里的路径写**仓库根相对路径**（例：`.qoder/rules/references/page.md`），
分册之间不互相引用。

> 组织方式沿用「先读约定 → 再读最近似真实代码 → 最后写码」的 CRUD 编码 skill 形态，
> 但内容必须来自目标仓库实际情况，不能沿用其他项目的结论。

## 一、生成流程

1. **确定基线**。不要假设项目有 `README` / `.docs`，也不要假设 git 信息一定存在——按候选顺序探测，
   **全部拿不到就删掉该行，规则正文里不出现这一项**，同时**绝不编造**仓库地址或分支。

   | 要确认的事 | 来源候选（自上而下尝试，前者缺失再用后者） | 全部拿不到 |
   | --- | --- | --- |
   | 是否 git 仓库 | `git rev-parse --is-inside-work-tree`；退化看 `.git/` 是否存在 | 按「非受控副本」处理，跳过所有 git 相关结论 |
   | 远端地址 | `git remote -v` → `package.json` 的 `repository`/`homepage`/`bugs` → CI 配置（`.github/workflows`、`.gitlab-ci.yml`、Jenkinsfile）→ `changelog.md`/文档里的链接 | 不写该行；规则中不出现任何远端链接，只用仓库内相对路径 |
   | 当前分支 / 默认分支 | `git branch --show-current` → `.git/HEAD` → `git for-each-ref refs/heads` → CI 里写死的分支 | 不写该行 |
   | 提交历史 | `git log --oneline -10`；**空仓库/单次 squash 导入是常见的**，此时不要从 commit 推断约定 | 不写；改从代码本身推断（近 2 周内被修改的文件 = 现行风格基准） |
   | 上游 fork / 二次开发来源 | `package.json` 的 `name`/`description`/`author`/`homepage`、`tea.yaml`、README、许可证头 | 不写该行 |
   | 包管理与 Node 约束 | `package.json` 的 `engines`/`packageManager`/`preinstall` → lockfile 类型与首个注释行 | 以 lockfile 类型为准；Node 需求看 CI 的 `node-version`，都没有 → 不写 |
   | 是否 monorepo + 版本策略 | `pnpm-workspace.yaml`（含 `catalog:`）、`workspaces` 字段、`lerna.json`、`nx.json`、`turbo.json` | 视为单包 |
   | 真实依赖版本 | `package.json` → workspace catalog → lockfile | 不写版本号，只写依赖名 |
   | 后端配对 / API 前缀 | `.env*`、`vite.config.*` 的 `server.proxy`、`requestBaseURL`、拦截器目录 | **关键路径：先问用户再写**；问不到就不写，并在交付说明里列出待用户补充 |
   | 加解密 / 鉴权方式 | `.env*` 开关 + `src/utils/http/*` + 登录 API | 同上 |
   | 应用装配 | `index.html`、`src/main.ts`、`bootstrap.ts`、`app.vue` | 从 `package.json` 的入口和构建配置反推 |
   | 目录职责 | 顶层 `ls` + `src/*` 2-3 层 `find` | 目录树本身即结论，不套别的项目的结构 |
   | 已有文档 | `README*`、`.docs/*`、`docs/*`、`changelog.md` | **缺失是常态**；有则交叉验证，与代码冲突以代码为准 |

2. **跑采集清单**（§3），逐格填事实，并同步产出 §4 的三段固化结果。
3. **盘点可复用能力**：按采集清单「全局公共组件」「业务共享组件（views 层）」「跨模块复用做法」「公共 hooks / 工具」四行成表，再挑参考页——规则的价值一半在于「禁止重复造」。
4. **选参考页**：1 个标准单表页、1 个复杂业务页、1 个树/分类页（缺失就退到「最典型的列表页 + 详情页」），完整读它们的页面 / 搜索 / 弹窗 / 列定义 / API / 类型文件。这 3 组页面决定模版里所有代码骨架示例。
5. **填模版**：复制 `templates/`（入口 `rule-entry.md` + `references/` 三册）到工具的规则目录（见步骤 7，落地时按 `SKILL.md` 改名），在入口和三个分册里替换全部占位符，删除未使用的 `（按需保留）` 分支与所有 `<!-- 填写指引 -->` 注释，并补上该工具的规则头（见步骤 7 表）。**章节标题保留**（见探测约定 4）。
6. **反向校验**：随机挑 2 个未参与采集的业务模块，检查规则能否直接解释它们的写法；对不上就改规则，不改代码。
7. **确认落地方式**（先问用户用哪个编辑器/Agent，不要默认）：

   | 工具 | 规则位置 | 规则头 |
   | --- | --- | --- |
   | Qoder | `.qoder/rules/`（子目录递归加载），仓库根 `AGENTS.md` 也被识别 | frontmatter `trigger:` 取 `always_on` / `model_decision` / `glob` / `manual`；`glob` 需配 `globs:` |
   | Trae | `.trae/rules/project_rules.md` | 以当前版本文档为准 |
   | Cursor | `.cursor/rules/*.mdc` | `alwaysApply` / `description` + `globs` |
   | 通用（多工具共用） | 仓库根 `AGENTS.md` | 无 frontmatter，纯正文 |

   路径与字段随工具版本变化，落地前与用户确认当前项目实际在读哪个目录；
   落地后做一次自检：被 `always_on` 加载的规则会出现在上下文里，据此确认头部写对了。

   **已落地示例（sinosite_admin，Qoder）**：

   ```
   .qoder/rules/
   ├── coding-posture.md          trigger: always_on —— §5 通用编码姿态（跨项目原样）
   ├── frontend.md       trigger: glob(src/**) —— 入口，§5 只留本项目具体化 + 指回姿态规则
   └── references/                trigger: manual —— 只有入口 §7 索引点名时才读
       ├── api-types.md
       ├── page.md
       └── components-style.md
   ```

   `trigger: glob` 未生效（版本差异）时，把入口那行改成 `trigger: always_on` 即可，内容不用动。

   **文件名跨项目固定**（`coding-posture.md` / `frontend.md` / `references/{api-types,page,components-style}.md`），
   不要把项目名写进文件名：入口里的分册路径、README 的落地说明、模版头部的示例才都能保持一份通用写法，
   换项目只替换正文内容。项目名只出现在正文（标题、基线、规则 `description:`）里。

   规则分两类放置：
   - **通用编码姿态**（与项目无关，如模版入口 §5 懒惰阶梯 / 修根因 / 不可妥协项）→ 单独一个 always_on 规则文件，
     让它在所有任务里生效，例：`.qoder/rules/ponytail.md`，frontmatter 写 `trigger: always_on`。
   - **项目专属约定**（技术栈、目录、命令、组件清单）→ 项目规则文件；只在相关任务里读，避免占用通用任务的上下文。

8. **按项目体量收敛文件数**（模版默认已拆好，这里是退化路径）：
   - 项目小 / 技术栈单一 / 任务类型单一 → 把三个分册并成一册 `references/detail.md`，入口索引跟着改；
   - 某册填完没有内容（如无表格增强库、无树页）→ 删掉该册，并删掉入口索引里指向它的所有行；
   - 新增能力域（图表大屏、工作流、多步表单）且已有内容明显超出原册职责 → 再加一册，**不要往入口塞**。
   - 交付前逐行核对入口索引：每条 `references/<file>.md §n` 都能在被引文件里找到对应标题，指不到的要么补内容要么删索引。

## 二、探测策略（采集清单通用规则）

1. **候选文件名 glob**：同一采集项准备 2-4 个候选路径，按社区惯例顺序尝试。
   例：格式配置 → `.prettierrc*` / `prettier.config.*` / `package.json:prettier` / `.editorconfig`；
   请求封装 → `src/utils/http` / `src/axios` / `src/api/request*` / `src/plugins/request*` / `src/lib/http*`。
2. **按依赖反查**：`package.json` 里有没有对应依赖（`element-plus` / `antd` / `naive-ui` / `vxe-table` / `@tanstack/vue-query` / `alova` / `unocss`…）。
   **没有依赖 = 项目没有该能力**，直接标「不适用」，不要描述不存在的组件或 hook。
3. **按符号 grep**：候选路径都不存在时，搜关键标识（`hasPermi` / `v-access` / `useVbenForm` / `defineStore` / `$t(` / `upload`），定位真实实现与调用点。
4. **缺失处理约定（重要）**：
   - 采集项在该项目**不存在** → 实例里该章节保留标题，正文写 `不适用：本项目没有 X（依赖中无 / 无调用点）`，并在「禁止事项」补一条「不要引入 X」。
   - 采集项**概念在、封装不在**（组件库或框架自带该能力，但项目没有一层封装）→ 不是「不适用」，判 §3.1 的 **B 档**，写清裸用写法并禁止新增封装。
   - 采集项**存在但与主流不同** → 记为该项目约定，并加一句「不要套用通用写法」。
   - 采集项**没找到、但看起来应该有** → **规则正文里不写它**（不写「未确认」这类占位）。
     需要用户拍板的关键项（请求出口、权限写法、API 前缀、命令名）当场问；问不到就在交付说明里列出待补充，而不是塞进规则文件。
   - 规则正文只保留两类结论：**确认存在**（写约定 + 证据）与**确认不存在**（写「不适用」并进禁止事项，用于阻止 AI 引入）。
     「未确认 / 待确认」属于会话状态，不进入长期上下文——它会诱导 AI 自行补假设，并降低整份规则的可信度。
   - 需要留痕时写到独立的临时文件（如 `open-questions.md`），不混进规则包。
5. **不要跨项目照搬**：其他项目（如 plus-ui/Element Plus 版）的 hook 名、指令名、类型入口只作提问线索，不得直接写进本项目的规则。

## 三、采集清单

「找不到时」列为降级动作；缺失按上面第 4 条处理。

| 采集项 | 优先看 | 找不到时 | 要得到什么 |
| --- | --- | --- | --- |
| 技术栈与版本 | `package.json`、workspace `catalog:`、lockfile | 只有 lockfile 时以 lockfile 为准 | 框架/UI 库/表格/状态/路由/HTTP/i18n 的**真实版本号** |
| 环境要求 | `engines`、`packageManager`、README | 由 lockfile 版本头推断 pm；Node 需求看 CI 的 `node-version` | Node 与包管理器强制策略 |
| 命令 | `package.json scripts` | monorepo 再看 `turbo.json`/`nx.json` 与子包 scripts | dev/build/typecheck/lint/format 的**准确脚本名** |
| 格式基线 | `.editorconfig`、`.prettierrc*`、`eslint.config.*` | 都缺 → 从实际源码统计缩进/引号/分号，标「无配置文件，风格来自代码现状」 | 缩进、行宽、引号、分号、特殊禁止规则 |
| Lint 自定义规则 | `eslint.config.*` 与 `internal/lint-configs`、`@<org>/eslint-config` 包 | 无 → 写「不适用：无共享 lint 配置」 | 本项目特有的禁止项（如禁止自身 barrel） |
| 别名 | `tsconfig.json paths`、`vite.config.*` alias | 无 → 只支持相对路径，规则中写明 | 有哪些别名；有无**未定义却被使用**的别名（`grep -rn "from '#/" src`） |
| 自动导入 | `vite.config.*` 的 unplugin-auto-import / unplugin-vue-components、`components.d.ts`/`auto-imports.d.ts` 是否存在 | 无 dts 文件 = 未启用 → 规则写「全部显式 import」 | 哪些必须显式 import，全局组件在哪注册 |
| **全局公共组件** | `ls src/components`（或 `src/widgets`、`packages/ui`）、其 barrel、注册函数 | 无 → 写「不适用：无公共组件层，业务代码直接用 UI 库」 | 每个组件一句话职责；页面骨架必需件；必须显式 vs 全局可用 |
| **业务共享组件（views 层）** | `find src/views -type d -name components`；模块内 `helper.ts(x)`、`type.d.ts`、`index.ts` | 无 → 写「不适用：无跨页面共享组件」 | 哪些组件在同业务域被多页面复用及其导出入口 |
| **跨模块复用做法** | `grep -rn "from '@/views/" src` | 无命中 → 写「本项目不跨模块引用 views」 | 是否允许直接引用其他 views 文件；「提升到 components 还是就地引用」的判据 |
| **公共 hooks / 工具** | `src/hooks`、`src/composables`、`src/utils` barrel、`src/core/composables` | 无 → 写「不适用」 | 现成组合式函数与工具清单（优先复用，别重写） |
| 请求层 | `src/utils/http/*`、`src/api/helper.ts`、`src/plugins/request*` | 按依赖判断：无 alova/axios 时看 `fetch` 封装位置 | 实例名、方法族、响应拆包规则、错误/401 处理、序列化、加密开关、下载 helper |
| 公共类型 | `src/api/common.d.ts`、`src/types/*` | 无 → 类型写法退化为「跟随相邻文件」 | `ID/IDS/PageQuery/PageResult/BaseEntity` 之类入口与字段 |
| API 写法 | 任一 `src/api/<mod>/<biz>/index.ts` | 无独立 api 目录 → 看页面内 `service`/`repository` 层 | 常量声明方式 / 函数命名 / 泛型位置 / params 与 data 传法 |
| 类型写法 | 同目录 `model.d.ts`/`types.ts`/`interface.ts` | 无 → 记「类型写在页面/API 文件内」 | 接口命名、是否继承基类、日期与数值映射 |
| 表格方案 | `src/components/vxe-table` 等封装、UI 库 Table 用法 | **见 §3.1**：A 自研封装 / B 增强库裸用 / C 组件库 Table / D 无表格形态 | 默认配置合并函数、数据获取模式（proxy/request）、分页排序列显隐约定 |
| 查询编排 | `useTableQuery` 之类 hooks，`grep -rn "commitProxy"` 等 | **见 §3.1**：A hooks / B 表格 proxy / C 页面自管 / D 无分页 | 搜索条件如何进入查询、刷新语义 |
| 弹窗体系 | 组件 barrel、`core/ui/popup`、`useModal/useDrawer` | **见 §3.1**：A 封装 hook / B 组件库弹层就地控制 / C 路由页或行内编辑 | Modal/Drawer API 名称与生命周期钩子 |
| 表单写法 | 任一 `*-drawer.vue`/`*-modal.vue`/`*-form.vue` | **见 §3.1**：A schema 驱动 / B 手写 Form / C 无独立表单层 | schema 驱动 or 手写 Form；校验规则类型；脏检查方案 |
| 搜索区 | 任一 `*-search.vue`/`*-filter.vue`/`SearchForm` | **见 §3.1**：A 独立组件+契约 / B 内联在列表页 / C 无搜索（树、卡片、详情直出） | 栅格类、折叠、暴露契约、按钮组组件 |
| 字典 | `grep -rn "getDictOptions"`、`grep -rn "useDict"` | **见 §3.1**：A 后端字典层 / B 前端枚举常量 / C 无字典概念 | 取选项 API、枚举常量、列渲染、组件名 |
| 权限 | `grep -rn "v-access"`、`grep -rn "hasPermi"`、`grep -rn "useAccess"` | **见 §3.1**：A 指令+函数 / B 仅路由守卫 / C 无前端权限 | 指令名与参数形式、函数式判断、超管通配符 |
| i18n | `src/locales/*`、`grep -rn "\$t(" src \| head` | 依赖无 i18n → 记「不适用：无国际化」 | key 组织；哪些文案走 `$t`、哪些直接写中文 |
| 路由 | `src/router/*`、菜单/权限生成逻辑 | 无 router 目录 → 记「单页/嵌入式场景」 | 静态 vs 动态来源、新页面是否要注册、`meta` 支持字段 |
| 样式 | `tailwind.config*`/`uno.config*`/`src/styles/*`、页面 class 用法 | 全无 → 记「仅组件库样式 + scoped CSS」 | 工具类方案；主题 token 来源；类名合并函数 |
| 能力样例 | 上传 / 导入导出 / 富文本 / 加密请求 / 图表 各找一个真实调用点 | 依赖里没有 → 标「不提供该能力，AI 不得生成相关代码」 | 组件或函数名 + 文件路径 |
| 全局对象 | `types/*.d.ts`、`src/bootstrap.ts`、`app.config.globalProperties` | 无 → 记「用组件库函数式 API」 | `window.modal` / `window.message` 之类是否可用 |
| 已知偏差 | 扫可疑 import、缩进统计、`git status` 前后对比 | 无偏差 → 明确写「未发现系统性偏差」 | 「历史遗留但新代码禁止」清单，并注明历史文件不顺手重排 |

### 3.1 骨架能力的档位判定（没有封装、甚至框架没这个概念时怎么写规则）

表格、弹窗、字典这几项直接决定页面骨架长什么样。**只写「不适用：本项目没有 X」是不够的**——
那样 AI 遇到「列表加一列状态」就没有可执行路径，转头自己造一层封装或引入新依赖。
每一项要判到具体档位，并把**该档位的真实代码**写进规则当骨架。

| 能力 | A：项目有自研封装 | B：无封装、能力在（组件库 / 框架自带） | C：框架或项目没这个概念 |
| --- | --- | --- | --- |
| 表格 | 默认配置合并函数 + 插槽约定（如 `withDefaultVxeGridOptions`） | 增强库裸用 `<vxe-grid :columns :data>`，或 UI 库 `Table` + `columns` 数组 | 无表格形态：卡片流 / 虚拟列表 / 树 → 规则贴对应的列表实现 |
| 查询编排 | `useTableQuery` 类 hooks + 搜索表单契约 | 表格自带 `proxyConfig` / `request` | 页面自管 `loading` + `pagination` ref + `onMounted` 请求；后端不分页 → 全量拉取 + 前端筛选 |
| 弹窗体系 | `useModal/useDrawer({ connectedComponent })` + `setData/open/lock/emit('reload')` | 组件库 `Modal/Drawer` + `v-model:open`（或 `visible`）就地控制 | 无弹层：独立路由页 / 行内编辑 / 展开行 → 规则写明「新增编辑去哪个页面」 |
| 表单 | schema 驱动（`useVbenForm`、formCreate、自研 schema） | 手写 `Form` + `rules` + `validate()` + `getDefaultValues()` | 无独立表单层：表单写在页面内，或 JSON / 富文本编辑器 |
| 字典 | 后端字典 API + store 缓存 + 取选项函数 + 列渲染函数/组件 | 前端枚举常量：`src/constants/*` 或就近 `options` 数组，文案在列定义里映射 | 无字典概念：后端直接返回中文，状态字段是自由文本 |
| 权限 | 指令 + 函数双轨（`v-access` / `hasPermi` / `useAccess`） | 仅路由守卫、按钮全放行 → 规则说明「按钮无需权限包裹」 | 无前端权限（后端接口鉴权）→ 规则禁止生成任何权限指令代码 |

判档规则（自上而下）：

1. **≥3 处调用点**才算该档现状。只有 1-2 处多半是残留或刚引入的少数派 → 主流档位按被用得最多的那种写，少数派记进「现状偏差」。
2. 依赖里有增强库、但全仓没有一处封装或默认配置 → 判 **B**：规则要给出该库的最小可用写法（分页、排序、列显隐分别怎么写），并明确**禁止再造一层封装**。
3. 依赖没有 + 调用点也没有 → 判 **C**：规则必须同时给出**替代做法**（常量文件 / 就地硬编码 / 路由页），不能只留「不适用」一行。
4. 档位要三处传导，缺一处规则就失效：
   - 入口 §4 速查：一句话写清档位与代表 API 名；
   - 分册示例：贴该档位在本仓库某个真实页面里的代码，不贴通用最佳实践；
   - 入口 §9 禁止事项：A 档 → 禁止绕开封装裸写；B 档 → 禁止新增封装或依赖；C 档 → 禁止引入该概念（例：「不要写 `getDictOptions`，本项目无字典层」）。
5. **自检**：拿最小需求「列表加一列状态并支持筛选」按当前档位走一遍。若只能得出「不适用」而答不出「改哪个文件的哪一段」，说明 C 档缺替代写法，回去补。

## 四、三段固化产出（必须成表，供模版 §2/§3/§4 直接消费）

采集结束后先落这三段，再写细则。三段是实例里最先被 AI 读到的部分，用于把「在哪找、跑什么、守什么」一次说清。

**A. 关键文件和目录** —— 每行：路径 | 作用 | 什么时候必须读

```
| src/utils/http/index.ts | 请求实例、拦截器、加解密、错误处理 | 写任何 API 前 |
```

必须覆盖：依赖与脚本清单、构建配置、格式/lint 配置、别名与 tsconfig、环境变量与代理、
请求与公共类型入口、组件 barrel 与全局注册、表格/弹窗/表单/字典/权限/路由/i18n 的实现位置、
参考页面（标准单表 / 复杂页 / 树表）、代码生成器位置。缺失项写「不适用：<查过哪里>」。

**B. 构建与开发命令** —— 每行：目的 | 实际命令 | 备注

必须覆盖：装依赖（含包管理器强制、monorepo 加依赖方式）、开发启动（端口、代理）、
类型检查、lint、格式化（单文件用法）、各环境构建、预览、以及**改动某类文件后必须跑哪几条**。
脚本名必须逐字来自 `package.json`，不得写成"通用惯例"命令。

**C. 重要约定（TL;DR 速查）** —— 8-20 条一行式硬约定，每条可直接判对错

覆盖：别名与 import 策略、请求唯一出口、响应是否已拆包、分页结构、页面文件四件套、
表格必备配置、搜索表单契约、表单是 schema 还是手写、权限写法、字典写法、i18n 边界、
缩进与引号、验证最低门槛、已知的"禁止引入"清单。
每条后面标注**证据来源路径**，让读者可复核。

## 五、填写原则

- **事实优先**：每个结论都能指向一个文件或一行代码；没读到的**不写**（不写「未确认」占位，更不猜测）。
- **基线来自工程实测**：git 可能缺远端、缺提交，配置可能没有——按候选顺序降级，而不是跳过。
- **先盘复用**：公共组件、业务域共享组件、跨模块引用现状、公共 hooks 都要成表。
- **区分约定与遗留**：仓库存在但不推广的写法，写进禁止事项，并说明历史文件保持原样。
- **可裁决**：保留「规则优先级」章节，冲突时有明确裁决顺序。
- **可验证**：验证矩阵按改动范围给命令，命令名与实际 scripts 一致。
- **不越界**：规则只约束实现方式与自检范围，实际代码冲突时以目标模块最近似实现为准。
