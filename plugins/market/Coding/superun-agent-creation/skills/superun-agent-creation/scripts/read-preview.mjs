/** 读取本专家的实时预览入口，不发布、不返回正式地址。@author xiuyu.yi */
import { constants } from 'node:fs';
import { access, readFile, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const expectsSlides = false;
const fail = (code, message) => Object.assign(new Error(message), { code });

async function cliRoot(executable) {
  if (!executable || !path.isAbsolute(executable)) throw fail('INVALID_ARGUMENT', '请传入运行准备返回的CLI绝对路径。');
  await access(executable, constants.X_OK);
  // Windows npm 的 cmd 位于 prefix，JavaScript 入口位于 node_modules 包内。
  const resolved = await realpath(executable);
  let root = /\.cmd$/i.test(resolved) ? path.join(path.dirname(resolved), 'node_modules', 'superun-ai-cli') : path.dirname(resolved);
  for (let depth = 0; depth < 6; depth++) {
    const metadata = await readFile(path.join(root, 'package.json'), 'utf8').then(JSON.parse).catch(() => null);
    if (metadata?.name === 'superun-ai-cli') {
      if (metadata.private === true) return root;
      const installation = path.join(root, 'dist/update/installation.js');
      // 与CLI发行入口使用同一个活动版本，不能误读全局启动器的旧实现。
      try { await access(installation, constants.R_OK); }
      catch (error) { if (error.code === 'ENOENT') return root; throw error; }
      const { installationRoot, activeEntry } = await import(pathToFileURL(installation).href);
      const active = await activeEntry((await installationRoot()).root);
      return active ? path.dirname(path.dirname(await realpath(active))) : root;
    }
    const parent = path.dirname(root);
    if (parent === root) break;
    root = parent;
  }
  throw fail('CLI_UNSUPPORTED', '当前CLI安装结构不支持读取预览，请保留原任务。');
}

export async function readPreview(values) {
  const sessionId = values.session;
  if (!/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,57}[a-zA-Z0-9])?$/.test(sessionId ?? ''))
    throw fail('INVALID_ARGUMENT', '请明确本次单个主项目ID。');
  const root = await cliRoot(values.cli);
  const load = name => import(pathToFileURL(path.join(root, 'dist', name)).href);
  const [config, auth, transport, conversation, queries, routing] = await Promise.all([
    load('config/runtime-config.js'), load('auth/pat-store.js'), load('transport/api-client.js'),
    load('api/conversation-api.js'), load('api/agent-query-api.js'), load('conversation/project-routing.js'),
  ]);
  const credential = (await new auth.PatStore().read()).pat;
  const client = new transport.ApiClient(config.runtimeConfig({ endpoint: values.endpoint, locale: values.locale }), credential);
  const query = new queries.AgentQueryApi(client);
  const [view, extra] = await Promise.all([
    new conversation.ConversationApi(client).recently(sessionId), query.extra(sessionId),
  ]);
  if (view.session.sessionId !== sessionId) throw fail('SOURCE_MISMATCH', '返回的项目与本次目标不一致。');
  if ((String(extra.hasSlidesIntent) === '1') !== expectsSlides)
    throw fail('PROJECT_TYPE_MISMATCH', '项目类型与本专家不一致，未交付链接。');
  // 与原专家团CLI的实时预览协议一致；不读取sessionKey，不采用发布域名或快照地址。
  const previewUrl = `https://id--${sessionId}.${config.getSuperunHostingDomain(client.config.endpoint)}`;
  const response = await fetch(previewUrl, { redirect: 'error', signal: AbortSignal.timeout(15_000) });
  await response.body?.cancel();
  if (!response.ok) return { state: 'PREVIEW_UNAVAILABLE', sessionId, environment: 'preview', httpStatus: response.status };
  return {
    state: 'PREVIEW_LINK', sessionId, environment: 'preview', previewUrl,
    routing: await routing.readProjectRouting(query, previewUrl, { sessionId }),
    httpStatus: response.status,
    // 此字段只解释现有站点公开状态，不证明本轮已发布，也不输出正式地址。
    publicStatus: view.session.publicStatus ?? null,
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const { values } = parseArgs({ options: {
      cli: { type: 'string' }, session: { type: 'string' }, endpoint: { type: 'string' }, locale: { type: 'string' },
    } });
    process.stdout.write(JSON.stringify({ ok: true, data: await readPreview(values) }) + '\n');
  } catch (error) {
    const known = ['INVALID_ARGUMENT', 'CLI_UNSUPPORTED', 'SOURCE_MISMATCH', 'PROJECT_TYPE_MISMATCH', 'AUTH_REQUIRED'].includes(error.code);
    process.stdout.write(JSON.stringify({ ok: false, error: {
      code: known ? error.code : 'PREVIEW_QUERY_FAILED',
      message: known ? error.message : '实时预览读取失败，请保留原项目，不改用正式地址或快照兜底。',
    } }) + '\n');
    process.exitCode = 1;
  }
}
