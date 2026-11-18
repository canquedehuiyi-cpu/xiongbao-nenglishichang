# 字幕视频制作：Go 原型

根据现成视频和 UTF-8 SRT/ASS 制作带硬字幕的 MP4。可先输出一段预览。输入不会被修改，输出文件已存在时会失败。

## 依赖

需要可执行的 FFmpeg（含 libass subtitles 滤镜、libx264、AAC）及 ffprobe；可通过 `-ffmpeg` 和 `-ffprobe` 指定路径。此包不包含 FFmpeg。安装与使用第三方构建时请遵循其许可。本机提供 Windows x64 Go 工具；其他系统使用 Go 1.22+ 在本目录运行 `go build -o subtitle-video ./cmd/subtitle-video`。

```powershell
.\bin\subtitle-video.exe -input '素材.mp4' -sub '字幕.srt' -output '预览.mp4' -start 2 -duration 5 -font 'Microsoft YaHei' -ffmpeg 'ffmpeg.exe路径' -ffprobe 'ffprobe.exe路径'
.\bin\subtitle-video.exe -input '素材.mp4' -sub '字幕.srt' -output '成片.mp4' -font 'Microsoft YaHei' -ffmpeg 'ffmpeg.exe路径' -ffprobe 'ffprobe.exe路径'
```

预览需在素材时间范围内。字体依赖系统实际安装，ASS 文件保留自己的样式；FFmpeg 可能回退字体，需视觉确认。输出写入目标目录的临时文件后以硬链接原子创建，文件系统需支持硬链接。工具不生成单独的参数记录或字幕副本。

当前为本地原型；尚未在 Qoder 目标宿主安装运行，也未提交市场审核。
