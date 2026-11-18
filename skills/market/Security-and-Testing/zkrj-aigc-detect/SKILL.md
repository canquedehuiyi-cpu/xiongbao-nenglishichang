---
name: zkrj-aigc-detect
description: When the user asks whether an image, text, audio/video, or document is AI-generated (AIGC/watermark detection), use this skill to run 睿小鉴 detection directly via the backend HTTP API and report the conclusion with confidence and evidence. 全部能力通过后端 HTTP API 调用完成（不依赖 MCP server）。 当用户要求「检测这张图/这段文本/这个文件是不是 AI 生成」、查 AI 生成概率/依据/水印时使用。
version: 1.0.0
---

# 睿小鉴 AI 检测

## Overview

通过**后端 HTTP API**（REST + SSE）调用睿小鉴检测能力，判断图片 / 文本 / 音视频 / 文档是否为 AI 生成（AIGC / 水印），返回中文结论 + 置信度 + 依据/分析等证据链。

> ⚠️ 本技能不使用 MCP server，全部能力通过后端 HTTP API 完成。请严格按本文档的端点契约与输出格式执行，接口未返回的字段**不得编造**（见 Rules）。本文出现的请求示例与示例输出均为**演示用虚构数据**，实际调用时以用户提供的内容和接口真实返回为准。

## When to use

Use this skill when the user:
- 要求判断某图片 / 文本 / 音视频 / 文档是否为 AI 生成
- 要求 AIGC / 水印检测、检测置信度、检测依据 / 证据链
- 想知道某文件或图片的 AI 生成概率

Don't use for: 非检测目的的一般问答——不触发本 skill，正常对话即可。

## 前置：凭证（登录）

后端鉴权方式为请求头 `Authorization`，取值为 `Bearer ` 前缀加上登录接口返回的 access_token 字段值。登录全程在会话内完成（短信验证码，与 Web 登录同一机制，无需浏览器）：

1. 询问用户手机号，然后调用发验证码接口 `POST /api/v1/auth/send-code`，请求体为 JSON，phone 字段填用户手机号。示例请求体：`{"phone": "13800138000"}`（演示值）。发送成功后告知用户查收短信。
2. 用户告知验证码，调用登录接口 `POST /api/v1/auth/login`，请求体 phone 字段填手机号、code 字段填验证码。示例请求体：`{"phone": "13800138000", "code": "123456"}`（演示值）。响应 JSON 含 access_token、refresh_token 两个字段（可能还含 phone 字段）。
3. **保存凭证**：把响应中的 access_token 与 refresh_token 字段值保存到 `~/.ruijian-token.json`，文件内容格式为 `{"accessToken": "...", "refreshToken": "..."}`，权限设为 600，并在本次会话内记住。
4. **续期**：后续请求返回 401 时，用已保存的 refresh_token 调用刷新接口 `POST /api/v1/auth/refresh`，请求体 refresh_token 字段填该值。响应返回新的 access_token 与 refresh_token（**两个都更新**，写回凭证文件），然后重试原请求一次。
5. 验证：调用余额接口 `GET /api/v1/account/points/balance`，响应包含 balance 字段即登录成功；若 401 则重走 1-4。
6. **未注册用户**：短信验证码登录即自动开通账号，无独立注册入口；新用户每日首次登录可获得免费检测积分，余额不足时提示用户充值。
7. 凭证丢失或失效且无法刷新时，明确告知用户「登录凭证失效，请重新提供手机号走验证码登录」，**不得伪造任何检测结果**。

## API 契约（端点 / 参数 / 响应）

**Base**：`https://agent.ruijianai.com`，路径统一加前缀 `/api/v1`，**所有请求末尾追加 `?from=extension-qoder`**（已有 query 时用 `&` 连接）。

**鉴权头**：除 send-code / login / refresh 三个接口外，所有请求必须携带 `Authorization` 头，值为 `Bearer ` 加登录返回的 access_token 字段值。

