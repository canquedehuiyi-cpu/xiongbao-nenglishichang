# synthetic-site — 验收夹具

这不是一个真实站点，是 site-audit 自带的**合成夹具**：一个刻意含有四类已知缺陷形状的微型
静态站点生成器，用来证明检测脚本真的抓得住它们。全部内容（媒体名、域名、日期、正文）均为编造，
`.example` 顶级域按 RFC 2606 保留。

## 内容契约（`tools/validate-content.js` 应当强制它——但它没有，见下）

每篇 `src/posts/YYYY-MM-DD.md` 形如：

```
## 板块名
### 标题
正文一行，可含 **粗体** 与裸链接。
来源：[甲社](https://a.example/1)、[乙社](https://b.example/2)（1 月 5 日）
```

- 一条来源可以有多个来源段，以顿号 `、` 分段；
- **多来源时每一段各自在末尾带 `（M 月 D 日）`**，渲染器为每段各出一个日期标记；
- 只允许 `https://`；
- 中文引语使用全角 `“”`。

## 凭据约定

本项目的服务令牌采用 **`tkv2_<22 位>_<59 位>`** 形态（新版）。
`tools/scan-secrets.js` 负责把误提交进内容目录的凭据挡在发布之前。

## 对外声明

- 「所有资源自托管，不加载任何第三方脚本」；
- 「带凭据扫描与漏洞基线两道门禁」。

## 已知缺陷（刻意的，勿修）

`bin/audit.mjs selftest` 会断言其中四项（F1–F4）必须被抓到、`INJ-1` 与 `SEC-3` 不得误报。
其余各项是顺带植入的真实形状，用于验证对应检查不是只对着 F1–F4 硬编码。

| 编号 | 形状 | 位置 | 应由哪项检查抓到 |
| --- | --- | --- | --- |
| F1 | 渲染字段完备性回归：一行多来源只有行尾一个日期标记 | `tools/render.js` + `src/posts/*` | CTX-1 / CTX-3 |
| F2 | 扫描器模式与实际推荐的凭据形态不匹配 | `tools/scan-secrets.js` | SEC-1 / SEC-2 |
| F3 | 门禁 fail-open：被调命令出错时仍退出 0 | `tools/audit-baseline.js` | SEC-4 |
| F4 | 被服务的响应与产物不一致（注入第三方脚本） | `tools/serve.js` | LIVE-1 / HDR-* |
| F5 | 发布脚本把「参数指向的目录里的代码」交给 node 执行，并对该目录无校验递归强删 | `tools/push-to-github.js` | PIPE-1 / PIPE-2 / PIPE-3 |
| F6 | 行内渲染先替链接后替粗体，且 URL 正则遇第一个 `)` 就停 | `tools/render.js` | INJ-2 |
| F7 | 板块查表不过原型链（`constructor` 取到函数并被写进 class 属性） | `tools/render.js` | INJ-3 |
| F8 | 站点地图含一个产物中不存在的 URL | `tools/build.js` | BLD-6 |
| F9 | 首页带 `noindex`；404 页仍发 canonical；`--fg-faint` 对比度 2.7:1；无 `:focus` 样式 | `tools/build.js`、`assets/*.css` | SEO-1 / A11Y-1 / A11Y-2 |
| F10 | 仓库里没有任何 CI 工作流 | （缺失） | CI-1 |
