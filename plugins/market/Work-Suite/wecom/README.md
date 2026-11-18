# WeCom / 企业微信 Qoder 插件

一次安装即可在 Qoder 中使用企业微信的 15 个 skills：消息、通讯录、日程、会议、待办、邮件、微盘、媒体、文档管理、在线文档、在线表格、智能表格、智能文档、在线 PPT，以及公共安装与授权检查。

## 安装

在 New Qoder 的扩展页面选择「添加插件」并导入 `wecom-new-qoder.zip`。ZIP 根目录直接包含 `.qoder-plugin/`、`skills/` 和 `bin/`，不要额外包裹插件名与版本目录。

也可以解压到单独目录后，通过 Qoder CLI 安装：

```bash
unzip wecom-new-qoder.zip -d wecom-plugin
qodercli plugins validate ./wecom-plugin --strict
qodercli plugins install ./wecom-plugin
```

开启新的 Qoder 会话后说：**“帮我连接企业微信”**。Agent 会检查运行环境，缺少 CLI 时安装运行时，并展示企业微信扫码授权入口。扫码成功后即可提出业务需求，例如“查一下今天的企业微信日程”。已有可用 CLI 和授权时会直接复用。

需要 Node.js 18+ 和 npm、企业微信账号，以及访问 npm 和企业微信服务的网络。平台与官方 CLI 一致：macOS/Linux x64、arm64，Windows x64。表格和 PPT 的部分辅助流程另需 Python 3；本地表格处理按需使用 openpyxl、pandas，公式重算还需要 LibreOffice。按具体 skill 提示检查依赖。

## 包结构

- `.qoder-plugin/plugin.json`：插件标识与展示信息。
- `skills/`：仓库技能、完整 references、scripts 和 assets；公共 skill 加入 Qoder 安装流程。
- `bin/`：Unix 与 Windows 命令入口，由 Qoder 加入 Agent Bash 的 PATH。
- `runtime.cjs`：运行时查找与安装逻辑。
- `runtime-version.json`：本包固定的 CLI 版本，与打包时仓库 `package.json` 一致。
- `LICENSE`、`NOTICE`：许可及来源快照。

## CLI 运行时

插件不内嵌平台二进制。`wecom-cli-runtime-check` 只查找运行时，不执行 CLI、不安装、不访问企业微信；`wecom-cli` 转发实际调用；`wecom-cli-install` 通过 npm 安装本包指定版本，不重复安装 skills。

运行时按以下顺序查找：

1. `WECOM_CLI_RUNTIME_EXECUTABLE` 显式指定的 CLI 可执行文件或 JS 入口。
2. 插件安装的 `~/.local/share/qoder/wecom-cli/node_modules/@wecom/cli/bin/wecom.js`。
3. `~/.qoder/bin`、`~/.qoder-cn/bin` 中的 CLI。
4. PATH 中已有的 CLI（跳过本插件及其别名，避免递归）。
5. `~/.local/bin` 中的 CLI。

可通过 `WECOM_CLI_INSTALL_ROOT` 修改独立安装目录；设置后同一环境中的检查、安装和执行会使用该目录。显式运行时无效时返回错误；安装器不会覆盖它。需要升级插件管理的 CLI 时，更新插件包后运行 `wecom-cli-install`。

Windows 提供 `.cmd` 入口，npm 的 CLI shim 会解析到 JS 文件；内部转发不再经 shell 拼接业务参数。调用者仍需遵守当前 shell 的参数引用规则。

授权由官方 CLI 的 `auth init --noninteractive` 完成。插件包不包含任何个人凭证，安装插件不等于已经完成企业微信授权。

## 维护

源码仓库：https://github.com/WecomTeam/wecom-cli 。更新时同步官方仓库的业务 skills 及其 references、scripts 和 assets，保留 `wecomcli-shared` 的 Qoder 安装与授权流程，并核对 npm 已发布的 CLI 版本。同步后更新插件版本、`runtime-version.json` 和 `NOTICE` 来源记录；打包时从插件根目录打包内容，保留 `bin/` 的可执行权限，不包含 macOS 元数据或个人凭证。验证应从 ZIP 解包后开始，覆盖 New Qoder 的根目录识别和 qodercli 严格校验。

## 0.1.1 更新（2026-11-02）

- 同步官方仓库提交 `1d48b6c9ecd1b4897c4bf728d564bfda1d62fbde` 的业务 skills。
- 更新在线表格技能及参考资料，覆盖区域、行列、样式、筛选、数据验证、条件格式、版本历史等操作，并加入本地表格处理辅助脚本。
- 同步微盘和智能表格参考资料修订，保留原有 Qoder 公共安装与扫码授权流程。
- CLI 固定版本仍为 `@wecom/cli@1.3.4`；更新时它仍是 npm 的 `latest` 版本。
