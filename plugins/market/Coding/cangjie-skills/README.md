# 仓颉开发助手

仓颉编程语言 AI 开发工具箱，覆盖语言特性、标准库、扩展标准库、工具链、编码规范和原始文档六大知识领域，支撑从零创建、开发、构建、运行、测试仓颉项目。包括 stdx、macro、CFFI 等场景的自动处理。

## 来源

转换自 [Cangjie-SIG/CangjieSkills](https://gitcode.com/Cangjie-SIG/CangjieSkills)，原始仓库为通用 AI 编码工具格式（`.agents/skills/`），本插件将其适配为 Qoder 插件格式。

## Skills

| Skill | 说明 |
|-------|------|
| cangjie-lang-features | 语言核心特性文档：类、结构体、接口、枚举、泛型、并发、宏、模式匹配、错误处理、CFFI 等 24 个主题 |
| cangjie-std | 标准库速查：集合、IO、文件系统、网络、正则、并发、反射、数学运算等 27 个模块 |
| cangjie-stdx | 扩展标准库速查：JSON 编解码、HTTP、WebSocket、TLS、日志、压缩、序列化等 |
| cangjie-toolchains | 工具链文档：cjc 编译器、cjpm 包管理器、cjdb 调试器、cjcov 覆盖率、cjfmt 格式化、cjlint 检查、cjprof 性能分析 |
| cangjie-regulations | 编码规范：项目结构、命名、格式化、错误处理、测试、并发、安全等最佳实践 |
| cangjie-original-docs | 原始文档兜底（内部知识库，不在用户菜单中显示） |

## 注意事项

- 请在全局环境配置好[仓颉通用版本工具链](https://cangjie-lang.cn/download/)，全局可引用 cjpm 等工具。
- 如果项目需要使用 stdx，建议手动下载所需版本的 stdx 并解压到项目根目录。
