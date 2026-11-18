# CLI 准备

# CLI 安装初始化

需要准备的命令：superun-ai-cli（命令 superun-ai，Node.js 22+）和 suxiaoqiang-cli（命令 sxq，Node.js 18+）。

## 运行环境由宿主提供

- 复用用户已有环境或宿主提供的托管 Node/npm、PATH、npm prefix/cache，不因路径属于宿主管理目录而拒绝使用，不另造安装目录。
- kit 不下载或安装 Node/npm，不安装环境管理器。缺少环境、版本不兼容或目录不可写时返回真实错误；交给宿主智能体处理，环境就绪后重试 CLI 准备并继续原任务。
- 凭据仍由 CLI 管理，不改 HOME、不迁移凭据；环境准备不登录、不关联项目或执行任何业务操作。

## CLI 准备策略

初始化会核对 npm latest，安装缺失 CLI 并更新旧版；版本已达到要求时复用，不在角色切换或登录完成后重复安装。首次安装从 npm latest 取得具体版本，完成后回读实际命令路径和版本；显式更新同样由本层处理，已是最新版本不重装。

没有专用准备脚本的端，在当前已提供的 npm 环境中安装相应包：`npm install -g superun-ai-cli@latest` 或 `npm install -g suxiaoqiang-cli@latest`。沿用宿主的实际 prefix 与缓存，不硬编码系统全局目录，不以权限错误为由自动创建另一套环境。

把 nodePath、各 CLI 的实际 path/version/status 传给执行者。失败只阻止依赖该 CLI 的操作，保留错误和原任务，由宿主智能体修复；不把环境错误当成项目创建失败，也不触发另一种业务模式。

READY 必须包含实际 version 和本次查到的 latestVersion；版本查询失败或更新后版本不符时保持 FAILED，不仅凭命令存在就继续业务。

## 本地项目依赖

源码拉取后、首次安装项目依赖前，使用已确认的 nodePath 运行 `<插件根目录>/scripts/resolve-pnpm.mjs --project <源码绝对目录>`。解析器只查找宿主和用户已有环境，不安装工具。READY 时按返回的 command 参数数组调用 pnpm，并沿用 environment 和 nodePath；不要又改回裸 pnpm 命令命中另一版本。

项目声明版本优先；未声明时采用沙箱基准 10.33.0，允许复用已有 10.33.0 及以上的稳定 10.x。PNPM_REQUIRED 由宿主准备 required 版本后重新检查；PROJECT_VERSION_REQUIRED 按项目声明确认兼容版本；NOT_APPLICABLE 沿用项目指定的其他包管理器。不要临时安装 pnpm@latest 或改全局默认版本。

保留用户的 registry、代理和 store 配置，复用本机缓存，不照搬 Linux 沙箱的 /pnpm-store，不跨版本强行拼接 store 路径，不共用其他项目的 node_modules。现有依赖能运行且与锁文件一致时复用；需要安装时按锁文件执行，同一源码目录只运行一个安装进程。

安装错误先区分下载失败与依赖构建脚本被阻止。后者按当前 pnpm 的真实帮助处理必要依赖，不靠重复完整安装或放开所有脚本解决。保留原命令退出码，不用尾部 echo 或未经 pipefail 处理的 tail 管道掩盖失败。


Windows、macOS、Linux 复用同一套准备与业务流程。Windows 的准备结果 path 是包内 JavaScript 入口，后续使用回执 nodePath 执行该 path，再逐项传入原业务参数；兼容 Shell 可沿原启动器调用。所有路径独立引用，保留中文、空格和原宿主的 npm prefix/cache，凭据仍由同一 CLI 管理。


## Qoder 原生环境准备

SessionStart Hook 使用 scripts/prepare-cli.cmd 双入口：Unix 转交原 sh 启动器，Windows 使用批处理发现宿主 Node；均支持 SUPERUN_KIT_NODE 和 QODER_NODE_RUNTIME。核对 npm latest、安装缺失项并更新旧版后注入实际路径与版本；达到要求时复用。需要显式更新时使用插件 update-cli 命令；排查也可运行 node scripts/prepare-cli.mjs --check。缺少 Node/npm 时保留失败上下文，处理环境后重试；脚本不登录或操作项目。
