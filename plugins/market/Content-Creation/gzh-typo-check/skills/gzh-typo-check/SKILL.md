---
name: gzh-typo-check
description: 用于公众号推文发文前核对:当用户贴出推文全文要求查错字、标点、数字用法或广告法极限词时使用,也用于维护个人词典(加词/删词);逐条核对、每处修改都带依据
---
# 公众号发文前错字核对

> 本文件是技能的对外契约(指令式)。发布前三平台的 manifest/description 均以本文件为源。
> 依赖声明走 frontmatter dependency(官方位);不要另建 build/requirements.txt。

## 何时使用

用于用户贴出推文全文要"发文前核对/查错字/查极限词",或要"把这个词加入词典/别再报"时,
按以下步骤执行。

## 主流程:发文前核对(task=check)

1. 确认输入是文本层内容;扫描件/截图请用户先转文本,残余未解析部分如实告知不覆盖。
2. 运行本地确定性引擎。**路径基准:本 SKILL.md 所在目录 = 技能根**，
   宿主不预设工作目录，请先在命令行切换到本文件所在的技能根目录，再执行:

   ```bash
   python ./scripts/engine/main.py run --scenario pre-send-check --json --task check \
     --set text="推文全文" --set whitelist="临时白名单,逗号分隔,可选"
   ```

   任务契约探测:`python ./scripts/engine/main.py tasks --scenario pre-send-check --json`
   环境自检(退出码 0=正常):`python ./scripts/engine/main.py selfcheck`
3. 读 stdout 严格 JSON:硬错清单在 `outputs.report.hard`(条条带 spec_id 与依据),
   `outputs.report.uncovered` 是未覆盖声明,原样向用户转述。
4. **Host 段·软建议**(引擎管不了的语义层,由你补):
   - 通读推文原文,补充**软建议**:语病、冗余、搭配不当、「的/地/得」;
   - 每条软建议**必须标注「建议」档**,不得写成"错误",不得编造国标/法规依据
     (依据只有引擎清单里的才是真的);
   - 你不得改动引擎的硬错判定:不多报、不漏报、不改判。
5. 按 `scripts/scenarios/pre_send_check/assets/pro/templates/report_template.md` 的格式生成**一次**《发文前核对报告》
   (两档:硬错/建议 + 未覆盖声明)。报告只在这一步出,中途不泄结论。
6. 用户对某条说"这个词没问题/是我们的品牌名"时:

   ```bash
   python ./scripts/engine/main.py run --scenario pre-send-check --json --task dict \
     --set action=add --set words="要加入词典的词条"
   ```

   加入成功即告知用户"已加入个人词典,以后不再报"。

## 个人词典管理(task=dict)

- `action=list` 列出当前词典;`action=remove` 删除词条(删除后该词恢复报告)。
- 词典文件:`~/.gzh-typo-check/dictionary.txt`,一行一词,用户可用记事本直接编辑;
  本地存储,零上云。
- 词典损坏时引擎会降级(报告里带 WARN,只用临时白名单),如实转告用户,别替它修。

## 演示路径(30 秒体验)

把 `scripts/scenarios/pre_send_check/assets/demo/翻车样例.txt` 的内容作为 text 跑主流程
——一篇 15+ 处硬错的典型推文,五类规则全命中,用于快速体验完整闭环。

## 异常与降级

- 引擎入口不可用（缺依赖、脚本报错、契约探测无响应）时:停止核对，把错误原样转告用户，
  并指引其先运行 selfcheck 排查；在引擎未实际运行前，不给出任何错字核对结论。
- 个人词典损坏时引擎降级为只用临时白名单（报告带 WARN），如实转告用户，不替用户修复词典文件。
- 扫描件、截图等非文本层输入无法核对:请用户先转文本，未解析部分明确告知不覆盖。

## 运行环境

- Python 3.10+;依赖见上方 frontmatter(首次使用先 pip install)。
- 推荐先设置环境变量 LOCAL_FLOW_DIST_ROOT 指向一个可写目录再运行,产物不落在插件目录内。

## 判据引用

本文件不复述判据值域与阈值,以下文件是唯一事实源:

- 规范封闭清单(判定阈值/词表/依据):`scripts/scenarios/pre_send_check/code/specs.py`
- 域判据骨架(证据优先级 / 域裁决规则 / 反模式):@references/EVALUATION_CRITERIA.md

## 红线（不要做的事）

- **硬错条条有依据**:依据只出自引擎清单(specs.py 封闭库);无依据的修改建议
  只能进「建议」档,不得标"错误"。
- 软建议不冒充错误;判定不了就转人工。
- 引擎零 LLM 调用、零网络:宿主只整理输入、补软建议、转述结论,不替引擎下判定。
- 不编造值;宣称"已生成"前核对 artifacts 文件真实存在;报错原样转告,不猜不改输入。
