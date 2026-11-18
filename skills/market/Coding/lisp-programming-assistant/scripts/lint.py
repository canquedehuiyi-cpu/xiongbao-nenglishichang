# -*- coding: utf-8 -*-
"""
用法: python scripts/lint.py <文件.lsp> [--json]

可选静态检查 —— 只是辅助定位 bug, 不是加载 / 交付门槛:
  · 不连 CAD, 纯本地读文件, 很快;
  · 结果**可能误报**(全是启发式规则): 报了错照样 push_test.py 加载实跑,
    最终以 CAD 实际的返回值 / 现象为准;
  · 退出码恒为 0, 不阻断任何流程。

查四类:
  syntax  括号 / 字符串 / 块注释闭合(带行列)、中文全角标点
  leak    变量没写进 / 后面(跑到全局)、踩受保护符号、重复 defun / c:XXX
  block   会让 lisp_eval 阻塞的交互函数(entsel / getfiled / getpoint ...)
  debug   残留的调试日志代码(交付前该删)

源文件按 GBK 优先、UTF-8 兜底读取(开发期多为 UTF-8, 交付已转 ANSI)。
"""
import json
import re
import sys

# ---------------------------------------------------------------- 1. 符号表
# 受保护符号: 把内置函数名当局部变量并在函数体内赋值 → CAD 弹「分配给受保护的符号」
_PROTECTED_SRC = (
    'defun defun-q lambda setq set quote function eval apply mapcar mapc maplist foreach while repeat if cond progn prog1 prog2 and or not null atom list listp numberp '
    'stringp symbolp boundp type vl-symbolp vl-symbol-name vl-symbol-value vl-princ-to-string vl-listp '
    'car cdr caar cadr cdar cddr caddr cadddr caddar cddar last nth nthcdr length append reverse cons assoc member subst sublist vl-position vl-sort vl-remove vl-remove-if vl-remove-if-not vl-member-if '
    'abs min max rem mod gcd lsh logand logior logxor expt exp log sqrt sin cos atan fix float itoa atoi atof rtos angtos angtof distof cvunit '
    'strcat strlen substr strcase vl-string-search vl-string-subst vl-string-trim vl-string-position '
    'prompt princ prin1 print write-line write-char read open close '
    'entget entmod entmake entmakex entdel entnext entlast entupd trans osnap ssget ssadd ssdel ssname sslength ssnamex ssgetfirst regapp tblsearch tblnext tblobjname '
    'getvar setvar getenv setenv getcfg setcfg command vl-cmdf vl-load-com vl-propagate vlax-invoke-method vlax-get-property vlax-put-property vlax-property-available-p vlax-for vlax-ename->vla-object vlax-get-acad-object '
    'vlax-curve-getstartpoint vlax-curve-getendpoint vlax-curve-getdistatparam vlax-curve-getendparam vlax-curve-getpointatdist vlax-curve-getparamatpoint vla-get-length vla-put-length '
    'findfile load menucmd dump exit quit distance angle polar inters boole equal eq alloc '
    't nil'
).split()
PROTECTED = set(_PROTECTED_SRC)
RESERVED = {'pi'}

# 交互函数: 经 lisp_eval 调用会阻塞 CAD 主线程(SKILL.md §3 铁律)
INTERACTIVE = {'entsel', 'nentsel', 'nentselp', 'ssget', 'getfiled', 'getstring', 'getreal',
               'getint', 'getpoint', 'getcorner', 'getdist', 'getangle', 'getorient',
               'getkword', 'grread'}

FW = {'（': '(', '）': ')', '；': ';', '，': ',', '：': ':', '“': '"', '”': '"',
      '‘': "'", '’': "'", '　': ' ', '、': ',', '。': '.', '？': '?', '！': '!', '＝': '='}
FW_QUIET = '，：“”‘’、'          # 实测不报错、结果静默出错 —— 比报错更难查

_DEBUG_RE = re.compile(r'^\*.+-log\*$', re.I)
_SPACE = ' \t\n\r\x0c\x0b'
_STOP = ' \t\n\r\x0c()"\';'


