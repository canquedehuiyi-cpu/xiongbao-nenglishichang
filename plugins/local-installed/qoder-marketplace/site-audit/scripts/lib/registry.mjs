/**
 * 48 项检查的唯一真源。
 *
 * 为什么是代码而不是一篇 checklist.md：跨 skill 引用 prose 文件的路径解析没有官方保证，
 * 各自 vendor 一份必然漂移；而检查项要能被 ledger.mjs 用来算「本轮漏跑了什么」，
 * 必须是可枚举的数据。完备性闸门依赖本文件，不依赖任何人的记性。
 *
 * 字段：
 *   id      稳定编号，跨轮不变（账本按它结转）
 *   t       一行名
 *   lvl     M 机器可判定 / S 需人调阈值 / J 需人判断
 *   script  归属脚本
 *   modes   适用的审查模式：whitebox（有仓库）/ blackbox（只有 URL）
 *   caps    所需能力，任一缺失则该轮整项记 not-run
 *   unblock 解锁命令模板（写进 not-run 行，让人知道怎么补上）
 */

export const MODES = ['whitebox', 'blackbox'];

export const CAPS = {
  repo: '一个可遍历的项目树（本地克隆或 git archive 导出）',
  replay: '能执行该项目自己的构建/测试命令',
  net: '能访问审查目标',
  browser: '一个真实浏览器（DevTools 控制台/网络/可访问性树）',
  links: '允许对外链做存活探测（会打别人家的站，见 --probe-links）',
  git: '可用的 git 且该树是仓库或含 .git',
  ci: '能读到 CI 配置（.github/workflows 或等价物）',
  ledger: '存在上一轮账本可对照',
};

const WB = ['whitebox'];
const BB = ['blackbox'];
const BOTH = ['whitebox', 'blackbox'];

