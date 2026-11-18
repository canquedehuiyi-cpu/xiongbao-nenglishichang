# 物料配方

所有命令追加 `--json --download-dir ./output/game/<物料单元>`，执行前用 `<command> --help` 确认当前版本参数与取值。`--ratio` 的可选值以 CLI 实际输出为准。

本文件只使用以下真实命令：`text-to-image`、`image-edit`、`image-poster-generate`、`image-cutout`、`image-style-transfer`、`image-background-replace`、`image-text-replace`、`image-transform`、`image-grid-split`、`image-superres-enhance`、`image-denoise-enhance`、`image-lowlight-enhance`、`text-to-video`、`image-to-video`、`video-motion-transfer`、`video-effect-apply`、`video-stitch`、`video-audio-add`、`video-logo-add`、`video-to-gif`、`text-generate`、`audio-music-generate`。

## 品类方案

拿到品类之前不要开跑。品类决定视角、素材清单和 UI 密度。完整物料包、推荐画风与边界见 [品类矩阵](genre-matrix.md)。

| 场景 | 品类 | 默认视角 | 常用风格 | 核心物料清单 | 易踩的坑 |
| --- | --- | --- | --- | --- | --- |
| 轻量休闲 | 休闲小游戏 | 竖版 9:16 或俯视 1:1 | 矢量扁平、极简几何、黏土玩具感 | 主视觉、关卡背景、图标按钮、简单道具、少量角色 | 素材多而小，UI 一致性比单张精度更重要 |
| 竖版卡牌 | 卡牌游戏 | 竖版 9:16，单卡 3:4 或 2:3 | 日式赛璐璐、暗黑哥特、写实 | 卡牌插画、卡框、图标、稀有度底板、主视觉 | 卡面文字必须原样保留，卡框与插画层级不能乱 |
| 等距经营 | 经营养成 | 等距 2.5D 1:1 或 4:3 | 欧美卡通厚涂、童话绘本、低多边形 | 地表底图、独立建筑、道具、角色立绘与表情、UI 面板 | 建筑与地块要在网格上对齐；角色要出表情组 |
| 剧情叙事 | 剧情游戏 | 横版 16:9 或竖版 9:16 | 日式赛璐璐、中式水墨、写实 | 角色立绘与表情组、背景分层、CG 插画、过场短片 | 同角色多表情、多姿态必须共用一张设定卡 |

## 按阶段取素材

| 阶段 | 典型素材 | 精度与规格 |
| --- | --- | --- |
| 立项 / 概念 | 美术方案、气氛图、Key Art、风格试稿 | 单张 2K，可不分层、不抠图 |
| 原型 / 预研 | 占位图、灰模、构图稿 | 快速出图，允许细节缺失，便于后续替换 |
| 预制作 / 美术定调 | 风格锚点图、角色设定卡、色板、Color Script | 2K 起；锚点质量决定后续全部素材 |
| 制作 / 量产 | 角色立绘与表情、道具单体、分层背景、UI 图标、卡牌插画、精灵图集 | 分层按远/中/近三层，单体透明底，图集等分宫格 |
| 打磨 / Alpha-Beta | 加载图、多语言改字、换肤、画质重制 | 按目标机型尺寸延展，必要时超分 |
| 发行 / 运营 | 游戏海报、商店封面、宣传视频、活动皮肤 | 多尺寸各出一版，不靠裁剪硬凑 |

## 视角配方

| 视角 | 默认画幅 | 构图关键词 | 分层建议 | 常见用途 |
| --- | --- | --- | --- | --- |
| 横版卷轴 | 16:9 | 侧视角、平视或轻微俯视、横向延展、左右可循环 | 远景天空与山脉 / 中景建筑与地形 / 前景遮挡物与雾 | 平台跳跃、动作、跑酷、剧情游戏 |
| 等距 2.5D | 1:1 或 4:3 | 45 度等距俯视、isometric、正交投影、无透视畸变 | 单张地表底图 / 独立建筑与道具层 | SLG、模拟经营、暗黑类（2D 等距绘制，不是 3D 模型） |
| 竖版手游 | 9:16 | 竖构图、主体居中、上 1/4 与下 1/5 保留 UI 空白 | 背景层 / 中景装饰 / 前景遮挡 | 休闲、消除、卡牌、竖版 RPG |
| 俯视地图 | 1:1 | 正俯视 top-down、正交、边缘规整 | 地表底图 / 建筑、植被、道路独立层 | 战棋、沙盒、地图场景 |

