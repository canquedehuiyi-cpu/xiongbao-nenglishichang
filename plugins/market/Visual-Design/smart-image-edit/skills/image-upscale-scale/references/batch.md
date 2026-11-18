# 批量与恢复

持久化本次需求的 `project_id`、创建幂等键，以及每张图片的以下记录：

```json
{
  "source_name": "原图.png",
  "upload_transfer_id": null,
  "asset_id": null,
  "import_key": "batch-uuid/image-1/import",
  "image_id": null,
  "revision_id": null,
  "quote_key":"<REDACTED>",
  "quote_id": null,
  "run_key":"<REDACTED>",
  "task_id": null,
  "task_status": "not_started",
  "result_image_id": null,
  "result_revision_id": null,
  "canvas_url": null,
  "canvas_link_delivered": false,
  "export_requested_by_user": false,
  "export_key": null,
  "export_id": null,
  "export_status": "not_requested"
}
```

`batch-uuid` 使用本次操作实际生成并保存的唯一标识替换；幂等键为 1–160 个非空白 ASCII 字符，不把中文文件名写进 HTTP 头。

- 两个并发槽供单图处理使用；`queued`、`running`、`cancel_requested`、`outcome_unknown` 都占在途槽。不能只计实际生图中的任务。
- 先汇总有效报价和预计容量，说明总积分。记录用户确认的图片范围、参数和预算。超过 10 分钟或配置改变的报价必须重取；预算变化再次确认。
- 同一原图多个步骤串行：上一结果产生新图片时取得其已保存版本后再报价下一步；OCR／翻译只有数据结果，后续文字处理沿用被识别图片的同一保存版本，不虚构结果图片或版本。不同原图可以并行，永不超过服务端的 `max_in_flight`。
- `429`：遵守 `Retry-After`／`retry_after`，用原幂等键退避重试；不要为了绕开限额新建项目或连接。
- 请求超时但不知道是否受理：有任务 ID 就查询；没有就重放同键同参数，不能改键创建新任务。进程恢复先查询未完成项，再安排未开始项。
- 失败是逐张状态，不取消其他已确认处理。展示已成功结果和未完成项；仅在用户要求后为明确失败项重新报价、确认并提交新的独立操作。结果未知仍查询原任务。
- 每个成功项先展示 `canvas_url`，再标记 `canvas_link_delivered=true`。不能用内部“即将展示”代替真实交付。
- 没有用户明确下载要求时，`export_requested_by_user=false`，不创建任何导出任务。客户端不得把“分离”自动理解为“下载 PSD”。
- 收到导出要求后，记录用户选择的图片 ID、格式和当前版本。只为已交付画布且明确选择的项置 `export_requested_by_user=true`；其他项保持 `not_requested`。
- 导出也逐张、最多两个在途，保留独立 `export_id`。成功、失败、取消均不影响分离任务状态。一个文件失败只重新导出该文件：`canvas_export` 传原 `retry_export_id`、原图片 ID／版本／格式和新的导出幂等键。网页已更新也仍重试原冻结版本，不重复成功文件。
- 下载过期用原 `export_id` 重新调用 `canvas_get_result`，不要换导出键生成新文件。

恢复文件不包含 Authorization、Cookie、下载 ticket 或服务端返回的内部配置。宿主文件传输能力不可用时，明确说明限制并交付画布链接，不声称已保存文件到用户设备。
