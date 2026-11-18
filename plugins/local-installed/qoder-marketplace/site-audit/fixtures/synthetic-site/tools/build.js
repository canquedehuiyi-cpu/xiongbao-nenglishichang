import { readFileSync, writeFileSync, mkdirSync, readdirSync, rmSync, existsSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { parsePost, renderPost } from './render.js';

const CSS = `:root{--fg:#111;--fg-faint:#b9b9b9;--bg:#fff}
@media (prefers-color-scheme:dark){:root{--fg:#eee;--fg-faint:#5a5a5a;--bg:#111}}
body{color:var(--fg);background:var(--bg);font-family:system-ui,sans-serif;line-height:1.7}
.src-date{color:var(--fg-faint);font-size:.72rem}
.stats b{font-variant-numeric:tabular-nums}
.item:hover{box-shadow:0 6px 18px rgba(0,0,0,.18);transform:translateY(-3px)}
a{text-decoration:none;color:#0645ad}
@media print{.stats{display:none}}
`;
const CSS_URL = '/assets/site.' + createHash('sha256').update(CSS).digest('hex').slice(0, 8) + '.css';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src', 'posts');
const dist = join(root, 'dist');

if (existsSync(dist)) rmSync(dist, { recursive: true, force: true });
mkdirSync(join(dist, 'posts'), { recursive: true });
mkdirSync(join(dist, 'assets'), { recursive: true });

const files = readdirSync(src).filter((f) => f.endsWith('.md')).sort();
const index = [];
for (const f of files) {
  const slug = basename(f, '.md');
  const md = readFileSync(join(src, f), 'utf8');
  const post = parsePost(md);
  const html = renderPost(post, {
    title: `合成日报 ${slug}`,
    canonical: `https://synthetic.example/posts/${slug}/`,
    css: CSS_URL,
  });
  mkdirSync(join(dist, 'posts', slug), { recursive: true });
  writeFileSync(join(dist, 'posts', slug, 'index.html'), html, 'utf8');
  index.push({ slug, items: post.items.length, sections: post.sections.length });
}

writeFileSync(
  join(dist, 'index.html'),
  `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>合成日报</title>
<link rel="canonical" href="https://synthetic.example/"><meta name="robots" content="noindex">
<link rel="stylesheet" href="${CSS_URL}"></head><body><main><h1>合成日报</h1><ul>
${index.map((i) => `<li><a href="/posts/${i.slug}/">${i.slug}</a>（${i.items} 条）</li>`).join('\n')}
</ul></main></body></html>\n`,
  'utf8'
);
writeFileSync(join(dist, '404.html'), '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>404</title><meta name="robots" content="noindex, nofollow"><link rel="canonical" href="https://synthetic.example/404"><link rel="stylesheet" href="${CSS_URL}"></head><body><h1>找不到</h1><p><a href="/">回到首页</a></p></body></html>\n', 'utf8');
writeFileSync(join(dist, 'assets', CSS_URL.split('/').pop()), CSS, 'utf8');
writeFileSync(
  join(dist, 'posts.xml'),
  `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>合成日报</title>
<link>https://synthetic.example/</link><description>合成数据，仅用于验收。</description>
${index.map((i) => `<item><title>合成日报 ${i.slug}</title><link>https://synthetic.example/posts/${i.slug}/</link><guid isPermaLink="true">https://synthetic.example/posts/${i.slug}/</guid><description>${i.items} 条</description></item>`).join('\n')}
</channel></rss>\n`,
  'utf8'
);
writeFileSync(join(dist, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://synthetic.example/</loc></url>
${index.map((i) => `<url><loc>https://synthetic.example/posts/${i.slug}/</loc></url>`).join('\n')}
<url><loc>https://synthetic.example/posts/9999-99-99/</loc></url>
</urlset>\n`, 'utf8');
writeFileSync(join(dist, 'robots.txt'), 'User-agent: *\nAllow: /\n\nSitemap: https://synthetic.example/sitemap.xml\n', 'utf8');

console.log(`build: ${files.length} 篇 → ${index.reduce((n) => n + 1, 0) + 3} 个文件`);