## 风格定位

完整画风库、关键词、视觉特征与生产链路见 [画风库](style-library.md)。不要只凭一个风格词开工，先按五层定位：

1. **画面形态**：2D 插画 / 像素 / 2.5D 等距 / 3D 观感（低多边形、体素、黏土）。
2. **写实度**：写实 / 半写实 / 风格化 / 卡通 / Q 版 / 极简。
3. **上色媒介**：平涂 / 赛璐璐 / 厚涂 / 半厚涂 / 手绘纹理 / 水彩 / 水墨 / 版画 / 纸雕 / 单色。
4. **题材**：日式 / 韩式 / 中式古风 / 暗黑哥特 / 赛博 / 蒸汽 / 废土 / 童话 / 科幻 / 诡异未知。
5. **视角与情绪**：横版 / 等距 / 俯视 / 竖版；饱和度、色温、对比、光位。

每次抽 3–4 个**组合候选**呈现给用户，附一句适用说明，不固定顺序。

快速对照：

- 日式：日式赛璐璐、日式厚涂/半厚涂、韩式半写实。
- 欧美：欧美卡通、欧美厚涂/手绘纹理、写实/半写实、美漫/墨线。
- 国风：水墨、工笔、青绿山水。
- 氛围：暗黑哥特、赛博朋克、蒸汽朋克、末世废土、诡异未知。
- 轻量：极简扁平/矢量、纸雕/拼贴、单色/版画、童话绘本。
- 3D 观感：低多边形、体素、黏土/定格（只做 2D 画面观感，不输出模型）。

## 整体美术方案

不直接出图，先生成方案文本：

```bash
meitu text-generate --summary "为<品类>游戏输出一页美术方案，包含：3 个美术方向候选（各附画面描述与适用理由）、主色板、视角与画幅、物料清单与优先级、以及风险点" --language zh-CN --json --download-dir ./output/game/art-direction
```

选定方向后，再出锚点与设定卡，进入量产。

## 素材类型模板

### 风格锚点

先按 [画风库](style-library.md) 写一张风格卡：主色 HEX、描边粗细、明暗级数、材质关键词、细节密度、禁止项。同一项目只用一个风格锚点。

```bash
meitu text-to-image --prompt "<题材>，<画面形态与视角>，<写实度>，<上色与线条>，<色彩>，<光照>，<材质与细节密度>，<构图与留白>，<主体场景>，<时段与天气>，无文字" --ratio <画幅> --size 2K --json --download-dir ./output/game/anchor
```

### 角色设定卡（角色锚点，必做）

```bash
meitu text-to-image --prompt "游戏角色设定图，<角色名与职业>，<体型与年龄感>，<发型与服装>，<配色>，正面全身站姿，纯色背景，居中，同一角色只出现一次，无文字，<风格措辞>" --ratio 3:4 --size 2K --json --download-dir ./output/game/<角色名>/anchor
```

确认后作为该角色唯一参考。

### 角色立绘

```bash
meitu image-edit --image_list "<角色设定图绝对路径>" --prompt "同一角色的半身立绘，<姿态与情绪>，保持发型、服装、配色、体型与画风不变，纯色背景，无文字" --ratio 3:4 --json --download-dir ./output/game/<角色名>/portrait
```

### 角色表情组

单张逐出或用宫格。宫格更省，但一致性靠锚点：

```bash
meitu image-edit --image_list "<角色设定图绝对路径>" --prompt "2x3 均分宫格，同一角色的六个表情：平静、微笑、愤怒、惊讶、悲伤、得意，同一视角同一比例，每格背景纯色，格间留细白分隔线" --ratio 1:1 --json --download-dir ./output/game/<角色名>/expression
meitu image-grid-split --image_url "<宫格图绝对路径>" --json --download-dir ./output/game/<角色名>/expression/frames
```

### 多方向视图

```bash
meitu image-edit --image_list "<角色设定图绝对路径>" --prompt "1x3 均分宫格，同一角色的正面、侧面、背面三视图，同一比例同一站姿，纯色背景，格间留细白分隔线" --ratio 3:1 --json --download-dir ./output/game/<角色名>/turnaround
meitu image-grid-split --image_url "<宫格图绝对路径>" --json --download-dir ./output/game/<角色名>/turnaround/frames
```

### 道具与建筑单体

