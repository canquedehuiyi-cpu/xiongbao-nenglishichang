# Excel

插件显示名称为 `Excel`，插件标识和 MCP Server 均为 `office-excel`，Skill 名称为 `excel`。Plugin 仅携带 Skill、references、JS MCP 与同源 XLSX 网关；不含原生程序，不按操作系统拆包。

- `office-excel.zip`：标准 Node.js 22+ 客户端。
- `office-excel-qoder.zip`：Qoder App，使用宿主提供的 `${QODER_NODE_RUNTIME}`。

两个包只在 MCP 启动命令上不同，均要求 Qoder 管理的 `QODER_HOME`。文件访问授权由 MCP 宿主负责；Plugin 不以 Qoder 目录上下文、MCP roots 或启动目录限制文档、导入目标和图片路径。不承诺脱离 Qoder 独立部署。

Extension 负责查看与手动编辑，独立 Plugin 负责 Agent。双方只通过已保存 XLSX、CSV、XLSM 文件交换内容；XLS 导入交付新的 XLSX；未保存草稿独立，冲突保存会保留草稿并拒绝覆盖。

Qoder Desktop 通过 shared-binary 机制统一安装原生引擎到 `${QODER_HOME}/bin/qoder-office-xlsx/xlsx-sidecar`（Windows 为 `.exe`）。Extension 与 MCP 使用同一份二进制，但各自管理进程和文档。启动检查平台、架构、执行权限和协议版本 2；缺失或不兼容时明确失败，不搜索其他目录或自行下载。

原生制品按平台构建并完成发行签名后再生成 ZIP、大小和 SHA-256；随 App 离线安装，单独更新 Plugin 不更新二进制。源码启动走 `npm run dev` 的当前源码 Cargo 构建及事务安装。正式多平台签名制品和资源清单属于 Desktop 发布流程。

支持范围由工具 `read_context` 返回：XLSX 保持现有功能；CSV 使用独立流式文本模型，支持直接生成、读取、文字编辑与原方言保存；XLS 转换后以新 XLSX 继续编辑；XLSM 仅编辑已有文件的数据、公式和普通格式，保留宏而不执行宏。所有表格文件必须小于 500 MiB（524,288,000 字节，达到即拒绝）；PPT 的独立限制不变。新格式要求配套的 Extension 和共享原生资源版本，单独更新旧 App 中的 Plugin 不能代替完整配套验收。

## Agent 指南与失败反馈

`load_guide` 保留 `name` 参数及单个 JSON 响应。领域指南只返回相关操作 Schema；完整能力仍由 `read_context` 声明。`name: "operations"` 返回精简目录，附带 `operations: ["set_range"]` 时只返回指定操作 Schema（每次最多 8 项）。XLSM 继续使用 `format: "xlsm"`，CSV 的能力仍由其上下文给出。

已知表格冲突和参数错误返回稳定类别及修正建议，未知异常继续脱敏。此变更不放宽文件上限、XLSM 能力、原子提交或保存冲突检查；PPT 的工具接口保持不变。
