# 素材上传与作品下载

所有设计业务通过宿主神火 MCP，下面的文件传输不是业务 API 客户端。不得读取本机应用数据库、OAuth 缓存或账号凭证来恢复连接。

## 上传

1. 确认用户授权使用的实际原文件与顺序，用宿主文件能力读取文件名、MIME、大小和 SHA-256。
2. `create_upload` 申请上传记录，保存原始回执与幂等键；使用回执实际 method、headers、URL 将原始字节上传，不猜字段、不复制 Base64、不将本机路径当资产 ID。
3. 把原始回执作为结构化对象或原样工具结果文件交给宿主文件工具读取；不要将签名地址重新抄进长 Shell 命令。URL 和请求头不写进公开交付。
4. `get_upload` 核对真实状态与 asset_id、sha256；status=pending 时继续查询原记录。超时先恢复，不换文件/换键重复上传；票据过期按实际工具合同重新领取上传凭证，不能猜签名。

## 下载

按成功结果的 image_index、variant_id 领取已结算作品。每次 `get_result` 的**完整原始 JSON 回执**保存到私有临时文件，或通过宿主结构化对象直接传给文件工具；原始结构没有变成模型手写的等价 JSON。不能凭记忆重建 download_url、transfer_id 或签名。

可使用随包 [download_result.py](../scripts/download_result.py)：

```sh
python3 /ABSOLUTE/SKILL/scripts/download_result.py --receipt /ABSOLUTE/private/original-receipt.json --output-dir /ABSOLUTE/project/downloads/new-page
```

该标准库脚本只消费已签发文件回执，不接触 OAuth 或设计 API；验证期限、文件头、HTTP 状态和大小后原样下载，报告文件路径与 sha256。每次选择新输出目录，避免覆盖旧文件。宿主没有原样保存回执的机制时优先直接使用其结构化下载能力；仍无法完整传递时说明限制，不手工猜测链接。

下载后查看实际格式、尺寸、图片内容、商品及文案，再加入交付清单。PNG/JPEG/WebP 原图保留，HTML 缩略展示不覆盖它们。对 401/403/410 或过期票据只重新领取原作品下载凭证；不重新生成图片。

部分成功先交付已结算图片，缺页单独说明。没有文件能力时提供原始短期链接和真实项目入口，并明确尚未下载到本机。短期凭证 expires_at 不是作品保留期限；文件回执不进入 HTML、ZIP。
