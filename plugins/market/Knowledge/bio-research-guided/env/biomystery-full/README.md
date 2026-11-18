# BioMysteryBench 完整依赖安装指引（给 Agent）

本配置按用户提供的 Dockerfile 逐项整理。`dockerfile-dependencies.json` 保存原文件
SHA-256、依赖分组和容器专属设置；不包含用户数据、凭证或评测工作脚本。
这是一份安装清单和操作指引，**整套依赖尚未完成真实安装、版本求解和跨平台验证**。
不要把“清单完整”说成“完整环境已经验证可用”。

## 先判断是否需要完整环境

1. 阅读实际选中方法的依赖要求。普通统计任务优先使用已验证的 `foundation`。
2. 需要 Dockerfile 中的生信工具、更多 Python/R 包或评测环境时，再使用本配置。
   不要只因激活 Skill 就下载整套依赖；不在本清单中的方法依赖仍需单独处理。
3. 安装前告诉用户将安装哪些组件、实际目录和较大的体积。可使用：

   > 这项任务需要安装较大的生信运行环境，包括 Python/R 包和生信命令行工具。
   > 完整环境可能占用数 GB 以上空间，下载和编译可能耗时较长。
   > 原 Dockerfile 注释估计镜像超过 10 GB，这不是本机安装大小或下载量的实测值。
   > 我会使用独立目录；系统编译库、包管理器和外部工具会按需另行安装。

4. `foundation` 的约 0.9 GB 实测值不能用于估算本配置。检查剩余磁盘空间和网络，
   只执行当前任务需要且用户已经授权的步骤；用户已授权安装时，不重复索要同一授权。
5. 始终记录执行命令、解释器、版本和失败包。出现不支持的平台或无法求解的版本，
   明确报告原因，不跳过依赖后宣称完整就绪。

## 覆盖范围与执行者

| 原 Dockerfile 内容 | 配置文件 / 处理方式 |
| --- | --- |
| 科学计算、生信、Agent 框架、后加的 Python 包 | `requirements.in`，53 个分发包，由脚本安装 |
| tidyverse、remotes | `r-packages.json` 的 CRAN 阶段 |
| DESeq2、edgeR、limma 等 25 个包 | `r-packages.json` 的 BiocManager 阶段，保留原列表 |
| lionessR | 脚本通过 remotes 从 `kuijjerlab/lionessR` 安装并检查包加载 |
| Python 3.11、R 4.3、生信工具、BLAST 2.17.0 | `conda-packages.txt`，Agent 调用 conda 安装 |
| Ubuntu 系统库、编译工具 | `apt-packages.txt`，Agent 按下方步骤安装 |
| Java 21、Node.js 20 | 已加入 conda 清单，避免必须修改系统软件源 |
| Miniconda / libmamba | 已有 conda 可复用；无 conda 时按官方指引安装对应架构的 Miniforge |
| uv 和它安装的 Python 包 | uv 工具另装；原包已合并到 requirements.in，包括 scikit-image |
| ossutil | 按阿里云官方指引选择系统和架构，单独安装并检查 |
| COPY scripts、/work、环境变量、默认 Bash | 任务工作目录配置，见最后一节；脚本和数据不在插件里 |

## 平台选择

- **Linux x86_64**：下面的 Bash 命令为参考安装路径；最接近原 Dockerfile，仍需实际求解。
- **macOS Intel / Apple Silicon、Linux ARM64**：conda/Bioconda 支持这些平台，
  但本清单的每个包和固定版本不一定都有对应构建。先做 dry-run；缺包时报告具体包名，
  必要时在 Linux x86_64 主机或容器中运行该方法，不默认使用模拟架构或改版本。
- **Windows**：完整生信工具链使用 WSL2/Linux 环境，插件路径也必须换成 WSL 中的路径。
  不要在原生 Windows 上执行 apt/Bash 命令或宣称 Bioconda 全链路可用。
  `foundation` 的 Python/R 安装器仍有原生 Windows 分支，但未实测。

