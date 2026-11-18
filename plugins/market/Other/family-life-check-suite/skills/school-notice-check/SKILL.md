---
name: school-notice-check
description: 家长群 99+ 之后使用：把刷屏的聊天记录整段贴进来，老师真正提的要求——截止时间、要带的东西、缴费、接龙——被提取成一张清单，顺带标出时间撞车的和已经过期却还在被转发的通知。粘贴前删掉其他家长的昵称，只留正文。
user-invocable: true
---
# 家长群通知要求核对

老师的话淹没在"收到"和接龙里。这个工具把整段群聊变成一张干净的要求清单。

## 群消息太吵？这样用

把家长群的聊天记录整段复制粘贴进来就行——不用自己先挑。它负责从里面把要求挑出来。

## 先清理粘贴内容

删掉其他家长的昵称、头像名，只留消息正文（尤其是接龙楼里的正文）。截图请先转成文字，转不出来的行会被如实标"待人工"。

## 执行

在本文件所在目录执行：

```bash
python ./scripts/engine/main.py run --scenario school-notice --json --task check --set text="「家长群消息文本」"
```

输入契约探测：`python ./scripts/engine/main.py tasks --scenario school-notice --json`
自检（退出码 0 再跑）：`python ./scripts/engine/main.py selfcheck`

Python 3.10+，依赖见页首；建议设 `LOCAL_FLOW_DIST_ROOT=「可写目录」`，产物不落插件目录。

## 输出一张要求清单

截止时间 / 带物 / 缴费 / 接龙逐条列出；同一天同一时间撞车的标冲突；已经过期却还在群里被转发的通知会点名提醒。相对日期按基准日期推算并标明，推不出的不硬猜。

## 原则

结果只认 stdout JSON 的 `state` / `issues` / `artifacts`（"已生成"前核对文件真实存在）；闲聊行不臆造要求；识别不出的标 UNKNOWN/REVIEW 转人工；判据唯一事实源：@references/EVALUATION_CRITERIA.md；引擎零 LLM、零联网。
