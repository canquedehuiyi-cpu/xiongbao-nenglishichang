# DevEco CLI

在 Qoder 中通过对话开发 HarmonyOS 应用。你可以让 AI Agent 创建项目、编译和运行应用、查看设备日志、操作应用界面，以及查询鸿蒙开发文档。

## 可以做什么

- **创建项目**：根据应用名称创建 HarmonyOS 工程。
- **配置签名**：登录开发者账号后，生成调试签名材料并写入项目配置。
- **编译和运行**：安装项目依赖、编译应用，并运行到已连接的设备或模拟器上，支持增量部署和热重载。
- **排查问题**：查看编译错误和设备日志，检查 ArkTS 语法、代码规范及 API 兼容性，支持部分问题的自动修复。
- **检查界面**：获取屏幕截图、录制真机屏幕、查看窗口和界面控件，执行点击、滑动、拖拽和文字输入。
- **查询文档**：搜索和阅读 HarmonyOS 开发指南、API 参考和示例。
- **管理设备**：查看已连接设备及其详情，在电脑和设备之间传输文件，操作设备上的 SQLite 数据库。
- **使用模拟器**：创建、启动、停止和删除模拟器，管理系统镜像，模拟定位、电量、传感器和折叠等场景。

## 使用准备

- 首次使用前，Agent 会在同一终端检查 `node --version` 和 `npm --version`。缺少 npm、未安装 Node.js 或 Node.js 版本低于 22 时，会提示安装带 npm 的 Node.js 22 或更高版本；重新打开终端并检查通过后再继续。安装 DevEco CLI 还需要能够访问 npm registry 的网络。
- 安装 DevEco Studio，并准备项目所需的 SDK。Linux 用户需要配置 Command Line Tools；可用功能取决于已安装的开发工具。
- 运行应用前，连接设备或启动模拟器。

首次使用时，Agent 会检查 DevEco CLI 是否可用。已有符合版本要求的 CLI 时，可以直接使用；需要安装或升级时，Agent 会根据你的授权执行。DevEco Studio、Command Line Tools 和 SDK 需要单独安装。

发布构建会将 OpenHarmony ARM64 的渠道标签解析为具体版本，并写入 wrapper 依赖；插件使用该版本的命令说明及最低版本要求。

## 开始使用

安装并启用插件后，在 Qoder 中打开 HarmonyOS 项目，向 Agent 描述你要完成的任务。例如：

> 帮我编译当前项目，并处理编译错误。

> 在支持模拟器的平台上，把当前应用运行到模拟器上。

> 查看设备上的错误日志，分析应用启动失败的原因。

> 获取当前应用的截图，检查登录按钮是否显示。

> 查询 ArkUI List 组件的用法和示例。

如果还没有项目，可以说：

> 在当前目录下创建一个名为 MyApp 的 HarmonyOS 项目。

连接多台设备时，请说明要使用的设备名称或序列号。任务需要登录时，按提示在浏览器中完成认证；非 HarmonyOS 原生环境需要接受模拟器协议时，阅读协议并确认后再继续。

## 入口与配置

插件提供以下命令，通常由 Agent 根据任务调用：

| 命令 | 用途 |
| --- | --- |
| `devecocli <command> [options]` | 调用选中的 DevEco CLI，执行编译、运行、查询文档等任务。 |
| `devecocli-runtime-check` | 检查当前运行环境和 CLI 版本，并给出需要完成的下一步操作。 |
| `devecocli-install` | 为插件安装或更新 CLI，使用插件指定的默认版本。 |
| `devecocli-install --help` | 查看安装目录、默认版本和安装用法。 |
| `devecocli-install --version <version-or-tag>` | 安装指定版本或 npm 标签对应的版本，版本需要满足插件的最低要求。 |

### 安装和删除 Skill

通过插件执行 `skills add` 或 `skills remove` 时，默认使用 Qoder 的用户 Skill 目录。用 `--project` 操作项目里的 Skill，用 `--agent` 指定 Agent，或用 `--path` 直接指定目录。

插件自带的 Skill 保存在插件目录，随插件更新。

### CLI 查找顺序

