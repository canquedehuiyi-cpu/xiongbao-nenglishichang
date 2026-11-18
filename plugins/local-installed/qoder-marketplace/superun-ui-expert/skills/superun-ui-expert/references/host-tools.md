# 当前宿主工具

按当前动作读取提问、展示或后台进程小节；业务材料的处理见 [云端展示](host-presentation.md)。

## 用户提问

<!-- @author xiuyu.yi -->

按当前运行时 schema 收答，保留问题、选项ID和原单多选语义；工具不可用时完整文本收答。取消、预选和通知不是答案。
需要选择项目时只允许本次唯一目标；多个候选使用单选并保留可区分标识。按当前工具 schema 的实际容量分页，不把工具上限写死。


## 成果展示

<!-- @author xiuyu.yi -->

只在本产品专业方法允许或用户明确要求展示时，先在正文给出真实链接，再使用本端浏览器导航同一地址；不可用或失败时说明并保留链接。 工具经 mcp_get 懒加载时，首次使用每种工具都先读取当前 schema，再用 mcp_call 的 toolName 和 arguments 调用，不凭相似工具猜参数。 本机已核对的 navigate_page 使用 type=url 与 url；click 使用当前 take_snapshot 返回的 uid，不传 text；evaluate_script 使用 function 字符串，不传 script；take_screenshot 使用 format，不传 type。 这些是当前端实测参数，运行时 schema 不同时以当前定义为准。导航或页面变化后先获取新快照，再引用本次 uid；参数校验失败只重新读取该工具定义并修正本地参数，不重复业务写入。
实际导航工具需要懒加载时先发现工具，再按其 schema 调用；网页打开不代表功能已验收。


## 后台进程

<!-- @author xiuyu.yi -->

后台长命令通过 Bash 的 `run_in_background: true` 提交，保存原 task-id 和输出文件绝对路径；使用原生后台参数时不在命令中追加 Shell 的 &、nohup 或重定向到另一份结果文件。完成通知须匹配原任务，再通过 Read(file_path) 读取原输出文件。Read 不等待完成，文件存在不代表终态；尚未完成时只续查原任务，不重新提交。业务 sessionId 不是后台 task-id。命令返回完整 JSON 后才能安排下一步。

