---
name: skill-update
description: alipay-onboarding Skill 版本自检与更新流程。按触发条件进入,24 小时节流,远端拉取 manifest.json 做 semver 比较,并按结果静默/提示/强制更新。SKILL.md 路由到本文件执行。
version: 0.0.1
---

# 版本自检

本 skill 当前版本见 `SKILL.md` frontmatter `version` 字段。

> 核心约束:SKILL.md 是 prompt 不是代码,agent 每次对话都会加载它,所以更新检查必须轻量、非阻塞、有节流。

## 触发条件

满足任一即进入检查流程,否则跳过直接进入业务流程:

- 用户明确提到"更新"、"升级"、"检查版本"
- 当前对话涉及提审、上架、通场、签约等关键流程

## 节流

进入检查流程后,先读取本 skill 目录下的 `.last-check` 文件:

- 文件不存在,或内容距当前时间超过 24 小时 → 继续执行远端请求
- 距上次检查不足 24 小时 → 跳过远端请求,视为无更新,静默继续
- 用户主动要求检查更新时,忽略节流,强制执行

## 检查流程

1. 从 `SKILL.md` frontmatter 取得当前 `version`。若值为 `__VERSION__` 占位符(未渲染的仓库源,非已安装版本),视为开发态,跳过本流程不比较。
2. 请求远端 manifest(从以下 URL 取最新版本,按当前环境选择命令):
   - macOS / Linux:`curl -fsSL --compressed "https://opengw.alipay.com/alipaycli/skill/alipay-onboarding/manifest"`(必须带 `--compressed`:manifest 经 302 跳转到 CDN,CDN 默认以 gzip 返回,不带则 curl 不自动解压、stdout 是 gzip 字节,JSON 解析失败导致更新检查静默失效)
   - Windows (PowerShell):`Invoke-RestMethod -Uri "https://opengw.alipay.com/alipaycli/skill/alipay-onboarding/manifest"`(PowerShell 自动处理 gzip,无需额外参数)
3. 按 semver 比较 `manifest.latest_version`(远端) 与当前版本(本地),判断是否有更新:
   - 先比 `major.minor.patch` 三段(数值比较),不等即可定论。例:`0.0.3 > 0.0.2-beta.99`(patch 3>2)。
   - 三段全等时:无 `-beta.N` 后缀的 release > 带后缀的预发布。例:`0.0.2 > 0.0.2-beta.99`。
   - 同为 `-beta.N` 预发布时,按 beta 编号数值比较。例:`0.0.2-beta.2 > 0.0.2-beta.1`、`0.0.2-beta.99 > 0.0.2-beta.2`。
   - 远端 > 本地 → 有更新;相等或更小 → 无更新。
   - 版本号无法按上述规则解析时,按"解析失败"处理(静默跳过,见下)。
4. 将当前时间(ISO 8601)写入本 skill 目录下的 `.last-check` 文件(覆盖写入,仅一行)

## 结果处理

- **无更新** → 静默继续,不输出任何提示
- **有更新,urgent=false** → 在回复末尾附一行提示(格式见下方模版)
- **有更新,urgent=true** → 在回复开头醒目提示,建议用户立即更新
- **当前版本 < min_supported** → 告知用户当前版本已不受支持,暂停后续业务流程,引导更新
- **网络失败 / 解析失败** → 静默跳过,不阻塞、不报错(不更新 `.last-check`,下次对话仍会重试)

## 更新提示模版

> **全覆盖更新(非 append,且失败可回滚)**:先把旧 `{SKILL_DIR}` 备份(mv 成 `.bak`),再解压新版到全新目录,**只有解压成功才删备份**。`unzip -o` / `Expand-Archive -Force` 只覆盖同名文件、不会删除新版本已移除的旧文件,故必须换目录而非原地解压。若解压失败,旧版本仍在 `.bak`,可 `mv` 回去回滚,不会丢文件。

