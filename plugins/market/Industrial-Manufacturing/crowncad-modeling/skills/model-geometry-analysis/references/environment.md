# 环境准备

路径约定：`<skill_dir>` 为本技能 `SKILL.md` 所在目录的实际绝对路径，由代理在执行前替换，不是 Python 或 Shell 自动替换的变量。相对输入、输出及 `generated/` 路径以当前任务工作区为基准，不切换到技能安装目录运行或写入任务资料。


需要 Python 3.12–3.14、pip 和 venv；版本范围来自依赖元数据，实际验证环境为 Windows x64 / Python 3.14.7。其他平台是否有对应二进制安装包须通过安装和检查确认，不保证通用兼容。

先检查已有解释器：

```powershell
python "<skill_dir>/scripts/environment.py" check
```

缺依赖时在独立目录初始化环境，不修改全局 Python：

```powershell
python "<skill_dir>/scripts/environment.py" setup --venv "generated/runs/<任务目录>/.venv"
```

后续用输出的虚拟环境解释器运行绘图脚本。初始化脚本只创建环境、安装依赖、执行网格与绘图检查，不下载安装 Python。若 Python 未安装，先安装兼容版本；多个 Python 时用明确的解释器路径调用初始化脚本。安装需要网络与磁盘空间；不自动更换镜像、提升权限或循环重试。

离线时先在匹配操作系统、架构和 Python 版本的联网环境准备依赖 wheel 及其传递依赖，再运行：

```powershell
python "<skill_dir>/scripts/environment.py" setup --venv "generated/runs/<任务目录>/.venv" --wheelhouse "D:/packages/cad-wheels"
```

`requirements.txt` 固定三个直接依赖版本，不是全部传递依赖的跨平台锁文件。安装成功后保存包清单；更新版本需重新验证实际 STEP 读取与图片。已有虚拟环境只允许复用同一解释器，不向未经识别的非空目录创建环境。

本地 STEP 分析无需连接 CrownCAD。在线拓扑查询使用插件已配置的 CrownCAD MCP 工具，通过宿主完成 OAuth 授权；调用规则见[执行器说明](../../crownscript-executor/SKILL.md#执行与验证)。
