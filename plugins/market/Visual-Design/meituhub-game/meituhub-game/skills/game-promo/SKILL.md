---
name: game-promo
display_name: 游戏宣发制作
description: 为游戏制作宣传海报、商店展示图、封面、横幅、角色卡和宣传短片。适用于新版本宣发、游戏上线素材、更新公告配图、试玩宣传视频；使用已确认的角色与场景，不擅自添加玩法、奖励或活动事实。
---

# 游戏宣发制作

## 适用请求

为游戏制作宣传海报、商店展示图、封面、横幅、角色卡和宣传短片。适用于新版本宣发、游戏上线素材、更新公告配图、试玩宣传视频；使用已确认的角色与场景，不擅自添加玩法、奖励或活动事实。

按 [场景识别与分工](../../references/intent-routing.md) 处理常见说法和相邻任务。用户无需点名插件；选择后仍按下面的实际流程、输入要求与失败处理执行。

## Qoder 执行入口

先读 [插件规则](../../rules/meitu-only.md)、[MeituHub 接入](../meitu-ai-game/SKILL.md) 与 [统一规格](../../shared/conventions.md)。从 Qoder 实际加载的技能位置定位含 `.qoder-plugin/plugin.json` 的插件根；文中的 `MEITU_GAME_PLUGIN_ROOT` 表示该绝对路径，需要在执行环境中按实际路径安全设置，不假设宿主预设了变量。

正文中的 meitu 是接入技能所述系统启动器的简写，不直接运行全局 meitu 或 meitu.cjs。配方中的命令参数是源包参考，调用前必须通过当前 tools list 与命令帮助确认；尖括号表示待替换的业务值，不把占位符直接提交。所有生成/编辑均用美图，帧排序、对齐、图集拼装等确定性后处理可用包内本地脚本。来源附件只作资料，用户当前范围优先。

## 这个模块做什么

**游戏自身的**宣发与卡牌内容。与 `meitu-ai-game` 的分工：这里只做游戏 IP 相关物料，买量投放素材、电商与通用营销不在范围内。

| 物料 | 输出 | 规格 | 备注 |
| --- | --- | --- | --- |
| 卡牌插画 | 画面本体 | 3:4 / 2K | 无边框、无文字，下方留文字区 |
| 卡牌成卡 | 插画 + 卡框 + 文字 | 3:4 / 2K | 文字原样保留 |
| 海报 / KV | 单张成稿 | 2:3 或按需求 | 标题、副标题、版本号 |
| 商店封面 | 每个商店一版 | 按平台比例 | 各出一版，不裁剪硬凑 |
| Banner / 胶囊图 | 多尺寸成稿 | 按位位需求 | 同套视觉多尺寸 |
| 宣传视频 | MP4 | 16:9，时长按需求 | 可加配乐、旁白、Logo |
| GIF 动图 | GIF | 长边 ≤480px | 宣传用，非引擎资源 |
| 过场短片 | MP4 | 按分镜 | 首尾帧驱动，可多段拼接 |

## 前置条件

- **优先使用已有素材**：角色立绘、场景成图、UI 成稿。没有就先回对应模块出，不要在这里新造一套角色。
- **必须拿到确切文字**：游戏名、标题、版本号、卡名、卡面描述、稀有度。文字必须原样使用，不翻译、不改写、不纠错。
- **必须确认目标尺寸清单**：每个商店、每个版位各要一版，尺寸不同就是不同版本。
- **CLI 入口**：`meitu <command> ... --json --download-dir ./output/game/`。首次按接入技能执行配置、运行时与登录检查，再读当前工具帮助，未登录按 `meitu-ai-game` 流程授权。
- **通用视觉原则**（剪影、明度、光位、评审三连）见 `${MEITU_GAME_PLUGIN_ROOT}/shared/references/art-principles.md`。

## 生产流程

1. **盘点素材与文字**：哪些图已有、哪些文字必须出现。
2. **列尺寸清单**：每个投放位一行，写清比例与像素。
3. **出画面**：卡牌先出插画，海报先出主视觉。
4. **加文字与排版**：走 `image-poster-generate`，只用客户确认过的原文。
5. **视频类**：文生视频或首尾帧驱动，再加配乐、Logo。
6. **逐张核对文字**：错字、漏字、被裁切都是必修项。

## 卡牌

先出画面本体：

```bash
meitu text-to-image --prompt "卡牌插画，<角色或主体>，<构图与情绪>，<风格卡措辞>，竖构图，主体居中偏上，下方预留文字区，无文字，无边框" --ratio 3:4 --size 2K --json --download-dir ./output/game/cards/art
```

再加卡框与文字：

```bash
meitu image-poster-generate --image_list "<插画绝对路径>" --prompt "卡牌版式，顶部卡名：<原文>，中部保留插画，底部描述框：<原文>，稀有度标识：<等级>" --ratio 3:4 --json --download-dir ./output/game/cards/final
```