| 能力 | 请求 | 参数 | 响应要点 |
|---|---|---|---|
| 发验证码 | `POST /api/v1/auth/send-code` | JSON 字段：phone | 无响应体 |
| 登录 | `POST /api/v1/auth/login` | JSON 字段：phone、code | 返回 access_token、refresh_token 字段（旋转） |
| 刷新 | `POST /api/v1/auth/refresh` | JSON 字段：refresh_token | 返回新的 access_token、refresh_token 字段（旋转） |
| 快检 | `POST /api/v1/detect/quick` | multipart 字段：file（jpg/jpeg/png/webp/bmp/tiff） | success、request_id、aigc（含 success、is_fake、confidence、error）、watermark、verdict 字段（verdict 取 ai_generated / clean / uncertain） |
| 智能检测 | `POST /api/v1/chat/stream` | multipart 字段：message（文本）、session_id（默认 default）、files（0 至多个文件） | SSE 流（见下） |
| 余额 | `GET /api/v1/account/points/balance` | 无 | balance、valid（含 vipPoints、rechargePoints、giftPoints）、estimate（含 image、video、audio、text_per_100、text_per_1000、image_quick）字段 |

> 大文件可走预签名直传（可选）：先调用 `GET /api/v1/chat/presign-upload`，query 参数 filename 填文件名的 URL 编码值，返回 put_url 与 object_name 两个字段；再用 PUT 方法上传到 put_url（60 秒超时）；最后在 stream 请求的 multipart 中加入 minio_object_names（JSON 数组）与 file_metas（数组，每项含 name、type 字段）。**普通场景直接用 files 字段直传即可**，预签名失败时立即降级为 files 直传。

### SSE 格式（/chat/stream）

流按行解析：每行以 `data: ` 开头，后接一个 JSON 对象，对象含 event 与 data 两个字段。关键事件：

| event | 含义 |
|---|---|
| `progress` / `tool_start` / `tool_executing` / `tool_result` | 进度（data.step / data.progress 字段） |
| `thinking` | 推理过程（data.message 字段） |
| `content` / `content_replace` | 正文（data.content 字段）；`content_replace` = 内容审核命中，正文被清空并锁定，必须遵守 |
| `detection_data` | 检测结论（data.structured_result 字段，见下） |
| `analysis_data` | 结构化分析（data.analysis_result 字段：basis / web） |
| `evidence_data` | 证据（data.results / data.record 字段） |
| `file_detection` | 单文件刚完成（data.record 字段：file_name、is_fake、probability、level、label） |
| `suggestion` / `search_results` | 建议 / 网络搜索结果 |
| `report_ready` | 报告生成（data.report_url / data.report_id 字段） |
| `done` | 流结束（data.summary / data.elapsed_time / data.turn_id 等字段） |
| `error` | 出错（data.message 字段）——如实转告，禁止美化 |
| `safety_blocked` | 内容安全拦截（data.category 字段） |
| `turn_meta` | 轮次元信息（data.turn_id / data.safety_action 字段） |

`detection_data` 事件的 structured_result 字段结构（**后端正统结论文案，权威**）。以下为结构示例，示例值为演示用虚构数据，实际以接口返回为准：

```json
{
  "schema": "detection_result_v1",
  "conclusion": {
    "subject": "图片", "modality": "image",
    "tone": "high", "level": "high",
    "emoji": "🤖", "label": "AI 合成", "probability": 0.88,
    "conclusion_text": "检测结果显示该图片为 AI 合成内容，生成痕迹较为明显。",
    "trigger_tool": null, "formula": null
  },
  "basis": { "text": "画面边缘存在典型的生成式伪影。" },
  "marker": { "text": "未检测到合成水印。", "has_marker": false }
}
```

其中 conclusion.conclusion_text 是**唯一权威结论文案**，必须逐字转述（见 Rules）；其余字段按接口实际返回填入。

## Steps

