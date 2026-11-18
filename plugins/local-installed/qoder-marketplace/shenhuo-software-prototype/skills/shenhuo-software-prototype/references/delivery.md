# 本地检查、预览与代码ZIP

使用专门的原型目录；神火任务恢复记录、候选图历史、报价和临时下载地址放在其外部。随包脚本只使用Python标准库，负责文件清单、采用记录、图片哈希、静态资源、预览回执与确定性ZIP；不调用神火、不生成页面、不代替人看图或浏览器点击。

图片审阅使用兄弟目录design-review的固定HTML入口，按 [设计稿总览](design-board.md) 在预览区反复更新。当前整组图确认后才制作此处的功能性原型；最终ZIP只包含最终采用图，不混入总览的候选历史。图片总览的放大点击不计作软件页面跳转验收。

先定位本Skill真实绝对目录。下面用绝对路径占位，执行时通过命令工具参数传值并正确引用，不假设当前目录就是Skill目录。

```sh
python3 '/absolute/skill/scripts/prototype.py' init --root '/absolute/work/prototype'
python3 '/absolute/skill/scripts/prototype.py' check --root '/absolute/work/prototype'
python3 '/absolute/skill/scripts/prototype.py' fingerprint --root '/absolute/work/prototype'
python3 '/absolute/skill/scripts/prototype.py' check --root '/absolute/work/prototype' --require-preview
python3 '/absolute/skill/scripts/prototype.py' pack --root '/absolute/work/prototype' --output '/absolute/delivery/prototype.zip'
```

init只向新目录复制模板，不覆盖既有项目；不会自动生成看似完成的HTML。专家须创建真正的HTML/CSS/JS并填写模板。脚本需Python 3.10及以上；无此环境可人工执行同一清单并说明未运行脚本，不以环境安装阻塞可完成的原型制作。

## prototype.json

`files`只列实际交付的HTML、CSS、JS、字体、图标和图片素材，不递归打包整个工作目录。index入口和三个Markdown自动包含。已采用reference图片由pages引用自动加入，预览截图由verification.json自动加入；不要把它们重复塞入files。路径使用项目相对路径和正斜线，无绝对路径、父目录跳转、隐藏文件或符号链接。

页面示例（所有值须替换为真实记录，示例本身不是已批准图）：

```json
{
  "id": "mobile-home",
  "terminal": "mobile",
  "route": "index.html#mobile-home",
  "viewport": {"width": 390, "height": 693},
  "reference": {
    "path": "reference/mobile-home-r01.png",
    "source": "shenhuo",
    "variant_id": "实际作品ID",
    "sha256": "实际文件SHA256"
  },
  "approval": {"status": "confirmed", "note": "用户明确采用该页该版本的原话或上下文依据"}
}
```

用户提供的批准图将source设为user，variant_id设为null。每页id唯一；route对应真实HTML，可以使用hash页面；viewport记录实际目标CSS宽高。transitions记录每个主要跳转或状态动作，例如 `{"id":"open-detail","from":"mobile-home","to":"mobile-detail","trigger":"点击预约卡片","result":"显示详情"}`。返回／关闭等主要动作也加入。

脚本只检查确认记录存在及一致性，不能证明用户真的批准；专家必须依据真实对话填写，不为通过检查伪造确认。

## 真实预览回执

在本机启动静态服务并用宿主浏览器打开入口。各页在声明的视口检查／截图，按跳转表点击主要流程。浏览器成功截图不等于自动视觉通过，还须对照采用图检查层级、布局、颜色、文字、遮挡和跨页一致性。必要修复后重新检查。

将实际截图存到preview，填写verification.json：

- status：not_run／partial／passed，checked_at写真实时间；limitations据实填写。
- pages：每项含page_id、viewport（与页面清单一致）、screenshot（preview内路径）、result（passed／failed）、notes（实际观察）。
- flows：每项含transition_id、result（passed／failed）、notes（实际点击与结果）。全部主要转换与各页均通过才可passed。
- source_hashes：最终文件完成时运行fingerprint，取其source_hashes字段；在这些文件上完成检查后保留同一指纹。代码、需求、规范、页面映射或采用图改动后旧回执会失效，需重新验证受影响内容并更新记录。README随后写实际检查说明，不参与指纹，避免文字更新造成循环。

脚本验证截图文件存在、页面／流程覆盖和指纹，不检测截图内容是否真实，不能自动证明审美或交互质量。严禁为消除报错编造passed。无浏览器可保留not_run或partial，用 `pack --allow-unverified-preview` 交付，并在README及回复明确未验证；不能以此宣称完成预览验收。

## 交付与限制

pack默认要求预览回执通过，输出单层prototype目录的ZIP，原输出不同字节时拒绝覆盖；使用新文件名保留旧版。只包含清单文件、三份文档、采用图、页面映射和预览回执／截图，不打包候选稿、OAuth信息、短期链接、内部Designer Skill、node_modules或任务恢复记录。

静态检查会拒绝外部运行资源、缺失本地资源、越界路径、无确认页面、参考图哈希变化和明显凭证内容；它不是完整代码安全审计。仍须检查JS动态资源、页面实际可用性及包内素材使用范围。仅文件清单通过不能声称浏览器或Qoder客户端已验收。

最终回复给出代码ZIP、实际预览入口／截图、启动方法和一两句模拟范围及未完成项。预览仅在服务运行期间有效，不称永久链接；公共托管另按用户明确要求处理。图片阶段已发生费用与代码交付状态分别说明，不能假称免费生成。