# ---------------------------------------------------------------- 2. 词法扫描
def scan(src):
    """返回 (tokens, errors); 注释 / 字符串里的括号不算括号。"""
    toks, errs = [], []
    n, i = len(src), 0
    while i < n:
        c = src[i]
        if c == ';':
            if src[i + 1:i + 2] == '|':                       # ;| 块注释
                e = src.find('|;', i + 2)
                if e < 0:
                    errs.append(('blockcomment-unterminated', i, i + 1))
                    i = n
                else:
                    i = e + 2
            else:                                              # 行注释到行尾
                e = src.find('\n', i)
                i = n if e < 0 else e
            continue
        if c == '"':
            k, closed = i + 1, False
            while k < n:
                if src[k] == '\\':
                    k += 2
                    continue
                if src[k] == '"':
                    k += 1
                    closed = True
                    break
                k += 1
            if not closed:
                toks.append(('string', i, n))
                errs.append(('string-unterminated', i, i + 1))
                i = n
            else:
                toks.append(('string', i, k))
                i = k
            continue
        if c == "'":                                           # 'X ≡ (quote X)
            toks.append(('quote', i, i + 1))
            i += 1
            continue
        if c == '(':
            toks.append(('open', i, i + 1))
            i += 1
            continue
        if c == ')':
            toks.append(('close', i, i + 1))
            i += 1
            continue
        if c in _SPACE:
            i += 1
            continue
        s = i
        while i < n and src[i] not in _STOP:
            i += 1
        if i == s:
            i += 1
        toks.append(('atom', s, i))
    return toks, errs


def parse(toks, errs, end):
    """建嵌套节点 {'k','f','g','kids','q'}；' 补成 (quote X) 的包装表。"""
    root = {'k': 'list', 'f': 0, 'g': end, 'kids': [], 'q': False}
    stack = [root]

    def close_quotes(at):
        """引号只作用于紧跟的一个表达式：装满了就收，到右括号时也收。"""
        while len(stack) > 1 and stack[-1]['q'] and len(stack[-1]['kids']) >= 2:
            nd = stack.pop()
            nd['g'] = nd['kids'][-1]['g']

    def flush_quotes(at):
        while len(stack) > 1 and stack[-1]['q']:
            nd = stack.pop()
            nd['g'] = nd['kids'][-1]['g'] if nd['kids'] else at

    for t, f, g in toks:
        close_quotes(f)
        if t == 'open':
            nd = {'k': 'list', 'f': f, 'g': end, 'kids': [], 'q': False}
            stack[-1]['kids'].append(nd)
            stack.append(nd)
        elif t == 'quote':
            nd = {'k': 'list', 'f': f, 'g': g, 'q': True,
                  'kids': [{'k': 'atom', 't': 'quote', 'f': f, 'g': g}]}
            stack[-1]['kids'].append(nd)
            stack.append(nd)
        elif t == 'close':
            if len(stack) > 1:
                nd = stack.pop()
                nd['g'] = g
                flush_quotes(g)
            else:
                errs.append(('unmatched-close', f, f + 1))
        else:
            stack[-1]['kids'].append({'k': t, 'f': f, 'g': g})
    flush_quotes(end)
    while len(stack) > 1:                                      # 剩下的都是没闭合的
        nd = stack.pop()
        nd['g'] = nd['f']
        if not nd['q']:
            errs.append(('unclosed-list', nd['f'], nd['f'] + 1))
    return root


def kids(n):
    return [k for k in n['kids'] if k['k'] not in ('comment', 'bcomment')]


def txt(src, n):
    return n['t'] if 't' in n else src[n['f']:n['g']]


def head(src, n):
    ks = kids(n)
    return txt(src, ks[0]).lower() if (ks and ks[0]['k'] == 'atom') else ''


def line_index(src):
    a = [0]
    for i, ch in enumerate(src):
        if ch == '\n':
            a.append(i + 1)
    return a


def off_to_pos(li, off):
    off = max(off, 0)
    lo, hi = 0, len(li) - 1
    while lo < hi:
        mid = (lo + hi + 1) >> 1
        if li[mid] <= off:
            lo = mid
        else:
            hi = mid - 1
    return lo, off - li[lo]


