# wxz-cli

万小智 (Wan Xiao Zhi) —— 阿里云 AI 对话建站平台命令行工具。

通过自然语言对话自动生成网站代码、预览效果并部署上线。

## 安装

```bash
pip install wxz-cli
```

安装后 `wxz` 命令全局可用：

```bash
wxz --version
wxz --help
```

## 快速开始

```bash
# 登录
wxz login --ak <ACCESS_KEY_ID> --sk <ACCESS_KEY_SECRET>

# 对话建站（自动模式）
wxz chat start "帮我做一个科技公司官网" --yes

# 预览
wxz preview

# 部署
wxz deploy publish --watch
```

## 作为 Qoder 插件使用

本仓库同时是一个 Qoder 插件，包含 `skills/wxz-cli/SKILL.md`，可在 Qoder 客户端中加载使用。

## 文档

- 阿里云产品文档: https://help.aliyun.com/zh/product/3039206.html
- 灵感值购买: https://dc.console.aliyun.com/#/inspiration
