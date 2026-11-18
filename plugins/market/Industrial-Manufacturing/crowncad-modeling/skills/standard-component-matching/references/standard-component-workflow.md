# 标准件查询、派生和装配交接

实际接口使用当前 CrownCAD OAuth MCP 会话。确认工具已注册；缺少工具是部署问题，不能改用本地凭据或历史成品冒充本次派生。

1. 图纸或已确认方案给出标准身份和规格后，按标准库调用 `query_gb_standard_list(search_keywords)` 或 `query_hg_standard_list(search_keywords)`。保留原始返回，不假设候选字段或只凭名称相似选件。
2. 用候选真实 `modelId` 调用 `get_standard_component_parameters(model_id)`，核对参数名、可选值及规格。身份和规格已完整确认时不另搜近似替代规格。
3. 调用 `derive_standard_component(project_id, knowledge_id, parameters, folder_code="0")`。`project_id` 来自本任务真实项目；参数值保留原字符串，不能自动混用 `40` 和 `PN40`。不传 operation、凭据路径或历史 projectId。
4. 响应中的 `documents` 保留全部文档。单文档上下文完整时读取 `executionContext`；多文档读取 `executionContexts` 并确认要插入的根件。缺少上下文时核对已创建文档，不能猜版本或 `docType`，也不能重发派生来补字段。响应中断或结果未知时先确认实际创建状态。
5. 用本任务真实 `projectId`、`documentId` 和 `versionId` 查看派生件，检查规格、完整性及接口。人孔若自带螺栓，不重复生成。接口需适配时按当前明确设计方案派生加工，不覆盖原库件定义。
6. 交给 `assembly-modeling`：在本次子装配插入真实文档，回查实例身份，再按当前拓扑建立配合。不得沿用历史文档、实例或面边 ID；派生工具不负责插入或宣称装配通过。

本地 `standard_component_tool.py` 只对 MCP 返回的目录候选执行离线文本匹配；它不调用 CrownCAD API，也不读取凭据。