# ---------------------------------------------------------------- 3. 检查
_FN_HEAD = ('defun', 'defun-q', 'lambda')


def targets(src, n, h):
    """setq / set 的赋值目标（每对固定占两个子节点，list 值不会错位）。"""
    ks = kids(n)
    if h == 'setq':
        return ks[1::2] if len(ks) >= 3 else []
    if len(ks) < 2:
        return []
    t1 = ks[1]
    if t1['k'] == 'list':                                      # (set 'x v)
        kk = kids(t1)
        if len(kk) == 2 and kk[0]['k'] == 'atom' and txt(src, kk[0]).lower() == 'quote':
            t1 = kk[1]
    return [t1]


def collect_toplevel_globals(src, root):
    """顶层赋值过的名字 = 文件显式声明的全局变量（双模式模板的 *xx-mode* 就靠这个不误报）。"""
    out = {}

    def w(n):
        ks = kids(n)
        h = head(src, n)
        if h in _FN_HEAD:
            return                                             # 函数内部一律不算顶层
        if h in ('foreach', 'vlax-for'):
            for k in ks[2:]:
                if k['k'] == 'list':
                    w(k)
            return
        if h in ('setq', 'set'):
            for t in targets(src, n, h):
                if t is None or t['k'] != 'atom':
                    continue
                nm = txt(src, t)
                if nm and nm[0] != ':':
                    out[nm.lower()] = nm
        for k in ks:
            if k['k'] == 'list':
                w(k)

    for k in kids(root):
        if k['k'] == 'list':
            w(k)
    return out


def has_mode_atom(src, n):
    """条件里出现 *xx-mode* 之类模式变量 → 这个分支是交互分支(lisp_eval 跑不到), 抑制阻塞告警。"""
    stack = [n]
    while stack:
        x = stack.pop()
        if x['k'] == 'atom' and 'mode' in txt(src, x).lower():
            return True
        stack.extend(x.get('kids') or [])
    return False


def build_frame(src, n, ks, kind):
    if kind == 'lambda':
        name = '(lambda)'
        al = ks[1] if len(ks) > 1 else None
    else:
        name = txt(src, ks[1]) if len(ks) > 1 else '(未命名)'
        al = ks[2] if len(ks) > 2 else None
    if al is not None and al['k'] == 'list':                   # defun-q 的 '(a / b)
        kk = kids(al)
        if len(kk) == 2 and kk[0]['k'] == 'atom' and txt(src, kk[0]).lower() == 'quote':
            al = kk[1]
    fr = {'kind': kind, 'name': name, 'node': n, 'decl': {},
          'al': al if (al is not None and al['k'] == 'list') else None}
    if fr['al'] is not None:
        for k in kids(fr['al']):
            if k['k'] != 'atom':
                continue
            nm = txt(src, k)
            if nm == '/' or not nm:
                continue
            fr['decl'][nm.lower()] = 1
    return fr