> 💡 alipay-onboarding 有新版本 {latest_version}(当前 {version}):{changelog}
>
> macOS / Linux(解压失败时备份保留在 `{SKILL_DIR}.bak.$$`,可手动 `mv` 回滚):
> `curl -fSL --compressed -o /tmp/alipay-onboarding.zip "{download.url}" && ( [ ! -d "{SKILL_DIR}" ] || mv "{SKILL_DIR}" "{SKILL_DIR}.bak.$$" ) && mkdir -p "{SKILL_DIR}" && unzip -o /tmp/alipay-onboarding.zip -d "{SKILL_DIR}" && rm -rf "{SKILL_DIR}.bak.$$" && rm -f /tmp/alipay-onboarding.zip`
>
> Windows (PowerShell)(解压失败时备份保留在 `{SKILL_DIR}.bak`):
> ```powershell
> $zip = Join-Path $env:TEMP "alipay-onboarding.zip"; $bak = "{SKILL_DIR}.bak"; Invoke-WebRequest -Uri "{download.url}" -OutFile $zip; if (Test-Path "{SKILL_DIR}") { Move-Item "{SKILL_DIR}" $bak -Force }; New-Item -ItemType Directory -Force -Path "{SKILL_DIR}" | Out-Null; try { Expand-Archive -Path $zip -DestinationPath "{SKILL_DIR}" -Force; Remove-Item -Recurse -Force $bak -ErrorAction SilentlyContinue; Remove-Item $zip -Force } catch { Write-Error "解压失败,旧版本备份在 $bak,可 Move-Item 回滚"; throw }
> ```

其中 `{SKILL_DIR}` 为本 skill 所在目录的绝对路径,`{download.url}`、`{latest_version}`、`{changelog}` 取自 manifest 对应字段。`.$$` 取 shell PID 作备份后缀,避免覆盖已有备份;PowerShell 用固定 `.bak`。

## manifest.json 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | skill 标识,固定 `alipay-onboarding` |
| latest_version | string | 最新版本号,semver |
| min_supported | string | 最低兼容版本,低于此版本必须更新 |
| released_at | string | 发布时间,ISO 8601 |
| download.url | string | zip 下载地址 |
| download.sha256 | string | zip 文件 SHA-256 校验值,解压前校验完整性,防 CDN 缓存脏数据 |
| changelog | string | 一句话变更摘要,提示用户时展示 |
| urgent | boolean | true 时 agent 应在回复开头主动提醒,而非等用户触发 |

## manifest 示例

> manifest 不在代码仓库内定义,由发布流程生成并发布。`latest_version` 取自发布 tag(`skill-vX.Y.Z[-beta.N]`,发布时渲染 `SKILL.md` 的 `__VERSION__` 占位符),`min_supported` 为发布侧维护的最小兼容版本,`changelog` 取自 `CHANGELOG.md` 对应版本段落(release 精确 `## X.Y.Z`;beta 优先 `## X.Y.Z-beta.N`,缺失用中性占位,不回退正式版摘要),`download.sha256` 为 zip 实际校验和。

```json
{
  "name": "alipay-onboarding",
  "latest_version": "0.0.1",
  "min_supported": "0.0.1",
  "released_at": "2026-08-04T10:00:00Z",
  "download": {
    "url": "https://mdn.alipayobjects.com/alipaycli/uri/file/as/alipaycli/skills/alipay-onboarding/0.0.1/alipay-onboarding.zip",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb924..."
  },
  "changelog": "首个版本:alipay-onboarding Skill 脚手架",
  "urgent": false
}
```

对外最新版本从以下 URL 获取(稳定地址,始终指向最新 release):
- manifest:`https://opengw.alipay.com/alipaycli/skill/alipay-onboarding/manifest`
- setup 引导:`https://opengw.alipay.com/alipaycli/skill/alipay-onboarding/setup`

`download.url` 指向该版本对应的不可变 zip 下载地址,每个版本一份,固定不变。