export const CHECKS = [
  /* ---------------- 构建产物取证 ---------------- */
  { id: 'BLD-1', t: '纯净导出重跑该项目的全套门禁（install/check/test/build/validate）', lvl: 'M', script: 'build-forensics.mjs', modes: WB, caps: ['repo', 'replay'], unblock: '提供 --repo 且该项目有可运行的构建脚本' },
  { id: 'BLD-2', t: '对产物 HTML 逐页断言关键结构存在（而非只看源码写了）', lvl: 'M', script: 'build-forensics.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo 与 --dist-glob' },
  { id: 'BLD-3', t: '把对抗性内容样本喂给真实渲染器并触发一次真实构建', lvl: 'M', script: 'build-forensics.mjs', modes: WB, caps: ['repo', 'replay'], unblock: '提供 --repo（需要能跑 build）' },
  { id: 'BLD-4', t: '产物安全普查：JS 数量、内联事件、URL 协议白名单、裸 HTML、控制字符', lvl: 'M', script: 'build-forensics.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo 与 --dist-glob' },
  { id: 'BLD-5', t: '体积与页数预算（逐页 HTML 字节、总量、增长趋势）', lvl: 'S', script: 'build-forensics.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo 与 --dist-glob' },
  { id: 'BLD-6', t: '站点地图集合与产物集合逐条相等 + 订阅源 XML 可解析且无双重转义', lvl: 'M', script: 'build-forensics.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo 与 --dist-glob' },

  /* ---------------- 线上 vs 产物 ---------------- */
  { id: 'LIVE-1', t: '被服务的响应 vs 构建产物：第三方脚本注入差异', lvl: 'M', script: 'live-and-edge.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url' },
  { id: 'LIVE-2', t: '真实浏览器控制台/网络里数 CSP 违规与被拒请求', lvl: 'S', script: 'live-and-edge.mjs', modes: BOTH, caps: ['browser'], unblock: '在带浏览器的环境里加 --browser（本工具不装浏览器驱动，用宿主浏览器）' },
  { id: 'LIVE-3', t: '上一轮每个修复上线后再量一次原指标（回执，不是信任）', lvl: 'S', script: 'live-and-edge.mjs', modes: BOTH, caps: ['net', 'ledger'], unblock: '需要上一轮账本' },

  /* ---------------- 传输层与边缘 ---------------- */
  { id: 'HDR-1', t: '端点×响应头矩阵（首页/深层页/订阅源/robots/自定义 404/http→https/favicon）', lvl: 'M', script: 'live-and-edge.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url' },
  { id: 'HDR-2', t: 'HSTS 是否存在、http 首跳窗口', lvl: 'M', script: 'live-and-edge.mjs', modes: BOTH, caps: ['net'], unblock: 'curl -sI <url> | grep -i strict-transport' },
  { id: 'HDR-3', t: '内容哈希资源的缓存寿命与不可变性', lvl: 'M', script: 'live-and-edge.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url 的静态资源' },
  { id: 'HDR-4', t: 'CSP 必要性核对（unsafe-inline 是否真被需要）+ 是否有违规上报', lvl: 'S', script: 'live-and-edge.mjs', modes: BOTH, caps: ['net'], unblock: '需要 --url（有 --dist 时能判定 inline 是否必需）' },

  /* ---------------- 注入面 ---------------- */
  { id: 'INJ-1', t: 'XSS 载荷电池打到真实渲染器，判据须转义感知（避免自误报）', lvl: 'S', script: 'injection.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo；本项只打本地渲染器，绝不打线上' },
  { id: 'INJ-2', t: '行内渲染顺序与 URL 正则的对抗样本（括号平衡、星号配对、占位符互踩）', lvl: 'M', script: 'injection.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'INJ-3', t: '不可信键做查表时的原型链命中（constructor/__proto__ 等）', lvl: 'M', script: 'injection.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },

  /* ---------------- 内容作为不可信输入 ---------------- */
  { id: 'CTX-1', t: '被渲染字段的完备性计数（DOM 里可数的成对结构是否一一兑现）', lvl: 'M', script: 'content-contract.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url' },
  { id: 'CTX-2', t: '页面公示的来源数用 HTML 三口径复算；加 --js 再叠一层渲染前源文件复算（跨阶段）', lvl: 'S', script: 'content-contract.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url' },
  { id: 'CTX-3', t: '文档声明的契约 vs 校验器实际断言：造一条违规样本看它放不放行', lvl: 'M', script: 'content-contract.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo（要能跑该校验器）' },
  { id: 'CTX-4', t: '语料级风格/假设计数器（标点、排版、时区、日期形态的分布漂移）', lvl: 'S', script: 'content-contract.mjs', modes: BOTH, caps: [], unblock: '' },
  { id: 'CTX-5', t: '编辑判断：具名个人非公开信息、归属缺口、自相矛盾日期、机器翻译痕迹', lvl: 'J', script: 'content-contract.mjs', modes: BOTH, caps: [], unblock: '' },

  /* ---------------- 发布链路信任边界 ---------------- */
  { id: 'PIPE-1', t: '实际执行的那份门禁代码来自哪里（可信副本能否被待发布快照反客为主）', lvl: 'J', script: 'pipeline-trust.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'PIPE-2', t: '破坏性操作与遍历读码：递归删除的路径校验、跟随符号链接', lvl: 'J', script: 'pipeline-trust.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'PIPE-3', t: '门禁顺序（校验是否在写远端之前）+ 是否存在只读预演模式', lvl: 'S', script: 'pipeline-trust.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'PIPE-4', t: '自动化幂等性与每次提交的范围（同名提交、超范围文件）', lvl: 'M', script: 'pipeline-trust.mjs', modes: WB, caps: ['repo', 'git'], unblock: '需要该树是 git 仓库（或用 --ref 指向克隆）' },
  { id: 'PIPE-5', t: '被跟踪文件里的本机绝对路径/用户名/内部目录', lvl: 'M', script: 'pipeline-trust.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'PIPE-6', t: '手上这份副本 == 远端 HEAD，且本地没有未提交/未推送的东西', lvl: 'M', script: 'pipeline-trust.mjs', modes: WB, caps: ['repo', 'git'], unblock: '需要 git；无 gh 时退回 git archive + git show（不改动任何克隆）' },

  /* ---------------- 凭据与依赖门禁 ---------------- */
  { id: 'SEC-1', t: '扫描器模式覆盖 vs 该文档自己推荐的凭据形态（用合成凭据实测）', lvl: 'M', script: 'gates.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'SEC-2', t: '扫描器自我触发（夹具里有真形态串会挡住发布）与日志回显片段', lvl: 'M', script: 'gates.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'SEC-3', t: '推送排除清单与忽略文件逐条比对（含子目录锚定形态）', lvl: 'M', script: 'gates.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'SEC-4', t: '门禁 fail-open 模糊测试：让被调命令出错，看它是红还是绿', lvl: 'M', script: 'gates.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'SEC-5', t: '放行清单/豁免开关的语义（一处确认是否清掉整个文件、能否被不可信内容武装）', lvl: 'S', script: 'gates.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'SEC-6', t: '依赖公告漂移 + 受影响特性在产物里是否真的可达', lvl: 'S', script: 'gates.mjs', modes: WB, caps: ['repo', 'replay'], unblock: '需要能跑 npm audit 且提供 --repo' },
  { id: 'SEC-7', t: 'lockfile 孤儿条目与 engines 声明一致性', lvl: 'M', script: 'gates.mjs', modes: WB, caps: ['repo', 'replay'], unblock: '提供 --repo' },
  { id: 'SEC-8', t: '令牌作用域是否超出所需、有无内嵌凭据、钩子来源是否仓库自带', lvl: 'M', script: 'gates.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo（令牌 scope 一项需 gh，缺则只记 not-run 该子项）' },

  /* ---------------- CI 与测试覆盖 ---------------- */
  { id: 'CI-1', t: '工作流清单、触发器与加固（permissions、SHA 钉、timeout、--ignore-scripts、注入面）', lvl: 'M', script: 'ci-hygiene.mjs', modes: WB, caps: ['repo', 'ci'], unblock: '提供 --repo' },
  { id: 'CI-2', t: '类型逃逸审计：每个 any/非空断言掩盖了什么、可空字段的调用点是否都收口', lvl: 'S', script: 'ci-hygiene.mjs', modes: WB, caps: ['repo', 'replay'], unblock: '提供 --repo' },
  { id: 'CI-3', t: '测试覆盖按层分布 vs 历史发现落在哪一层', lvl: 'S', script: 'ci-hygiene.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'CI-4', t: 'CI 到底挡不挡得住东西（是否只是事后信号、有无分支保护）', lvl: 'J', script: 'ci-hygiene.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },

  /* ---------------- SEO 与元数据 ---------------- */
  { id: 'SEO-1', t: 'head 完整性与错误页索引策略（canonical 逐页、noindex、OG/Twitter/theme-color）', lvl: 'M', script: 'surface.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url' },
  { id: 'SEO-2', t: '结构化数据说的真是事实吗（dateModified 与实际修订记录比对）', lvl: 'M', script: 'surface.mjs', modes: WB, caps: ['repo', 'git'], unblock: '提供 --repo（要能查该文件的修改历史）' },

  /* ---------------- 可访问性 ---------------- */
  { id: 'A11Y-1', t: '对比度按 WCAG 相对亮度逐令牌×主题算，并枚举其使用点', lvl: 'S', script: 'surface.mjs', modes: BOTH, caps: [], unblock: '' },
  { id: 'A11Y-2', t: '状态/可点性 CSS 与可访问名称（焦点环、减弱动效、卡片可访问名、永不命中的选择器）', lvl: 'S', script: 'surface.mjs', modes: BOTH, caps: ['browser'], unblock: '在带浏览器的环境里加 --browser' },

  /* ---------------- 文档与现实是否一致 ---------------- */
  { id: 'DOC-1', t: '对外声明 vs 实际产物/仓库元数据（说的托管方式、声明的防护是否存在）', lvl: 'M', script: 'content-contract.mjs', modes: WB, caps: ['repo'], unblock: '提供 --repo' },
  { id: 'DOC-2', t: '上一轮修复的逐项台账：复跑并记录证据，标出回归/部分修/未修', lvl: 'S', script: 'ledger.mjs', modes: BOTH, caps: ['ledger'], unblock: '需要上一轮账本' },
  { id: 'DOC-3', t: '注释过期、指向已删代码、永不成立的兜底、提交历史考古', lvl: 'J', script: 'content-contract.mjs', modes: WB, caps: ['repo', 'git'], unblock: '提供 --repo' },

  /* ---------------- 链接 ---------------- */
  { id: 'LNK-1', t: '追踪参数、协议降级、域名形态不一致、点击中转页', lvl: 'M', script: 'content-contract.mjs', modes: BOTH, caps: ['net'], unblock: '需要能访问 --url（有 --dist 时改扫产物）' },
  { id: 'LNK-2', t: '外链存活探测，并把「被 WAF 挡」与「真死」分开判定', lvl: 'S', script: 'surface.mjs', modes: BOTH, caps: ['links'], unblock: '加 --probe-links（会对外站发请求，受预算与熔断约束）' },
];

export const IDS = CHECKS.map((c) => c.id);

export function byId(id) {
  return CHECKS.find((c) => c.id === id) || null;
}

/** 某模式适用的检查 id 列表（完备性闸门的分母）。 */
export function applicable(mode) {
  return CHECKS.filter((c) => c.modes.includes(mode)).map((c) => c.id);
}

/** 缺能力 → 该检查在此模式下不可跑的原因。返回缺失的能力数组。 */
export function missingCaps(check, capabilities) {
  return check.caps.filter((c) => !capabilities || capabilities[c] !== true);
}

export function renderChecklist(mode) {
  const rows = CHECKS.filter((c) => !mode || c.modes.includes(mode));
  const byScript = new Map();
  for (const c of rows) {
    if (!byScript.has(c.script)) byScript.set(c.script, []);
    byScript.get(c.script).push(c);
  }
  const out = [`检查注册表：共 ${CHECKS.length} 项` + (mode ? `，${mode} 模式适用 ${rows.length} 项` : ''), ''];
  for (const [script, list] of byScript) {
    out.push(`## ${script}  (${list.length})`);
    for (const c of list) {
      out.push(`- ${c.id} [${c.lvl}] ${c.t}`);
      if (c.caps.length) out.push(`      需要能力: ${c.caps.join(', ')}`);
    }
    out.push('');
  }
  out.push('## 能力含义');
  for (const [k, v] of Object.entries(CAPS)) out.push(`- ${k} — ${v}`);
  return out.join('\n');
}
