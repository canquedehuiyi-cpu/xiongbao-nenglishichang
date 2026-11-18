"""用法: python to_ansi.py <文件.lsp> [输出.lsp] —— 交付前把 UTF-8 源码转成 ANSI(GBK); 省略输出则原地转换"""
import sys, pathlib

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src
raw = src.read_bytes()
try:
    text = raw.decode("utf-8-sig")      # 开发期常态
except UnicodeDecodeError:
    text = raw.decode("gbk")            # 已是 ANSI
try:
    data = text.encode("gbk")           # ZWCAD load 按 ANSI 读
except UnicodeEncodeError as e:
    sys.exit(f"含 GBK 外字符, 不能交付 ANSI: {e}")
dst.write_bytes(data)
if dst.read_bytes().decode("gbk") != text:
    sys.exit("回读校验失败, 交付文件不可用")
print(f"OK {dst}  {len(data)} bytes  ANSI/GBK  回读校验通过")
