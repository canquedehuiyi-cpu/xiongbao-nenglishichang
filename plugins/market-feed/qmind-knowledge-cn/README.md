# QMind Knowledge

QMind 知识库工具集，覆盖知识问答（RAG）、Notebook 管理、批量文件夹上传、单文件与目录管理。

首次使用时检查 CLI，缺失时通过脚本（sh / PowerShell / CMD）或 `npm i` 安装。

## 功能

- **知识问答（RAG）**：基于知识库内容生成回答
- **知识检索**：检索知识库内容，保留来源与引用
- **批量上传**：保留目录结构的幂等文件上传
- **Notebook 管理**：发现普通与共享知识库，查看服务端返回的权限信息，创建、查看、删除知识库
- **文件管理**：上传、下载、移动、重命名、删除单个文件或目录

## 使用

两种安装方式任选其一。

### 脚本安装

#### sh（macOS / Linux）

```sh
curl -fsSL https://static.qoder.com.cn/qmind-cli-cn/qmind-cn-install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
qmind-cn version
```

#### PowerShell / pwsh（Windows）

```powershell
$installer = Join-Path $env:TEMP "qmind-cn-install.ps1"
Invoke-WebRequest -UseBasicParsing "https://static.qoder.com.cn/qmind-cli-cn/qmind-cn-install.ps1" -OutFile $installer
pwsh -NoProfile -ExecutionPolicy Bypass -File $installer
$env:PATH = "$env:LOCALAPPDATA\Programs\qmind-cn\bin;$env:PATH"
qmind-cn version
```

使用 Windows PowerShell 5.1 时，将 `pwsh` 换成 `powershell.exe`。

#### CMD（Windows）

```bat
curl.exe -fsSL "https://static.qoder.com.cn/qmind-cli-cn/qmind-cn-install.cmd" -o "%TEMP%\qmind-cn-install.cmd" && curl.exe -fsSL "https://static.qoder.com.cn/qmind-cli-cn/qmind-cn-install.ps1" -o "%TEMP%\qmind-cn-install.ps1" && call "%TEMP%\qmind-cn-install.cmd"
set "PATH=%LOCALAPPDATA%\Programs\qmind-cn\bin;%PATH%"
qmind-cn version
```

CMD 入口需要同目录下配套的 `.ps1` 文件。Windows 默认安装目录为 `%LOCALAPPDATA%\Programs\qmind-cn\bin`，后续终端也需将该目录加入 `PATH`。

### npm i（macOS / Linux / Windows）

需要 Node.js `>=20.18.1`，并将 npm 全局可执行文件目录加入 `PATH`。

```sh
npm i -g @qodercn-ai/qmind-cli@latest
qmind-cn version
```

安装后通过 `qmind-cn` 使用。Native 版运行 `qmind-cn update` 升级；npm 版重新执行上述 `npm i` 命令升级。

## 共享知识库

共享发现要求 CLI `>=3.3.0`；先通过 `qmind-cn notebook list --help` 确认参数，旧版本按上述安装渠道升级。

```sh
qmind-cn notebook list --shared --page 1 --page-size 20 --format json
```

普通列表未找到目标时检查共享列表，按分页信息继续查找，以 Notebook ID 确认目标。`--shared` 不可与 `--filter-client` 组合。结果中的 `permission` 和 `access` 以服务端返回为准；字段缺失表示未知，不等于无权限，列出知识库也不代表拥有写权限。
