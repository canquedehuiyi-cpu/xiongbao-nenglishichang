# CrownCAD CrownScript Executor

路径约定：`<skill_dir>` 为本技能 `SKILL.md` 所在目录的实际绝对路径，由代理在执行前替换，不是 Python 或 Shell 自动替换的变量。相对输入、输出及 `generated/` 路径以当前任务工作区为基准，不切换到技能安装目录运行或写入任务资料。

`<case_skill_dir>` 为 `modeling-case-library/SKILL.md` 所在目录的实际绝对路径，须从当前可用技能位置取得。测试命令仅用于源码开发环境，安装包不包含测试目录。


将自然语言建模需求转换为 CrownScript；CrownCAD 文档和 API 操作通过插件已配置的 CrownCAD MCP 服务执行。

能力与文档路由见 [SKILL.md](SKILL.md)，建模顺序见 [执行流程](references/execution-workflow.md)，检查工具和验收方法见 [验证流程](references/verification-workflow.md)，案例查找与保存见 [案例参考与保存](../modeling-case-library/references/case-workflow.md)。

`generated/runs/` 保存任务全部过程，`generated/models/` 保存用户确认后的固定快照。索引位于 `generated/models/case-index.json`，由正式保存或显式重建生成；README 是事实来源。

## 工具使用

文档创建、脚本执行、STEP 导出、拓扑查询、草图平面解析和装配状态查询，默认使用插件已配置的 CrownCAD MCP 工具，身份来自宿主当前连接的 OAuth 授权。代理不查找或读取本地凭据文件，不传入凭据参数。未授权或授权失效时，请用户通过宿主完成授权或重新授权，不自动改用本地直连。仅在用户明确要求本地直连时使用对应 Python 执行器；本地计算、几何分析、检查和案例管理仍可使用 Python。

AI 维护完整 `model.crownscript.js`，仓库提供的 [run_files.py](scripts/run_files.py) 管理实际提交、响应、证据和报告，按用途保存、替换及清理。Python API 直接接收内容，CLI 通过 `--stdin` 接收 UTF-8 JSON；新流程不生成 `.work` 或同类中转目录。分析图放 `analysis/`，实际 CAD 查询和截图放 `evidence/`，标准报告放 `reports/`；完整源码与本次提交片段分别保留。不建编号执行目录，不默认 STEP/output 或每任务 build.py/verify.py。初始化不创建 CAD 文档；未知写入先回查，不重发。适用范围、命令和来源字段集中见[执行流程 1.1](references/execution-workflow.md#11-累计源脚本阶段与修订)。

查询工具不接受 `task_dir`、`request_log_path`，STEP 导出不接受 `output_path` 或文件覆盖参数。服务端自动管理临时资料，在业务数据之外返回 `artifacts` 下载地址。按[跨机器文件交付](references/execution-workflow.md#51-跨机器文件交付与证据使用)在内存下载、校验大小与 SHA-256，适用公共入口的资料直接保存到正式用途位置，不另写输入副本；报告只引用已入库的本地文件。STEP 仍按明确请求及其既有流程处理。

装配实例与配合调用 `collect_assembly_state(document_id, version_id)`，全部实例矩阵调用 `collect_assembly_transforms(document_id, version_id)`。两者直接返回业务数据并附对应证据包下载链接；按[跨机器文件交付](references/execution-workflow.md#51-跨机器文件交付与证据使用)下载到调用端任务目录。视角调整见[执行流程第 2.1 节](references/execution-workflow.md#21-建模过程中的视角展示)，截图见[验证流程第 4.1 节](references/verification-workflow.md#41-视口截图与跨环境证据保存)；截图同样通过临时下载链接交付。

本地案例索引与归档脚本仍通过 Python 运行：

```powershell
python "<case_skill_dir>/scripts/find_cases.py" search --workspace "." --term "支座" --term "加强筋"
python "<case_skill_dir>/scripts/find_cases.py" rebuild-index --workspace "."
python "<case_skill_dir>/scripts/save_case.py" --workspace "." --source "generated/runs/支座__1234abcd" --required-file "model.crownscript.js" --required-file "runtime/submitted.crownscript.js" --required-file "runtime/response.json" --required-file "reports/verification.json"
```

拓扑四层查询通过 MCP 完成：先用 `collect_topology` 的 `level="ids"` 获取当前对象和元素 ID；再按需用 `query_topology_geometry` 查询面、边/曲线或顶点。`include_edges` 补充面—边关系，`include_vertices` 补充边—点 ID。完整关系或兼容旧图结构时显式使用 `collect_topology` 的 `level="full"`。下载校验后通过公共入口按证据用途保存，必要不同子集分别命名，正式保存后由程序清理可靠替代的旧副本，不等待报告 passed，也不改验收结论；分析图、必需过程证据及未解决现场保留。模型修改后不复用旧 ID。参数见[四层查询](references/entity-modeling/details/topology-layer-design.md)。

选定草图平面后调用 MCP 工具 `resolve_sketch_plane`。它先验证元素类型为 `Plane`，再读取 CrownCAD 的工作平面信息，并返回 `origin`、`xAxis`、`yAxis` 和 `normal`。不得根据法向自行推导局部轴；工具只读取 API，不创建或编辑 CAD 文档。调用前确认 `plane_element_id` 来自当前有效拓扑，并下载返回的 artifacts 证据包。

`collect_topology` 的 `level="full"` 保留完整采集；`output_format="compact"` 可返回精简视图，原始完整图仍保存为 `topology.json`。`level="ids"` 不查询元素几何详情。必要不同查询结果使用独立 `purpose` 的 `queries/` 或 `bundles/` 路径，避免互相覆盖。

保存前须完成模型验收、真实保存授权和资料核对：

```powershell
python "<case_skill_dir>/scripts/save_case.py" --workspace "." --source "generated/runs/支座__1234abcd" --required-file "model.crownscript.js" --required-file "runtime/submitted.crownscript.js" --required-file "runtime/response.json" --required-file "reports/verification.json"
```

保存结果结合 JSON 字段及错误输出判断，详见案例规范的 [结果处理](../modeling-case-library/references/case-workflow.md#54-结果处理成功或失败怎么反馈)；不能只凭退出码判断是否已保存。

## 测试

```powershell
python -m pytest "<skill_dir>/tests" -q
```


标准件查询与匹配仍由 `standard-component-matching` 技能处理。
