# 接口文档模板

按本模板逐接口生成。尖括号内容为占位符，生成时替换为真实值；不适用的段落整段省略。

```markdown
# <模块名>接口文档

> 更新时间：YYYY-MM-DD ｜ 基础地址：<http://127.0.0.1:8080 或 http://127.0.0.1:18080>
> 认证方式：<服务端：请求头 Authorization 携带 token（POST /login 获取）｜客户端后端：Cookie JSESSIONID（POST /api/v1/auth/login 建立会话）>

## 接口目录

| # | 接口名称 | 方式 | 路径 |
|---|---------|------|------|
| 1 | <接口名称> | GET | `<路径>` |

---

## <接口名称>

**请求方式**：GET / POST / PUT / DELETE
**请求路径**：`<完整路径，含类级 @RequestMapping 前缀>`
**权限标识**：`xxx:yyy`（仅服务端有 @PreAuthorize 时写）

### 请求头

| 名称 | 必填 | 示例 / 说明 |
|------|------|------------|
| Content-Type | 是（Body 为 JSON 时） | `application/json` |
| Authorization | <服务端：是/否> | `eyJhbGciOi...`（登录返回的 token） |

（客户端后端会话接口此处写 `Cookie: JSESSIONID=xxx`）

### 请求参数

| 字段名 | 类型 | 位置 | 必填 | 备注 |
|--------|------|------|------|------|
| drugCode | String | Path | 是 | 药品编码 |
| page | Integer | Query | 否 | 页码，默认 1 |
| qrCode | String | Body | 是 | 输液袋二维码内容 |

（无参数时写"无"）

### 返回 JSON 示例

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": { ... }
}
```

（客户端后端为 `{"success": true, "data": { ... }}`；服务端分页接口为 `{"code":200,"msg":"查询成功","rows":[...],"total":n}`）

### 错误码说明

| 错误码 / 状态 | 说明 |
|--------------|------|
| 200 | 成功（服务端） |
| 500 | 业务失败，msg 为具体原因（服务端） |
| CAMERA_UNAVAILABLE | 摄像头不可用或未选择（客户端后端业务错误码，来自代码实际抛出的 BusinessException） |
```

---

## 填写示例（客户端后端登录接口）

```markdown
## 登录

**请求方式**：POST
**请求路径**：`/api/v1/auth/login`

### 请求头

| 名称 | 必填 | 示例 / 说明 |
|------|------|------------|
| Content-Type | 是 | `application/json` |

### 请求参数

| 字段名 | 类型 | 位置 | 必填 | 备注 |
|--------|------|------|------|------|
| loginName | String | Body | 是 | 登录账号 |
| password | String | Body | 是 | 登录密码 |

### 返回 JSON 示例

```json
{
  "success": true,
  "data": {
    "userName": "张药师",
    "roleName": "调配药师"
  }
}
```

### 错误码说明

| 错误码 / 状态 | 说明 |
|--------------|------|
| AUTH_FAILED | 账号或密码错误 |
```