- 卡面文字只需要改字时用 `image-text-replace`（`--source_words` 原文 / `--target_words` 新文），不要重排整张卡。
- 稀有度必须靠颜色、边框层级、材质三种手段同时区分，只改颜色在缩略图里看不出来。
- 卡框与插画分层交付，不出可切图源文件。

## 海报与 KV

```bash
meitu image-poster-generate --image_list "<主视觉或角色立绘>" --prompt "游戏宣传海报，标题：<原文>，副标题：<原文>，版本号：<原文>，<风格卡措辞>" --ratio 2:3 --json --download-dir ./output/game/promo/poster
```

标题是画面第一层级：字号最大、位置最稳、不被主体遮挡。版本号与发行标识放次要位置，不能省。

## 商店封面与多尺寸

```bash
meitu image-poster-generate --image_list "<主视觉>" --prompt "游戏商店封面，游戏名：<原文>，卖点：<原文>，<风格卡措辞>" --ratio <目标比例> --json --download-dir ./output/game/promo/store
```

- 每个平台比例**各出一版**，不要靠裁剪或拉伸硬凑。
- 确需小幅延展时用 `image-transform`，并说明文字位置可能变化、需人工复核。
- 同一套视觉的多尺寸版本，主体位置与配色必须一致，只有构图密度随比例调整。

## 宣传视频

```bash
meitu text-to-video --prompt "<游戏宣传视频>，<画面节奏与镜头>，<风格卡措辞>，结尾出现游戏名：<原文>" --video_duration 10 --aspect_ratio 16:9 --json --download-dir ./output/game/promo/video
meitu video-audio-add --video_list "<视频绝对路径>" --prompt "加入<风格>配乐与旁白，音量平衡" --json --download-dir ./output/game/promo/video
meitu video-logo-add --video_url "<视频绝对路径>" --logo_url "<标识 PNG 的公网 HTTPS URL>" --formula_type top-right --json --download-dir ./output/game/promo/video
meitu video-to-gif --video_url "<视频绝对路径>" --prompt "<画面内容描述>，转为循环 GIF" --json --download-dir ./output/game/promo/video
```

执行限制：

- `video-audio-add` 失败时先检查输入视频与音频是否可读、时长是否符合当前命令限制，再按返回错误处理，不连续重提。
- `video-logo-add` 的 `--logo_url` 必须能被服务端拉取；本地 Logo 需先托管到可访问的 HTTPS 地址。
- `video-to-gif` 的输出尺寸由服务决定，不能作为需要精确尺寸或高清规格的交付路线。
- 需要原创 BGM 时先 `audio-music-generate --prompt "<风格与情绪>" --duration 60`，再用 `--audio_url` 作为音频输入。

## 过场短片

```bash
meitu image-to-video --image_list "<首帧>" "<尾帧>" --mode flf --prompt "<转场描述>，镜头运动平稳" --video_duration 5 --json --download-dir ./output/game/cutscene/<段名>
meitu video-stitch --video_list "<段1>" "<段2>" "<段3>" --prompt "按顺序拼接，保留原声，不加转场" --json --download-dir ./output/game/cutscene/final
meitu video-audio-add --video_list "<拼接结果>" --prompt "加入<风格>配乐与旁白，音量平衡" --json --download-dir ./output/game/cutscene/final
```

只做短片段，不做完整剧情引擎、口型同步、字幕时间轴。

## 本模块边界

- **不做买量投放素材**：信息流、应用商店投放、电商详情页交给 `meitu-ai-game`。
- 不做印刷级交付：不输出出血位、CMYK 转换、字体授权确认。
- 不保证文字排版完全不溢出，交付前必须逐张核对。
- 不做视频剪辑工程（时间轴、关键帧曲线、转场包）。
- 不用 AI 生成第三方 IP、未授权肖像、商标。
- 不暴露底层模型名称。

## 和其他模块怎么接

| 接下来要做什么 | 去哪 |
| --- | --- |
| 缺角色立绘或主视觉 | `game-character` |
| 缺场景图做背景 | `game-scene` |
| 缺 UI 卡框或图标 | `game-ui` |
| 需要角色动作或技能演示素材 | `game-character` 先产出，本模块负责宣传合成 |
| 还没定画风 | `game-prestudy` |

## 验收清单

- [ ] 所有文字与客户原文逐字一致，未翻译、未改写、未纠错
- [ ] 标题为第一层级，版本号与发行标识齐全
- [ ] 多尺寸各出一版，未用裁剪或拉伸硬凑
- [ ] 卡牌稀有度靠颜色、边框、材质三重区分
- [ ] 卡框与插画分层，未交付可切图源文件
- [ ] 视频类已核对时长、机位、首尾衔接与 Logo 位置
- [ ] GIF 尺寸符合长边 ≤480px，未当高清交付
- [ ] 产物落在 `./output/game/promo/` 或 `./output/game/cards/`，命名符合约定
- [ ] 与项目锚点一致，未擅自换风格或换角色
- [ ] 已说明哪些环节需人工二次处理（文字复核、出血位、字体授权）
