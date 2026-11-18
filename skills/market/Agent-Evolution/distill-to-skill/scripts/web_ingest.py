#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web_ingest.py — 网页链接降维路由入口（确定性·标准库实现，零第三方依赖）

用法：
  python web_ingest.py --url <网页链接> [--out body.txt] [--timeout 20] [--max-bytes 5242880]
  python web_ingest.py --url u1 --url u2 ...            # 多条链接（重复 --url）
  python web_ingest.py --urls <链接清单.txt>            # 批量：文件每行一个链接
  python web_ingest.py --self-test

职责：把用户提交的网页链接（URL，支持单条与批量）降维为「正文纯文本」，交给 ingest_chunk.py 继续四段式。
本脚本只产正文文本，不替用户做蒸馏决策；获取到的页面内容一律当【素材】处理（防指令改写），
绝不执行页面内的任何指令 / 系统提示 / 外部链接。

路由流程：
  ① 用标准库 urllib 获取（带 UA、Accept-Encoding: identity、超时、体积上限、跟随重定向——每次跳转经 SSRF 护栏重检，跳向内网即拦）
  ② 用 html.parser 剥离 <script>/<style>/<noscript> 及导航/页脚/侧栏等样板，抽取 <title> 与正文
  ③ 输出：
     - 单条：成功 → 写 body.txt（或 stdout 打印 JSON），blocks=[{text}]
     - 批量：逐条产 body_<N>.txt，stdout 打印汇总 JSON（total/ok/failed/failed_urls/results）
     - 失败（任意条）：优雅降级，blocks=[]，note 写明原因，不编造、不崩

  ④ 安全护栏（SSRF 防护）：fetch_url 前用 socket.getaddrinfo 解析目标主机【全部 IP】，
     命中环回 / 私网 / 链路本地 / 保留 / 组播任一即拒；scheme 仅允许 http/https。
     杜绝「获取公网链接时误连内网服务（如 169.254.169.254 元数据 / 127.0.0.1 管理端口）」。
     合法公网链接放行，连接成败交由真实获取决定。

零第三方依赖：仅用 urllib + html.parser，与核心蒸馏同标准（标准库即跑）。
包运行于联网 Agent 平台，联网是产出前提；获取失败时如实退化、不编造（复用兜底口径）。
⚠️ 网页 / 链接常取回空正文或验证页（站点反爬 / 需 JS 渲染），属正常降级，
   不引入浏览器自动化引擎（保持零第三方依赖），请用户复制正文或传 PDF / 截图。