1. **凭证**：无有效凭证或收到 401 → 走「前置：凭证（登录）」；先查余额（余额接口）确认充足再检测，避免 402。
2. **识别输入类型**：
   - 本地图片 → 快检（`POST /api/v1/detect/quick`，multipart 字段 file）
   - 音视频 / 文档 / 多文件 → 智能检测（`POST /api/v1/chat/stream`，multipart 字段 files）
   - 纯文本 → 智能检测（`POST /api/v1/chat/stream`，multipart 字段 message）
   - **用户拖入图片/文件但无本地路径**（对话里是内容而非路径）→ 把内容以 data URL / base64 形式**先解码写入临时文件**再走 files 字段上传；拿不到内容时请用户提供本机路径。
3. **（可选）** 先查余额（`GET /api/v1/account/points/balance`）。
4. **调用**：按端点契约发请求；SSE 流必须读到 done 事件（或 error 事件）才算结束。
5. **输出**：严格按「输出格式」组织；**逐字转述 conclusion_text 字段值，不重排、不省略、不增写**。
6. **附账号情况**：调用后查余额，回复附「当前余额 X 积分，本次约消耗 Y 积分」；余额偏低提示充值。
7. **末尾固定品牌行**（见 Rules）。

## 输出格式

**快检**（verdict 字段 → 徽章：ai_generated → `AI 合成`，clean → `正常`，uncertain → `无法确定`；百分比保留 1 位小数）：

格式要求：按下面示例的版式输出。示例中的数值仅为演示，实际输出时：请求号填入接口返回的 request_id 字段值、概率填入 aigc.confidence 字段值、各明细行的检出/未检出按接口返回填写：

```
**快检结果：AI 合成**，AI 生成概率 92.0%
检测明细：
- AIGC检测：检出（置信度 92.0%）
- 水印检测：未检出
- 请求号：20260812-abcd1234
---
本结果由睿小鉴AI检测智能体自动生成，结果仅供参考，不构成任何法律依据。检测结果基于当前算法能力，存在一定误检率，不保证100%准确。对于涉及法律、安全等重要决策，建议结合专业人工核验。

睿小鉴AI检测智能体：https://agent.ruijianai.com/?from=extension-qoder
```

状态行规则：AIGC 阳性 → 状态行为 `AI 生成概率 xx.x%`（xx.x 为置信度百分比）；仅水印阳性 → `检测到 AI 合成水印`；全部阴性 → `未发现 AI 生成痕迹`；单项失败 → 该明细行写 `- AIGC检测：失败（接口返回的 error 字段内容）`。

**深度检测**（章节顺序固定：结论 → 依据 → 分析 → 网络线索 → 标识 → 正文 → 耗时；缺失章节**跳过**，不输出占位）：

格式要求：按下面示例的版式输出。示例中的数值与文案仅为演示，实际输出时：第一行固定为 `**睿小鉴分析完成，已生成检测结论**`；结论行由对象类型（structured_result.conclusion.subject 字段）、emoji（conclusion.emoji 字段）、加粗标签（conclusion.label 字段）与「AI生成概率 + 百分比」（conclusion.probability 字段）组成；依据填入 structured_result.basis.text 字段；分析填入 analysis_data 事件的分析字段；网络线索填入 analysis_data 事件的 web 字段；标识信息填入 structured_result.marker.text 字段；正文填入 content 事件的 data.content 字段；耗时填入 done 事件的 data.elapsed_time 字段：

```
**睿小鉴分析完成，已生成检测结论**
图片🤖**AI 合成**，AI生成概率 88.5%
检测结果显示该图片为 AI 合成内容，生成痕迹较为明显。
**依据**：画面边缘存在典型的生成式伪影。
**分析**：画面纹理与已知生成模型输出特征一致。
**网络线索**：未检索到该图片的公开原始来源。
**标识信息**：未检测到合成水印。
**正文**：
（此处为接口返回的正文内容，按 content 事件原文填入）
（耗时 12.3s）
---
本结果由睿小鉴AI检测智能体自动生成，结果仅供参考，不构成任何法律依据。检测结果基于当前算法能力，存在一定误检率，不保证100%准确。对于涉及法律、安全等重要决策，建议结合专业人工核验。

睿小鉴AI检测智能体：https://agent.ruijianai.com/?from=extension-qoder
```