```bash
meitu text-to-image --prompt "游戏道具单体，<物件描述>，<风格措辞>，纯白背景，正面 3/4 视角，居中，无投影，无文字" --size 2K --json --download-dir ./output/game/<单元>/props
meitu image-cutout --image_url "<单体图绝对路径>" --model_type 1 --json --download-dir ./output/game/<单元>/props/cutout
```

生成后按主体类型抠图：道具与商品走 `model_type 1`，图标与符号走 `model_type 2`。建筑一次只试一张，效果不达标就交付白底图。

### 场景概念图

```bash
meitu text-to-image --prompt "<视角>，<风格措辞>，<场景主体>，<时段与天气>，<光源方向>，<镜头高度>，<构图描述与留白要求>，高细节，无文字" --ratio <画幅> --size 2K --json --download-dir ./output/game/<场景名>
```

### 视差分层背景

逐层生成，每层单独描述并把其他层显式排除。示例措辞：

- 远景：`仅远景层，天空与远山，<时段>，无建筑无前景物体，画面下方大片留空`
- 中景：`仅中景层，<主要建筑或地貌>，<风格措辞>，背景为纯色，无天空无前景遮挡`
- 前景：`仅前景遮挡物，<岩石或植被剪影>，背景纯色便于抠图，边缘清晰`

需要把某层主体单独提取时：

```bash
meitu image-cutout --image_url "<分层图绝对路径>" --model_type 2 --json --download-dir ./output/game/<场景名>/cutout
```

### UI 图标

```bash
meitu text-to-image --prompt "游戏 UI 图标，<图标含义>，<风格措辞>，扁平或微立体，正视角，居中，纯白背景，无文字，无投影，统一圆角与描边粗细" --size 1K --json --download-dir ./output/game/ui/icons
meitu image-cutout --image_url "<图标图绝对路径>" --model_type 2 --json --download-dir ./output/game/ui/icons/cutout
```

同组图标必须用同一锚点与同一段措辞批量出，否则线宽与圆角会漂移。图标建议一次出一张，不为了省事塞进宫格。

### UI 按钮与面板

```bash
meitu text-to-image --prompt "游戏 UI <按钮或面板>，<用途>，<风格措辞>，正面平视，居中，边缘清晰，预留文字区，无文字内容，无投影" --ratio 3:1 --size 2K --json --download-dir ./output/game/ui/panel
```

只交付成品位图。九宫格拉伸配置、切图源文件不在能力范围内。

### 卡牌插画

先出画面本体：

```bash
meitu text-to-image --prompt "卡牌插画，<角色或主体>，<构图与情绪>，<风格措辞>，竖构图，主体居中偏上，下方预留文字区，无文字，无边框" --ratio 3:4 --size 2K --json --download-dir ./output/game/cards/art
```

再加卡面文字与卡框（客户给的确切文字原样保留）：

```bash
meitu image-poster-generate --image_list "<插画绝对路径>" --prompt "卡牌版式，顶部卡名：<原文>，中部保留插画，底部描述框：<原文>，稀有度标识：<等级>" --ratio 3:4 --json --download-dir ./output/game/cards/final
```

卡面文字只需要改字时用 `image-text-replace`，不要重排整张卡。参数是 `--source_words`（原文）与 `--target_words`（新文），`--prompt` 只是可选补充，单独传它定位不到要改的字：

```bash
meitu image-text-replace --image_url "<成卡绝对路径>" --source_words "<原文>" --target_words "<新文>" --json --download-dir ./output/game/cards/final
```

### 风格统一与换肤

整套画风统一：

```bash
meitu image-style-transfer --image_url "<原图>" "<风格参考图>" --prompt "<目标风格措辞>，保持构图、主体位置与画面比例不变" --json --download-dir ./output/game/<单元>/styled
```

批量统一时，参考图与措辞必须逐字一致，只替换原图。

注意：`image-style-transfer` 会重绘主体造型，不是滤镜级的材质替换，同一角色或道具经它处理后外形细节会漂移。需要严格保持造型不变的资产（角色、武器、图标），改用 `image-edit` 并明确写出「保持外形轮廓、零件位置与比例不变」，风格迁移只用于氛围与质感统一。

`image-edit`、`image-style-transfer`、`image-background-replace`、`image-superres-enhance` 的输出均为不透明 JPG，透明底会丢失。需要透明 PNG 的物料，先做编辑与风格处理，最后一步再用 `image-cutout` 抠图。

角色换肤（只改配色与材质，不换款式）：

