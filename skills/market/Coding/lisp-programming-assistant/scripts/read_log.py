"""用法: python read_log.py <日志文件> —— LISP 写出的中文按 ANSI(GBK) 落盘, 故先按 GBK 解码再退回 UTF-8"""
import sys, pathlib
raw = pathlib.Path(sys.argv[1]).read_bytes()
for enc in ("gbk", "utf-8-sig"):
    try:
        print(raw.decode(enc)); break
    except UnicodeDecodeError:
        continue
else:
    print(raw.decode("gbk", errors="replace"))
