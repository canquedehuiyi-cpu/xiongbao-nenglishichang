# 安装并接入 PolarDB-PG 记忆管理

按照 `polarmem0-onboarding` skill 的流程，为当前客户端接入 PolarDB-PG 记忆管理，开启记忆的自动召回与自动沉淀。

用户可能通过参数提供 API Key 与服务端点：`/polarmem0-setup <api-key> <base-url>`。若参数缺失或不完整，请向用户询问，不要使用示例值或猜测。

执行要求：

1. 先执行 `node -v` 确认 Node.js 版本不低于 20；不满足则告知用户自行安装，不要修改用户的 Node 环境。
2. 确认用户使用的是 Qoder 还是 QoderWork，以确定 `--agent` 取值（`qoder` 或 `qoderwork`）。
3. 执行 `npm install -g @aliyunpolar/polarmem0` 前，向用户说明这是全局安装并取得同意。
4. 执行 `polarmem0 setup --agent <qoder|qoderwork> --api-key <API_KEY> --base-url http://<host>:<port>`。
5. 提示用户重启客户端（新开一个会话），随后执行 `polarmem0 status --agent <qoder|qoderwork> --json` 验证，确认 `connected`、`hooks_installed`、`skill_installed` 三项均为 `true` 并把结果展示给用户。

任一步骤失败时，按 skill 中的排查表处理，不要重复盲试。不要在对话中复述用户的 API Key。
