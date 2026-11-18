# Qoder Office — Presentations

独立生成、读取、修改和保存可编辑 PPTX。Plugin 自带引擎、工具、Skill、字体及保存校验，不需要安装或启动 Office Extension，也不需要安装 npm 依赖。

## Qoder Plugin 安装

发布提供同一 Plugin 的两种启动配置：`office.zip` 使用环境中的 Node 22+，适用于裸 QoderCLI 等 Node 环境；`office-qoder.zip` 使用 Qoder App 自带 Node。工具、Skill 和引擎完全一致，按接入宿主选一份安装。

解压包后，用 Qoder 的 Plugin 安装入口选择此目录，或执行：

```sh
qodercli plugins install /absolute/path/to/office
```

清单 `.qoder-plugin/plugin.json` 同时登记 `skills/` 和 `.mcp.json`。Qoder App 安装 App 配置包后自动使用自身 Node 运行时，并负责 MCP 调用的权限管理。安装后使用 Office Skill，描述需要生成或修改的 PPT 即可。MCP 与预览 Extension 各自安装和启停，双方通过磁盘 PPTX 交接内容。

## 其他标准 MCP 客户端

需要 Node.js 22 或更新版本，以及支持 stdio MCP 的 Agent。将以下配置中的路径替换为实际安装路径，并放入客户端的 MCP 配置：

```json
{
  "mcpServers": {
    "office": {
      "command": "node",
      "args": ["/absolute/path/to/office/runtime/server.cjs"]
    }
  }
}
```

`node` 由接入方的运行环境提供，也可改成已确定的 Node 可执行文件绝对路径。无需设置 Qoder 专用变量或安装 Extension；`.mcp.json` 中的 `${QODER_NODE_RUNTIME}` 只由 Qoder App 自动解析，其他客户端使用上面的普通 Node 配置。

文件访问授权由接入宿主负责。Plugin 接受目标文稿和图片素材的绝对路径，不查询 MCP `roots`，不要求 Qoder 目录上下文，也不根据启动工作目录或安装目录建立文件白名单。相对路径仍需由 Agent 根据用户任务解析为绝对路径；操作系统文件权限、文件格式和保存冲突校验继续生效。

## Skill 与工具

仅连接 MCP 不会自动安装 Skill。其他客户端请通过自己的 Skill 机制加载 `skills/pptx/SKILL.md`，并保持相邻 `references/` 目录完整；也可让 Agent 先读取该 Skill。工具定义由 MCP `tools/list` 提供，当前有 11 个工具，涵盖逐页生成、结构/样式修改、图片、检查和保存。

用户只需描述目标；模型通过工具完成规划、内容生成与编辑。运行时不另外调用模型，也不提供图片搜索服务。

## 保存与验证边界

修改先进入本 MCP 的私有草稿，必须调用 `save_document` 才会写回 PPTX。Extension 或其他程序看不到未保存草稿；文件被其他程序改动时拒绝覆盖。当前临时草稿仅在本次 MCP 进程存续期间使用，不应通过重启恢复未保存操作。

保存会校验候选文件并用真实引擎重开，之后才原子提交。结构校验不等同于视觉验收。包内没有编辑器界面；可以用 Office Extension 或 PowerPoint 打开已保存文件。

字体的常规、粗体、斜体、粗斜体及 HarfBuzz 排版资源随包提供；生成过程无需额外下载它们。必要的第三方许可证保留在 `runtime/THIRD_PARTY_NOTICES.txt`；源码来源清单保留在开发仓库，不进入 Plugin 发行包。
