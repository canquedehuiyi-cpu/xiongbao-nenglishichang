#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 _raw 里的原始资产整理成可直接移植的目录结构。

输出根目录由 OUT 指定（默认 D:/xiongbao-nenglishichang）。
"""
import os, re, sys, json, csv, shutil, zipfile, tarfile, glob

RAW = "D:/workbuddy-market-export/_raw"
OUT = os.environ.get("EXPORT_OUT", "D:/xiongbao-nenglishichang")
BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
RESERVED = {"CON", "PRN", "AUX", "NUL"} | {"COM%d" % i for i in range(1, 10)} | {"LPT%d" % i for i in range(1, 10)}
CJK = re.compile(r"[\u4e00-\u9fff]")
SPLIT_LIMIT = 90 * 1024 * 1024  # GitHub 单文件 100MB 红线，留余量


def log(*a):
    print(*a, flush=True)


def safe_name(s, limit=78):
    s = BAD.sub("_", str(s)).strip().strip(".")
    if not s:
        s = "未命名"
    s = s[:limit].rstrip(". ")
    if s.split(".")[0].upper() in RESERVED:
        s = "_" + s
    return s


def zh_candidate(*vals):
    """优先返回含中文的候选，保留专有名词。"""
    for v in vals:
        if v and CJK.search(str(v)):
            return str(v)
    return next((str(v) for v in vals if v), "未命名")


def first_sentence(s, limit=70):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if not s:
        return "（源数据未提供简介）"
    m = re.split(r"[。！？!?；;\n]", s, 1)[0]
    return (m or s)[:limit]


def uniq_dir(parent, name):
    base = safe_name(name)
    p = os.path.join(parent, base)
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)
        return base, p
    for i in range(2, 1000):
        cand = "%s(%d)" % (base[:70], i)
        p = os.path.join(parent, cand)
        if not os.path.exists(p):
            os.makedirs(p, exist_ok=True)
            return cand, p
    raise RuntimeError("uniq_dir exhausted: " + name)


def write_note(path, category, ident, intro, extra=None):
    lines = [
        "- **类目**：%s" % category,
        "- **原始标识**：%s" % ident,
        "",
        "## 简介",
        "",
        intro,
    ]
    if extra:
        lines += ["", "## 备注", ""] + [str(x) for x in extra]
    with open(os.path.join(path, "说明.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def extract_tar(member_path, dest):
    """解包 tar.gz：跳过软链接；超大文件切片。返回 (文件数, 跳过的软链接数, 切片列表)。"""
    n = lnk = 0
    splits = []
    with tarfile.open(member_path, "r:gz") as t:
        for m in t.getmembers():
            if m.issym() or m.islnk():
                lnk += 1
                continue
            rel = m.name.lstrip("./")
            if not rel:
                continue
            out = os.path.join(dest, safe_name(rel.replace("/", "__"), 100)) if ".." in rel else os.path.join(dest, *[safe_name(x, 80) for x in rel.split("/")])
            if m.isdir():
                os.makedirs(out, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            src = t.extractfile(m)
            if src is None:
                continue
            if m.size > SPLIT_LIMIT:
                with src:
                    idx = 1
                    while True:
                        chunk = src.read(SPLIT_LIMIT)
                        if not chunk:
                            break
                        part = "%s.part%02d" % (out, idx)
                        with open(part, "wb") as fp:
                            fp.write(chunk)
                        splits.append((os.path.basename(part), m.size))
                        idx += 1
            else:
                with src, open(out, "wb") as fp:
                    shutil.copyfileobj(src, fp, 1024 * 1024)
            n += 1
    return n, lnk, splits


def extract_zip(zip_path, dest):
    n = lnk = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            if info.is_dir():
                continue
            # zip 外部属性高位表示符号链接
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                lnk += 1
                continue
            parts = [safe_name(x, 80) for x in name.replace("\\", "/").split("/")]
            out = os.path.join(dest, *parts)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with z.open(info) as src, open(out, "wb") as fp:
                shutil.copyfileobj(src, fp, 1024 * 1024)
            n += 1
    return n, lnk


# ------------------------------------------------------------------ 01 专家
def do_experts():
    cat = json.load(open(os.path.join(RAW, "expert_center.json"), encoding="utf-8"))
    catmap = {c["id"]: c["name"].get("zh") or c["name"].get("en") for c in cat["categories"]}
    root = os.path.join(OUT, "01-专家市场")
    done = 0
    missing = []
    for e in cat["experts"]:
        category = catmap.get(e.get("categoryId"), "未分类")
        cdir = os.path.join(root, safe_name(category))
        os.makedirs(cdir, exist_ok=True)
        name = "%s（%s）" % (e["displayName"].get("zh") or e["displayName"].get("en"),
                            e["profession"].get("zh") or e["profession"].get("en"))
        dname, dest = uniq_dir(cdir, name)
        plugin = e.get("plugin") or e.get("agentName") or e["id"]
        bundle = os.path.join(RAW, "experts", "bundles", plugin + ".tar.gz")
        extra = ["- **专家 ID**：`%s`" % e["id"], "- **插件标识**：`%s`" % plugin]
        if os.path.isfile(bundle):
            n, lnk, splits = extract_tar(bundle, dest)
            extra.append("- **正文文件数**：%d" % n)
            if splits:
                extra += ["- **超大文件已切片**（GitHub 单文件上限）："] + [
                    "  - `%s`（原始 %d MB，需按顺序合并）" % (p, sz // 1048576) for p, sz in splits
                ]
            if lnk:
                extra.append("- **跳过软链接数**：%d" % lnk)
        else:
            missing.append(plugin)
        avatar = os.path.join(RAW, "experts", "avatars", e["id"] + ".png")
        if os.path.isfile(avatar):
            shutil.copy2(avatar, os.path.join(dest, "头像.png"))
        write_note(dest, category, e["id"],
                   first_sentence(e["description"].get("zh") or e["description"].get("en")), extra)
        done += 1
    log("[experts] organized %d entries, missing bundles=%d" % (done, len(missing)))
    return done


# ------------------------------------------------------------------ 02 连接器
def do_connectors():
    meta = json.load(open(os.path.join(RAW, "local", "connectors.json"), encoding="utf-8"))
    by_id = {c["id"]: c for c in meta["connectors"]}
    src_root = os.path.join(RAW, "local", "connectors")
    dest_root = os.path.join(OUT, "02-插件市场", "连接器")
    n = 0
    for name in sorted(os.listdir(src_root)):
        src = os.path.join(src_root, name)
        if not os.path.isdir(src):
            continue
        m = by_id.get(name, {})
        zh = zh_candidate(m.get("name"), m.get("name_en"), name)
        dname, dest = uniq_dir(dest_root, zh)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dest, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            elif os.path.isfile(s):
                shutil.copy2(s, d)
        write_note(dest, "连接器", name,
                   first_sentence(m.get("description_zh") or m.get("description")),
                   ["- **类型**：%s" % m.get("type", "—"),
                    "- **认证方式**：%s" % m.get("auth_mode", "—")] if m else None)
        n += 1
    log("[connectors] organized %d entries" % n)
    return n


# ------------------------------------------------------------------ 02 插件包
def do_plugins():
    src_root = os.path.join(RAW, "local", "plugins")
    dest_root = os.path.join(OUT, "02-插件市场", "插件包")
    n = 0
    for mk in sorted(os.listdir(src_root)):
        sub = os.path.join(src_root, mk)
        if not os.path.isdir(sub):
            continue
        for name in sorted(os.listdir(sub)):
            src = os.path.join(sub, name)
            if not os.path.isdir(src):
                continue
            mf = os.path.join(src, ".codebuddy-plugin", "plugin.json")
            m = {}
            if os.path.isfile(mf):
                try:
                    m = json.load(open(mf, encoding="utf-8"))
                except Exception:
                    pass
            desc = m.get("description") or ""
            zh = zh_candidate(first_sentence(desc, 24), name)
            cdir = os.path.join(dest_root, safe_name(mk))
            os.makedirs(cdir, exist_ok=True)
            dname, dest = uniq_dir(cdir, "%s（%s）" % (zh, name))
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dest, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                elif os.path.isfile(s):
                    shutil.copy2(s, d)
            write_note(dest, "插件包 / " + mk, name, first_sentence(desc),
                       ["- **许可**：%s" % m.get("license", "未声明"),
                        "- **作者**：%s" % (m.get("author", {}).get("name") if isinstance(m.get("author"), dict) else m.get("author", "—"))])
            n += 1
    log("[plugins] organized %d entries" % n)
    return n


# ------------------------------------------------------------------ 03 官方技能
def do_official():
    zp = os.path.join(RAW, "official", "skill-marketplace.zip")
    dest_root = os.path.join(OUT, "03-技能市场", "官方技能")
    with zipfile.ZipFile(zp) as z:
        mf = json.loads(z.read(".codebuddy-skill/marketplace.json").decode("utf-8-sig"))
    skills = mf["skills"]
    by_src = {s["source"]: s for s in skills}
    count = 0
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        tops = sorted({n.split("/")[1] for n in names if n.startswith("skills/") and len(n.split("/")) >= 3})
        for slug in tops:
            m = by_src.get(slug, {})
            category = (m.get("tags_zh") or ["未分类"])[0]
            cdir = os.path.join(dest_root, safe_name(category))
            os.makedirs(cdir, exist_ok=True)
            zh = zh_candidate(m.get("name"), first_sentence(m.get("description_zh"), 24), slug)
            dname, dest = uniq_dir(cdir, zh)
            prefix = "skills/%s/" % slug
            for info in z.infolist():
                if not info.filename.startswith(prefix) or info.filename.endswith("/"):
                    continue
                rel = info.filename[len(prefix):]
                if not rel:
                    continue
                out = os.path.join(dest, *[safe_name(x, 80) for x in rel.split("/")])
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with z.open(info) as src, open(out, "wb") as fp:
                    shutil.copyfileobj(src, fp, 1024 * 1024)
            write_note(dest, category, slug,
                       first_sentence(m.get("description_zh") or m.get("description")),
                       ["- **版本**：%s" % m.get("version", "—")])
            count += 1
    log("[official] organized %d entries" % count)
    return count


# ------------------------------------------------------------------ 03 内置技能
def do_builtin():
    src_root = os.path.join(RAW, "local", "builtin")
    dest_root = os.path.join(OUT, "03-技能市场", "内置技能")
    n = 0
    for name in sorted(os.listdir(src_root)):
        src = os.path.join(src_root, name)
        if not os.path.isdir(src):
            continue
        _, dest = uniq_dir(dest_root, name)
        for item in os.listdir(src):
            s, d = os.path.join(src, item), os.path.join(dest, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            elif os.path.isfile(s):
                shutil.copy2(s, d)
        write_note(dest, "内置", name, "WorkBuddy 内置插件/技能包（含多个历史版本目录）。",
                   ["- **版本目录**：%s" % ", ".join(sorted(os.listdir(src))[:6])])
        n += 1
    log("[builtin] organized %d entries" % n)
    return n


# ------------------------------------------------------------------ 03 社区技能
def do_community():
    meta = json.load(open(os.path.join(RAW, "skillhub", "meta_top200.json"), encoding="utf-8"))
    cats = {c["key"]: c["name"] for c in meta["categories"]}
    dest_root = os.path.join(OUT, "03-技能市场", "社区技能")
    zroot = os.path.join(RAW, "skillhub", "zips")
    have = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(zroot, "*.zip"))}
    n = miss = 0
    for s in meta["skills"]:
        slug = s["slug"]
        ns = (s.get("namespace") or {}).get("handle") or ""
        key = ("%s__%s" % (slug, ns)).replace("/", "_")[:110]
        zp = os.path.join(zroot, key + ".zip")
        category = cats.get(s.get("category"), s.get("category") or "未分类")
        cdir = os.path.join(dest_root, safe_name(category))
        os.makedirs(cdir, exist_ok=True)
        zh = zh_candidate(first_sentence(s.get("name"), 40), first_sentence(s.get("description_zh"), 24), slug)
        dname, dest = uniq_dir(cdir, zh)
        extra = ["- **作者**：%s" % (s.get("publisher", {}).get("name") or ns or "—"),
                 "- **版本**：%s" % s.get("version", "—"),
                 "- **下载量**：%s" % s.get("downloads", "—"),
                 "- **主页**：%s" % s.get("homepage", "—")]
        if os.path.isfile(zp):
            cnt, lnk = extract_zip(zp, dest)
            extra.append("- **正文文件数**：%d" % cnt)
        else:
            miss += 1
            extra.append("- **状态**：源站下载失败（404 或网络错误），仅保留元数据")
        write_note(dest, category, "%s@%s" % (slug, ns or "—"),
                   first_sentence(s.get("description_zh") or s.get("description")), extra)
        n += 1
    log("[community] organized %d entries, missing zip=%d" % (n, miss))
    return n


# ------------------------------------------------------------------ 索引
def build_index():
    idx = os.path.join(OUT, "索引")
    os.makedirs(idx, exist_ok=True)
    rows = []
    for root, dirs, files in os.walk(OUT):
        if "说明.md" not in files:
            continue
        note = os.path.join(root, "说明.md")
        txt = open(note, encoding="utf-8").read()
        def field(k):
            m = re.search(r"^- \*\*%s\*\*：(.+)$" % k, txt, re.M)
            return m.group(1).strip() if m else ""
        rel = os.path.relpath(root, OUT).replace("\\", "/")
        part = rel.split("/")[0]
        rows.append((part, field("类目"), os.path.basename(root), field("原始标识"), rel, note))
    rows.sort()
    for part in sorted({r[0] for r in rows}):
        p = os.path.join(idx, part + ".csv")
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["分区", "类目", "条目名称", "原始标识", "相对路径", "说明文件"])
            for r in rows:
                if r[0] == part:
                    w.writerow(r)
    with open(os.path.join(idx, "全部条目.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["分区", "类目", "条目名称", "原始标识", "相对路径", "说明文件"])
        w.writerows(rows)
    log("[index] %d rows, %d partition CSVs" % (len(rows), len({r[0] for r in rows})))
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    counts = {}
    for k, fn in [("experts", do_experts), ("connectors", do_connectors), ("plugins", do_plugins),
                  ("official", do_official), ("builtin", do_builtin), ("community", do_community)]:
        try:
            counts[k] = fn()
        except Exception as e:
            log("[%s] FAILED %s: %s" % (k, type(e).__name__, e))
            raise
    rows = build_index()
    json.dump({"counts": counts, "indexRows": len(rows)},
              open("D:/workbuddy-market-export/_raw/organize-summary.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    log("[organize] DONE counts=%s" % counts)
