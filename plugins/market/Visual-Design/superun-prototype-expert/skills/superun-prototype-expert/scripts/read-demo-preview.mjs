/** 只读查询演示完成轮的真实快照，不改变 CLI 或项目阶段。@author xiuyu.yi */
import { access, readFile, realpath } from 'node:fs/promises';
import { constants } from 'node:fs';
import { delimiter, dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

function failure(code, message) {
  return Object.assign(new Error(message), { code });
}

async function activeCliRoot(root, metadata) {
  // 私有开发包不切换缓存版本，与 CLI 发行入口保持一致。
  if (metadata.private === true) return root;
  const installation = join(root, 'dist/update/installation.js');
  try {
    await access(installation, constants.R_OK);
  } catch (error) {
    if (error.code === 'ENOENT') return root;
    throw failure('CLI_UNSUPPORTED', '无法读取当前 CLI 的安装目录解析模块，请保留原回执。');
  }
  try {
    const { installationRoot, activeEntry } = await import(pathToFileURL(installation).href);
    const active = await activeEntry((await installationRoot()).root);
    return active ? dirname(dirname(await realpath(active))) : root;
  } catch {
    throw failure('CLI_UNSUPPORTED', '无法确认 CLI 实际使用的版本，请保留原回执，不升级或改写 CLI。');
  }
}

async function installedCli(explicit) {
  const searchPath = process.env.PATH ?? Object.entries(process.env).find(([key]) => key.toUpperCase() === 'PATH')?.[1] ?? '';
  const candidates = explicit ? [explicit] : searchPath.split(delimiter).filter(Boolean).map(directory => join(directory, process.platform === 'win32' ? 'superun-ai.cmd' : 'superun-ai'));
  for (const executable of candidates) {
    try {
      await access(executable, constants.X_OK);
    } catch {
      continue;
    }
    const resolved = await realpath(executable);
    let root = /\.cmd$/i.test(resolved) ? join(dirname(resolved), 'node_modules', 'superun-ai-cli') : dirname(resolved);
    for (let depth = 0; depth < 6; depth++) {
      let metadata;
      try {
        metadata = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
      } catch {
        // 沿真实可执行文件向上定位包，不搜索其他项目或凭据目录。
      }
      if (metadata?.name === 'superun-ai-cli') return activeCliRoot(root, metadata);
      const parent = dirname(root);
      if (parent === root) break;
      root = parent;
    }
    throw failure('CLI_UNSUPPORTED', '当前 CLI 安装结构不支持只读预览查询；请保留原回执，不升级或改写 CLI。');
  }
  throw failure('CLI_UNAVAILABLE', '未找到当前宿主已安装的 superun-ai。');
}

async function readPreview() {
  const { values } = parseArgs({
    options: { cli: { type: 'string' }, session: { type: 'string' }, 'message-id': { type: 'string' }, 'list-completed': { type: 'boolean' } },
  });
  const sessionId = values.session;
  const sourceMessageId = values['message-id'];
  if (!sessionId?.trim() || (!sourceMessageId?.trim() && !values['list-completed'])
    || (sourceMessageId && values['list-completed'])) {
    throw failure('INVALID_ARGUMENT', '必须提供 session，并选择 message-id 或 list-completed 其中一种查询。');
  }
  const root = await installedCli(values.cli);
  const load = (name) => import(pathToFileURL(join(root, 'dist', name)).href);
  let modules;
  try {
    modules = await Promise.all([
      load('config/runtime-config.js'), load('auth/pat-store.js'),
      load('transport/api-client.js'), load('api/agent-query-api.js'),
      load('api/conversation-api.js'), load('conversation/round-selector.js'),
      load('conversation/development-snapshot.js'), load('conversation/task-progress-reader.js'),
      load('conversation/state-resolver.js'), load('contracts/value.js'),
      load('conversation/text-projector.js'),
    ]);
  } catch {
    throw failure('CLI_UNSUPPORTED', '当前 CLI 查询模块不兼容；请保留原回执，不升级或改写 CLI。');
  }
  const [configModule, auth, transport, queryModule, conversationModule, rounds, snapshots,
    progressModule, states, valuesModule, textModule] = modules;
  const credential = await new auth.PatStore().read();
  const client = new transport.ApiClient(configModule.runtimeConfig({}), credential.pat);
  const query = new queryModule.AgentQueryApi(client);
  const conversation = new conversationModule.ConversationApi(client);
  const progress = new progressModule.TaskProgressReader(client);
  const [recently, extra, activeSubagentWork] = await Promise.all([
    conversation.recently(sessionId), query.extra(sessionId), progress.hasPendingSubagentWork(sessionId),
  ]);
  if (recently.session.sessionId !== sessionId) throw failure('SOURCE_MISMATCH', '项目来源不一致。');
  const view = { ...recently, extra, activeSubagentWork };
  const current = rounds.roundMessage(view, rounds.currentRound(view));
  if (valuesModule.enabled(extra.startDevelopment) || valuesModule.enabled(current?.roundExtra?.startDevelopment)) {
    throw failure('STAGE_MISMATCH', '当前项目已进入研发，不属于本专家演示范围。');
  }
  if (values['list-completed']) {
    if (!valuesModule.enabled(extra.hasViewedDemo)) {
      throw failure('STAGE_MISMATCH', '当前项目尚未确认查看演示，不能恢复既有演示成果。');
    }
    const candidates = (view.pipeline.render?.rounds ?? []).filter((item) => {
      const source = rounds.roundMessage(view, item);
      return item.sessionId === sessionId && item.status === 'completed'
        && !item.meta?.consult && !item.meta?.passive
        && valuesModule.enabled(source?.roundExtra?.hasSelectedStyle)
        && !valuesModule.enabled(source?.roundExtra?.startDevelopment);
    }).slice(-10).reverse().map((item) => ({
      messageId: rounds.roundMessage(view, item).messageId,
      roundId: item.roundId,
      timestamp: item.time.timestamp,
      messages: textModule.projectText([item]).messages,
    }));
    return { state: 'COMPLETED', sessionId, completedRounds: candidates };
  }
  let round = rounds.roundContainingMessage(view, sourceMessageId);
  if (!round) {
    const snapshot = await conversation.snapshot(sessionId, sourceMessageId);
    if (snapshot.pipeline) view.pipeline = snapshot.pipeline;
    round = rounds.roundContainingMessage(view, sourceMessageId);
  }
  const message = rounds.roundMessage(view, round);
  if (!round || round.sessionId !== sessionId || !message) {
    throw failure('SOURCE_MISMATCH', '未找到本次功能完成轮，不能用历史快照替代。');
  }
  if (!valuesModule.enabled(extra.hasViewedDemo) || !valuesModule.enabled(message.roundExtra?.hasSelectedStyle)
    || valuesModule.enabled(message.roundExtra?.startDevelopment)) {
    throw failure('STAGE_MISMATCH', '无法确认本轮属于已查看的演示阶段。');
  }
  // 未选候选不是运行任务；仍按真实消息、工具和后台任务门控完成。
  const target = { ...view, pipeline: { ...view.pipeline, render: { ...view.pipeline.render, rounds: [round] } } };
  if (view.session.status !== 3 || view.session.errorType || round.status !== 'completed'
    || states.hasPendingCreationWork(target)) {
    return { state: 'NOT_READY', sessionId, sourceMessageId };
  }
  const messageIds = [...new Set([
    round.anchorUserMessageId, message.messageId,
    ...(round.meta?.sourceMessageIds ?? []),
    ...round.agentItems.map((item) => item.source?.messageId),
  ].filter((id) => typeof id === 'string' && id))];
  // 复用 CLI 同一个演示更新快照查询，仅接受该轮所属消息返回的 visitUrl。
  const preview = await snapshots.findDevelopmentSnapshot(query, sessionId, messageIds);
  return preview
    ? { state: 'COMPLETED', sessionId, sourceMessageId, demo: { ...preview, viewed: true } }
    : { state: 'NOT_READY', sessionId, sourceMessageId };
}

try {
  process.stdout.write(`${JSON.stringify({ ok: true, data: await readPreview() })}\n`);
} catch (error) {
  const known = ['AUTH_REQUIRED', 'CLI_UNAVAILABLE', 'CLI_UNSUPPORTED', 'INVALID_ARGUMENT',
    'SOURCE_MISMATCH', 'STAGE_MISMATCH'].includes(error?.code);
  // 不输出凭据、请求头、响应正文、堆栈或第三方异常详情。
  process.stdout.write(`${JSON.stringify({ ok: false, error: {
    code: known ? error.code : 'PREVIEW_QUERY_FAILED',
    message: known ? error.message : '本轮预览查询失败，请保留原回执并核对原任务。',
  } })}\n`);
  process.exitCode = 1;
}
