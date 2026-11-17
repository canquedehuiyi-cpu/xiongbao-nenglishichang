#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WorkBuddy 三市场 + 连接器/插件导出流水线。

子命令：
  experts    专家包 + 头像（429）
  official   官方技能整包 zip
  shmeta     SkillHub 元数据（13 类目 x Top200，按 slug 去重保下载量最高）
  shdl       SkillHub 技能 zip（依赖 shmeta）
  local      本机连接器 298 个 + 插件市场包
"""
import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = "D:/workbuddy-market-export"
RAW = os.path.join(ROOT, "_raw")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WorkBuddyMarketExport/1.0"


def log(*a):
    print(*a, flush=True)


def download(url, dest, retries=4, timeout=90):
    """断点续传下载；成功返回 'ok'/'exists'，失败返回 FAIL 字符串。"""
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "exists"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    offset = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", UA)
            if offset:
                req.add_header("Range", "bytes=%d-" % offset)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                mode = "ab"
                if offset and r.status != 206:
                    mode = "wb"
                    offset = 0
                with open(tmp, mode) as f:
                    while True:
                        chunk = r.read(262144)
                        if not chunk:
                            break
                        f.write(chunk)
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
            offset = os.path.getsize(tmp) if os.path.exists(tmp) else 0
            time.sleep(1 + attempt)
    return "FAIL " + last


def parallel(items, fn, workers=10, label="task"):
    ok = fail = 0
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): it for it in items}
        for i, f in enumerate(as_completed(futs), 1):
            it = futs[f]
            try:
                res = f.result()
            except Exception as e:
                res = "FAIL EXC %s: %s" % (type(e).__name__, e)
            if isinstance(res, str) and res.startswith("FAIL"):
                fail += 1
                failures.append((it, res))
            else:
                ok += 1
            if i % 25 == 0 or i == len(items):
                log("[%s] %d/%d ok=%d fail=%d" % (label, i, len(items), ok, fail))
    if failures:
        with open(os.path.join(RAW, "failures-%s.json" % label), "w", encoding="utf-8") as fp:
            json.dump([{"item": str(a), "error": b} for a, b in failures], fp, ensure_ascii=False, indent=2)
        log("[%s] failures written: failures-%s.json" % (label, label))
    return ok, fail


# ---------------------------------------------------------------- experts
def cmd_experts():
    cat = json.load(open(os.path.join(RAW, "expert_center.json"), encoding="utf-8"))
    base = "https://acc-1258344699.cos.accelerate.myqcloud.com/workbuddy/expert-marketplace"
    jobs = []
    seen = set()
    for e in cat["experts"]:
        plugin = e.get("plugin") or e.get("agentName") or e["id"]
        if plugin not in seen:
            seen.add(plugin)
            jobs.append(("bundle", plugin, "%s/bundles/%s.tar.gz" % (base, plugin),
                         os.path.join(RAW, "experts", "bundles", plugin + ".tar.gz")))
        aid = e["id"]
        jobs.append(("avatar", aid, "%s/avatars/%s.png" % (base, aid),
                     os.path.join(RAW, "experts", "avatars", aid + ".png")))
    log("[experts] %d experts, %d unique bundles, %d total files" %
        (len(cat["experts"]), len(seen), len(jobs)))

    def one(job):
        kind, name, url, dest = job
        return download(url, dest)

    ok, fail = parallel(jobs, one, workers=12, label="experts")
    log("[experts] DONE ok=%d fail=%d" % (ok, fail))


# ---------------------------------------------------------------- official
def cmd_official():
    url = "https://download.codebuddy.cn/skill-marketplace/skill-marketplace.zip"
    dest = os.path.join(RAW, "official", "skill-marketplace.zip")
    log("[official] downloading -> %s" % dest)
    res = download(url, dest, retries=6, timeout=180)
    log("[official] %s size=%s" % (res, os.path.getsize(dest) if os.path.exists(dest) else 0))


# ---------------------------------------------------------------- shmeta
def api_get(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1 + i)


def cmd_shmeta():
    cats = api_get("https://lightmake.site/api/v1/categories")["items"]
    log("[shmeta] categories=%d" % len(cats))
    all_skills = []
    per_cat = {}
    for c in cats:
        key = c["key"]
        got = []
        for page in (1, 2):
            url = ("https://lightmake.site/api/skills?category=%s&pageSize=100&page=%d&sortBy=downloads"
                   % (key, page))
            d = api_get(url)
            batch = d.get("data", {}).get("skills", [])
            got.extend(batch)
            log("[shmeta] %s page=%d got=%d" % (key, page, len(batch)))
            if not batch:
                break
        per_cat[key] = len(got)
        all_skills.extend(got)
    # 全局按 slug 去重，保 downloads 最高的版本
    best = {}
    for s in all_skills:
        slug = s.get("slug")
        if not slug:
            continue
        cur = best.get(slug)
        if cur is None or (s.get("downloads") or 0) > (cur.get("downloads") or 0):
            best[slug] = s
    skills = sorted(best.values(), key=lambda x: x.get("downloads") or 0, reverse=True)
    out = {"categories": cats, "perCategoryRaw": per_cat,
           "rawCount": len(all_skills), "dedupCount": len(skills), "skills": skills}
    p = os.path.join(RAW, "skillhub", "meta_top200.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    log("[shmeta] raw=%d dedup=%d -> %s" % (len(all_skills), len(skills), p))


# ---------------------------------------------------------------- shdl
def cmd_shdl():
    meta = json.load(open(os.path.join(RAW, "skillhub", "meta_top200.json"), encoding="utf-8"))
    skills = meta["skills"]
    jobs = []
    for s in skills:
        slug = s["slug"]
        ns = (s.get("namespace") or {}).get("handle") or ""
        url = "https://lightmake.site/api/v1/download?slug=%s" % urllib.parse.quote(slug)
        if ns:
            url += "&namespace=" + urllib.parse.quote(ns)
        safe = ("%s__%s" % (slug, ns)).replace("/", "_")[:110]
        dest = os.path.join(RAW, "skillhub", "zips", safe + ".zip")
        jobs.append((slug, url, dest))
    log("[shdl] %d skills to download" % len(jobs))

    def one(job):
        slug, url, dest = job
        return download(url, dest, retries=4, timeout=120)

    ok, fail = parallel(jobs, one, workers=8, label="shdl")
    log("[shdl] DONE ok=%d fail=%d" % (ok, fail))


# ---------------------------------------------------------------- local
def safe_copytree(src, dst):
    if os.path.exists(dst):
        return "exists"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return "ok"


def cmd_local():
    home = os.path.expanduser("~")
    jobs = []
    conn_root = os.path.join(home, ".workbuddy", "connectors-marketplace", "connectors")
    for name in sorted(os.listdir(conn_root)):
        src = os.path.join(conn_root, name)
        if os.path.isdir(src):
            jobs.append(("connector", src, os.path.join(RAW, "local", "connectors", name)))
    for mk in sorted(os.listdir(os.path.join(home, ".workbuddy", "plugins", "marketplaces"))):
        ep_root = os.path.join(home, ".workbuddy", "plugins", "marketplaces", mk, "external_plugins")
        if os.path.isdir(ep_root):
            for name in sorted(os.listdir(ep_root)):
                src = os.path.join(ep_root, name)
                if os.path.isdir(src):
                    jobs.append(("plugin", src,
                                 os.path.join(RAW, "local", "plugins", mk, name)))
    # 内置技能
    for cand in [
        os.path.join(home, ".workbuddy", "plugins", "workbuddy-builtin"),
        os.path.join(home, ".workbuddy", "plugins", "marketplaces", "workbuddy-builtin"),
    ]:
        if os.path.isdir(cand):
            jobs.append(("builtin", cand, os.path.join(RAW, "local", "builtin")))
            break
    log("[local] %d source directories" % len(jobs))

    def one(job):
        kind, src, dst = job
        return safe_copytree(src, dst)

    ok, fail = parallel(jobs, one, workers=8, label="local")
    # 元数据 JSON 也带上
    for src, dst in [
        (os.path.join(home, ".workbuddy", "connectors-marketplace", ".codebuddy-connector", "connectors.json"),
         os.path.join(RAW, "local", "connectors.json")),
        (os.path.join(home, ".workbuddy", "connectors-marketplace", "connectors.json"),
         os.path.join(RAW, "local", "connectors-alt.json")),
    ]:
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    log("[local] DONE ok=%d fail=%d" % (ok, fail))


if __name__ == "__main__":
    import urllib.parse
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"experts": cmd_experts, "official": cmd_official, "shmeta": cmd_shmeta,
     "shdl": cmd_shdl, "local": cmd_local}[cmd]()
