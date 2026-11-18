# 支付宝开放平台对接与集成

将支付宝开放平台相关任务统一路由到对应工作流，包括：

- 阿宝 Skill 生产与上架
- 支付产品接入、沙箱与多语言代码示例
- 支付产品签约开通与 MCC 经营类目推荐
- 支付宝小程序发布、提审、灰度与版本管理

## 来源

由用户提供的 `alipay-onboarding.zip` 转换为 Qoder 插件，原始 Skill 版本为 `0.0.7`。原有 `SKILL.md`、变更记录、脚本和参考资料均保留在 `skills/alipay-onboarding/`，未省略源文件。

## 使用

在 Qoder 中上传生成的插件 zip。安装后，涉及支付宝开放平台对接、支付、签约或小程序发布的请求会由 `alipay-onboarding` Skill 处理。

具体业务操作依赖 AlipayCLI，并可能需要登录、授权或人工确认；请按 Skill 内对应文档执行。插件不包含账号、密钥或其他凭据。

## 目录

```text
alipay-onboarding/
├── .qoder-plugin/plugin.json
├── README.md
└── skills/alipay-onboarding/
    ├── SKILL.md
    ├── CHANGELOG.md
    ├── references/
    └── scripts/
```

## 校验

已使用 Qoder 官方离线校验器 `validate_qoder_plugin.py` 检查插件目录和最终 zip，结果均为 `OK: no issues found`。zip 根目录直接包含 `.qoder-plugin/plugin.json`，中文路径均带 UTF-8 标志，且已通过压缩包完整性检查。
