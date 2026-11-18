# 设计稿总览：同一个预览区入口反复审图

基准页采用、其余主要页面生成完成后，先交付图片总览，再等整组确认。这个HTML只是图片审阅工具，不是最终可交互软件原型；此时不得提前提取正式DESIGN.md或写产品界面代码。

恢复旧对话或继续修改时先读当前board.json及实际下载记录，确认本轮要更新的是同一总览。不能等用户“采用新版”才把新版放进总览；展示最新版是让用户能做采用决定的前提。更新总览已经属于改图请求，不再询问许可。

## 必须呈现的内容

- 按需求页表平铺全部页面，每页一张，包含用户采用的基准页。页面名称写在图上方，另标手机／PC、版本、基准页和已采用／待确认。
- 采用的是基准页r02就显示r02，不能把未采用r01和r02当成两个页面。之后用户要改基准页时仍只显示当前新版，标“修改待确认”；旧采用图保留在版本记录中，不默默视为已批准新版。
- 图片按原始比例完整展示，不裁掉底部导航或长图内容；手机竖图和PC横图自适应平铺，可点击放大。总览的中性框架不能修改原效果图。
- 固定入口 `design-review/index.html`，稳定页面ID。每轮只替换指定页面的当前版本；未改页保持。新结果下载失败则保留旧图，并说明哪页尚未更新。
- “最新显示版本”与“已采用版本”分别记录。整组确认对应当前具体页面和图片哈希；任何新版都会撤销旧的整组通过状态，等用户再次确认。

总览放在最终 `prototype/` 的兄弟目录，旧稿、历史与任务记录不进入最终代码ZIP。纯图片文件只需离线HTML展示，不必启动开发服务器。

## 脚本与清单

随包 [design_board.py](../scripts/design_board.py) 使用Python 3.10+标准库，支持初始化、单页／多页更新、再渲染、检查和记录整组确认，不联网、不生图。定位Skill的实际绝对目录后调用，不假设当前工作目录就是Skill目录。

首先根据已有需求写 `board-plan.json`，列全本轮页面（下面只是结构示例）：

```json
{
  "title": "项目名称",
  "pages": [
    {"id":"mobile-home","name":"首页","terminal":"mobile","baseline":true},
    {"id":"mobile-list","name":"列表","terminal":"mobile","baseline":false}
  ]
}
```

```sh
python3 '/absolute/skill/scripts/design_board.py' init --root '/absolute/work/design-review' --input '/absolute/work/board-plan.json'
```

写 `board-update.json`。首次加入基准页与其余各页；后续仅列本轮生成成功的修改页，可以一次多页。图片路径必须指向真实下载的PNG/JPEG/WebP。下面的路径、作品ID和采用依据须换成真实值：

```json
{
  "pages": [
    {"id":"mobile-home","version":"r02","image":"/absolute/work/screens/mobile-home-r02.jpg","source":"shenhuo","variant_id":"实际基准图作品ID","adoption_note":"用户实际采用该基准图的原话或上下文"},
    {"id":"mobile-list","version":"r01","image":"/absolute/work/screens/mobile-list-r01.jpg","source":"shenhuo","variant_id":"实际列表图作品ID"}
  ]
}
```

用户提供图设置 `source:"user"`、`variant_id:null`。新图尚未批准就不写 `adoption_note`；不要复制旧版采用依据给新版。每次用新的版本号，不覆盖已有图片。

```sh
python3 '/absolute/skill/scripts/design_board.py' update --root '/absolute/work/design-review' --input '/absolute/work/board-update.json'
python3 '/absolute/skill/scripts/design_board.py' check --root '/absolute/work/design-review' --expected '/absolute/work/board-update.json'
```

脚本保存 `board.json` 和版本图片，重新生成同一 `index.html`，最后写入`preview-state.json`刷新标记。check --expected用**本轮真实下载清单**核对版本、来源、作品ID和实际图片哈希，并检查当前HTML和刷新标记同步；不能拿总览自身旧数据生成expected来掩盖漏更新。漏一页或只改JSON未重新渲染都会失败。update若因版本已存在而失败，先check --expected；只有对应当前结果确实一致时可按已更新继续，不能为避错另造新版本。

图片内嵌，不依赖临时签名链接或CDN。未生成的计划页会显示缺项，缺页不能整组通过；完整首轮做好再呈现给用户。旧版总览升级后可先执行render生成新版HTML及刷新标记。运行失败不能宣称总览已更新。

## 在当前宿主打开

按[预览规则](preview.md)使用Qoder实际可用的文件展示、HTML预览或浏览器工具，支持右侧时优先右侧。每轮更新、check --expected之后刷新同一个入口并看到新版本；无预览能力时如实说明，不编造已打开。用户明确当前整组确认并要求下一步之前继续审稿。

## 整组确认与交接

用户明确认可当前全部效果图后，使用真实原话记录确认（下方文字为占位，不能照抄充当批准）：

```sh
python3 '/absolute/skill/scripts/design_board.py' confirm --root '/absolute/work/design-review' --note '用户本轮真实的整组采用依据'
python3 '/absolute/skill/scripts/design_board.py' check --root '/absolute/work/design-review' --require-confirmed
```

确认工具只检查记录和文件一致性，无法证明用户真的批准，专家必须以真实对话为依据。它不接受只把状态改为passed，任何新版本都会使旧确认失效。用户明确退回旧版时，可在board.json中把该页current_version与adopted_version指向实际旧版本、记录本次选择依据并清除confirmation，再render；不得删除新旧历史。随后重新确认当前整组。

检查通过后，读取输出pages中各页current的本地图片、哈希、来源和作品ID，复制最终采用图到 `prototype/reference/`，填写prototype.json的采用记录，再提取DESIGN.md并实现真实DOM和页面跳转。不要把审图HTML或整页图片热点当成交互原型交付。后续若主要视觉要改，回到这个总览入口继续迭代。