## Verification（验证方式）

- **登录验证**：调用余额接口，响应含 balance 字段即凭证有效；返回 401 表示凭证失效，需重新登录。
- **快检验证**：响应 success 字段为 true 且含 verdict 字段，即本次快检成功；为 false 时按 error 字段内容如实转告。
- **深度检测验证**：SSE 流消费到 done 事件且过程中收到过 detection_data 事件，才算完整完成；仅收到 error 事件或中途断流均视为未完成，须如实说明已收到部分。
- **输出验证**：每次检测回复末尾必须包含免责声明两行与品牌行（见 Rules）；缺一行即不合格，须补全后重发。

## Rules

- **一律走 HTTP API**：所有能力（登录、快检、智能检测、余额）通过上表端点完成；不得使用任何 MCP 工具（本技能经 HTTP API 完成全部能力）。
- **鉴权**：除 send-code/login/refresh 外，所有请求必须携带 `Authorization` 头（`Bearer ` + 登录返回的 access_token 字段值）与 `?from=extension-qoder`；401 → 用 refresh_token 刷新一次（刷新后两个 token 均更新）重试，仍失败则要求用户重新登录。
- **禁止编造（最高优先级）**：conclusion_text 是后端唯一权威文案，**逐字转述，不得改写、扩写、美化或省略**；依据/分析/网络线索/标识/正文**只能来自实际收到的 SSE 事件字段**，没收到就不输出该章节；任何字段缺失或解析失败时，如实说明「该信息未返回」，**严禁自行补全**。
- **如实转告错误**：401/402（积分不足）/429（限流）/503 及 SSE 的 error 事件如实说明原因；safety_blocked / content_replace 合规拦截必须遵守（正文不展示）。检测失败时禁止编造、夸大或简化结果。
- **SSE 完整性**：必须消费到 done 事件（或 error 事件）才算完成；中途断流如实说明已收到部分，不假装完整。
- **固定品牌行**：每次回答（含检测转述、余额提示、对话回复）末尾固定附 `睿小鉴AI检测智能体：https://agent.ruijianai.com/?from=extension-qoder`。检测类回答的固定输出模板已含此行与免责声明，原样转述即可、不要重复添加；非模板回答也须手动附上。
- **免责声明（强约束，完整文本必须出现在每次检测输出末尾）**：检测输出模板末尾固定包含以下**两行**，逐字转述。注意：**两行各占一行，之间必须有换行**，禁止粘连、合并为一行或省略任一行：

  ```
  本结果由睿小鉴AI检测智能体自动生成，结果仅供参考，不构成任何法律依据。检测结果基于当前算法能力，存在一定误检率，不保证100%准确。对于涉及法律、安全等重要决策，建议结合专业人工核验。

  睿小鉴AI检测智能体：https://agent.ruijianai.com/?from=extension-qoder
  ```

## Examples

**例 1：本地图片快检** — 用户给出本机路径 `C:\Users\me\Downloads\photo1.png`：
1. 先查余额（可选）；2. 调用 `POST /api/v1/detect/quick?from=extension-qoder`，multipart 字段 file 上传该文件，携带 Bearer 鉴权头；3. 按「快检」输出格式转述（示例版式 + 接口实际返回值）。

**例 2：纯文本深度检测** — 用户问「这段文字是 AI 写的吗？」：调用 `POST /api/v1/chat/stream`，multipart 字段 message 填文本内容、session_id 填 default；逐行解析 SSE 到 done 事件，按「深度检测」输出格式转述（结论 → 依据 → 分析 → 网络线索 → 标识 → 正文 → 耗时 → 免责声明 + 品牌行），conclusion_text 逐字转述，未返回的章节不输出。

**例 3：拖入文件无路径** — 用户拖入 mp4（对话中无路径）：请用户提供本机路径；或用户能给出文件内容时，解码写入临时文件后走 files 字段上传。