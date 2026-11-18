"""用法: python push_test.py <文件.lsp> "<lisp表达式>" —— 源文件 UTF-8 时转 ANSI 临时副本再加载, 用后即删; 已是 ANSI 则直接 load 源文件"""
import json, os, sys, pathlib, tempfile, urllib.request

lsp = pathlib.Path(sys.argv[1]).resolve()
appdata = os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")
addr = json.loads(pathlib.Path(appdata, "TmAgent", "api_address.json").read_text(encoding="utf-8-sig"))
base = addr.get("baseUrl", "http://127.0.0.1:9876").rstrip("/")   # 先探地址, 失败时不留临时文件

target = lsp                                # 已是 ANSI 的旧文件直接加载
try:
    text = lsp.read_bytes().decode("utf-8-sig")     # AI 写码常态
    target = pathlib.Path(tempfile.gettempdir(), f"tm_{lsp.stem}_ansi.lsp")
    try:
        target.write_bytes(text.encode("gbk"))      # ZWCAD load 按 ANSI 读
    except UnicodeEncodeError as e:
        sys.exit(f"无法转 ANSI, 文件含 GBK 不支持的字符: {e}")
except UnicodeDecodeError:
    pass

cmds = [{"command": "lisp_eval", "code": f'(load "{target.as_posix()}")'},
        {"command": "lisp_eval", "code": sys.argv[2]}]
req = urllib.request.Request(base + "/api/execute",
                             data=json.dumps({"commands": cmds}).encode("utf-8"),
                             headers={"Content-Type": "application/json"})
try:
    print(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
finally:
    if target != lsp:
        target.unlink(missing_ok=True)      # 临时副本不留在交付目录