参考：[Bioconda 平台与 channel 指引](https://bioconda.github.io/index.html)、
[Miniforge 安装](https://conda-forge.org/download/)。

## 1. 设置路径、检查工具

以下示例在 Bash 中执行；Agent 必须把占位路径换成实际路径，所有路径保留引号。
默认写在插件树外，不修改 `.bashrc` 或用户现有 conda 配置。

```bash
PLUGIN_ROOT="/absolute/path/to/installed/plugin"
BIO_ENV_ROOT="$HOME/.qoder/bio-research/env"
BIO_RUNTIME="$HOME/.qoder/bio-research/runtimes/biomystery-full"
python3 "$PLUGIN_ROOT/scripts/setup_env.py" list
conda --version
```

没有 conda 时，先按上面的 Miniforge 官方链接选择系统/架构并安装到用户目录，
再用该安装的 conda 绝对路径替换下面的 `conda`。不要在 macOS/Windows 下载原 Dockerfile
中的 `Linux-x86_64.sh`；Miniconda 安装器版本不是本配置已复现的承诺。

## 2. Ubuntu/Debian 编译库

`apt-packages.txt` 保留原始 Ubuntu 软件包名；不能原样用于其他 Linux 发行版或 macOS。
下面把 Java 和 Node.js 留给 conda 安装，另加 R 源码编译可能需要的 gfortran。
先展示将执行的系统安装命令，在系统允许的权限下执行，不规避权限限制。

```bash
mapfile -t BIO_APT_PACKAGES < <(sed '/^#/d; /^$/d; /^openjdk-21-jdk-headless$/d; /^nodejs$/d' \
    "$PLUGIN_ROOT/env/biomystery-full/apt-packages.txt")
sudo apt-get update
sudo apt-get install -y --no-install-recommends "${BIO_APT_PACKAGES[@]}" gfortran
```

macOS 使用当前 Xcode Command Line Tools，按实际编译错误从 Homebrew 安装相应库，
不要把 apt 包名机械改成 brew 命令。原生 Windows R 源码编译可能需要匹配版本的 Rtools；
完整配置优先在 WSL 中执行。SDK/linker 问题见上级 `env/README.md`。

## 3. 独立 conda 运行时与生信工具

```bash
conda create --dry-run --prefix "$BIO_RUNTIME" \
    --override-channels -c conda-forge -c bioconda --strict-channel-priority \
    --file "$PLUGIN_ROOT/env/biomystery-full/conda-packages.txt"
conda create -y --prefix "$BIO_RUNTIME" \
    --override-channels -c conda-forge -c bioconda --strict-channel-priority \
    --file "$PLUGIN_ROOT/env/biomystery-full/conda-packages.txt"
conda run --prefix "$BIO_RUNTIME" python --version
conda run --prefix "$BIO_RUNTIME" Rscript --version
conda run --prefix "$BIO_RUNTIME" blastn -version
conda run --prefix "$BIO_RUNTIME" java -version
conda run --prefix "$BIO_RUNTIME" node --version
```

目录已存在时，先检查归属和现有包；需要补装时使用相同 channel 参数的
`conda install --prefix ... --file ...`，不删除或覆盖他人的环境。
要求分别核对 Python 3.11、R 4.3、BLAST 2.17.0、Java 21、Node.js 20。
R 4.3 对应较早的 Bioconductor 版本；新包可能与其不兼容。
求解或安装失败时报告包名、平台与版本，不偷偷放宽固定版本。
参考：[conda create 的清单参数](https://docs.conda.io/projects/conda/en/stable/commands/create.html)。

## 4. Python、CRAN、Bioconductor、GitHub R 包

```bash
conda run --prefix "$BIO_RUNTIME" python "$PLUGIN_ROOT/scripts/setup_env.py" \
    install --domain biomystery-full --env-root "$BIO_ENV_ROOT" --dry-run
conda run --prefix "$BIO_RUNTIME" python "$PLUGIN_ROOT/scripts/setup_env.py" \
    install --domain biomystery-full --env-root "$BIO_ENV_ROOT"
```

脚本使用 conda 运行时的 Python 创建独立 venv，并使用同次 `conda run` 中的 R。
本路径已有 R，不使用 `--install-r` 另装一个系统 R。
Python 在 `$BIO_ENV_ROOT/biomystery-full`，R 包在其 `R/library` 子目录。
`--skip-r` 可以仅处理 Python 阶段，但不能因此宣称完整 R 环境可用。
R GitHub 安装继承 remotes 支持的环境凭据，不能把 token 写入清单或日志。

清单沿用原 Dockerfile 中未锁定的 Python/R 包；GitHub 仓库也未锁定 commit。
没有已验证的完整 lock 文件。依赖冲突、历史版本包不可用或编译失败时保留日志，
根据任务处理对应问题，不把 foundation 的 macOS 验证结论套到此配置。
参考：[remotes 官方项目](https://github.com/r-lib/remotes)。

## 5. uv、ossutil 与备用 Python

若任务需要复现 uv 工具，按 [uv 官方安装指引](https://docs.astral.sh/uv/getting-started/installation/)
选择平台。也可将 uv 安装在独立 conda 运行时，而不是用户的系统 Python 中：

```bash
conda run --prefix "$BIO_RUNTIME" python -m pip install uv
conda run --prefix "$BIO_RUNTIME" uv --version
```

原 Dockerfile 的 `uv pip install --system` 是额外修改另一套 Python 的行为。
本配置把它的包合并到独立 venv，不自动写系统 Python；如果评测明确要求第二套解释器，
额外创建任务专用 venv，用 uv 的 `--python <该解释器>` 安装 JSON 清单中的
`uv_system_python_packages`，并记录任务究竟使用哪一套解释器。

ossutil 按 [阿里云官方安装说明](https://help.aliyun.com/en/oss/developer-reference/ossutil)
选择架构和版本，安装到用户可执行目录；验证 `ossutil --version`。
不要直接执行 Dockerfile 的 `curl | bash`，不要复制或写入他人的 OSS 凭证。

## 6. 验证与实际运行

```bash
conda run --prefix "$BIO_RUNTIME" python "$PLUGIN_ROOT/scripts/setup_env.py" \
    check --domain biomystery-full --env-root "$BIO_ENV_ROOT" --json
conda run --prefix "$BIO_RUNTIME" "$BIO_ENV_ROOT/biomystery-full/bin/python" -m pip check
```

`check` 检查 Python 分发包是否存在、verify.json 中的代表性 import、所有声明 R 包的
加载，以及 system.json 中的命令是否可找到。`ready` 不检查全部 apt 动态库、CLI 版本、
数据文件、每个工作流或第二套 Python；`pip check`、版本检查和选中方法的最小运行测试
必须另外执行。系统工具缺失时按本指引补齐，不反复只跑 pip。

运行时保持同一 conda 上下文，并设置隔离 R 库，例如：

```bash
R_LIBS_USER="$BIO_ENV_ROOT/biomystery-full/R/library" \
    conda run --prefix "$BIO_RUNTIME" Rscript "/absolute/task/path/analysis.R"
conda run --prefix "$BIO_RUNTIME" "$BIO_ENV_ROOT/biomystery-full/bin/python" \
    "/absolute/task/path/analysis.py"
```

## 7. Docker 专属工作目录、脚本与数据

原 Dockerfile 还执行 `COPY scripts/*`、`COPY *.sh`、CRLF 转换、chmod、设置 `/work`
和 Bash 默认命令。这些不是依赖安装：必须先向实际评测仓库定位脚本和数据，
本插件没有这些构建上下文文件，不能凭空创建替代脚本或声称已复现评测。

在用户任务目录按需设置 `BMB_FULL_DIR`、`BMB_STAGE_ROOT` 和 `BIOMYSTERY_ENV`；
前两者指向实际脚本/阶段目录，后者指向 `$BIO_RUNTIME`，不要照抄容器的 `/work`、
`/root`、`/opt/miniconda3` 到宿主机。原 `R_LIBS_USER` 改用上述隔离库。
需要 UTF-8 时选择宿主机实际存在的 locale，不假设每台机器都有 `C.UTF-8`。
使用显式 `conda run`，不需要修改用户的 `.bashrc` 或系统默认 Shell。
