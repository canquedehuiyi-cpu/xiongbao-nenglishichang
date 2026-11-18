---
name: homework-checklist-check
description: 孩子说作业写完了？把老师布置的要求、孩子报的完成清单各贴一段，逐项勾稽出缺漏：没写的、听读背诵签字这类最容易漏的、明天要带的东西。用于每晚查作业漏项，判定不了的行如实标待人工；不用孩子姓名班级，也不用拍作业本。
user-invocable: true
---
# 孩子作业清单核对

一句话：两段粘贴——老师要求的作业 + 孩子报的完成清单，逐项对出漏了什么。本地引擎判，不猜。

## 先做这步

只贴条目本身：不要孩子姓名班级；作业要求或清单是截图/扫描件，先转成文字，转不出来的行会被标"待人工"。

## 跑核对（在本文件所在目录执行）

```bash
python ./scripts/engine/main.py run --scenario homework-check --json --task check --set plan="「作业要求」" --set log="「完成清单」"
```

- 想先看这个技能接什么输入：`python ./scripts/engine/main.py tasks --scenario homework-check --json`
- 环境自检（退出码 0 才继续）：`python ./scripts/engine/main.py selfcheck`
- 需要 Python 3.10+，依赖见页首声明；建议设 `LOCAL_FLOW_DIST_ROOT=「可写目录」`，产物别落进插件目录。

## 读结果

只认 stdout 的 JSON：`state`、`issues`、`artifacts` 三个字段说了算。向用户说"已生成"之前，先确认 artifacts 里的文件真实存在；引擎报错原样转告，不猜不改输入。

## 它专门盯的坑

听读背诵签字类（最容易被"写完了"糊过去）、明日带物、要求里有但清单里没有的项。判据值域与阈值不写死在本页，唯一事实源：@references/EVALUATION_CRITERIA.md。

## 三条铁律

1. 不改输入：格式不对、缺字段、扫描件没转文字——报错请用户修正，不代改。
2. 不下无证据的结论：对不齐、两侧不可比、没解析出来，一律标 UNKNOWN/REVIEW 转人工。
3. 引擎零 LLM 调用、零联网：宿主只整理输入与转述结论，判定权在引擎。
