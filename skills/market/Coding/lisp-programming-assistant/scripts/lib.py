# -*- coding: utf-8 -*-
"""
已验证辅助函数库 —— 一个函数一个文件, 存在技能目录之外(技能更新不会覆盖)。

库在 D:/TmLispLib(环境变量 TM_LISP_LIB 或 --dir 可改)。路径可以公开, 但**通道只有脚本**:
一律走下面这些命令, 不准直接读写库目录里的文件(索引/元数据/编码靠脚本维持)。

一轮到位(首选):
  python scripts/lib.py get <关键词> [更多词] [--with-deps]   直接给源码, 取分最高的那个
                                                              多个命中另列最多 3 个候选名
  python scripts/lib.py show <函数名> [--with-deps]           精确取(滤掉前缀也认)

探索 / 维护:
  python scripts/lib.py find <关键词> [更多词]          只看名字和说明, 不给源码(命中多的排前)
  python scripts/lib.py list                          重建索引并打印(库大了就贵, 非必要不用)
  python scripts/lib.py index                         只重建 references/_index.md
  python scripts/lib.py add <文件.lsp> <函数名> --desc "一句话说明" [--tags a,b]
  python scripts/lib.py rm <函数名>

索引:
  · 位置 references/_index.md(技能内) —— 技能更新整目录被换掉, 索引就没了, 但 D 盘库还在;
    这时跑 `index` 全量扫库重建即可, 内容一条不少。
  · **每次写入都是全量重建, 不是追加**: 追加会重复失序, 也反映不了 rm 删除。
  · 库为空时不写索引(并删掉旧的) —— 留个空的或旧的都会骗人, 没文件才是真没有。

约定:
  · **库文件名 = 函数名**(一个函数一个文件), 所以库里只有这一个标识, 没有"作用名";
    函数名按用途起英文名(tm-layer-create), 检索靠它 + 说明 + 标签, 不靠另起一个文件名;
  · 文件头 ;; desc: / ;; fn: / ;; tags: / ;; deps: / ;; created: / ;; updated: 是元数据,
    get/show 只把源码给出去(剥掉注释), 元数据不占版面 —— desc/tags 供检索, deps 供取依赖;
  · 同名 add = 覆盖, updated 写当天, created 保留最早那次;
  · 编码统一 UTF-8(开发期源码口径, AI 拿回去直接拼进自己的文件); 源文件按 GBK 优先读。
"""
import os
import re
import sys
import datetime

# 库存 D 盘(技能更新不影响); 索引放技能内 references/(技能更新后随目录被删 → 跑 `lib.py index` 重建)
LIB = os.environ.get('TM_LISP_LIB') or 'D:/TmLispLib'
REF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'references')
INDEX = os.path.join(REF, '_index.md')
HEAD = re.compile(r'^;;\s*([a-z]+):\s*(.*)$')
SEP = ';; ----------------------------------------------------------------'
_SPACE = ' \t\n\r\x0c\x0b'