首次使用或插件更新后，Agent 会先运行 Runtime check。已有符合要求的 CLI 时可以直接使用；如果缺少 Node、CLI 或开发工具，Agent 会按照检查结果提示你完成对应操作，并在完成后重新检查。

在 Windows、macOS 和 Linux 上，插件安装使用自己的安装位置，不会要求你修改主机上的全局 CLI。HarmonyOS PC 会优先使用公共安装位置。

私有 CLI 升级会先在临时位置安装和验证，验证成功后才替换现有版本并清理其他旧 UUID 安装目录；如果安装或验证失败，原版本会继续保留。清理失败不会撤销已成功激活的新版本。全局 CLI 升级后只重新检查入口和版本，不会自动初始化 Skill 或修改 Agent 配置。

插件管理的 Runtime 禁止执行 `init`，但允许执行 `skills add` 和 `skills remove`。这两个命令默认管理插件目录中的 Skill；传入 `--path` 时才使用指定目录。插件内置 Skill 随插件更新，不会被 CLI 安装或升级流程修改。

### 指定要使用的 CLI

如果安装了多个版本，或 CLI 没有加入 `PATH`，可以设置 `DEVECO_PLUGIN_RUNTIME_EXECUTABLE`。变量值必须是 CLI 入口文件的绝对路径，例如 npm 安装目录内的 `@deveco/deveco-cli/dist/cli.js`。请根据实际安装位置替换下面的示例路径。

Windows PowerShell：

```powershell
$env:DEVECO_PLUGIN_RUNTIME_EXECUTABLE = 'C:\tools\deveco-cli\node_modules\@deveco\deveco-cli\dist\cli.js'
```

macOS / Linux：

```sh
export DEVECO_PLUGIN_RUNTIME_EXECUTABLE='/opt/deveco-cli/node_modules/@deveco/deveco-cli/dist/cli.js'
```

设置后，从同一终端启动 Qoder。使用桌面客户端时，也可以将变量加入用户环境配置，再重新启动客户端。随后让 Agent 运行 `devecocli-runtime-check`，确认检查状态和 CLI 版本。

这个变量也支持真实的 CLI 可执行文件；Windows 支持 npm 生成的标准 `.cmd` 入口和 `.exe` 文件。请指向已经安装的 DevEco CLI，不能填写目录或插件自身的 `bin/devecocli`、`bin/devecocli.cmd`。设置后会优先检查该入口，但它仍然必须满足插件要求的最低版本和当前平台兼容性；路径无效或不兼容时，需要修正或删除这个变量。

### 其他配置

| 环境变量 | 用途 |
| --- | --- |
| `DEVECO_PLUGIN_INSTALL_ROOT` | 修改插件安装 CLI 的目录，默认是 `~/.local/share/qoder/deveco-cli`。需要填写绝对路径，并放在插件目录和当前项目目录之外。 |
| `DEVECO_CLI_DEBUG=1` | 输出命令执行日志，便于排查问题。 |

## 常见问题

### 已经安装过 DevEco CLI，还需要重新安装吗？

符合版本要求时可以直接使用。版本过旧时，Agent 会提示升级；如果你希望保留现有版本，也可以让 Agent 为插件单独安装 CLI。

### 更新插件后，还需要更新 DevEco CLI 吗？

插件和 DevEco CLI 分别更新。更新插件后的首次使用会重新检查 CLI，Agent 会提示是否需要升级。由插件单独安装的 CLI 也可以直接让 Agent 更新。

### 提示开发工具或设备不可用，怎么办？

让 Agent 检查 DevEco CLI、DevEco Studio 或 Command Line Tools 的配置，以及设备连接状态。安装失败时，请检查 npm registry 和代理配置；编译提示缺少 SDK 时，请安装项目要求的 SDK。

### 卸载插件会删除哪些内容？

卸载插件会保留已有的 CLI、项目、SDK、认证和签名文件。插件单独安装的私有 CLI 也会保留；需要释放空间时，可在相关进程停止后删除安装帮助中显示的私有安装目录。

## 数据与隐私

DevEco CLI 默认开启匿名使用统计。设置环境变量 `DEVECO_CLI_DISABLE_TELEMETRY=1` 可以关闭。采集内容、存储方式和关闭步骤见随插件提供的 `PRIVACY.md`。
