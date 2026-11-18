# superun 开发

使用本插件限定的主入口执行当前任务。问答使用 AskUserQuestion，后台命令使用 Bash 与 Read。模式 hook 拦截时先处理项目模式，不重发被拦截的功能请求；模式问题单独一题、单选，选项标签为“云端生成（superun-ai）”和“本地开发（sxq-cli）”。真实选择写入项目记忆后继续。本地接管安装项目依赖前，按 ENVIRONMENT.md 的“本地项目依赖”复用 pnpm 和缓存。页面和文件交付按当前工具方法处理。

执行前确认 CLI 已就绪；初始化失败时按 [环境指引](ENVIRONMENT.md) 处理后继续原任务。

任务开始时读取 [主 Skill](skills/superun-creation/SKILL.md) 和 [阶段指引](skills/superun-creation/references/mode-selection.md)。