```bash
meitu image-edit --image_list "<角色设定图或立绘绝对路径>" --prompt "只替换配色与材质为<新方案>，保持姿势、构图、比例、发型与体型完全不变，背景不变" --json --download-dir ./output/game/<角色名>/skin
```

角色换装（换整套服装款式）用 `image-edit` 传双图：第一张角色底图，第二张用户自有或已授权的服装设计图。`--image_list` 支持多张，第一张是底图，其余是设计输入。

```bash
meitu image-edit --image_list "<角色设定图输入文件>" "<已授权服装设计图>" --prompt "第一张是角色原图，第二张是已授权服装设计图。提取其款式、配色与材质特征并适配到角色。保持角色的脸、发型、体型、姿势、手持物、构图、画幅和<画风>不变，背景不变，只改服装设计与配色" --ratio 3:4 --json --download-dir ./output/game/<角色名>/outfit
```

服装参考图先单独出，用 `text-to-image` 生成平铺服装设计图（无人物、纯色背景、居中、无文字），不要用角色穿新衣的图当参考，否则参考图里的身体会污染底图。

注意：**不要用 `image-outfit-swap` 做游戏角色换装**。该命令定位为真人试衣，目标是保留真人面部与身体、只替换衣物；用于 2D 插画角色时会把五官、发型、冠饰与手部一并重绘，角色一致性直接丢失，画面还会偏向真人渲染质感、丢掉原画风。`image-edit` 传双图能覆盖「按参考图换装」这一需求，且角色与画风保持更好。

换装后如需透明底或新表情组，仍按原流程走：换装图作为新的角色锚点，重新出表情宫格与动作序列，再在最后一步 `image-cutout` 抠透明底。

场景换背景氛围：

```bash
meitu image-background-replace --image_url "<场景图绝对路径>" --prompt "<新背景描述>，保持前景主体不变" --json --download-dir ./output/game/<场景名>/skin
```

### 精灵图集与序列帧

动作物料由 `game-character` 的动态流程负责。动作拆解、路线决策、视频抽帧、逐帧姿态参考、对齐门禁和导出格式统一见 [动作拆解](animation-breakdown.md)，本通用配方不维护第二套流程。

- 正式 GIF 或图集默认使用连续视频抽帧，静态宫格只作动作概念稿。
- 需要精确控制关键姿态时使用逐帧姿态参考。
- 后处理只统一画布、锚点和缩放，不能修复姿态、朝向、手型或肢体拓扑错误。
- 通过静态与动态门禁后，才导出图集、JSON 和预览 GIF。

### 角色动作短片

动作视频走「单张角色图 → 图生视频」，输入只用一张角色图（锚点或立绘）。

```bash
meitu image-to-video --image_list "<角色锚点图绝对路径>" --prompt "<角色>完成<动作>，<镜头说明>，保持角色发型服装配色不变，纯色或简单背景" --video_duration <覆盖完整动作的最短可用时长> --json --download-dir ./output/game/<角色名>/motion
```

注意：**不要把宫格关键帧图喂给 `image-to-video`**。模型把整张宫格当成一张参考图理解，输出的是单个角色的动作，不会按格逐帧联动。

视频输入数量与模式以当前命令帮助和服务端校验为准。不要把拆帧图片列表当作时间序列输入；需要连续动作时使用连续视频路线，需要首尾过渡时使用当前命令支持的首尾帧模式。

`image-to-video` 默认会自行加镜头。需要严格机位时显式传 `--multi_shot false`，并在提示词里写「固定机位、无运镜、角色不位移」。

有动作参考视频时，可把姿态迁移到角色图上。输入时长以当前命令帮助为准，参考素材必须完整包含动作识别所需的人体区域；检测失败时更换构图清晰、人物完整的参考视频。

```bash
meitu video-motion-transfer --image_list "<角色图绝对路径>" --reference_video_list "<动作参考视频>" --prompt "保留原视频动作节奏，保持角色外貌不变" --video_duration <覆盖完整动作的最短可用时长> --json --download-dir ./output/game/<角色名>/motion
```

### 技能特效

序列帧：

```bash
meitu text-to-image --prompt "2x3 均分宫格，<技能名>特效的连续帧，每格一帧，纯色深底，中心发光，无角色，格间留细白分隔线，<风格措辞>" --ratio 3:2 --json --download-dir ./output/game/fx/<技能名>
```

短片：

