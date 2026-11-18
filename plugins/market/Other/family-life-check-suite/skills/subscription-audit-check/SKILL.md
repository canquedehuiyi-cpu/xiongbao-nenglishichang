---
name: subscription-audit-check
description: 觉得这个月扣费变多了，或想把全家订阅盘一盘的时候触发：微信/支付宝/Apple 各渠道的自动续费流水贴进来，同一会员重复扣、悄悄涨价、早就不看却还在扣的僵尸订阅、异常大额，逐条翻出来带判据编号。只要日期+服务名+金额（+渠道），卡号姓名不用贴。
user-invocable: true
---
# 会员订阅体检

订阅这件事的麻烦在于"忘了"。这个工具把散在各渠道的续费流水合起来看，专门翻出那些你早就忘了还在扣钱的。

## 什么时候值得跑一次

- 账单日前后，想核对这月扣了什么；
- 想清理僵尸订阅（试完忘了取消的那种）；
- 换机/换支付方式前后，怕有订阅跟丢。

## 流水怎么贴

各渠道账单里"自动续费/订阅"类的条目，保留**日期 + 服务名 + 金额（+渠道）**。卡号、姓名、卡尾号删掉——本核对不消费身份字段。

## 跑起来

在本文件所在目录执行：

```bash
python ./scripts/engine/main.py run --scenario subscription-audit --json --task check --set text="「扣费流水文本」"
```

输入契约探测：`python ./scripts/engine/main.py tasks --scenario subscription-audit --json`
自检（退出码 0 再跑）：`python ./scripts/engine/main.py selfcheck`

Python 3.10+，依赖见页首；建议设 `LOCAL_FLOW_DIST_ROOT=「可写目录」`。

## 它会翻出来的四类问题

同一会员重复扣、比上期涨价、连续扣费的僵尸订阅、大额扣费。判定标准不在本页——唯一事实源：@references/EVALUATION_CRITERIA.md。

## 底线

结果只认 stdout JSON 的 `state` / `issues` / `artifacts`（"已生成"前核对文件真实存在）；不代改输入；认不出的行标 UNKNOWN/REVIEW 转人工；引擎零 LLM、零联网，只比对不推荐"该退哪个"。