def read_source(path):
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('gbk', 'utf-8-sig', 'utf-8'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('gbk', errors='replace')


def read_utf8(path):
    """读本脚本自己写的文件(库文件 / 索引): 一律 UTF-8。

    不能走 read_source —— 那是给用户的 GBK 源码用的。拿它读 UTF-8 中文会中招:
    UTF-8 字节恰好也是合法 GBK 时, 解码"成功"但解出满屏乱码(如 创建 → 鍒涘缓),
    而且随文字内容时好时坏 —— 最难查的一类 bug。
    """
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return raw.decode('gbk', errors='replace')


def strip_comments(src):
    """给 AI 看的源码不带注释：行注释 / ;|块注释|; 全剥，但字符串里的 ; 一律不动。"""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':                                   # 字符串整体照抄(里面的 ;; 不是注释)
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(src[i:j])
            i = j
            continue
        if c == ';':
            if src[i + 1:i + 2] == '|':
                e = src.find('|;', i + 2)
                i = n if e < 0 else e + 2
            else:
                e = src.find('\n', i)
                i = n if e < 0 else e                  # 换行留着, 别把两行粘一起
            continue
        out.append(c)
        i += 1
    lines = [ln.rstrip() for ln in ''.join(out).split('\n')]
    return '\n'.join(ln for ln in lines if ln.strip())


# ---------------------------------------------------------------- 提取 defun
def match_paren(src, i):
    """给 '(' 的下标, 返回配对 ')' 的下标(不含); 跳过字符串与注释。"""
    depth, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == ';':
            if src[i + 1:i + 2] == '|':
                e = src.find('|;', i + 2)
                i = n if e < 0 else e + 2
            else:
                e = src.find('\n', i)
                i = n if e < 0 else e
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def preceding_comment(src, start):
    """defun 上方紧挨着的一段 ;; 注释(给它当默认说明)。"""
    lines = src[:start].split('\n')
    got = []
    for ln in reversed(lines):
        s = ln.strip()
        if s.startswith(';;') and not HEAD.match(s):
            got.append(s.lstrip(';').strip())
        elif not s:
            if got:
                break
        else:
            break
    return '；'.join(reversed(got))


def extract_defun(src, fn):
    """返回 (起, 止) —— 止为独占下标; 找不到返回 None。"""
    for m in re.finditer(r'\((defun|defun-q)\s+' + re.escape(fn) + r'(?=[\s()])', src):
        end = match_paren(src, m.start())
        if end > 0:
            return m.start(), end + 1
    return None


def atoms_called(src, a, b):
    """粗略取这段里的调用头(位置为表首的元素), 用来判断依赖。"""
    out, i, n = [], a, b
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == ';':
            if src[i + 1:i + 2] == '|':
                e = src.find('|;', i + 2)
                i = n if e < 0 else e + 2
            else:
                e = src.find('\n', i)
                i = n if e < 0 else e
            continue
        if c == '(':
            j = i + 1
            while j < n and src[j] in _SPACE:
                j += 1
            k = j
            while k < n and src[k] not in _SPACE + '()"\';':
                k += 1
            if k > j:
                out.append(src[j:k].lower())
            i = k
            continue
        i += 1
    return out


# ---------------------------------------------------------------- 元数据
def load_entry(path):
    """读一个库文件 → {'slug','fn','desc','tags','deps','created','updated','body'}"""
    src = read_utf8(path)                                      # 库文件是脚本写的, 固定 UTF-8
    meta = {'slug': os.path.splitext(os.path.basename(path))[0], 'fn': '', 'desc': '',
            'tags': '', 'deps': '', 'created': '', 'updated': ''}
    body_start = 0
    for idx, ln in enumerate(src.split('\n')):
        m = HEAD.match(ln)
        if ln.strip().startswith(SEP):
            body_start = idx + 1
            break
        if m and m.group(1) in meta:
            meta[m.group(1)] = m.group(2).strip()
        elif ln.strip() and not ln.startswith(';;'):
            body_start = idx
            break
        else:
            body_start = idx + 1
    meta['body'] = '\n'.join(src.split('\n')[body_start:]).strip() + '\n'
    return meta


def entries():
    if not os.path.isdir(LIB):
        return []
    out = []
    for f in sorted(os.listdir(LIB)):
        if f.endswith('.lsp'):
            out.append(load_entry(os.path.join(LIB, f)))
    return out


def write_index():
    """全量重建(不追加): 每次扫整个库重写 —— 追加会重复失序, 也反映不了删除。
    库为空就不留索引(顺手删掉旧的, 免得旧内容骗人): 空库 = 没有文件 = 触发重建流程。"""
    es = entries()
    if not es:
        if os.path.exists(INDEX):
            os.remove(INDEX)
        return 0
    os.makedirs(REF, exist_ok=True)
    rows = ['| 函数名 | 说明 | 标签 | 依赖 | 更新日期 |',
            '|---|---|---|---|---|']
    for e in es:
        rows.append('| %s | %s | %s | %s | %s |'
                    % (e['fn'] or e['slug'], e['desc'], e['tags'], e['deps'], e['updated']))
    with open(INDEX, 'w', encoding='utf-8') as f:
        f.write('# LISP 函数库\n\n' + '\n'.join(rows) + '\n')
    return len(es)


def ensure_lib():
    if not os.path.isdir(LIB):
        os.makedirs(LIB)
    return LIB


# ---------------------------------------------------------------- 命令
def cmd_index(a):
    """重建 references/_index.md。技能更新删了索引、但 D 盘库还在时用这条全量扫回来。"""
    ensure_lib()
    n = write_index()
    if not n:
        print('库是空的：还没存过函数（索引就不写了，等存了自动带上）。')
        return 0
    print('索引已重建: references/_index.md（全量扫描，库 %d 个函数）' % n)
    return 0


def cmd_list(a):
    ensure_lib()
    n = write_index()
    if not n:
        print('库是空的：还没存过函数（索引就不写了，等存了自动带上）。')
        return 0
    print(read_utf8(INDEX))                                    # 索引也是脚本写的 UTF-8
    return 0


_WEIGH = (('slug', 3), ('fn', 3), ('desc', 2), ('tags', 2), ('deps', 1), ('body', 1))


def hits_in(entry, kws):
    """加权命中数: 名字(3) > 说明/标签(2) > 依赖/正文(1)。
    关键词里的空格不较真 —— 「csv行」要能命中「CSV 行」。"""
    n = 0
    for key, w in _WEIGH:
        v = entry[key].lower()
        v_ns = v.replace(' ', '')
        for k in kws:
            k_ns = k.replace(' ', '')
            if (k and k in v) or (k_ns and k_ns in v_ns):
                n += w
                break
    return n


def score(kws):
    """关键词 → 命中的条目, 按加权分降序: [(-分, slug, entry)]"""
    out = []
    for e in entries():
        n = hits_in(e, kws)
        if n:
            out.append((-n, e['slug'], e))
    return sorted(out)


def cmd_find(a):
    """没有库列表可翻: 关键词是唯一入口。多个词 = 任一命中即入选, 命中多的排前面。"""
    kws = [x.lower() for x in a if not x.startswith('-')]
    if not kws:
        print('用法: lib.py find <关键词> [更多关键词]')
        return 2
    all_e = entries()
    scored = score(kws)
    if not scored:
        print('没有匹配「%s」的函数（全库 %d 个）。换个词再 find，或 list 看全库。'
              % (' '.join(kws), len(all_e)))
        return 0
    for _, _, e in sorted(scored):
        print('%s  (%s)  %s' % (e['slug'], e['fn'], e['desc']))
        extra = ' | '.join(x for x in (('标签: ' + e['tags']) if e['tags'] else '',
                                       ('依赖: ' + e['deps']) if e['deps'] else '') if x)
        if extra:
            print('     %s' % extra)
    print('（命中 %d / 全库 %d 个；取用: lib.py show <函数名> [--with-deps]）'
          % (len(scored), len(all_e)))
    return 0


def cmd_show(a):
    args = [x for x in a if not x.startswith('-')]
    with_deps = '--with-deps' in a
    if not args:
        print('用法: lib.py show <函数名> [--with-deps]')
        return 2
    allmap = {e['slug']: e for e in entries()}
    # 库文件名就是函数名; 滤掉前缀也认(show layer-create → tm-layer-create)
    byfn = {e['fn'].lower(): e['slug'] for e in entries() if e['fn']}
    key = args[0] if args[0] in allmap else byfn.get(args[0].lower())
    if key is None:
        # 前缀容错: AI 常把 tm-layer-create 滤成 layer-create 再查 —— 唯一能对上就认
        q = args[0].lower()
        tails = set()
        for e in entries():
            for cand in (e['slug'], e['fn']):
                t = cand.lower()
                if '-' in t and t.split('-', 1)[1] == q:
                    tails.add(e['slug'])
        if len(tails) == 1:
            key = tails.pop()
        elif len(tails) > 1:
            print('「%s」对上多条: %s —— 用完整名字再查。'
                  % (args[0], ', '.join(sorted(tails))))
            return 1
    if key is None:
        import difflib
        near = difflib.get_close_matches(args[0], list(allmap) + list(byfn), n=3, cutoff=0.5)
        print('库里没有「%s」。%s' % (args[0],
                                ('最接近的: ' + ', '.join(near)) if near else '先 get / find 确认名字'))
        return 1
    printed, queue = set(), [key]
    while queue:
        s = queue.pop(0)
        if s in printed:
            continue
        printed.add(s)
        e = allmap.get(s)
        if not e:
            continue
        print(';; ===== %s (%s) =====' % (s, e['fn'] or '?'))
        print(strip_comments(e['body']))                        # 给 AI 的不带注释
        if with_deps:
            for d in [x.strip() for x in e['deps'].split(',') if x.strip()]:
                dep = next((k for k, v in allmap.items() if v['fn'] == d), None)
                if dep:
                    queue.append(dep)
                else:
                    print(';; 注意: 依赖 %s 不在库里，得从别处拿' % d)
    return 0


def cmd_get(a):
    """一轮到位: 关键词 → 直接给源码(取分最高的那个), 省掉 find → show 两趟。"""
    kws = [x.lower() for x in a if not x.startswith('-')]
    with_deps = '--with-deps' in a
    if not kws:
        print('用法: lib.py get <关键词> [更多词] [--with-deps]')
        return 2
    scored = score(kws)
    if not scored:
        print('没有匹配「%s」的函数（全库 %d 个）。换个词再 get。'
              % (' '.join(kws), len(entries())))
        return 1
    top = scored[0][2]
    others = [s[1] for s in scored[1:4]]                     # 候选最多给 3 个名字
    print(';; ===== %s (%s) =====' % (top['slug'], top['fn'] or '?'))
    print(';; %s' % top['desc'])
    if others:
        hidden = len(scored) - 1 - len(others)                # 列不下的还剩几个
        print(';; 命中 %d 个，取的是分最高的这个。其它: %s%s'
              % (len(scored), ', '.join(others), (' …等 %d 个' % hidden) if hidden > 0 else ''))
        print(';; 取错了就 show <上面任一名字>')
    print(strip_comments(top['body']))                          # 给 AI 的不带注释
    if with_deps:
        allmap = {e['slug']: e for e in entries()}
        for d in [x.strip() for x in top['deps'].split(',') if x.strip()]:
            dep = next((k for k, v in allmap.items() if v['fn'] == d), None)
            if dep:
                print(';; ===== 依赖 %s (%s) =====' % (dep, d))
                print(strip_comments(allmap[dep]['body']))
            else:
                print(';; 注意: 依赖 %s 不在库里，得从别处拿' % d)
    return 0


def cmd_add(a):
    args = [x for x in a if not x.startswith('-')]
    if len(args) < 2:
        print('用法: lib.py add <文件.lsp> <函数名> --desc "一句话说明" [--tags a,b]')
        return 2
    if '--name' in a:                                          # 文件名就是函数名, 没有第二个名字
        print('--name 已取消：库文件名 = 函数名，不需要另起名字。')
        return 2
    src_path, fn = args[0], args[1]

    def opt(name, default=''):
        return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default

    desc = opt('--desc')
    tags = ','.join([t.strip() for t in opt('--tags').split(',') if t.strip()])
    # 文件名 = 函数名。Windows 文件名不收 : * ? " < > | / \ —— 撞上就换成 -（冒号时代的 tm:join 走这里）
    name = re.sub(r'[:*?"<>|/\\]', '-', fn)
    ensure_lib()
    if name != fn:
        print('注意: 函数名里的 %s 不能做文件名，库文件名用了 %s —— 建议源码里也改成这个名。'
              % (''.join(sorted(set(fn) - set(name))), name))
    if len([t for t in tags.split(',') if t]) > 5:             # 标签别堆成垃圾场
        print('标签最多 5 个，你给了 %d 个: %s' % (len(tags.split(',')), tags))
        print('挑最管用的 5 个重来（检索是靠它们在捞）。')
        return 2

    if not os.path.isfile(src_path):
        print('找不到文件: %s' % src_path)
        return 1
    src = read_source(src_path)
    got = extract_defun(src, fn)
    if not got:
        print('在 %s 里找不到 (defun %s ...)；确认函数名写对了。' % (src_path, fn))
        return 1
    body = src[got[0]:got[1]]
    if not desc:
        desc = preceding_comment(src, got[0]) or '（没写说明）'

    # 依赖: 这段调到的、在本文件里另有 defun 的名字
    local = set()
    for m in re.finditer(r'\((?:defun|defun-q)\s+([^\s()]+)', src):
        local.add(m.group(1).lower())
    called = set(atoms_called(src, *got))
    deps = sorted(local & called - {fn.lower()})

    dst = os.path.join(LIB, name + '.lsp')
    old = load_entry(dst) if os.path.isfile(dst) else None
    today = datetime.date.today().isoformat()
    created = (old or {}).get('created') or today

    with open(dst, 'w', encoding='utf-8') as f:
        f.write(';; desc: %s\n;; fn: %s\n;; tags: %s\n;; deps: %s\n;; created: %s\n;; updated: %s\n%s\n'
                % (desc, fn, tags, ','.join(deps), created, today, SEP))
        f.write(body + '\n')
    write_index()

    print('已存入: %s  (%s)' % (name, fn))
    print('  说明: %s' % desc)
    if deps:
        miss = [d for d in deps if not os.path.isfile(os.path.join(LIB, d.replace(':', '-') + '.lsp'))
                and d not in [e['fn'] for e in entries()]]
        print('  依赖: %s%s' % (','.join(deps), ('  ← 依赖还没入库: ' + ','.join(miss)) if miss else ''))
    print('  取用: python scripts/lib.py show %s [--with-deps]' % name)
    return 0


def cmd_rm(a):
    args = [x for x in a if not x.startswith('-')]
    if not args:
        print('用法: lib.py rm <函数名>')
        return 2
    dst = os.path.join(LIB, args[0] + '.lsp')
    if not os.path.isfile(dst):
        print('库里没有「%s」。' % args[0])
        return 1
    os.remove(dst)
    write_index()
    print('已删除: %s' % args[0])
    return 0


CMD = {'list': cmd_list, 'index': cmd_index, 'find': cmd_find, 'get': cmd_get,
       'show': cmd_show, 'add': cmd_add, 'rm': cmd_rm}


def take_dir(a):
    """剥掉 --dir <路径>(临时换个库时用); 日常不用 —— 路径不进 SKILL.md。"""
    global LIB
    if '--dir' in a:
        i = a.index('--dir')
        if i + 1 >= len(a):
            sys.exit('--dir 后面要跟路径')
        LIB = a[i + 1].rstrip('/\\')
        del a[i:i + 2]
        ensure_lib()
    return a


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    args = take_dir(argv[1:])
    if not args or args[0] not in CMD:
        sys.stderr.write('用法: python scripts/lib.py get <关键词> [更多词] [--with-deps] '
                         '| find <关键词> | show <函数名> [--with-deps] | index | list '
                         '| add <文件.lsp> <函数名> --desc "说明" [--tags a,b] '
                         '| rm <函数名>\n')
        return 2
    return CMD[args[0]](args[1:])


if __name__ == '__main__':
    sys.exit(main(sys.argv))