def analyze(src):
    toks, errs = scan(src)
    root = parse(toks, errs, len(src))
    LI = line_index(src)
    toplevel = collect_toplevel_globals(src, root)
    items = []
    leaks = {}                                                 # 帧 -> 未声明变量, 最后聚合成一条

    def push(sev, rule, off, msg, hint):
        ln, ch = off_to_pos(LI, off)
        items.append({'sev': sev, 'rule': rule, 'line': ln + 1, 'col': ch + 1,
                      'off': off, 'msg': msg, 'hint': hint or ''})

    # ---- syntax: 括号 / 字符串 / 块注释 ----
    SYN = {
        'string-unterminated': ('error', '这里的字符串没闭合（缺结尾双引号）→ 后面代码被整段吞进字符串，宿主报「输入的字符串有缺陷」', '补上 "；串内的双引号写成 \\"'),
        'blockcomment-unterminated': ('error', '块注释 ;| 没闭合（缺 |;）→ 宿主报「End of file within comment」，且前面的语句已执行、后面的被吃掉', '补上 |;'),
        'unmatched-close': ('error', '多余的 ) → 宿主报「misplaced right paren」', '删掉它，或在前面补一个配对的 ('),
        'unclosed-list': ('error', '这个 ( 没有配对的 ) → 宿主报「输入的列表有缺陷」', '在这个表达式末尾补 )'),
    }
    for code, f, g in errs:
        sev, msg, hint = SYN[code]
        push(sev, 'syntax', f, msg, hint)

    # ---- syntax: 中文全角标点 ----
    for t, f, g in toks:
        if t != 'atom':
            continue
        for k in range(f, g):
            half = FW.get(src[k])
            if not half:
                continue
            quiet = src[k] in FW_QUIET
            push('warn', 'syntax', k,
                 '中文全角标点「%s」—— AutoLISP 只认半角 %s，它会被拼进相邻符号名%s'
                 % (src[k], half, '（实测不报错、结果静默出错，更难查）' if quiet else '（宿主多半直接加载失败）'),
                 '改成半角 %s' % ('空格' if half == ' ' else half))

    # ---- 逐节点: 泄漏 / 受保护 / 阻塞 / 日志残留 ----
    frames = []
    defined = {}

    def walk(n, stack, in_quote=False, gui_ok=False):
        ks = kids(n)
        h = head(src, n)
        pushed = False
        q = in_quote
        if h == 'if' and len(ks) >= 3 and has_mode_atom(src, ks[1]):
            gui_ok = True                                      # 交互分支: lisp_eval 走不到, 不报阻塞
        if h in _FN_HEAD and len(ks) >= 2:
            if h != 'lambda' and not in_quote:
                defined.setdefault(txt(src, ks[1]).lower(), []).append(n)
            fr = build_frame(src, n, ks, 'lambda' if h == 'lambda' else 'defun')
            stack.append(fr)
            frames.append(fr)
            pushed = True
            q = False                                          # 被引号包住的 lambda/defun 也是函数
        elif h in ('foreach', 'vlax-for') and len(ks) > 1 and ks[1]['k'] == 'atom':
            stack.append({'kind': h, 'name': '循环变量 ' + txt(src, ks[1]), 'node': n,
                          'decl': {txt(src, ks[1]).lower(): 1}, 'al': None})
            pushed = True

        # 赋值检查
        if h in ('setq', 'set') and not in_quote:
            tv = list(zip(targets(src, n, h), (kids(n)[2::2] if h == 'setq' else [None])))
            for t, val in tv:
                if t is None or t['k'] != 'atom':
                    continue
                nm = txt(src, t)
                if not nm or nm[0] == ':':
                    continue
                if val is not None and _DEBUG_RE.match(nm) \
                        and val['k'] == 'atom' and txt(src, val).upper() == 'T':
                    push('info', 'debug', t['f'],
                         '调试日志开关 %s 还开着：交付前删掉日志代码并复位（SKILL.md §3.1「读完必须清」）' % nm,
                         '设为 nil 或直接删掉整段')
                ln = nm.lower()
                if any(ln in f['decl'] for f in stack):
                    continue
                if ln in PROTECTED:
                    push('error', 'leak', t['f'],
                         '(setq %s ...)：%s 是 AutoLISP 内置函数（受保护符号），运行时弹「分配给受保护的符号」'
                         % (nm, nm), '改名，例如 %s → %s_v' % (nm, nm))
                    continue
                if ln in RESERVED:
                    push('warn', 'leak', t['f'], '赋值覆盖了 AutoLISP 常量 %s' % nm, '换一个名字')
                    continue
                if not stack or ln in toplevel:
                    continue                                   # 顶层 / 已声明的全局变量，不算泄漏
                cur = stack[-1]
                owner = cur
                if cur['kind'] in ('foreach', 'vlax-for'):     # 循环帧: 变量其实属于外层函数, 归到它名下
                    owner = next((f for f in reversed(stack)
                                  if f['kind'] in ('defun', 'lambda')), cur)
                d = leaks.setdefault(id(owner), {'node': t, 'owner': owner, 'names': []})
                if nm not in d['names']:
                    d['names'].append(nm)                      # 同名只记一次

        # lisp_eval 阻塞预警
        if h in INTERACTIVE and not (in_quote or gui_ok) and ks and ks[0]['k'] == 'atom':
            if not (h == 'ssget' and len(ks) > 1):             # (ssget "_X" ...) 不阻塞，(ssget) 要用户框选
                push('warn', 'block', ks[0]['f'],
                     '(%s ...) 要用户交互：这段若经 lisp_eval 调用会阻塞 CAD 主线程（请求挂起超时、后续请求排队）' % h,
                     '调试模式从预设变量取参数；确需交互就走 lisp 异步通道')
        if h == 'command' and any(k['k'] == 'atom' and txt(src, k).lower() == 'pause' for k in ks[1:]):
            push('warn', 'block', ks[0]['f'],
                 '(command ... pause) 等待用户输入：经 lisp_eval 调用会阻塞 CAD 主线程',
                 '调试模式把 pause 换成预设值')

        # 残留的调试日志函数
        if h == 'tm-log':
            push('info', 'debug', ks[0]['f'], '残留调试日志调用 tm-log：交付前删掉整段',
                 '确认无误后可忽略；交付版不得往用户磁盘写日志')

        for k in ks:
            if k['k'] == 'list':
                walk(k, stack, q or h == 'quote', gui_ok)
        if pushed:
            stack.pop()

    for k in kids(root):
        if k['k'] == 'list':
            walk(k, [])

    # ---- leak: 按函数聚合（一个函数一条，列出变量名，别刷屏）----
    for d in leaks.values():
        f = d['owner']
        tag = '匿名函数 (lambda) 内' if f['kind'] == 'lambda' else '函数 %s 内' % f['name']
        ns = d['names']
        head_txt = ', '.join(ns[:6]) + (' …' if len(ns) > 6 else '')
        push('error', 'leak', d['node']['f'],
             '%s有 %d 个变量没写进参数表：%s → 跑到全局，命令之间互相干扰 / 二次运行结果不对'
             % (tag, len(ns), head_txt),
             '一起补进参数表 / 后面（含循环里的临时变量）')

    # ---- 重复定义 defun / c:XXX ----
    for nm, ns in defined.items():
        if len(ns) < 2:
            continue
        for nd in ns[1:]:
            push('error', 'leak', kids(nd)[1]['f'],
                 '%s %s 在本文件定义了 %d 次：CAD 不报错，生效的是最后那个，前面的被静默覆盖'
                 % ('命令' if nm.startswith('c:') else '函数', txt(src, kids(nd)[1]), len(ns)),
                 '改名，或确认是不是改坏了没删旧版')

    items.sort(key=lambda it: (0 if it['sev'] == 'error' else 1 if it['sev'] == 'warn' else 2, it['off']))
    return {'items': items, 'lines': len(LI), 'funcs': len(frames)}


