---
name: medication-schedule-check
description: 医嘱一段、家人实际吃药打卡一段，本地引擎逐条比对：该吃没吃的、一天吃了两次的、两次间隔太近的、不该同服的、疗程中途断掉的，全部点名带判据编号。用于每天早/晚（尤其爸妈异地、打卡发家人群之后）核对用药执行；只要药名和时间，不要病历和身份证号。
user-invocable: true
---
# 家庭用药打卡核对

两段话交给它：医生嘱咐怎么吃（医嘱计划），家人实际怎么吃的（打卡记录）。它只做比对，不下医嘱。

## 交给它两段话

- 第一段·医嘱：药名、频次、剂量、起止（如"氨氯地平 每早1片 5mg，连服30天"）。
- 第二段·打卡：实际服药的日期时间（如"11-03 早7:20 氨氯地平1片"）。

## 贴之前

只保留药名 + 日期 + 时间（+剂量）。病历、诊断、身份证号、就诊卡号一律不贴——本核对只消费这几个字段。

## 怎么跑

在本文件所在目录执行：

```bash
python ./scripts/engine/main.py run --scenario medication-check --json --task check --set plan="「医嘱计划文本」" --set log="「打卡记录文本」"
```

先看它接什么输入：`python ./scripts/engine/main.py tasks --scenario medication-check --json`
自检（退出码 0 再继续）：`python ./scripts/engine/main.py selfcheck`
Python 3.10+，依赖见页首；建议设 `LOCAL_FLOW_DIST_ROOT=「可写目录」`，产物不落进插件目录。

## 拿到结果怎么读

以 stdout JSON 里的 `state` / `issues` / `artifacts` 为准转述；说"已生成"前先确认 artifacts 文件真实存在。引擎报错原样转告。

## 查哪些问题

漏服、重复服药、间隔不足、同服禁忌、疗程断档。判定阈值不在本页——唯一事实源：@references/EVALUATION_CRITERIA.md。

## 边界

输入不代改（格式不对请用户修正）；对不上的行标 UNKNOWN/REVIEW 转人工，不猜；引擎零 LLM、零联网，宿主不替引擎下判定。
