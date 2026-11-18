# 设计令牌库（design_tokens 参考）

> 本文件为 `scripts/design_tokens.py` 的前置令牌说明，仅在用户选定 B/C 模板模式、需更细自由组合时加载。设计令牌由脚本前置为统一令牌库，Agent 按场景任选，**严禁手搓字体 / 配色 / 排版**——手搓 = 不可交付、不可复用。

## 自由组合（覆盖模板模式默认值）

- 配色族 `--palette`：
  - amber（琥珀金蓝）· red（红黑）· sky（天蓝）· teal（欧美 teal）· warm（暖橙）· ink（墨绿）· violet（紫灰）
- 字体族 `--font`：
  - hei（黑体 / 微软雅黑·现代商务）· song（宋体·报告书籍感）· kai（楷体·金句引文温暖感）· deng（等线·轻商务简净）
- 字号规格 `--scale`：
  - standard（标准商务）· compact（极简紧凑·留白多）· report（学术报告·正文略大行距宽）
- 序号系统 `--number`：
  - arabic（1. / 1.1. / 1.1.1.）· cn（一、/（一）/ 1））· circle（①②③）· none（无前缀极简）

## 层级尺寸自动分层

生成器按所选规格自动套用，无需手调：大标题 / 中标题 / 小标题 / 正文 / 核心句 / 注释 / 页码 各档字号不同，封面主标题最大、逐级递减、正文清晰可读；同一份产物里标题与正文尺寸明显分差，视觉才有层次。

## 模板模式 / 版本 / 用途文体（视觉风格 A–H、版本 1–7 在用户菜单可点选——**仅选 PPT 时弹**；用途文体 1–4 全格式可点选）

用户侧视觉风格编码 `A`–`H` 与内部模板模式令牌（`biz` / `lean` / `report` / `warm` / `red` / `sky` / `teal` / `violet`）的**映射硬表见 SKILL.md A0.5**；版本令牌（`standard` / `minimal` / `classic` / `premium` / `summary` / `course` / `data`，默认 `standard`）与文体令牌（`plain` / `speech` / `oral` / `card`，默认 `plain`）**均在 `references/mode-bc-guide.md` Step 3 / Step 4 明面可点选**（用户侧只见中文名与编码，内部令牌名一律不出现）。**内部令牌一律不得出现在用户菜单或对话正文中**——用户看到的只有编码加一句话说明。
