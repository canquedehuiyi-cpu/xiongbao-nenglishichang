# 建项规格参数

先发现当前工具 Schema，再读取所选设计师本次 `get_designer` 回执。当前 `image_spec` 输入对象只接受两个必填字符串：`resolution`、`aspect_ratio`；与回执里的 `resolution_tier` 字段名不同。省略整个对象才能沿用全部设计师默认值。

| 用户明确要求 | 本次建项参数 |
|---|---|
| 未指定比例和分辨率 | 不传 `image_spec`，不要传 `{}` 或 `null` |
| 只指定比例，例如正方形 | `aspect_ratio="1:1"`，`resolution` 取实时 `default_image_spec.resolution_tier` |
| 只指定分辨率 | `resolution` 取用户要求，`aspect_ratio` 取实时 `default_image_spec.aspect_ratio` |
| 两者都指定 | 两个字段均使用用户要求，并核对当前支持值 |

默认值来自**本次**设计师回执，不从历史任务、示例或代码里固定为 1.5K／2K。`auto` 只有在当前默认或真实用户要求允许时使用。必需默认字段缺失时重新查询能力；仍缺失则说明阻塞，不凭空补值。

例如本次回执恰为 `{"resolution_tier":"1.5K","aspect_ratio":"auto"}`、用户只要求正方形，则正确参数为 `{"resolution":"1.5K","aspect_ratio":"1:1"}`。这个示例不是全局默认值。不要发 `{"aspect_ratio":"1:1"}`，不要把输出对象中的 `resolution_tier`、`width`、`height`、`size` 当成输入字段。用户要求当前 Schema 无法表达的自定义像素时，先说明限制并核对支持方式，不丢弃约束或猜字段。

提交前核对：字段完整、名称正确、值非空、用户约束保留、未附多余字段。只有明确收到未受理的参数校验错误，才修正参数后沿用原建项幂等键重试；网络超时或结果不明先查询原操作，不能改参数重放或换键重复建项。已受理任务的规格变更属于独立新任务。
