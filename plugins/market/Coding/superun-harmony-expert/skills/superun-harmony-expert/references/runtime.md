<!-- @author xiuyu.yi -->

# 独立云端产品运行准备

本产品仅使用 superun-ai。已有本次执行环境的有效 READY 绑定时直接复用，否则从实际 Skill 安装位置运行：

```sh
node "<当前Skill根目录>/scripts/prepare-cli.mjs" --ensure superun-ai
```

准备脚本复用既有跨系统实现，按本产品 profile 核对实际命令、选项和 capability；缺失或失败不当作就绪。保存 nodePath、实际 CLI 路径、版本及检查结果，后续固定该绑定。Windows 返回 JavaScript 入口时通过 nodePath 执行，PowerShell 带空格路径用 &。保留原 npm prefix/cache、HOME 和凭据位置，不另造安装器、不读取或展示 PAT。Node/npm 缺失或不兼容时由宿主先准备并回读，再继续原任务；只要求检查时不安装。

`CLI_VERSION_MISMATCH` 表示官方 registry 版本与实际启动入口不一致，不能据此推断版本不存在。安装可能已完成，先回读同一 Node/CLI 绑定并执行原准备入口的 `--check superun-ai`；已 READY 就恢复原任务，不重复更新。仍不一致时核对启动器实际生效版本及其正式 update 帮助，按原绑定恢复后再检查。不要绕过准备脚本裸跑 npm、使用另一镜像查询推翻官方结果、修改 active.json 或循环重装。`PREPARATION_BUSY` 时读取原准备任务，不并发安装或删除锁。技术恢复保留原用户请求和授权。

准备只处理 CLI，不登录或调用业务。auth status 只核对本地配置；业务返回 AUTH_REQUIRED 时沿 CLI 的原登录流程恢复，立即展示真实授权链接，由系统浏览器完成授权；不另起重复登录、不使用业务预览工具接管授权。成功后保留原目标、用户全文、附件、答案与任务锚点。

后台长命令通过 Bash 的 `run_in_background: true` 提交，保存原 task-id 和输出文件绝对路径；使用原生后台参数时不在命令中追加 Shell 的 &、nohup 或重定向到另一份结果文件。完成通知须匹配原任务，再通过 Read(file_path) 读取原输出文件。Read 不等待完成，文件存在不代表终态；尚未完成时只续查原任务，不重新提交。业务 sessionId 不是后台 task-id。命令返回完整 JSON 后才能安排下一步。

原命令仍运行时读取原输出，不并发提交；终态及完整业务 JSON 到齐后再判断下一步。stdout、stderr 与退出码分别保留，结果未知不重发写命令。READY、通知和本地进程成功均不代替实际业务交付。

## 网页展示工具

只在本产品专业方法允许或用户明确要求展示时，先在正文给出真实链接，再使用本端浏览器导航同一地址；不可用或失败时说明并保留链接。 工具经 mcp_get 懒加载时，首次使用每种工具都先读取当前 schema，再用 mcp_call 的 toolName 和 arguments 调用，不凭相似工具猜参数。 本机已核对的 navigate_page 使用 type=url 与 url；click 使用当前 take_snapshot 返回的 uid，不传 text；evaluate_script 使用 function 字符串，不传 script；take_screenshot 使用 format，不传 type。 这些是当前端实测参数，运行时 schema 不同时以当前定义为准。导航或页面变化后先获取新快照，再引用本次 uid；参数校验失败只重新读取该工具定义并修正本地参数，不重复业务写入。
