# 隐私 / 备案 开关双模式 skill 处理

本附录说明 `privacy create` 与 `icp submit` 两类配置的 **双模式** 处理逻辑:服务端 DRM 开关控制走 URL 页面交互还是 CLI 直接提交,tool 返回 JSON 含 `mcpMode` 字段供 skill 分支。

## 开关说明

| Tool | DRM 开关字段 | false(默认,关闭) | true(打开) |
|---|---|---|---|
| `privacy create` (managePrivacy APPLY) | `cliPrivacyApplyMcpMode` | 返隐私管理页 URL,用户浏览器操作 | CLI 直接提交隐私政策(已实现) |
| `icp submit` (icpSubmit) | `cliIcpSubmitMcpMode` | 返备案页 URL,用户浏览器操作 | CLI 结构化提交备案(三期暂未接入,返提示) |

> CANCEL / QUERY / icpStatus / icpRevoke 不受开关影响,始终走 CLI 直查/直操作。

## tool 返回格式

两个 tool 都返回 JSON 字符串,含 `mcpMode` 字段:

**开关关闭 (mcpMode=false)**:
```json
{"mcpMode":false,"url":"https://open.alipay.com/...","tips":"请在浏览器打开以下链接完成..."}
```
skill 渲染 `url` + `tips` 给用户,human-only 等待浏览器完成。

**开关打开 (mcpMode=true)**:
```json
{"mcpMode":true,"message":"隐私政策已提交"}
```
skill 读 `message`,直接推进主链,不需人工浏览器操作。

## skill 处理逻辑

skill 调 `privacy create` 或 `icp submit` 后:
1. 解析返回 JSON
2. 读 `mcpMode` 字段
3. `false` -> 渲染 URL + tips 给用户(human-only),等待用户浏览器完成后继续
4. `true` -> 读 message,直接推进下一步

skill 不感知 DRM 开关配置,只读 tool 返回的 `mcpMode` 做分支。

## URL 模板(仅供参考,实际由 tool 返回)

### 隐私管理页
```
https://open.alipay.com/develop/privacy/mini/privacyManagement?appId={appId}&bundleId={bundleId}&edit=true&source=draft&usePrivacyType=template&from=
```

### 备案页
```
https://open.alipay.com/platform/portal/icp.htm?appId={appId}
```

## skill 提示话术

### 隐私创建 (mcpMode=false)

```
正生成隐私政策协议配置链接...
请在浏览器打开以下链接完成隐私政策配置:
   {URL}
   主体类型:个体工商户
   建议使用官方模板勾选生成,收集的个人信息按业务实际填写
完成配置后,skill 可继续调 `alipay-cli miniapp privacy get` 查询生效版本
```

### 备案提交 (mcpMode=false)

```
正生成备案页链接...
请在浏览器打开以下链接完成备案材料提交:
   {URL}
   需上传主体材料 + 人脸核验 + 工信部短信验证
完成备案后,skill 可继续调 `alipay-cli miniapp icp status` 查询备案状态
```

### 开关打开时 (mcpMode=true)

skill 直接读 `message` 字段,以自然语言告知用户结果,无需渲染 URL 或等待浏览器操作。