```bash
meitu text-to-video --prompt "<技能特效描述>，由蓄力到爆发到消散，纯色或简单背景，无角色，<风格措辞>" --video_duration <覆盖完整特效的最短可用时长> --json --download-dir ./output/game/fx/<技能名>
```

已有视频要套风格或转绘时用 `video-effect-apply`，只套预设，不重画内容。长任务超时后按返回结果处理；没有可查询任务标识时不要盲目轮询或重复提交，可缩短输入片段后重试。

```bash
meitu video-effect-apply --video_url "<原视频绝对路径>" --prompt "<目标风格>，保持动作节奏与运镜不变" --json --download-dir ./output/game/fx/<技能名>/styled
```

### 剧情过场

```bash
meitu image-to-video --image_list "<首帧>" "<尾帧>" --mode flf --prompt "<转场描述>，镜头运动平稳" --video_duration 5 --json --download-dir ./output/game/cutscene/<段名>
```

多段拼接与配音配乐：

```bash
meitu video-stitch --video_list "<段1>" "<段2>" "<段3>" --prompt "按顺序拼接，保留原声，不加转场" --json --download-dir ./output/game/cutscene/final
meitu video-audio-add --video_list "<拼接结果>" --prompt "加入<风格>配乐与旁白，音量平衡" --json --download-dir ./output/game/cutscene/final
```

需要原创 BGM 时先 `audio-music-generate --prompt "<风格与情绪>" --duration 60` 生成（时长 30–120 秒），再用 `--audio_url` 作为音频输入。

`video-audio-add` 失败时先确认输入视频与音频可读、时长符合当前命令限制，再按返回错误决定是否重试，不连续重提。

### 游戏海报与商店封面

```bash
meitu image-poster-generate --image_list "<主视觉或角色立绘>" --prompt "游戏宣传海报，标题：<原文>，副标题：<原文>，版本号：<原文>，<风格措辞>" --ratio 2:3 --json --download-dir ./output/game/promo/poster
```

商店封面按各商店要求的比例**各出一版**，不要靠裁剪或拉伸硬凑；确需小幅延展时再用 `image-transform`，并说明文字位置可能变化、需人工复核：

```bash
meitu image-poster-generate --image_list "<主视觉>" --prompt "游戏商店封面，游戏名：<原文>，卖点：<原文>，<风格措辞>" --ratio <目标比例> --json --download-dir ./output/game/promo/store
```

### 宣传视频

```bash
meitu text-to-video --prompt "<游戏宣传视频>，<画面节奏与镜头>，<风格措辞>，结尾出现游戏名：<原文>" --video_duration 10 --aspect_ratio 16:9 --json --download-dir ./output/game/promo/video
meitu video-audio-add --video_list "<视频绝对路径>" --prompt "加入<风格>配乐与旁白，音量平衡" --json --download-dir ./output/game/promo/video
meitu video-logo-add --video_url "<视频绝对路径>" --logo_url "<标识 PNG 的公网 HTTPS URL>" --formula_type top-right --json --download-dir ./output/game/promo/video
meitu video-to-gif --video_url "<视频绝对路径>" --prompt "<画面内容描述>，转为循环 GIF" --json --download-dir ./output/game/promo/video
```

`video-to-gif` 的输出尺寸由服务决定，不能作为需要精确尺寸或高清规格的交付路线。

`video-logo-add` 的 `--logo_url` 必须能被服务端拉取。CLI 没有上传命令，本地 Logo 需先托管到可访问的 HTTPS 地址。

### 尺寸延展与画质重制

```bash
meitu image-transform --image_url "<原图绝对路径>" --target_width <宽> --target_height <高> --prompt "向两侧自然延展场景，保持地平线高度与光源方向不变，不新增主体" --json --download-dir ./output/game/<单元>/adapt
meitu image-superres-enhance --image_url "<原图绝对路径>" --prompt "<画面内容描述>，提升清晰度并保留原风格" --json --download-dir ./output/game/<单元>/upscale
meitu image-denoise-enhance --image_url "<原图绝对路径>" --json --download-dir ./output/game/<单元>/denoise
meitu image-lowlight-enhance --image_url "<原图绝对路径>" --json --download-dir ./output/game/<单元>/brighten
```

分工：`image-transform` 改画幅不改内容，`image-superres-enhance` 改清晰度不改画幅。不要用超分代替扩图，也不要用扩图修补画质。

