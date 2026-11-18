# 当前宿主工具

按当前动作读取提问、展示或后台进程小节；业务材料的处理见 [云端展示](host-presentation.md)。

## 用户提问

<!-- @author xiuyu.yi -->

### 原生问答

需要用户选择时使用 `AskUserQuestion`。每题使用 question、header、multiSelect、options；options 包含 label、description。单选 multiSelect=false，多选 true，按当前 schema 的容量分页。选项 label 只填业务名称，编号交给控件，不额外添加数字、字母或圈号。

先展示当前真实成果、预览和费用，再汇总为一道单选。交付后的入口为完成托管，继续创作／查看完成报告／创作历程；报告和历程展示后都直接引导完成托管，继续创作。正常收费与完成状态核对成功后，再给推荐更多功能／手动输入需求／上线运营。暂停时提供继续全托管。

金额、账户和优惠写在对应完成选项的 description 中，使用当前报价，不把预计区间当作付款授权。价格变化时更新选项说明后取得真实选择。取消、预选、超时和工具通知均不是用户答案。

后续实际业务问卷保留原题、单多选语义和业务 ID 映射；推荐功能由用户真实选择后执行，不默认全选。用户仅选择手动输入需求且尚无具体内容时，再询问具体要求；已有原话不重复询问。

工具实际不可用或无法完整表达题目时说明原因并完整文本收答，不用权限弹窗替代业务问答，不伪造已选择的结果。


## 成果展示

<!-- @author xiuyu.yi -->

只在本产品专业方法允许或用户明确要求展示时，先在正文给出真实链接，再使用本端浏览器导航同一地址；不可用或失败时说明并保留链接。 工具经 mcp_get 懒加载时，首次使用每种工具都先读取当前 schema，再用 mcp_call 的 toolName 和 arguments 调用，不凭相似工具猜参数。 本机已核对的 navigate_page 使用 type=url 与 url；click 使用当前 take_snapshot 返回的 uid，不传 text；evaluate_script 使用 function 字符串，不传 script；take_screenshot 使用 format，不传 type。 这些是当前端实测参数，运行时 schema 不同时以当前定义为准。导航或页面变化后先获取新快照，再引用本次 uid；参数校验失败只重新读取该工具定义并修正本地参数，不重复业务写入。
实际导航工具需要懒加载时先发现工具，再按其 schema 调用；网页打开不代表功能已验收。


## 后台进程

<!-- @author xiuyu.yi -->

后台长命令通过 Bash 的 `run_in_background: true` 提交，保存原 task-id 和输出文件绝对路径；使用原生后台参数时不在命令中追加 Shell 的 &、nohup 或重定向到另一份结果文件。完成通知须匹配原任务，再通过 Read(file_path) 读取原输出文件。Read 不等待完成，文件存在不代表终态；尚未完成时只续查原任务，不重新提交。业务 sessionId 不是后台 task-id。命令返回完整 JSON 后才能安排下一步。

