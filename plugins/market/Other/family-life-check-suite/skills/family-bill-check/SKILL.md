---
name: family-bill-check
description: 每月账单日使用：把家庭成员微信、支付宝、银行卡各渠道的月度流水贴进来，合并勾稽出漏记、重复记、同一会员两边都在扣、异常大额与分摊对不上的项。只需要金额/日期/摘要/成员代号，卡号姓名先隐掉；判定不了的行如实标待人工。
user-invocable: true
---
# 家庭多渠道账单核对

一个人一个支付渠道，一个家 N 本账。这个工具把各渠道流水合成一本，替你找对不上的地方。

## 输入是什么样

各渠道导出的流水文本，粘贴即可；家庭成员用代号 A/B/C。卡号、姓名、卡尾号先删掉再贴——本核对只看金额、日期、摘要和成员代号。

## 三步走

1. **脱敏**：按上面的口径清理流水。
2. **粘贴跑引擎**（在本文件所在目录执行）：

   ```bash
   python ./scripts/engine/main.py run --scenario family-bill --json --task check --set text="「账单流水」"
   ```

   输入契约探测：`python ./scripts/engine/main.py tasks --scenario family-bill --json`
   自检（退出码 0 再跑）：`python ./scripts/engine/main.py selfcheck`
3. **读结果**：只认 stdout JSON 的 `state` / `issues` / `artifacts`；说"已生成"前核对 artifacts 文件确实存在。

Python 3.10+，依赖在页首声明；建议设 `LOCAL_FLOW_DIST_ROOT=「可写目录」`，产物不落插件目录。

## 结果里找什么

漏记/重记、同一会员多渠道重复扣、异常大额、分摊勾稽差异。阈值与值域不在本页——唯一事实源：@references/EVALUATION_CRITERIA.md。

## 规矩

不代改输入（格式不对就报错请用户修）；两侧不可比、对不齐的行标 UNKNOWN/REVIEW 转人工，不编数值；引擎零 LLM、零联网，判定权在引擎。
