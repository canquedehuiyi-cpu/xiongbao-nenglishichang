# 维护与发布

## 插件结构

- `.qoder-plugin/plugin.json`：插件标识、版本和组件声明。
- `skills/`：39 个技能及脚本、模板、引用等支持文件。
- `README.md`：面向插件用户的介绍与使用说明。
- `LICENSE`：上游原始 MIT 许可证。
- `assets/icon.png`：本插件原创生成图标，512 × 512 PNG；供市场单独上传，不声明当前 CLI 尚不识别的 `logo` 字段。

仅声明实际存在的组件；当前插件只有 `skills`，不自动注册 Hook、MCP、Rule 或 Qoder Agent。

## 本地验证

在仓库根目录运行：

```bash
qoderclicn plugins validate . --strict
```

开发时可将当前目录安装到用户范围后，新建测试会话检查发现和调用：

```bash
qoderclicn plugins install . --scope user
qoderclicn plugins list
qoderclicn skills list
```

结构校验与会话运行验证分别记录。发布前，检查 `grill-me` 能否调用同包的 `grilling`，并验证团队实际采用的工作流；不凭结构校验宣称全部技能均已验证。

## ZIP 打包

在仓库根目录执行，将 ZIP 输出到上级目录。打包前先移走同名旧包，避免 ZIP 更新时残留已删除的条目。

```bash
zip -r ../team-grill.zip .qoder-plugin skills assets README.md CONTRIBUTING.md LICENSE \
  -x '*/.DS_Store' '*/__pycache__/*' '*.pyc' '*.log' '*/settings.local.json'
```

ZIP 根目录应直接包含 `.qoder-plugin/plugin.json` 和 `skills/`，不增加 `team-grill/` 外层目录。不打包 `.git/`、个人设置、缓存、凭证或本地运行状态。

## 发布流程

1. 更新变更内容与用户说明；需要新版本时同步修改清单和 README 中的版本。
2. 校验插件、ZIP 完整性及目标工作流，确认来源与许可证完整。
3. 通过团队管理员提供的企业市场入口发布，或将插件登记到团队自建 marketplace。
4. 在市场中核对名称、版本、可见范围和安装结果，再告知成员安装或更新。

当前尚未配置远程仓库、市场地址或自动发布。上传 ZIP 到个人客户端属于本地导入，不代表已经完成市场发布。市场清单、上架权限和审核要求以实际分发平台为准，不使用虚构的安装地址。

## 来源快照

- 来源仓库：`kaixin-edit-system-service`。
- 来源目录：`.qoder/skills/`。
- 来源提交：`bef15798fa1a0f52959f4e3d4c326c1fad088a23`。
- 初次打包日期：2026-10-27。
- 初次复制：39 个技能、114 个文件，复制时与来源逐字节一致。
- 技能原文与支持文件保留；插件清单、说明和打包信息由团队单独维护。

初次结构校验使用 Python 3.9.6 的离线校验器及 Qoder CLI CN 1.1.79，均为 0 错误、0 警告。实际运行验证状态见对应发布记录；没有记录时不视为完成。