# ---------------------------------------------------------------- 4. 命令行
def read_source(path):
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('gbk', 'utf-8-sig', 'utf-8'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('gbk', errors='replace')


def main(argv):
    try:                                                       # Windows 控制台默认 GBK
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    args = argv[1:]
    as_json = '--json' in args
    path = next((a for a in args if not a.startswith('-')), None)
    if not path:
        sys.stderr.write('用法：python scripts/lint.py <文件.lsp> [--json]\n')
        return 2

    res = analyze(read_source(path))
    items = res['items']
    if as_json:
        print(json.dumps({'file': path, 'lines': res['lines'], 'funcs': res['funcs'],
                          'items': items}, ensure_ascii=False, indent=2))
        return 0

    mark = {'error': 'X', 'warn': '!', 'info': '.'}
    print('%s   共 %d 行   函数 %d 个' % (path, res['lines'], res['funcs']))
    if not items:
        print('没有发现问题')
    for it in items:
        print('%s %d:%d  [%s] %s' % (mark[it['sev']], it['line'], it['col'], it['rule'], it['msg']))
        if it['hint']:
            print('      -> %s' % it['hint'])
    c = {s: sum(1 for it in items if it['sev'] == s) for s in ('error', 'warn', 'info')}
    print('---- 错误 %d · 警告 %d · 提示 %d ----' % (c['error'], c['warn'], c['info']))
    print('（静态检查仅供参考，可能误报：报错也照常加载实跑，以 CAD 实际返回值为准）')
    return 0                                                   # 恒为 0：不做闸门，不阻断流程


if __name__ == '__main__':
    sys.exit(main(sys.argv))
