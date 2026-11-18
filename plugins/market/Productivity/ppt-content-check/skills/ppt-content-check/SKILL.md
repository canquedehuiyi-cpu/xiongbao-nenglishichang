---
name: ppt-content-check
description: 用于汇报材料提交前的数字核对:当用户给出 PPT 大纲文本或 .pptx 文件并附上源数据表时使用,逐数字回源对账,每个数字给出单元格出处或点名「无出处」;不改
  PPT,不猜对应关系
---
# PPT 内容核对

> 本文件是技能的对外契约(指令式)。发布前三平台的 manifest/description 均以本文件为源。
> 依赖声明走 frontmatter dependency(官方位);不要另建 build/requirements.txt。

## 何时使用

用于演示/汇报材料提交前:用户粘贴 PPT 大纲文本（每页文字）或给出 .pptx 文件，
并提供源数据表 CSV，本技能逐数字对账——每个数字要么在源表找到出处（带单元格定位），
要么点名「无出处」。不改 PPT、不猜对应关系；数字抄错/过期当场现形。

## 执行步骤

1. 确认输入：优先直接给 .pptx 文件；没有文件时粘贴每页大纲文本（二选一）。
   源数据表 .csv（首行可为列名）。指标缩写与数字之间请带空格（「GMV 68 万」），
   紧贴写法（GMV68万）会被当编号排除。
2. 运行本地确定性引擎。**路径基准:本 SKILL.md 所在目录 = 技能根**，
   宿主不预设工作目录，请先在命令行切换到本文件所在的技能根目录，再执行:

   ```bash
   python ./scripts/engine/main.py run --scenario ppt-content-check --json --task check --set pptx-file="PPT 文件的绝对路径" --set source-file="源表 CSV 的绝对路径"
   ```

   任务契约探测:`python ./scripts/engine/main.py tasks --scenario ppt-content-check --json`
   环境自检(退出码 0=正常):`python ./scripts/engine/main.py selfcheck`
3. 读 stdout 严格 JSON:以 `state` / `artifacts` / `issues` 为准向用户转述。
4. 宣称"已生成"前核对 artifacts 文件真实存在;报错原样转告,不猜不改输入。

## 异常与降级

- 引擎入口不可用（缺依赖、脚本报错、契约探测无响应）时:停止对账，把错误原样转告用户，
  并指引其先运行 selfcheck 排查；在引擎未实际运行前，不给出任何数字核对结论。
- .pptx 解析不出文本（加密/损坏/扫描版）时:降级为请用户粘贴每页大纲文本，不猜测页内文字。
- 源表缺列、口径对不上或数字无出处时:如实列入「无出处」清单转人工，不强行配平。

## 运行环境

- Python 3.10+;依赖见上方 frontmatter(首次使用先 pip install)。
- 推荐先设置环境变量 LOCAL_FLOW_DIST_ROOT 指向一个可写目录再运行,产物不落在插件目录内。

## 判据引用

本文件不复述判据值域与阈值,以下文件是唯一事实源:

- 域判据骨架(证据优先级 / 域裁决规则 / 反模式):@references/EVALUATION_CRITERIA.md

## 红线（不要做的事）

- 结论只认引擎报告;待人工项(冲突/不可比/未解析)如实转告用户。
- 引擎零 LLM 调用、零网络:宿主只整理输入与转述结论,不替引擎下判定。
- 不编造出处、不猜数字与指标的对应关系;判定不了就转人工。
