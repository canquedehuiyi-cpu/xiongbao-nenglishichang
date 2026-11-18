---
name: weekly-report-check
description: 用于周报提交前的体检:当用户粘贴写好的周报全文（可附上周周报）时使用,点名无负责人、无期限的待办和没有数字支撑的空转进展句,逐条带行号定位;不改写原文,不评文风
---
# 周报体检

> 本文件是技能的对外契约(指令式)。发布前三平台的 manifest/description 均以本文件为源。
> 依赖声明走 frontmatter dependency(官方位);不要另建 build/requirements.txt。

## 何时使用

用于周报提交前（每周固定动作）:用户把写好的周报全文粘贴进来（可选再给上周周报，
不给则用上次运行存档的待办做呼应对比，首次使用建议给），挑出无负责人、无期限的待办和
没有任何数字、没有交付物的空转进展句，逐条带行号定位。不改一个字，只点名——
生成周报是平台自己的活，本技能管「写出来的经得起领导追问」。

## 执行步骤

1. 确认输入是周报全文文本(粘贴);节名(本周工作/下周计划等)对不上时,在
   `scripts/scenarios/weekly_report_check/assets/pro/templates/rules.yaml` 的清单里加词即可,不需要改代码。
2. 运行本地确定性引擎。**路径基准:本 SKILL.md 所在目录 = 技能根**，
   宿主不预设工作目录，请先在命令行切换到本文件所在的技能根目录，再执行:

   ```bash
   python ./scripts/engine/main.py run --scenario weekly-report-check --json --task check --set report-text="周报全文" --set last-report-text="上周周报全文,可选"
   ```

   任务契约探测:`python ./scripts/engine/main.py tasks --scenario weekly-report-check --json`
   环境自检(退出码 0=正常):`python ./scripts/engine/main.py selfcheck`
3. 读 stdout 严格 JSON:以 `state` / `artifacts` / `issues` 为准向用户转述。
4. 宣称"已生成"前核对 artifacts 文件真实存在;报错原样转告,不猜不改输入。

## 异常与降级

- 引擎入口不可用（缺依赖、脚本报错、契约探测无响应）时:停止体检，把错误原样转告用户，
  并指引其先运行 selfcheck 排查；在引擎未实际运行前，不给出任何周报结论。
- 周报节结构认不出来时:不硬套规则，如实告知用户无法解析的节名并转人工处理。

## 运行环境

- Python 3.10+;依赖见上方 frontmatter(首次使用先 pip install)。
- 推荐先设置环境变量 LOCAL_FLOW_DIST_ROOT 指向一个可写目录再运行,产物不落在插件目录内。

## 判据引用

本文件不复述判据值域与阈值,以下文件是唯一事实源:

- 域判据骨架(证据优先级 / 域裁决规则 / 反模式):@references/EVALUATION_CRITERIA.md

## 红线（不要做的事）

- 结论只认引擎报告;待人工项(冲突/不可比/未解析)如实转告用户。
- 引擎零 LLM 调用、零网络:宿主只整理输入与转述结论,不替引擎下判定。
- 不改写周报、不评价文风;不编造值;判定不了就转人工。
