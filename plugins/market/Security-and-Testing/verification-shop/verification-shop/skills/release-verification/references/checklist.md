# 发布前核对清单（逐项打勾用）

## A. 元数据与结构

- [ ] 元数据目录存在：`.qoder-plugin/` 或 `.codebuddy-plugin/`
- [ ] plugin.json 可被 JSON 解析，无注释、无尾逗号
- [ ] `name`：小写字母/数字/连字符，不以连字符开头结尾，≤64 字符
- [ ] `version`：语义化版本（x.y.z）
- [ ] （Qoder）`skills` 字段指向存在的技能目录
- [ ] （WorkBuddy 专家包）`agents/` 目录存在；`settings.json` 存在且 `{"agent": agentName}`；team 型有 `teamInfo` 与 `members`（含 role=lead）
- [ ] 声明的每个文件/目录在磁盘上存在（零幽灵引用）
- [ ] 磁盘上无未声明的多余文件（列出清单）
- [ ] 头像文件存在且格式/尺寸合规（512×512，≤500KB）
- [ ] plugin.json 引用的每个 avatar 路径真实存在

## B. 一致性（平台硬校验）

- [ ] `defaultInitPrompt.zh` === `quickPrompts[0].zh`（逐字）
- [ ] `defaultInitPrompt.en` === `quickPrompts[0].en`（逐字）
- [ ] `tags` 恰好 3 个（WorkBuddy）
- [ ] `quickPrompts` 恰好 3 个（WorkBuddy）
- [ ] displayDescription.zh 长度在 40–50 字（WorkBuddy 推荐）
- [ ] `profession.zh` 未被同类型资产占用（重名会被解析拒绝）
- [ ] 双平台包文案同步（简介、标签、版本一致）

## C. 功能可用性

- [ ] 无 TODO / `<your-token>` / 占位符
- [ ] 无不可执行的伪代码
- [ ] 每个声明的能力在正文/脚本中有实现痕迹
- [ ] 示例命令可直接照抄执行
- [ ] 有失败路径说明（输入缺失/格式错误时的行为）

## D. 文档与引用

- [ ] description 与正文语义一致
- [ ] 正文引用的文件、路径、锚点全部可解析
- [ ] 中文/英文简介语义一致

## E. 合规与安全

- [ ] 无硬编码密钥、真实凭证、内网地址
- [ ] 无越权指令
- [ ] （Qoder）引用的 Connector 已在市场上架
- [ ] 联系方式只出现在指定位置（author / README / 角色文档）
- [ ] 无夸大宣传、绝对化用语

## 裁决

- 全部通过 → **PASS**
- 仅建议级问题 → **REVIEW**（列出需作者确认项）
- 任一硬校验失败 → **BLOCKED**（列出证据）
