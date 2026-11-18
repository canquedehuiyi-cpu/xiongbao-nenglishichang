package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

type probe struct {
	Format struct {
		Duration string `json:"duration"`
	} `json:"format"`
}

func run() error {
	fs := flag.NewFlagSet("subtitle-video", flag.ContinueOnError)
	input := fs.String("input", "", "input video")
	sub := fs.String("sub", "", "UTF-8 SRT or ASS subtitles")
	output := fs.String("output", "", "new MP4 output")
	ffmpeg := fs.String("ffmpeg", "ffmpeg", "FFmpeg executable with libass")
	ffprobe := fs.String("ffprobe", "ffprobe", "ffprobe executable")
	start := fs.Float64("start", 0, "preview start seconds")
	duration := fs.Float64("duration", 0, "preview duration seconds; 0 means full remainder")
	font := fs.String("font", "", "font family for SRT (optional)")
	size := fs.Int("size", 24, "SRT font size")
	if err := fs.Parse(os.Args[1:]); err != nil {
		return err
	}
	if *input == "" || *sub == "" || *output == "" {
		return errors.New("required: -input, -sub, -output")
	}
	if *start < 0 || *duration < 0 || *size < 8 || *size > 96 {
		return errors.New("invalid start, duration or font size")
	}
	if strings.ContainsAny(*font, "',:;\\\n\r") {
		return errors.New("unsupported characters in font family")
	}
	ext := strings.ToLower(filepath.Ext(*sub))
	if ext != ".srt" && ext != ".ass" {
		return errors.New("subtitle must be SRT or ASS")
	}
	if strings.ToLower(filepath.Ext(*output)) != ".mp4" {
		return errors.New("output must be MP4")
	}
	for _, p := range []string{*input, *sub} {
		if s, e := os.Stat(p); e != nil || !s.Mode().IsRegular() {
			return fmt.Errorf("input file unavailable: %s", p)
		}
	}
	if _, e := os.Lstat(*output); e == nil {
		return errors.New("output already exists")
	} else if !os.IsNotExist(e) {
		return e
	}
	outAbs, e := filepath.Abs(*output)
	if e != nil {
		return e
	}
	for _, p := range []string{*input, *sub} {
		a, _ := filepath.Abs(p)
		if strings.EqualFold(a, outAbs) {
			return errors.New("output must differ from inputs")
		}
	}
	b, e := exec.Command(*ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", *input).Output()
	if e != nil {
		return fmt.Errorf("ffprobe failed: %w", e)
	}
	var info probe
	if e = json.Unmarshal(b, &info); e != nil {
		return e
	}
	length, e := strconv.ParseFloat(info.Format.Duration, 64)
	if e != nil || length <= 0 {
		return errors.New("cannot determine video duration")
	}
	if *start >= length || (*duration > 0 && *start+*duration > length+0.001) {
		return fmt.Errorf("preview exceeds video duration %.3fs", length)
	}
	// Use a simple subtitle filename in a temporary working directory; avoids FFmpeg filter path escaping.
	temp, e := os.MkdirTemp("", "subtitle-video-")
	if e != nil {
		return e
	}
	defer os.RemoveAll(temp)
	src, e := os.Open(*sub)
	if e != nil {
		return e
	}
	dst, e := os.Create(filepath.Join(temp, "subtitle"+ext))
	if e != nil {
		src.Close()
		return e
	}
	_, e = io.Copy(dst, src)
	src.Close()
	closeErr := dst.Close()
	if e != nil {
		return e
	}
	if closeErr != nil {
		return closeErr
	}
	inAbs, e := filepath.Abs(*input)
	if e != nil {
		return e
	}
	filter := "subtitles=subtitle" + ext
	if ext == ".srt" {
		style := fmt.Sprintf("FontSize=%d", *size)
		if *font != "" {
			style += ",FontName=" + *font
		}
		filter += ":force_style='" + style + "'"
	}
	// Reserve a temporary output in destination directory so successful installation stays on one filesystem.
	f, e := os.CreateTemp(filepath.Dir(outAbs), ".subtitle-video-*.mp4")
	if e != nil {
		return e
	}
	tmpOut := f.Name()
	f.Close()
	defer os.Remove(tmpOut)
	args := []string{"-hide_banner", "-nostdin", "-y", "-i", inAbs, "-vf", filter}
	if *start > 0 {
		args = append(args, "-ss", strconv.FormatFloat(*start, 'f', 3, 64))
	}
	if *duration > 0 {
		args = append(args, "-t", strconv.FormatFloat(*duration, 'f', 3, 64))
	}
	args = append(args, "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", tmpOut)
	cmd := exec.Command(*ffmpeg, args...)
	cmd.Dir = temp
	cmd.Stderr = os.Stderr
	if e = cmd.Run(); e != nil {
		return fmt.Errorf("render failed: %w", e)
	}
	// Hard link atomically refuses an existing output; temporary file is removed on return.
	if e = os.Link(tmpOut, outAbs); e != nil {
		return fmt.Errorf("cannot create output (existing file or unsupported filesystem): %w", e)
	}
	fmt.Printf("Created: %s\nInput duration: %.3fs; start: %.3fs; duration: %.3fs\n", outAbs, length, *start, *duration)
	return nil
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