`image-transform` 输出为不透明图，透明底精灵经它缩放会丢失 alpha。抠图后的角色、道具、图标要缩放，交给引擎或图像工具处理，不要走这条命令。

## 五类素材族配方（动画 / 转面 / 风格 / 场景地图 / UI）

五类方向适合成套生产：先定族规格，再一次性出整族。同族必须共用锚点、视角、方向命名、画幅、色板与验收线，不要一张张散着出。

| 族 | 交付物 | 推荐画幅 | 数量建议 | 必须锁死 |
| --- | --- | --- | --- | --- |
| 动画序列帧 | 序列帧图集 + JSON 元数据 + 预览 GIF | 按入选帧等分拼装 | 帧数由动作阶段和全帧筛选结果决定 | 视角、朝向、接地帧脚底线、锚点、比例 |
| 4/8 方向转面 | 方向单体 + 可选转面预览 | 1:1 | 4 或 8 方向 | 比例、脚底线、光位、发型服装结构 |
| 同风格素材套装 | 4 / 9 / 16 件同风格单体 | 1:1 或 3:2 | 4 或 9 件最稳 | 锚点、色板、描边、圆角、光位 |
| 场景地图与瓦片 | 地图、分层背景、4×4 瓦片表、纹理 | 1:1 / 16:9 / 4:3 | 按关卡与地图数量 | 视角、地平线、网格、色板 |
| UI 套装 | 按钮四态、血条、图标、背包格、面板 | 1:1 / 3:2 / 3:1 | 4–12 件 | 圆角、描边粗细、高光方向、文字安全区 |

### 动画序列帧

