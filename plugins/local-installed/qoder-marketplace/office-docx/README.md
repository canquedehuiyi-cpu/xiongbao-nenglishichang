# Office DOCX

独立 Word Plugin，提供 `office-docx` MCP 与 Skill。包内包含固定版本的 Word 引擎和 DOM 依赖；安装和运行无需 npm、源码目录、独立应用或原生编译器。

`office-docx-qoder.zip` 使用 Qoder 提供的 Node 运行时；`office-docx.zip` 使用标准 Node（22.12 及以上的 22.x，或 24 及以上）。两个包共用工具、Skill 和引擎，仅启动命令不同。

Word View 由 Office Extension 提供，不依赖本 Plugin。两者通过保存后的 DOCX 文件交换内容，各自的草稿、版本和回执独立。保存发生冲突时保留草稿并拒绝覆盖。

工具：`load_guide`、`create_document`、`read_context`、`read_blocks`、`insert_content`、`replace_blocks`、`apply_ops`、`check_document`、`save_document`。以实际 `tools/list` 和 `read_context` 返回的操作目录为准。

文件访问权限由 MCP 宿主裁决；Word 工具接受本机绝对路径，不再按 cwd、additionalDirectories 或 MCP roots 重复限制目录，也不查询 MCP roots。仍校验 DOCX 格式、常规文件、取消信号与保存冲突。编辑器继续只操作宿主绑定的文件。

The plugin includes its Word engine and DOM dependencies. It exchanges saved DOCX files with the independent Office View. Unsaved drafts are private; conflicting saves fail without overwriting the other writer. No additional model, native binary or dependency download is required.
