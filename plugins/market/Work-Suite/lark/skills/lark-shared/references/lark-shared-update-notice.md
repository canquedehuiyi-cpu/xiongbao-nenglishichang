# 更新与 `_notice`

lark-cli 命令执行后，如果检测到新版本，JSON 输出中会包含 `_notice.update` 字段（含 `message`、`command` 等）。

除非用户正在询问更新、版本或 notice，否则不要把 `_notice` 原样复制为当前任务的主要答案，也不要为了 notice 中断当前任务去反复查 help。

需要稳定 JSON 给脚本或机器读取时，可以在命令前设置：

```bash
LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1 LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1 <lark-cli command>
```

当你在输出中看到 `_notice.update` 时，先完成用户当前请求；如仍相关，再简短告知可升级 Qoder 插件。导入更新后的插件包后，按公共安装引导运行：

```bash
lark-cli-install
```

**Qoder 适配**：本插件携带固定快照的 Skills，安装器只更新配套 CLI。不要运行会同时修改其他位置 Skills 的 `lark-cli update` 或官方 `install` 向导；单独升级二进制不等于插件内的 Skills 已更新。先更新插件包，再检查并安装其配套运行时。

另外两类 notice：
- `_notice.skills`：本地 Skills 与当前 CLI 不同步。
- `_notice.deprecated_command`：本次使用了兼容保留的旧命令；后续调用改用 `replacement`。如果同时提供 `action: "lark-cli update"`，按上方插件升级流程处理。
