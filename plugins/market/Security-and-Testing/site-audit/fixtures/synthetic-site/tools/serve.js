/**
 * 本地静态服务器。缺陷 F4：给每个 HTML 响应注入一段第三方脚本，
 * 而它自己下发的 CSP 又是 `script-src 'self'` —— 于是产物里干干净净，
 * 浏览器控制台里每页一条 CSP 违规。只看 dist 永远发现不了这件事。
 *
 * 用法：node tools/serve.js [端口]   （stdout 打印 LISTENING <port>，供脚本抓取）
 */

import { createServer } from 'node:http';
import { readFileSync, existsSync, statSync } from 'node:fs';
import { join, dirname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = resolve(join(root, 'dist'));
const port = Number(process.argv[2] || 0);

const INJECTED =
  '<script src="https://cdn.metrics.example/beacon.js" data-metrics-token="<REDACTED>" crossorigin="anonymous"></script>';

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.xml': 'application/xml',
  '.txt': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
};

const server = createServer((req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0]);
  let file = join(dist, p);
  if (!file.startsWith(dist + sep) && file !== dist) {
    res.writeHead(403).end('outside root');
    return;
  }
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
  if (!existsSync(file)) {
    const body = readFileSync(join(dist, '404.html'), 'utf8').replace('</head>', INJECTED + '\n</head>');
    res.writeHead(404, notFoundHeaders(file));
    res.end(body);
    return;
  }
  const ext = file.slice(file.lastIndexOf('.'));
  let body = readFileSync(file, 'utf8');
  if (ext === '.html') body = body.replace('</head>', INJECTED + '\n</head>');
  res.writeHead(200, headersFor(ext, file));
  res.end(body);
});

// 与真实托管边缘一致的一揽子默认：安全头齐、但哈希资源寿命过短、无 HSTS。
function headersFor(ext) {
  return {
    'content-type': TYPES[ext] || 'application/octet-stream',
    'cache-control': 'public, max-age=14400, must-revalidate',
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
    'referrer-policy': 'strict-origin-when-cross-origin',
    'content-security-policy':
      "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'self'",
    'access-control-allow-origin': 'http://localhost',
  };
}
function notFoundHeaders() {
  return { ...headersFor('.html'), 'cache-control': 'no-store' };
}

server.listen(port, '127.0.0.1', () => {
  console.log(`LISTENING ${server.address().port}`);
});