生成方法、帧序规格表与对齐规则见前面的 [精灵图集与序列帧](#精灵图集与序列帧)。本节只补族级要求：

- 同族共用同一锚点、同一视角朝向、同一画幅与色板，不要一张张散着出。
- **帧数按动作定**：先覆盖必要动作阶段，再按信息增量与节奏筛选；不得预设固定数量或为凑数保留重复帧。
- 帧时长按阶段配置，不匀速：预备 120–200 ms、动作 30–60 ms、跟随 80–150 ms、回待机 60–100 ms。
- 拆分后逐帧检查脚底线（接地帧）、朝向、体型与道具位置，漂移帧单独重生成。

循环动效短片（仅作预览，不进引擎）：

```bash
meitu image-to-video --image_list "<角色锚点图绝对路径>" --prompt "<动作>循环播放，固定机位，无运镜，角色不位移，背景静止，首尾画面衔接，<视角与朝向>，保持发型服装配色不变" --video_duration 4 --multi_shot false --json --download-dir ./output/game/<角色名>/anim/<动作>/preview
meitu video-to-gif --video_url "<视频绝对路径>" --prompt "<动作>循环，固定机位" --json --download-dir ./output/game/<角色名>/anim/<动作>/preview
```

`--multi_shot` 只在当前 `--help` 提供时传；没有该参数就删掉，并在提示词里继续写固定机位、无运镜。生成结果仍可能自动加镜头，交付前逐条检查，不合格就换一版。

透明底：在纯白背景上生成，拆分后逐帧 `image-cutout`（角色 `model_type 0`，道具 `model_type 1`）。抠图放最后一步，先抠后编辑会丢 alpha。

### 4/8 方向转面

4 方向用 2×2 宫格：

```bash
meitu image-edit --image_list "<角色锚点图绝对路径>" --prompt "2x2 均分宫格，同一角色的正面、右侧、背面、左侧四个方向，<视角>，同一比例、同一脚底线、同一光位、同一发型服装配色与体型，正交投影，无透视畸变，每格纯色背景，格间留细白分隔线，<风格措辞逐字一致>" --ratio 1:1 --size 2K --json --download-dir ./output/game/<角色名>/turnaround-4
meitu image-grid-split --image_url "<宫格图绝对路径>" --json --download-dir ./output/game/<角色名>/turnaround-4/frames
```

8 方向用 3×3 宫格，中心格留空：

```bash
meitu image-edit --image_list "<角色锚点图绝对路径>" --prompt "3x3 均分宫格，中心格留空为纯色，其余八格为同一角色的八个方向：南、东南、东、东北、北、西北、西、西南，<视角>，同一比例、同一脚底线、同一光位、同一发型服装配色与体型，正交投影，每格纯色背景，格间留细白分隔线，<风格措辞逐字一致>" --ratio 1:1 --size 2K --json --download-dir ./output/game/<角色名>/turnaround-8
meitu image-grid-split --image_url "<宫格图绝对路径>" --json --download-dir ./output/game/<角色名>/turnaround-8/frames
```

拆分后剔除中心格，按 `S / SE / E / NE / N / NW / W / SW` 重命名。逐个核对左右方向是否镜像正确、背面服装结构与正面是否一致、脚底线是否水平。

转面预览（只作展示，不替代方向单体）：

```bash
meitu image-to-video --image_list "<角色锚点图绝对路径>" --prompt "固定机位，角色原地匀速顺时针旋转一周，背景与地面静止，保持发型服装配色与体型不变，正交视角" --video_duration 4 --multi_shot false --json --download-dir ./output/game/<角色名>/turnaround-preview
meitu video-to-gif --video_url "<视频绝对路径>" --prompt "角色原地旋转一周，固定机位" --json --download-dir ./output/game/<角色名>/turnaround-preview
```

### 同风格素材套装

一次出 4 件（2×2）或 9 件（3×3），用同一锚点与多张风格参考图：

```bash
meitu image-edit --image_list "<风格锚点图绝对路径>" "<风格参考图 2>" "<风格参考图 3>" --prompt "2x2 均分宫格，四件同风格的游戏<道具或图标>：<主体清单>，统一圆角、统一描边粗细、统一高光方向、统一色板，<风格措辞逐字一致>，每格纯色背景，格间留细白分隔线，无文字" --ratio 1:1 --size 2K --json --download-dir ./output/game/<单元>/style-set
meitu image-grid-split --image_url "<宫格图绝对路径>" --json --download-dir ./output/game/<单元>/style-set/frames
```

批量扩展时，复制同一段提示词，只替换主体清单，不重写风格措辞、光位、描边与色板描述。新增第二批前保留第一批作为风格参考图一起传入。

局部改色、换材质、加配件：

```bash
meitu image-edit --image_list "<原图绝对路径>" --prompt "只把<部位>改为<新方案>，保持人物姿势、轮廓、比例、构图与背景完全不变，<风格措辞>" --json --download-dir ./output/game/<单元>/edit
```

CLI 没有 mask / inpainting 参数，局部修改也会整图重绘，交付前必须人工比对外形与像素细节；不要向客户承诺"只改这一块、其他像素完全不动"。

### 场景、地图与瓦片

俯视地图：

```bash
meitu text-to-image --prompt "正俯视 top-down 游戏地图，<地貌与建筑>，正交投影，边缘规整，<时段与天气>，<风格措辞>，无文字，无 UI" --ratio 1:1 --size 2K --json --download-dir ./output/game/<场景名>/map
```

瓦片表（4×4，一次 16 个地块或物件）：

```bash
meitu text-to-image --prompt "4x4 均分瓦片表，每格一个可拼接地块或物件：<16 项清单>，同一视角、同一色板、同一光源方向，地块边缘对齐，orthographic，每格纯色深底，格间留细白分隔线，<风格措辞>，无文字" --ratio 1:1 --size 2K --json --download-dir ./output/game/<场景名>/tiles
meitu image-grid-split --image_url "<瓦片表绝对路径>" --json --download-dir ./output/game/<场景名>/tiles/frames
```

可平铺纹理：

```bash
meitu text-to-image --prompt "可平铺纹理，<材质>，四方连续，无明显接缝，正交俯视，<风格措辞>，无文字" --ratio 1:1 --size 2K --json --download-dir ./output/game/<场景名>/texture
```

场景循环动效（篝火、水流、旗帜等单元素动）：

```bash
meitu image-to-video --image_list "<场景图绝对路径>" --prompt "固定机位，仅<篝火 / 水流 / 旗帜>循环运动，其他画面完全静止，无运镜，无角色进入，首尾画面衔接" --video_duration 4 --multi_shot false --json --download-dir ./output/game/<场景名>/ambient
meitu video-to-gif --video_url "<视频绝对路径>" --prompt "<元素>循环，固定机位" --json --download-dir ./output/game/<场景名>/ambient
```

平铺与瓦片接缝不做保证：4×4 表只保证构图规整与视角一致，拼接后仍需美术修补接缝、统一地块明度。

### UI 套装

2×3 套装（血条、按钮、背包格、面板、关闭键等）：

```bash
meitu image-edit --image_list "<UI 风格锚点图绝对路径>" --prompt "2x3 均分宫格，同一套游戏 UI：<元件清单>，统一圆角半径、统一描边粗细、统一高光方向与色板，正面平视，每格纯色背景，格间留细白分隔线，预留文字区但不写入文字，<风格措辞逐字一致>" --ratio 3:2 --size 2K --json --download-dir ./output/game/ui/kit
meitu image-grid-split --image_url "<宫格图绝对路径>" --json --download-dir ./output/game/ui/kit/frames
```

按钮四态用 2×2：

```bash
meitu image-edit --image_list "<按钮或 UI 锚点图绝对路径>" --prompt "2x2 均分宫格，同一按钮的普通、悬停、按下、禁用四种状态，尺寸、圆角、描边、文字区位置完全一致，只改变明度、内阴影与描边发光，无文字，<风格措辞>" --ratio 1:1 --size 2K --json --download-dir ./output/game/ui/button-states
```

需要透明 PNG 时逐张 `image-cutout --model_type 2`；抠图放最后一步。面板只交成品位图与文字安全区说明，不输出九宫格拉伸配置与可切图源文件。

### 像素风附加约束

同一像素风项目，在所有族的提示词里固定追加同一组措辞，不要每张换说法：

`pixel art, 16-bit, 有限调色板（16–32 色）, 硬边缘, 无抗锯齿, 无渐变, 1px 描边, 正交视角`

- 色板：把同一组 hex 色值写进每段提示词，或额外传一张色板图作为参考图；不要只写"像素风"三个字。
- 缩放：CLI 输出高分辨率图。若目标是 32×32 / 64×64 原生像素画布，需美术在图像工具中按最近邻降采样、限色、修边；本 Skill 不直接产出原生低分辨率画布。
- 透明底：所有编辑、风格化、超分、扩图都先做完，最后一步再 `image-cutout`。
- 动画：帧数由动作阶段、信息增量、节奏和最终显示尺寸决定；循环必须完整闭合，单次动作必须覆盖必要阶段。

格子尺寸、原生分辨率换算、角色比例下限与对齐细节见 [像素风专项](pixel-guide.md)。

### 五类素材族验收

| 族 | 必查项 |
| --- | --- |
| 动画序列帧 | 必要动作阶段齐全；接地帧脚底线、朝向、比例一致；腾空帧高度差是否保留；首末帧可衔接；无多余肢体或道具漂移；图集元数据齐全 |
| 4/8 方向转面 | 方向齐全且左右正确；正面与背面服装结构一致；脚底线水平；光位与色板一致 |
| 同风格素材套装 | 描边粗细、圆角、光位、色板一致；主体无文字与多余装饰；混排时风格不跳 |
| 场景地图与瓦片 | 视角与地平线一致；瓦片每格尺寸一致；拼接处无错位与明显色差；纹理接缝已复核 |
| UI 套装 | 圆角半径、描边粗细、高光方向统一；按钮四态尺寸一致；面板文字安全区充足；无烘焙文字 |

## 一致性检查清单

交付前逐项确认，未通过就说明而不是假装达标：

1. 视角与画幅是否与项目设定一致，镜头高度是否漂移。
2. 主光源方向与色温跨图是否一致。
3. 风格措辞是否与其他图逐字一致。
4. 分层图之间元素是否重复（同一建筑不该同时出现在中景和远景）。
5. 透明底图边缘是否有白边、缺角或残留背景。
6. 序列帧图集每格的尺度、朝向是否一致；接地帧脚底线是否对齐、腾空帧高度差是否保留。
7. 尺寸延展后主体比例与地平线高度是否与母图一致；超分图是否出现过锐化或塑料感。
8. 同一角色的发型、服装、配色、体型、瞳色跨图是否一致；多表情是否共用同一设定卡。
9. UI 图标与面板的圆角半径、描边粗细、高光方向是否统一；是否误留文字。
10. 卡牌的文字、稀有度层级与卡框是否错位，文字是否被改写。
11. 动画视频时长、镜头运动与首尾帧是否与分镜一致。
12. 宣传物料的标题、版本号、发行标识是否原样保留，多尺寸是否各出一版而非裁剪。
13. 序列帧是否覆盖必要动作阶段，帧数是否来自全帧筛选，逐帧时长是否按阶段配置，图集 JSON 是否含锚点与逐帧时长。
14. 4/8 方向转面的左右关系是否正确，背面与正面的服装结构是否一致。
15. 瓦片表每格尺寸是否一致、地块边缘能否衔接；UI 套装圆角、描边、高光是否统一且无烘焙文字。
