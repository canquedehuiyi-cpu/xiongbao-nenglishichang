---
name: anim-convert
version: 1.1.1
display_name: 动画格式互转
display_name_en: Animation Format Converter
description_zh: 序列帧文件夹、GIF、WebP、APNG 与 MP4/WebM/MOV 视频之间任意转换，支持批量转换、提取每帧、帧率/时长/循环/缩放控制。
description_en: Interconvert between sequence-frame folders, animated GIF/WebP/APNG and MP4/WebM/MOV video, with batch conversion, frame extraction, and fps/duration/loop/scale control.
description: 动画格式互转：序列帧文件夹、GIF、WebP、APNG 与 MP4/WebM/MOV 视频之间任意转换，支持批量转换（文件夹内所有动画统一转格式）、提取每帧、序列帧合成动画或视频。触发词：序列帧转gif、gif转apng、webp转序列帧、提取每一帧、文件夹图片合成动画、转成mp4、视频转gif、批量转webp。
---

# 动画格式互转

序列帧文件夹、GIF、WebP、APNG、MP4/WebM/MOV 视频互转工具(基于 Pillow,视频能力依赖 ffmpeg)。

## 功能

- **序列帧合成动画/视频**:将文件夹内按序命名的图片(png/jpg/webp 等)合成为 GIF、WebP、APNG 或 MP4/WebM/MOV 视频
- **动画格式转换**:GIF、WebP、APNG、MP4/WebM/MOV 之间任意互转,保留原有播放速度
- **视频互转**:MP4/WebM/MOV 视频 ↔ GIF/WebP/APNG/序列帧,按 --fps 抽帧或合成
- **提取动画帧**:将 GIF/WebP/APNG/视频拆分为 PNG 序列帧,保留透明背景
- **批量转换**:把文件夹里所有图片/动画文件逐转成同一格式(自然排序,单文件失败自动跳过)
- **尺寸缩放**:--scale 480 / 480x360 / x360 输出缩放

## 使用示例

**序列帧转 GIF**
> 把 D:\frames 这个序列帧文件夹转成 gif,15 帧每秒。

**GIF 转 APNG**
> 把 in.gif 转成 apng,保留原来的播放速度。

**提取每一帧**
> 把 in.webp 的每一帧提取出来,放到 frames 文件夹里。

**序列帧合成视频**
> 把 D:\frames 的序列帧合成 mp4,12 帧每秒。

**视频转 GIF**
> 把 clip.mp4 转成 gif,每秒 10 帧。

**文件夹合成无损 WebP**
> 把这一文件夹的图合成无损 webp 动画。

**调整帧率**
> 这个 gif 太快了,帮我转成 apng,每秒 10 帧。

**设置循环次数**
> 把序列帧转成 gif,播放 3 次就停。

**保留透明背景**
> 把这个 apng 转成 webp,背景要透明。

**批量转换**
> 把文件夹里所有 gif 都转成 webp。

**批量转视频**
> 把 D:\gifs 里所有 gif 都批量转成 mp4。

**缩小动画尺寸**
> 把这一文件夹的序列帧转成 gif,缩到宽 480。

## 用法

所有命令在技能目录下执行:

```bash
python scripts/convert.py <input> <output> [选项]

<input>/<output>: 文件(按扩展名判断格式)或文件夹(作为序列帧/批量输入)
支持输入:  .gif .webp .png .apng .mp4 .webm .mov 图片序列文件夹
支持输出:  .gif .webp .png(.apng) .mp4 .webm .mov 或帧序列文件夹
批量模式:  python scripts/convert.py <输入文件夹> <输出文件夹> --batch <ext>

常用选项:
  --fps N        帧率(默认 24;影响序列帧/视频 合成与抽帧)
  --duration MS  覆盖每帧时长(毫秒,优先于 --fps)
  --loop N       循环次数(0=无限)
  --pattern GLOB 序列帧文件夹只取匹配文件,如 '*.png'
  --quality N    WebP 质量 0-100(默认 80,--lossless 时忽略)
  --lossless     无损 WebP
  --scale W[H]   输出缩放:480 / 480x360 / x360
  --batch EXT    批量:输入/输出均为文件夹,逐文件转成 EXT
```

依赖: Pillow;视频输入输出额外需要 PATH 中的 ffmpeg(缺失时给出明确提示)。

## 自检

```bash
python scripts/self_test.py
```

生成临时素材并覆盖帧序列、GIF/WebP/APNG、MP4、批量转换与缩放路径;全部 PASS 表示环境可用。