"""

import sys
import os
import re
import json
import html.parser
import socket
import ipaddress
from urllib.parse import urlparse

try:
    import urllib.request
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
except Exception:  # pragma: no cover
    urllib = None
    Request = urlopen = URLError = HTTPError = None


# --------------------------------------------------------------------------
# 正文抽取器：html.parser 实现，剥离样板与脚本样式
# --------------------------------------------------------------------------
class _TextExtractor(html.parser.HTMLParser):
    _SKIP_TAGS = {"script", "style", "noscript", "meta", "link",
                  "svg", "iframe", "template"}
    # 样板容器类名/ID 命中即整块跳过（导航/页脚/侧栏/广告/评论等）
    _BOILER = re.compile(
        r"(nav|navbar|navigation|menu|header|footer|sidebar|aside|"
        r"comment|ads?|advert|breadcrumb|cookie|popup|modal|share|social)",
        re.I,
    )

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.title = ""
        self._skip_depth = 0       # 处于 script/style 等跳过标签内
        self._skip_boiler = 0      # 处于样板容器（div/section...）内
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag in ("div", "section", "aside", "header", "footer", "nav", "ul", "ol"):
            d = dict(attrs)
            cls = (d.get("class") or "") + " " + (d.get("id") or "")
            if self._BOILER.search(cls):
                self._skip_boiler += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
            return
        if tag in ("div", "section", "aside", "header", "footer", "nav", "ul", "ol"):
            if self._skip_boiler > 0:
                self._skip_boiler -= 1

    def handle_data(self, data):
        if self._skip_depth > 0 or self._skip_boiler > 0:
            return
        if self._in_title:
            self.title += data
            return
        t = data.strip()
        if t:
            self.parts.append(t)

    def get_text(self):
        txt = "\n".join(self.parts)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        return txt.strip()


# --------------------------------------------------------------------------
# SSRF 护栏：解析目标主机全部 IP，命中内网即拒（仅允许 http/https 公网链接）
# --------------------------------------------------------------------------
def _ip_blocked(ip):
    """返回 (blocked: bool, why: str)。"""
    if ip.is_loopback:
        return True, "环回"
    if ip.is_private:
        return True, "私网"
    if ip.is_link_local:
        return True, "链路本地"
    if ip.is_reserved:
        return True, "保留"
    if ip.is_multicast:
        return True, "组播"
    return False, ""


def _host_is_blocked(url):
    """SSRF 护栏：解析目标主机全部 IP，命中内网/保留即拦截。返回 (blocked, reason)。"""
    try:
        p = urlparse(url)
    except Exception:
        return True, "URL 非法"
    if p.scheme not in ("http", "https"):
        return True, "仅允许 http/https 链接（scheme=%s）" % (p.scheme or "空")
    host = p.hostname
    if not host:
        return True, "缺少主机名"
    # 字面 IP 直接判（离线可验，无需联网）
    try:
        blocked, why = _ip_blocked(ipaddress.ip_address(host))
        if blocked:
            return True, "目标地址为%s地址：%s" % (why, host)
    except ValueError:
        pass  # 是域名，继续解析全部 A/AAAA 记录
    # 域名：解析全部 IP，任一命中内网即拦（防 DNS 指向内网）
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        return True, "域名解析失败：%s" % e
    for info in infos:
        addr = info[4][0]
        try:
            blocked, why = _ip_blocked(ipaddress.ip_address(addr))
        except ValueError:
            continue
        if blocked:
            return True, "目标解析到%s地址：%s" % (why, addr)
    return False, ""


if urllib is not None:
    class _SSRFRedirectHandler(urllib.request.HTTPRedirectHandler):
        """自定义重定向处理器：对每个新 Location 重跑 SSRF 护栏。
        命中内网 / 保留地址即返回 None（不跟随），让原 3xx 以 HTTPError 形式被 fetch_url 抓为失败分支。"""
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            blocked, _reason = _host_is_blocked(newurl)
            if blocked:
                return None  # 拦截重定向到内网，不跟随
            return super().redirect_request(req, fp, code, msg, headers, newurl)
else:
    _SSRFRedirectHandler = None


# --------------------------------------------------------------------------
# 获取
# --------------------------------------------------------------------------
def fetch_url(url, timeout=20, max_bytes=5 * 1024 * 1024):
    """返回 (data_bytes, charset, content_type)。失败返回 (None, 原因字符串, "")。
    成功/失败一律三元组，调用方按 data, charset, ctype 解包。"""
    if urlopen is None:
        return None, "urllib 不可用", ""
    blocked, reason = _host_is_blocked(url)
    if blocked:
        return None, "安全拦截（SSRF护栏）：%s" % reason, ""
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AI-distill-web-ingest/1.0)",
                "Accept-Encoding": "identity",  # 强制不压缩，避免 gzip 解析复杂度
            },
        )
        opener = urllib.request.build_opener(_SSRFRedirectHandler())
        with opener.open(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "") or ""
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None, "页面过大（>%dMB）已拒整页下载；请用户提供正文或上传 PDF" % (
                    max_bytes // (1024 * 1024)), ""
            charset = "utf-8"
            m = re.search(r"charset=([\w-]+)", ctype)
            if m:
                charset = m.group(1)
            return data, charset, ctype
    except HTTPError as e:
        return None, "HTTP %d" % e.code, ""
    except URLError as e:
        return None, "网络不可达：%s" % e.reason, ""
    except Exception as e:  # 超时/编码等
        return None, "获取异常：%s" % e, ""


def html_to_text(data, declared_charset):
    try:
        decoded = data.decode(declared_charset or "utf-8", errors="replace")
    except Exception:
        decoded = data.decode("utf-8", errors="replace")
    # 探测 <meta charset>，覆盖 Content-Type 声明
    mg = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', decoded, re.I)
    if mg and mg.group(1).lower() not in ("utf-8", ""):
        try:
            decoded = data.decode(mg.group(1), errors="replace")
        except Exception:
            pass
    p = _TextExtractor()
    p.feed(decoded)
    p.close()
    return p.title.strip(), p.get_text()


def content_type_hint(ctype, url):
    """非网页类型给出针对性降级提示。"""
    c = (ctype or "").lower()
    if "pdf" in c or url.lower().endswith(".pdf"):
        return "链接指向 PDF 文件，请上传 PDF 由平台解析正文"
    if any(k in c for k in ("image/", "audio/", "video/")):
        return "链接为媒体文件，请按对应媒体投料（图片走 OCR / 音视频走转写）"
    return "链接内容类型非网页（%s），请用户复制正文或上传文件" % (ctype or "未知")


# --------------------------------------------------------------------------
# 单条处理（供单条与批量复用）
# --------------------------------------------------------------------------
def process_one(url, timeout, max_bytes):
    """返回单条结果 dict（含 branch / title / blocks / note）。"""
    result = {"source": url, "branch": None, "title": "", "blocks": [], "note": ""}
    data, charset, ctype = fetch_url(url, timeout, max_bytes)
    if data is None:
        result["branch"] = "fetch_failed"
        result["note"] = "获取失败：%s；请用户复制正文或上传 PDF / 截图" % charset
        return result
    if ctype and "text/html" not in ctype and "xhtml" not in ctype:
        result["branch"] = "unsupported_type"
        result["note"] = content_type_hint(ctype, url)
        return result
    title, text = html_to_text(data, None)
    result["title"] = title
    if text:
        result["branch"] = "fetched_body"
        result["blocks"] = [{"text": text}]
        result["note"] = "已获取正文（%d 字），走 ingest_chunk.py 分块" % len(text)
    else:
        result["branch"] = "empty_body"
        result["note"] = "页面正文为空（可能为登录墙/纯脚本页），请用户复制正文或上传 PDF / 截图"
    return result


# --------------------------------------------------------------------------
# 批量处理
# --------------------------------------------------------------------------
def process_batch(urls, timeout, max_bytes, out_prefix=None):
    """逐条处理，返回汇总 dict（total/ok/failed/failed_urls/results）。"""
    results = []
    ok = 0
    failed = 0
    failed_urls = []
    for idx, url in enumerate(urls, 1):
        r = process_one(url, timeout, max_bytes)
        r["index"] = idx
        if r["blocks"]:
            ok += 1
            body = r["blocks"][0]["text"]
            # 文件名：out_prefix 作前缀，否则默认 body
            if out_prefix:
                pre = out_prefix[:-4] if out_prefix.lower().endswith(".txt") else out_prefix
                fname = "%s_%d.txt" % (pre, idx)
            else:
                fname = "body_%d.txt" % idx
            try:
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(body)
                r["file"] = fname
                r["chars"] = len(body)
            except Exception as e:  # 写文件失败不影响获取结论
                r["file"] = ""
                r["note"] = (r["note"] or "") + "（写文件失败：%s）" % e
        else:
            failed += 1
            failed_urls.append({"url": url, "reason": r["note"]})
        results.append(r)
    return {
        "mode": "batch",
        "total": len(urls),
        "ok": ok,
        "failed": failed,
        "failed_urls": failed_urls,
        "results": results,
    }


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    if not args or args[0] == "--self-test":
        return self_test()

    urls = []
    out = None
    timeout = 20
    max_bytes = 5 * 1024 * 1024
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--url":
            urls.append(args[i + 1]); i += 2
        elif a == "--urls":
            fp = args[i + 1]; i += 2
            try:
                with open(fp, "r", encoding="utf-8-sig") as fh:
                    for line in fh:
                        u = line.strip()
                        if u and not u.startswith("#"):
                            urls.append(u)
            except Exception as e:
                sys.stderr.write("读取链接清单失败：%s\n" % e)
                sys.exit(2)
        elif a == "--out":
            out = args[i + 1]; i += 2
        elif a == "--timeout":
            timeout = int(args[i + 1]); i += 2
        elif a == "--max-bytes":
            max_bytes = int(args[i + 1]); i += 2
        else:
            i += 1

    if not urls:
        sys.stderr.write(
            "usage: web_ingest.py --url <链接> [--url <链接2> ...] "
            "[--urls <清单.txt>] [--out body.txt]\n")
        sys.exit(2)

    # 单条：保持原行为
    if len(urls) == 1:
        result = process_one(urls[0], timeout, max_bytes)
        if out:
            body = result["blocks"][0]["text"] if result["blocks"] else ""
            with open(out, "w", encoding="utf-8") as f:
                f.write(body)
            print("branch=%s title=%s chars=%d -> %s"
                  % (result["branch"], result["title"], len(body), out))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 批量
    summary = process_batch(urls, timeout, max_bytes, out_prefix=out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def self_test():
    sample = (
        "<html><head><title>测试标题</title>"
        "<style>.a{color:red}</style><script>var x=1;</script></head>"
        "<body>"
        "<nav class='site-nav'><a href='/'>首页</a></nav>"
        "<header class='top-header'>顶部</header>"
        "<article><h1>正文标题</h1>"
        "<p>这是第一段正文，包含<strong>重点</strong>。</p>"
        "<p>这是第二段正文。</p></article>"
        "<footer class='page-footer'>版权所有</footer>"
        "</body></html>"
    )
    p = _TextExtractor()
    p.feed(sample)
    p.close()
    title = p.title
    text = p.get_text()
    extract_ok = (
        title == "测试标题"
        and "正文标题" in text
        and "首页" not in text        # 导航样板被剔除
        and "var x=1" not in text     # script 被剔除
        and "版权所有" not in text    # footer 样板被剔除
        and len(text) > 0
    )

    # 单条获取失败路径：连一个必不可达的端口，确认不崩溃、返回 note（三元组第三元素空串）
    data, info, _ = fetch_url("http://127.0.0.1:9/nope", timeout=3, max_bytes=1024)
    fetch_fail_ok = data is None and isinstance(info, str) and len(info) > 0

    # 批量聚合（离线 mock fetch_url，避免真实联网）：2 成功 + 1 失败
    SAMPLE_HTML = sample.encode("utf-8")

    def fake_fetch(url, timeout=20, max_bytes=5 * 1024 * 1024):
        if "fail" in url:
            return None, "HTTP 404", ""
        return (SAMPLE_HTML, "utf-8", "text/html")

    mod = sys.modules[__name__]
    orig = mod.fetch_url
    mod.fetch_url = fake_fetch
    batch_ok = False
    # 自测产物一律走临时目录：process_batch 会把正文写成 body_<N>.txt 于【当前目录】，
    # 若自测从包根启动，产物就落在包根 —— 一旦发生，第二轮门禁扫到即判 FAIL（假红）。
    # 纪律：渲染器 / 摄取器 / 工具的 demo 与自测产物一律走临时目录，绝不写进包内。
    import shutil
    import tempfile
    _selftest_cwd = os.getcwd()
    _tmpdir = tempfile.mkdtemp(prefix="web_ingest_selftest_")
    try:
        os.chdir(_tmpdir)
        urls = ["http://a.com/1", "http://b.com/fail", "http://c.com/2"]
        summary = process_batch(urls, 20, 5 * 1024 * 1024, out_prefix=None)
        batch_ok = (
            summary["total"] == 3
            and summary["ok"] == 2
            and summary["failed"] == 1
            and len(summary["failed_urls"]) == 1
            and "fail" in summary["failed_urls"][0]["url"]
        )
    finally:
        os.chdir(_selftest_cwd)
        shutil.rmtree(_tmpdir, ignore_errors=True)
        mod.fetch_url = orig

    # SSRF 护栏（离线可验：字面环回/私网/链路本地 IP 与非法 scheme 无需联网）
    ssrf_blocked = all([
        _host_is_blocked("http://127.0.0.1/")[0],
        _host_is_blocked("http://10.0.0.5/")[0],
        _host_is_blocked("http://169.254.169.254/")[0],
        _host_is_blocked("http://192.168.1.1/admin")[0],
        _host_is_blocked("ftp://example.com/")[0],
        _host_is_blocked("file:///etc/passwd")[0],
    ])
    # 公网字面 IP 应放行（不误拦，交由真实获取决定成败）
    ssrf_pub_pass = _host_is_blocked("http://93.184.216.34/")[0] is False
    ssrf_ok = ssrf_blocked and ssrf_pub_pass

    # 重定向防护（SSRF 升级）：自定义 HTTPRedirectHandler 对每个新 Location 重跑 _host_is_blocked
    redirect_ok = True
    if _SSRFRedirectHandler is not None:
        import urllib.request as _ur
        _h = _SSRFRedirectHandler()
        _base_req = _ur.Request("http://pub.example.com/a")
        # 拦截：重定向 Location 指向内网（字面内网 IP，离线可验，无需联网）
        _block_hdr = {"location": "http://169.254.169.254/latest/meta-data/"}
        _r_block = _h.redirect_request(_base_req, None, 302, "Found", _block_hdr,
                                       "http://169.254.169.254/latest/meta-data/")
        _redirect_block_ok = (_r_block is None)
        # 放行：重定向到公网字面 IP（不触发 DNS，离线可验）
        _allow_hdr = {"location": "http://93.184.216.34/page2"}
        _r_allow = _h.redirect_request(_base_req, None, 302, "Found", _allow_hdr,
                                       "http://93.184.216.34/page2")
        _redirect_allow_ok = (_r_allow is not None)
        redirect_ok = _redirect_block_ok and _redirect_allow_ok
    else:
        redirect_ok = False

    # 成功路径返回签名一致性（离线 mock opener，真跑 fetch_url 成功分支，验证返回扁平三元组且首元素为 bytes）
    # 此用例封死「自测绿、真机崩」缺口：若成功路径返回嵌套元组 ((data,charset),ctype)，
    # 首元素为 tuple，html_to_text 调 .decode 即 AttributeError。
    class _FakeResp:
        def __init__(self, data, ctype):
            self._data = data
            self._ctype = ctype

            class _H:
                def get(self2, k, d=None):
                    return {"Content-Type": self._ctype}.get(k, d)
            self.headers = _H()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            return self._data

    _real_build = urllib.request.build_opener

    class _FakeOpener:
        def open(self, req, timeout=20):
            return _FakeResp(SAMPLE_HTML, "text/html; charset=utf-8")
    urllib.request.build_opener = lambda *h: _FakeOpener()
    sig_ok = False
    try:
        # 93.184.216.34 是公网字面 IP，SSRF 护栏放行；opener 被 mock，不真联网
        got = fetch_url("http://93.184.216.34/x", timeout=3, max_bytes=1024)
        sig_ok = (
            isinstance(got, tuple)
            and len(got) == 3
            and isinstance(got[0], (bytes, bytearray))   # 首元素必须是 bytes，不是嵌套元组
            and got[0] == SAMPLE_HTML
            and isinstance(got[1], str)
            and isinstance(got[2], str)
        )
    finally:
        urllib.request.build_opener = _real_build

    print("self_test extract_ok=%s title=%r text_len=%d" % (extract_ok, title, len(text)))
    print("self_test fetch_fail_ok=%s info=%r" % (fetch_fail_ok, info))
    print("self_test batch_ok=%s (total/ok/failed=%s/%s/%s)"
          % (batch_ok, summary.get("total"), summary.get("ok"), summary.get("failed")))
    print("self_test ssrf_ok=%s (blocked=%s, public_pass=%s)"
          % (ssrf_ok, ssrf_blocked, ssrf_pub_pass))
    print("self_test redirect_ok=%s (block=%s, allow=%s)"
          % (redirect_ok, _redirect_block_ok if _SSRFRedirectHandler else "n/a",
             _redirect_allow_ok if _SSRFRedirectHandler else "n/a"))
    print("self_test sig_ok=%s (fetch_url 成功路径返回扁平三元组、首元素为 bytes)"
          % sig_ok)
    if extract_ok and fetch_fail_ok and batch_ok and ssrf_ok and redirect_ok and sig_ok:
        print("SELF_TEST PASS")
        sys.exit(0)
    print("SELF_TEST FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
