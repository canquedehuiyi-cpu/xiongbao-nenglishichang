# 原始文件传输

仅上传用户同意用于正式图片制作的必要素材；本地需求讨论不自动上传整套资料。

远程服务器无法读取用户电脑路径。调用 MCP `create_upload(filename,mime_type,role,idempotency_key,label)` 获取五分钟有效的 PUT 地址；单文件最多 20 MiB，类型由服务端校验。已采用页面原图、指定待改图和视觉参考用 `reference`，通过 label 说明各自用途；文档类型以服务端实际支持为准。保留用户选择的文件顺序。

宿主拥有文件／命令能力时上传原始字节，不需要 Python。macOS 示例（用真实路径、票据替换占位符，严格作 Shell 参数引用，不拼接用户 Brief）：

```sh
curl --fail --silent --show-error --request PUT --upload-file '/absolute/input.png' 'UPLOAD_URL'
shasum -a 256 '/absolute/input.png'
```

读取上传回执 `receipt.asset_id` 和 `receipt.sha256`，核对哈希；响应丢失先调用 `get_upload(transfer_id)`，完成则复用资产，不重复上传。相同票据只能重试相同原始字节；未完成且票据过期，另申请上传票据，不重新创建设计任务。

对已结算作品调用`get_result`，优先直接传递完整原始回执给下方下载辅助程序或宿主原生文件能力。不要手工重写长票据URL。

将输出路径放在已创建的目标目录中，并确认 HTTP 请求成功、文件非空且内容确为图片后，用宿主产物展示能力呈现本机文件。十分钟下载凭证到期后重新调用 `get_result` 使用新的领取幂等键，不调用生图工具。票据 URL 是短期凭证，不写入公开日志、插件包或审核报告。

软件原型已进入总览阶段时，下载后必须继续 [本轮总览更新](design-board.md)：用真实下载清单update、check --expected，最后呈现并核对同一个预览区总览。单张图片卡片不能代替此收尾；新图尚未采用也必须立即在总览显示为待确认。

`get_result` 返回的是传输票据，票据 `status=pending` 不能覆盖已经成功的生成任务状态；按票据中的地址下载，再依据真实传输结果判断是否交付。下载地址不追加文字或改写查询参数；可点击链接格式和凭证有效期与作品保留期限的区别见主 Skill。

无本地文件能力时可展示远程预览／下载链接及神火原项目入口，明确尚未执行本机下载；无法上传的输入不能宣称已经作为参考图参与设计。Windows 尚未实机验收，不从 macOS 成功推断 Windows 已通过。

## 原始回执下载辅助程序

本包提供 [download_result.py](../scripts/download_result.py)，只需 Python 3.9+ 标准库。仅在宿主已有该解释器时使用，不自动安装运行时。原始 `get_result` JSON 通过宿主工具结果直接保存／复制到私有临时文件（权限 0600），或者直接传入脚本标准输入；不要手工挑字段、重新生成 JSON 中的票据或让模型按记忆输入 URL。接受裸回执、`structuredContent` 或 MCP `content[type=text].text` 包装。

```sh
python3 '/absolute/skill/scripts/download_result.py' --receipt '/private/temp/result.json' --output-dir '/absolute/output-directory'
```

`--receipt -` 表示从标准输入接收原始 JSON。命令参数只有本机路径，没有下载地址。脚本验证完整票据形状、transfer_id 与 URL 一致、HTTPS 真实下载域名、回执有效期及文件名，再直接使用原字段下载；不重建 URL，不跟随跳转、不附 OAuth 头。默认不覆盖已有文件；已有目标存在时使用新的输出目录。成功输出本机绝对路径、字节数、图片类型和 SHA-256，再用宿主图片能力检查尺寸与视觉内容。

脚本报票据无效时，从原始工具回执重新取得完整数据，不自行补字符；HTTP 401／403／410 或过期时重新 `get_result` 并用新的领取幂等键，替换整份回执，只重试下载。网络临时错误先检查是否已有完整文件，再使用仍有效的原回执重试。校验只能发现结构错误，不能证明任意同长度字符抄写都正确，必须使用原始回执传递。不要重建项目或重新生图。

脚本不持久化票据；由宿主在结束时移除本次创建的私有临时回执。无法程序化取得完整原始回执或无可用文件能力时，说明尚未下载本机，保留作品和项目入口，不能用猜测地址继续尝试。
