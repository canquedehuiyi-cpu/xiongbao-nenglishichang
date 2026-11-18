# 碳阻迹企业碳管理与产品碳足迹顾问

Qoder 中文顾问插件，版本 1.0.0，准备日期2026-10-27。碳阻迹企业碳管理、产品碳足迹与低碳转型顾问。结合 CREOS 框架梳理现状、证据缺口和行动计划，准备核算边界及数据清单，通过 CCDB 查询和比较真实碳排放因子并提供可追溯链接。内含顾问技能、因子查询技能和远程 MCP 连接；查询需用户授权。

内含 `carbon-advisor-cn` 顾问技能、`ccdb-cn` 因子技能，以及远程 MCP `carbonstop-advisor-ccdb-cn`。顾问技能分别提供企业 CREOS 分析和产品碳足迹工作参考；图标沿用碳阻迹公司 Logo。无 Hooks、脚本、固定令牌或平台建模写入。

解压 ZIP 后保留隐藏目录 `.qoder-plugin` 和 `.mcp.json`，在 Qoder 插件设置中导入根目录，或按市场要求上传完整 ZIP。安装后检查技能和工具是否加载；仅在需要真实因子查询时完成 Qoder 的用户授权。企业诊断和数据准备可先独立开展。

如已有 Qoder CLI，可执行 `qoder plugins validate ./carbonstop-carbon-advisor-cn` 和 `qoder plugins install ./carbonstop-carbon-advisor-cn`，再重启或执行 `/plugins reload`。本包未运行 Qoder 原生校验和实际 OAuth 业务全流程；只完成本地结构、JSON、技能和压缩包校验。

公开咨询框架不等于 CM3 完整评分规则，产品数据准备不等于完整 LCA 核算或认证。因子数值与可见范围受账户权限和许可限制；缺失或掩码不能用于计算。详见 [工具与验收](docs/TOOLS.md) 和 [OAuth 对接](docs/OAUTH.md)。国内托管回调为 `https://mcp.qoder.cn/api/mcp/oauth_callback`；本地客户端应核对实际回调。

产品入口：[Carbon Agent](https://agent.carbonstop.com)。联系方式：mail@carbonstop.com。插件名为 `carbonstop-carbon-advisor-cn`，MCP 服务名为 `carbonstop-advisor-ccdb-cn`，两者用途不同。
