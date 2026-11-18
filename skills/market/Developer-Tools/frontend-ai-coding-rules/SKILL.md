---
name: frontend-ai-coding-rules
version: 1.0.0
description: Generate or refresh a project-specific AI coding rule pack for a Vue 3 frontend repository by measuring the real repo (package.json, lockfile, vite/tsconfig, ESLint config, actual call sites) and writing an entry rule plus references volumes into the project's rules directory. Use when the user asks to generate, fill, or update frontend AI coding rules / project rules / onboarding conventions for a frontend project. Do not use for ordinary feature coding in a project that already has rules.
description_zh: 通过实测目标 Vue 3 前端仓库生成该项目专属的 AI coding 规则包（入口规则 + references 分册），落在该项目的规则目录。用于「给这个前端项目生成/更新 AI coding 规则」；项目已有规则、只是正常写业务代码时不要用。
user-invocable: true
argument-hint: <目标前端仓库路径或当前项目｜要新建还是更新规则>
---

# 前端 AI Coding 规则生成器

给一个**具体的**前端仓库生成「AI coding 开发规则包」。规则的全部价值在于它描述的是**这个仓库的真实写法**——
版本、命令、路径、组件名一律实测得出，不写记忆中的版本，不套其他项目（例如 Element Plus 版后台）的约定。

产物形态：`入口规则（每次任务都读）+ references/ 分册（按任务类型才读）`。
入口必须保留「任务类型 → 读哪一册哪一节」索引表，否则分册永远不会被加载，细则等于白写。

## 何时用

- 新项目 / 接手老项目，需要一份让 AI 直接照着写的规则
- 已有规则与代码现状对不上，要重新采集刷新
- 生成器产出的代码和项目风格冲突，需要先立约定再改代码

不适用：后端 / 非 Vue 项目；只需要改某个页面逻辑的普通任务（那应该读项目里已有的规则，而不是再生成一份）。

## 流程（严格按顺序，前一步没落定不要往后写）

1. **确认落地工具与目录**（先问，不要默认）。Qoder → 目标项目 `.qoder/rules/`（子目录递归加载，
   仓库根 `AGENTS.md` 同样被识别）；其他编辑器见 `references/discovery.md` 步骤 7 的对照表。
   同时确认该项目是否已有规则文件——有则增量更新，不清空重写。
2. **跑基线探测**（`references/discovery.md` §一.1）：git 信息可能缺远端、缺提交，按候选链降级；
   **全部拿不到的那一项直接删掉，不写「未确认 / 待定」占位**。
3. **跑采集清单**（§三，28 项）：每项都要给出证据路径。公共组件、views 层共享组件、跨模块引用现状、
   公共 hooks / 工具这四行必须成表——规则的一半价值是「禁止重复造」。
4. **能力档位判定**（§3.1）：表格 / 查询编排 / 弹窗 / 表单 / 字典 / 权限逐项判 A（有自研封装）/
   B（无封装、组件库或框架自带）/ C（没这个概念）。C 档必须给出替代做法，否则 AI 遇到「列表加一列状态」
   会自己造封装或引入新依赖。
5. **先交三段固化产出**（§四：关键文件和目录 / 构建与开发命令 / 重要约定速查）给用户确认，再写细则。
6. **填模版落盘**：复制 `templates/` 内容到目标项目规则目录，替换全部 `{{占位符}}`，
   删除所有 `<!-- 填写指引 -->` 注释与未使用的 `（按需保留）` 分支。落地映射：
   - `templates/rule-entry.md` → `.qoder/rules/frontend.md`，头部 `trigger: glob` + `globs: src/**/*.{vue,ts,tsx,js,jsx,scss,css}`
     （glob 未生效就改成 `trigger: always_on`，内容不动）；
   - 入口 §5「编码姿态」整节拆成 `.qoder/rules/coding-posture.md`，`trigger: always_on`，跨项目原样复用；
     入口只留 §5.1 的项目具体化并指回它；
   - `templates/references/*.md` → `.qoder/rules/references/`，头部 `trigger: manual`；
   - 文件名跨项目固定，**不要把项目名写进文件名或目录名**，项目名只进正文标题、基线和 `description:`。
7. **反向校验**：随机挑 2 个未参与采集的业务模块，检查规则能否直接解释它们的写法；对不上就改规则，不改代码。

## 落盘后自检（在项目根目录跑）

```bash
# 1. 没有残留占位符与填写指引注释
grep -rn '{{\|填写指引' .qoder/rules && echo 'FAIL: 还有占位或注释' || echo 'OK: 已清空占位'
# 2. 入口每条分册索引都指向真实文件
grep -rho 'references/[a-z-]*\.md' .qoder/rules/frontend.md | sort -u | while read f; do test -f ".qoder/rules/$f" || echo "MISSING: $f"; done
# 3. 索引里的 §n 小节在被引分册里真实存在（逐条人工核对，或按下面两条命令比对）
grep -n '^## ' .qoder/rules/references/*.md
grep -n 'references/.*\.md` §' .qoder/rules/frontend.md
# 4. 命令逐字存在于 package.json scripts
python3 -c "import json;print('\n'.join(json.load(open('package.json'))['scripts']))"
```

规则里出现的每个文件路径都要 `test -f` 通过；`always_on` 的那份落地后会出现在上下文里，据此确认头部写对了。

## 只允许两类结论

- **确认存在** → 写约定 + 证据路径。
- **确认不存在** → 该章节保留标题写 `不适用：本项目没有 X（依赖中无 / 无调用点）`，并在「禁止事项」补一条「不要引入 X」。
- **探测不到** → 删掉该行/该条。长期上下文里的「待确认」会诱导 AI 自行补假设，并降低整份规则的可信度。
- 需要留痕的开放问题写到临时文件（如 `open-questions.md`），不混进规则包，交付说明里列出即可。
