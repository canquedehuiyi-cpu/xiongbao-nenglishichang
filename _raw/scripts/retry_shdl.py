#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重试 SkillHub 失败项：依次尝试 1) 原样 2) 去掉 namespace 3) 换分页元数据里的 homepage。"""
import os, sys, json, time, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_all import RAW, UA, download, log

fails = json.load(open(os.path.join(RAW, "failures-shdl.json"), encoding="utf-8"))
meta = json.load(open(os.path.join(RAW, "skillhub", "meta_top200.json"), encoding="utf-8"))
by_slug = {s["slug"]: s for s in meta["skills"]}
ok = still = 0
for i, x in enumerate(fails, 1):
    item = x["item"]  # (slug, url, dest)
    if isinstance(item, str):
        item = eval(item)
    slug, url, dest = item
    s = by_slug.get(slug, {})
    ns = (s.get("namespace") or {}).get("handle") or ""
    attempts = [
        "https://lightmake.site/api/v1/download?slug=%s" % urllib.parse.quote(slug),
        "https://lightmake.site/api/v1/download?slug=%s&namespace=%s" %
        (urllib.parse.quote(slug), urllib.parse.quote(ns)) if ns else None,
    ]
    res = "FAIL"
    for u in attempts:
        if not u:
            continue
        res = download(u, dest, retries=2, timeout=90)
        if not res.startswith("FAIL"):
            break
    if res.startswith("FAIL"):
        still += 1
    else:
        ok += 1
    if i % 10 == 0 or i == len(fails):
        log("[retry] %d/%d ok=%d still=%d" % (i, len(fails), ok, still))
json.dump([{"item": x["item"], "error": "retry exhausted"} for x in fails
           if not os.path.exists(eval(x["item"])[2] if isinstance(x["item"], str) else x["item"][2])],
          open(os.path.join(RAW, "skillhub", "still-missing.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
log("[retry] DONE ok=%d still=%d" % (ok, still))
