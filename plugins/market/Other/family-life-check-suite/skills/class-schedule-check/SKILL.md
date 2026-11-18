---
name: class-schedule-check
description: 适用场景:当收到新机构课表要排周课时。对多个兴趣班的课表与接送安排做核对,查上课时间冲突、地点衔接不足、接送人撞车与请假补课错档,输出冲突清单;适合给孩子报了多个班、每周要排场的家长。各机构课表/群通知粘贴即可,先删掉孩子姓名班级。
user-invocable: true
---
# 兴趣班排期核对

> 本文件是技能的对外契约(指令式)。发布前三平台的 manifest/description 均以本文件为源。
> 依赖声明走 frontmatter dependency(官方位);不要另建 build/requirements.txt。

## 何时使用

当用户要做「兴趣班排期核对」时:粘贴文本做确定性核对,出带判据编号的问题清单。

**脱敏粘贴指引(先做这一步)**:删除孩子姓名班级,机构名可保留。

## 使用方法(执行步骤)

1. 确认输入是文本层文件;扫描件/截图请用户先转文本层,残余未解析行一律转人工。
2. 运行本地确定性引擎。**路径基准:本 SKILL.md 所在目录 = 技能根**,命令相对该目录执行(宿主不预设工作目录,请先按本文件实际位置 cd):

   ```bash
   cd 到本 SKILL.md 所在目录(即技能根)
   python ./scripts/engine/main.py run --scenario class-schedule --json --task check --set text="「课表文本」"
   ```

   任务契约探测:`python ./scripts/engine/main.py tasks --scenario class-schedule --json`
   环境自检(退出码 0=正常):`python ./scripts/engine/main.py selfcheck`
3. 读 stdout 严格 JSON:以 `state` / `artifacts` / `issues` 为准向用户转述。
4. 宣称"已生成"前核对 artifacts 文件真实存在;报错原样转告,不猜不改输入。

## 运行环境

- Python 3.10+;依赖见上方 frontmatter(首次使用先 pip install)。
- 推荐设置 `LOCAL_FLOW_DIST_ROOT=「可写目录」` 再运行,产物不落在插件目录内。

## 判据引用

本文件不复述判据值域与阈值,以下文件是唯一事实源:

- 域判据骨架(证据优先级 / 域裁决规则 / 反模式):@references/EVALUATION_CRITERIA.md

## 不要做什么

- 不替用户改输入:格式不对、缺字段、扫描件未转文本层——原样报错并请用户修正。
- 不在无证据时下结论:判定不了、两侧不可比、单位不一致,一律标 UNKNOWN/REVIEW 转人工。
- 不编造数值、来源与完成状态;结论只引用引擎报告里的字段。

## 红线

- 结论只认引擎报告;待人工项(冲突/不可比/未解析)如实转告用户。
- 引擎零 LLM 调用、零网络:宿主只整理输入与转述结论,不替引擎下判定。
- 不编造值;判定不了就转人工。
