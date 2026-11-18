---
name: update-cli
description: Check and update the superun CLI tools in the current host environment.
---

# 更新 superun CLI

由插件环境层处理：执行当前插件根目录 scripts/prepare-cli.cmd --update all，复用初始化的宿主运行时发现；PowerShell 调用带引号的绝对路径时使用 &。读取 JSON 结果后返回实际版本；失败保留原因，不修改业务项目，不登录、不创建项目。不要把环境更新转交业务 Skill。
