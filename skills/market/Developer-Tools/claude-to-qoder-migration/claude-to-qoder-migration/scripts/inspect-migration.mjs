#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const MCP_FIELDS = new Set([
  'command',
  'args',
  'env',
  'cwd',
  'url',
  'headers',
  'tcp',
  'type',
  'timeout',
  'trust',
  'description',
  'includeTools',
  'excludeTools',
  'extension',
  'oauth',
  'disabled',
  'headersHelper',
  'alwaysAllow',
]);

const SETTINGS_HANDLED = new Set([
  '$schema',
  'mcpServers',
  'permissions',
  'hooks',
  'outputStyle',
  'enabledPlugins',
  'extraKnownMarketplaces',
  'env',
  'model',
  'fallbackModel',
]);

const IGNORED_DIR_ENTRIES = new Set(['.DS_Store']);

let STATE_CTX = {
  force: false,
  forceUser: false,
  userItems: new Set(),
  projectItems: new Set(),
};

function parseArgs(argv) {
  const opts = {
    project: process.cwd(),
    home: os.homedir(),
    format: 'markdown',
    state: null,
    force: false,
    forceUser: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--project') opts.project = argv[++i];
    else if (arg === '--home') opts.home = argv[++i];
    else if (arg === '--format') opts.format = argv[++i];
    else if (arg === '--state') opts.state = argv[++i];
    else if (arg === '--force') opts.force = true;
    else if (arg === '--force-user') opts.forceUser = true;
    else if (arg === '--help' || arg === '-h') {
      console.log('用法: inspect-migration.mjs [--project PATH] [--home PATH] [--state PATH] [--force] [--force-user] [--format markdown|json]');
      process.exit(0);
    } else {
      throw new Error(`未知参数: ${arg}`);
    }
  }
  opts.project = path.resolve(opts.project);
  opts.home = path.resolve(opts.home);
  if (opts.state) opts.state = path.resolve(opts.state);
  if (!['markdown', 'json'].includes(opts.format)) {
    throw new Error('--format 必须是 markdown 或 json');
  }
  return opts;
}

function exists(p) {
  try {
    return fs.existsSync(p);
  } catch {
    return false;
  }
}

function isDir(p) {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

function stripJsonComments(input) {
  let out = '';
  let inString = false;
  let quote = '';
  let escaped = false;
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    const next = input[i + 1];
    if (inString) {
      out += ch;
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === quote) inString = false;
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      out += ch;
      continue;
    }
    if (ch === '/' && next === '/') {
      while (i < input.length && input[i] !== '\n') i++;
      out += '\n';
      continue;
    }
    if (ch === '/' && next === '*') {
      i += 2;
      while (i < input.length && !(input[i] === '*' && input[i + 1] === '/')) i++;
      i++;
      continue;
    }
    out += ch;
  }
  return out;
}

function readJson(pathname) {
  if (!exists(pathname)) return { exists: false };
  try {
    const raw = fs.readFileSync(pathname, 'utf8');
    const parsed = JSON.parse(stripJsonComments(raw));
    return { exists: true, parsed, raw };
  } catch (error) {
    return { exists: true, error: error.message };
  }
}

function readMcpServersFromJsonFile(pathname) {
  const result = readJson(pathname);
  if (!result.exists) return { exists: false, servers: {} };
  if (result.error) return { exists: true, servers: {}, error: result.error };
  const mcpServers = result.parsed?.mcpServers;
  if (!mcpServers || typeof mcpServers !== 'object' || Array.isArray(mcpServers)) {
    return { exists: true, servers: {} };
  }
  return { exists: true, servers: mcpServers };
}

function listFiles(dir) {
  if (!isDir(dir)) return [];
  const result = [];
  const walk = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const p = path.join(current, entry.name);
      if (entry.isDirectory()) walk(p);
      else if (entry.isFile()) result.push(p);
    }
  };
  walk(dir);
  return result.sort();
}

function listTopLevelItems(dir) {
  if (!isDir(dir)) return [];
  const items = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (IGNORED_DIR_ENTRIES.has(entry.name)) continue;
    const itemPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      items.push({
        name: entry.name,
        path: itemPath,
        files: listFiles(itemPath),
        kind: 'directory',
      });
    } else if (entry.isFile()) {
      items.push({
        name: entry.name,
        path: itemPath,
        files: [itemPath],
        kind: 'file',
      });
    }
  }
  return items.sort((a, b) => a.name.localeCompare(b.name));
}

function projectEntryCandidates(project) {
  const candidates = new Set([project]);
  try {
    candidates.add(fs.realpathSync(project));
  } catch {
    // ignore
  }
  let current = project;
  while (current && current !== path.dirname(current)) {
    if (exists(path.join(current, '.git'))) candidates.add(current);
    current = path.dirname(current);
  }
  return [...candidates];
}

function normalizeProjectKeyForMatch(value) {
  let normalized = String(value).replace(/\\/g, '/').replace(/\/+$/, '');
  if (process.platform === 'win32') normalized = normalized.toLowerCase();
  return normalized;
}

function projectKeyMatches(key, candidates) {
  const normalizedKey = normalizeProjectKeyForMatch(key);
  return candidates.some(
    (candidate) => normalizeProjectKeyForMatch(candidate) === normalizedKey,
  );
}

function qoderHome(home) {
  if (process.env.QODER_CONFIG_DIR) return path.resolve(process.env.QODER_CONFIG_DIR);
  const base = process.env.QODER_CLI_HOME ? path.resolve(process.env.QODER_CLI_HOME) : home;
  return path.join(base, '.qoder');
}

function claudeSettingsHome(home) {
  if (process.env.CLAUDE_CONFIG_DIR) return path.resolve(process.env.CLAUDE_CONFIG_DIR);
  return path.join(home, '.claude');
}

function claudeStatePath(home) {
  if (process.env.CLAUDE_CONFIG_DIR) return path.join(path.resolve(process.env.CLAUDE_CONFIG_DIR), '.claude.json');
  return path.join(home, '.claude.json');
}

const MAX_SANITIZED_LENGTH = 200;

function djb2Hash(input) {
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    hash = (hash * 33) ^ input.charCodeAt(i);
  }
  return hash;
}

function sanitizeProjectId(name) {
  const sanitized = name.replace(/[^a-zA-Z0-9]/g, '-');
  if (sanitized.length <= MAX_SANITIZED_LENGTH) return sanitized;
  const hash = Math.abs(djb2Hash(name)).toString(36);
  return `${sanitized.slice(0, MAX_SANITIZED_LENGTH)}-${hash}`;
}

function add(plan, section, item) {
  plan[section].push(item);
}

function scopeLabel(scope) {
  return {
    user: '用户级',
    project: '项目级',
    local: '项目本地',
  }[scope] || scope;
}

function addTargetMcpFile(plan, index, label, pathname) {
  const result = readMcpServersFromJsonFile(pathname);
  if (!result.exists) return;
  if (result.error) {
    add(plan, 'unsupported', {
      source: pathname,
      path: 'mcpServers',
      reason: `目标 MCP 冲突检查已跳过: ${result.error}`,
    });
    return;
  }
  if (!index[label]) index[label] = {};
  for (const name of Object.keys(result.servers)) {
    if (!index[label][name]) index[label][name] = [];
    index[label][name].push(pathname);
  }
}

function buildTargetMcpIndex(plan, qHome, qProject, project) {
  const index = {};
  addTargetMcpFile(plan, index, '~/.qoder/settings.json', path.join(qHome, 'settings.json'));
  addTargetMcpFile(
    plan,
    index,
    '<project>/.qoder/settings.local.json',
    path.join(qProject, 'settings.local.json'),
  );
  addTargetMcpFile(
    plan,
    index,
    '<project>/.mcp.json',
    path.join(project, '.mcp.json'),
  );
  addTargetMcpFile(
    plan,
    index,
    '<project>/.mcp.json',
    path.join(qProject, 'settings.json'),
  );
  return index;
}

function existingMcpTargets(targetMcpIndex, target, serverName) {
  return targetMcpIndex?.[target]?.[serverName] ?? [];
}

function buildTargetSettingsIndex(qHome, qProject) {
  const index = {};
  const record = (label, file) => {
    const result = readJson(file);
    const parsed = result.exists && !result.error ? result.parsed : null;
    index[label] = new Set(
      parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? Object.keys(parsed) : [],
    );
  };
  record('~/.qoder/settings.json', path.join(qHome, 'settings.json'));
  record('<project>/.qoder/settings.json', path.join(qProject, 'settings.json'));
  record('<project>/.qoder/settings.local.json', path.join(qProject, 'settings.local.json'));
  return index;
}

function targetSettingsFieldExists(index, target, field) {
  return index?.[target]?.has(field) ?? false;
}

function stringSet(items) {
  return new Set(Array.isArray(items) ? items.filter((x) => typeof x === 'string') : []);
}

function readMigrationState(statePath) {
  const result = readJson(statePath);
  if (!result.exists) return { exists: false, data: null };
  if (result.error) return { exists: true, error: result.error, data: null };
  const data = result.parsed;
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return { exists: true, error: '状态文件不是 JSON 对象', data: null };
  }
  if (data.version !== 1 || data.tool !== 'claude-to-qoder-migration') {
    return { exists: true, error: 'version 或 tool 字段不匹配，非本 skill 的迁移状态文件', data: null };
  }
  return { exists: true, data };
}

function collectUserStateItems(data) {
  return stringSet(data?.userScope?.items);
}

function collectProjectStateItems(data, candidates) {
  const set = new Set();
  const projects = data?.projects;
  if (!projects || typeof projects !== 'object' || Array.isArray(projects)) return set;
  for (const [key, entry] of Object.entries(projects)) {
    if (!projectKeyMatches(key, candidates)) continue;
    for (const item of stringSet(entry?.items)) set.add(item);
  }
  return set;
}

function isAlreadyMigrated(scope, identity) {
  if (!identity || STATE_CTX.force) return false;
  if (scope === 'user') {
    if (STATE_CTX.forceUser) return false;
    return STATE_CTX.userItems.has(identity);
  }
  return STATE_CTX.projectItems.has(identity);
}

function mcpIdentity(targetPath, serverName) {
  return `${targetPath}#mcpServers.${serverName}`;
}

function summarizeValue(value) {
  if (value === null) return 'null';
  if (Array.isArray(value)) return `数组(${value.length})`;
  if (typeof value === 'object') return `对象(${Object.keys(value).length})`;
  return {
    string: '字符串',
    number: '数字',
    boolean: '布尔值',
    bigint: 'bigint',
    undefined: 'undefined',
    symbol: 'symbol',
    function: 'function',
  }[typeof value] || typeof value;
}

function emptyValue(value) {
  if (value === null) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (value && typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

function pluginScope(targetScope) {
  return targetScope === 'project' ? 'project' : targetScope === 'local' ? 'local' : 'user';
}

function shellQuote(value) {
  if (/^[A-Za-z0-9_./:@-]+$/.test(value)) return value;
  return `'${value.replace(/'/g, "'\\''")}'`;
}

function marketplaceCommandSource(value) {
  const source = value?.source && typeof value.source === 'object' ? value.source : value;
  if (typeof source === 'string') return source;
  if (!source || typeof source !== 'object' || Array.isArray(source)) return null;
  if (source.source === 'github' && typeof source.repo === 'string') {
    return source.ref ? `${source.repo}@${source.ref}` : source.repo;
  }
  if (source.source === 'git' && typeof source.url === 'string') return source.url;
  if (source.source === 'url' && typeof source.url === 'string') return source.url;
  if (source.source === 'path' && typeof source.path === 'string') return source.path;
  if (typeof source.repo === 'string') return source.repo;
  if (typeof source.url === 'string') return source.url;
  if (typeof source.path === 'string') return source.path;
  return null;
}

function stringifyForSearch(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function includesOfficialClaudeMarketplace(value) {
  return stringifyForSearch(value).includes('anthropics/claude-plugins-official') ||
    stringifyForSearch(value).includes('claude-plugins-official');
}

function enabledPluginIds(value) {
  if (Array.isArray(value)) return value.filter((x) => typeof x === 'string');
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .filter(([, enabled]) => enabled !== false)
      .map(([pluginId]) => pluginId);
  }
  if (typeof value === 'string') return [value];
  return [];
}

function pluginPlanDetails(key, value, targetScope) {
  const scope = pluginScope(targetScope);
  const commands = [];
  const notes = [
    '不要复制 Claude 插件缓存、installed_plugins 或 marketplace state',
  ];
  if (includesOfficialClaudeMarketplace(value)) {
    commands.push(`qodercli plugins marketplace add anthropics/claude-plugins-official --scope ${scope}`);
    notes.push('检测到 Claude 官方插件市场引用；Qoder 可直接添加该 marketplace');
  }
  if (key === 'extraKnownMarketplaces' && value && typeof value === 'object' && !Array.isArray(value)) {
    for (const entry of Object.values(value)) {
      const source = marketplaceCommandSource(entry);
      if (source) {
        commands.push(`qodercli plugins marketplace add ${shellQuote(source)} --scope ${scope}`);
      }
    }
  }
  if (key === 'enabledPlugins') {
    for (const pluginId of enabledPluginIds(value)) {
      commands.push(`qodercli plugins install ${shellQuote(pluginId)} --scope ${scope}`);
      commands.push(`qodercli plugins enable ${shellQuote(pluginId)} --scope ${scope}`);
    }
    if (commands.length === 0) {
      notes.push('enabledPlugins 形态无法直接生成插件名；需要人工确认具体插件 ID');
    }
  }
  return {
    recommendation: '列出 Qoder 插件命令；默认不执行，不直接编辑插件状态文件',
    commands: [...new Set(commands)],
    notes: [...new Set(notes)],
  };
}

function analyzeMcpServers(plan, sourcePath, sourceScope, target, servers, options = {}) {
  if (!servers || typeof servers !== 'object' || Array.isArray(servers)) {
    add(plan, 'unsupported', {
      source: sourcePath,
      path: 'mcpServers',
      reason: 'mcpServers 不是对象',
    });
    return;
  }
  const names = Object.keys(servers);
  if (names.length === 0) {
    add(plan, 'emptySkipped', { source: sourcePath, path: 'mcpServers' });
    return;
  }

  for (const name of names) {
    const cfg = servers[name];
    if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) {
      add(plan, 'unsupported', {
        source: sourcePath,
        path: `mcpServers.${name}`,
        reason: 'server 配置不是对象',
      });
      continue;
    }
    const unsupported = Object.keys(cfg).filter((key) => !MCP_FIELDS.has(key));
    const sensitive = ['env', 'headers', 'headersHelper'].filter((key) => cfg[key] !== undefined);
    const identity = mcpIdentity(target, name);
    const item = {
      source: sourcePath,
      sourceScope,
      target,
      server: name,
      identity,
      sensitive,
      unsupportedFields: unsupported,
    };
    const existingTargets = existingMcpTargets(
      options.targetMcpIndex,
      target,
      name,
    );
    const migrated = !options.compatibleInPlace &&
      existingTargets.length &&
      isAlreadyMigrated(sourceScope, identity);
    if (options.compatibleInPlace) add(plan, 'compatibleInPlace', item);
    else if (migrated) {
      add(plan, 'alreadyMigrated', {
        source: sourcePath,
        sourceScope,
        target,
        identity,
        label: `MCP server ${name}`,
        existingTargets,
      });
    } else if (existingTargets.length) {
      const conflictItem = {
        ...item,
        existingTargets,
        reason: '目标中已存在同名 MCP server',
      };
      add(plan, 'needsDecision', conflictItem);
      add(plan, 'conflicts', {
        source: sourcePath,
        target,
        label: `MCP server ${name}`,
        server: name,
        existingTargets,
        choices: ['保留目标', '替换目标', '重命名源 server', '跳过'],
      });
    } else add(plan, sensitive.length ? 'needsDecision' : 'migratable', item);
    for (const field of unsupported) {
      add(plan, 'unsupported', {
        source: sourcePath,
        path: `mcpServers.${name}.${field}`,
        reason: '不支持的 MCP server 字段',
      });
    }
  }
}

function analyzeSettings(plan, sourcePath, sourceScope, targetScope, settings, targetMcpIndex, targetSettingsIndex) {
  if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
    add(plan, 'unsupported', {
      source: sourcePath,
      path: '',
      reason: 'settings 文件不是 JSON 对象',
    });
    return;
  }
  const addSettingsField = (field, target, extra) => {
    const identity = `${target}#${field}`;
    if (
      targetSettingsFieldExists(targetSettingsIndex, target, field) &&
      isAlreadyMigrated(sourceScope, identity)
    ) {
      add(plan, 'alreadyMigrated', {
        source: sourcePath,
        sourceScope,
        target,
        identity,
        label: field,
      });
      return;
    }
    add(plan, 'needsDecision', {
      source: sourcePath,
      sourceScope,
      target,
      identity,
      path: field,
      ...extra,
    });
  };
  for (const [key, value] of Object.entries(settings)) {
    if (emptyValue(value)) {
      add(plan, 'emptySkipped', { source: sourcePath, path: key });
      continue;
    }
    if (key === '$schema') continue;
    if (key === 'mcpServers') {
      const target =
        targetScope === 'project' ? '<project>/.mcp.json' :
        targetScope === 'local' ? '<project>/.qoder/settings.local.json' :
        '~/.qoder/settings.json';
      analyzeMcpServers(plan, sourcePath, sourceScope, target, value, {
        targetMcpIndex,
      });
      continue;
    }
    if (key === 'permissions') {
      addSettingsField(
        'permissions',
        targetScope === 'user' ? '~/.qoder/settings.json' : targetScope === 'local' ? '<project>/.qoder/settings.local.json' : '<project>/.qoder/settings.json',
        { reason: '会改变工具访问或信任边界' },
      );
      continue;
    }
    if (key === 'hooks') {
      addSettingsField(
        'hooks',
        targetScope === 'local' ? '<project>/.qoder/settings.local.json' : targetScope === 'project' ? '<project>/.qoder/settings.json' : '~/.qoder/settings.json',
        {
          reason: 'hooks 会执行命令或触发评估；需要用户确认执行风险',
          transform: '仅自动替换 $CLAUDE_PROJECT_DIR -> $QODER_PROJECT_DIR；其他字段、token、命令、matcher、timeout、type、事件名和顺序保持原样',
        },
      );
      continue;
    }
    if (key === 'outputStyle') {
      addSettingsField(
        'outputStyle',
        targetScope === 'project' ? '<project>/.qoder/settings.json' : '~/.qoder/settings.json',
        { reason: '仅在对应 style 文件存在后才设置 active style' },
      );
      continue;
    }
    if (key === 'enabledPlugins' || key === 'extraKnownMarketplaces') {
      const details = pluginPlanDetails(key, value, targetScope);
      add(plan, 'pluginPlan', {
        source: sourcePath,
        sourceScope,
        path: key,
        ...details,
      });
      continue;
    }
    if (key === 'env') {
      add(plan, 'reportOnly', {
        source: sourcePath,
        path: 'env',
        reason: 'Qoder settings 没有等价的顶层 env 注入字段',
      });
      continue;
    }
    if (key === 'model' || key === 'fallbackModel') {
      add(plan, 'reportOnly', {
        source: sourcePath,
        path: key,
        reason: '模型、provider 或 auth 语义不同',
      });
      continue;
    }
    if (!SETTINGS_HANDLED.has(key)) {
      add(plan, 'unknown', {
        source: sourcePath,
        path: key,
        summary: summarizeValue(value),
      });
    }
  }
}

function compareDir(plan, source, target, label, scope, options = {}) {
  const requiresDecision = !!options.requiresDecision;
  const items = options.items || listTopLevelItems(source);
  if (items.length === 0) return;
  for (const item of items) {
    const targetPath = path.join(target, item.name);
    const conflictedFiles = [];
    if (exists(targetPath)) {
      conflictedFiles.push(targetPath);
    } else {
      for (const file of item.files) {
        const rel = path.relative(source, file);
        const candidate = path.join(target, rel);
        if (exists(candidate)) conflictedFiles.push(candidate);
      }
    }
    const identity = targetPath;
    if (conflictedFiles.length && isAlreadyMigrated(scope, identity)) {
      add(plan, 'alreadyMigrated', {
        source: item.path,
        sourceScope: scope,
        target: targetPath,
        identity,
        label: `${label}: ${item.name}`,
      });
      continue;
    }
    const planItem = {
      source: item.path,
      sourceScope: scope,
      target: targetPath,
      identity,
      label: `${label}: ${item.name}`,
      item: item.name,
      itemKind: item.kind,
      files: item.files.length,
      conflicts: conflictedFiles.length,
      conflictedFiles,
      reason: conflictedFiles.length ? '目标已存在或存在同路径文件冲突' : undefined,
      rule: '只复制；保留相对路径；绝不覆盖',
    };
    if (requiresDecision) planItem.sensitive = true;
    const section = conflictedFiles.length || requiresDecision ? 'needsDecision' : 'migratable';
    add(plan, section, planItem);
    if (conflictedFiles.length) {
      add(plan, 'conflicts', {
        source: item.path,
        target: targetPath,
        label: `${label}: ${item.name}`,
        item: item.name,
        count: conflictedFiles.length,
        conflictedFiles,
        choices: ['跳过', '重命名源副本', '手动合并'],
      });
    }
  }
}

function compareFile(plan, source, target, label, options = {}) {
  if (!exists(source)) return;
  const scope = options.scope;
  const identity = target;
  if (exists(target)) {
    if (isAlreadyMigrated(scope, identity)) {
      add(plan, 'alreadyMigrated', {
        source,
        sourceScope: scope,
        target,
        identity,
        label,
      });
      return;
    }
    add(plan, 'needsDecision', {
      source,
      sourceScope: scope,
      target,
      identity,
      label,
      reason: options.reason || '目标已存在',
      choices: options.choices || ['跳过', '追加', '另存并列文件', '手动合并'],
    });
    add(plan, 'conflicts', { source, target, label, reason: '目标已存在' });
  } else {
    add(plan, 'migratable', {
      source,
      sourceScope: scope,
      target,
      identity,
      label,
      rule: '只复制',
    });
  }
}

function analyzeClaudeState(plan, statePath, project, candidates, targetMcpIndex) {
  const result = readJson(statePath);
  if (!result.exists) return;
  add(plan, 'sourcesFound', { path: statePath, kind: 'Claude 状态文件' });
  if (result.error) {
    add(plan, 'unsupported', { source: statePath, path: '', reason: result.error });
    return;
  }
  const state = result.parsed;
  if (state?.mcpServers) {
    analyzeMcpServers(plan, statePath, 'user', '~/.qoder/settings.json', state.mcpServers, {
      targetMcpIndex,
    });
  }
  const projects = state?.projects;
  if (projects && typeof projects === 'object' && !Array.isArray(projects)) {
    const matching = Object.keys(projects).filter((p) =>
      projectKeyMatches(p, candidates),
    );
    if (matching.length === 0) {
      const projectCount = Object.keys(projects).length;
      if (projectCount > 0) {
        add(plan, 'reportOnly', {
          source: statePath,
          path: 'projects',
          reason: `发现 ${projectCount} 个项目条目，但没有匹配当前项目`,
        });
      }
    } else if (matching.length > 1) {
      add(plan, 'needsDecision', {
        source: statePath,
        path: 'projects',
        reason: '多个项目条目匹配当前项目；需要用户选择一个',
        choices: matching,
      });
    }
    for (const key of matching) {
      const entry = projects[key];
      if (entry?.mcpServers) {
        analyzeMcpServers(
          plan,
          `${statePath}#projects[${key}]`,
          'local',
          '<project>/.qoder/settings.local.json',
          entry.mcpServers,
          { targetMcpIndex },
        );
      }
    }
  }
}

function inspect(opts) {
  const home = opts.home;
  const project = opts.project;
  const cHome = claudeSettingsHome(home);
  const qHome = qoderHome(home);
  const cProject = path.join(project, '.claude');
  const qProject = path.join(project, '.qoder');
  const plan = {
    project,
    home,
    qoderHome: qHome,
    generatedAt: new Date().toISOString(),
    sourcesFound: [],
    compatibleInPlace: [],
    migratable: [],
    needsDecision: [],
    conflicts: [],
    reportOnly: [],
    unsupported: [],
    unknown: [],
    emptySkipped: [],
    pluginPlan: [],
    alreadyMigrated: [],
    stateFile: null,
  };

  const candidates = projectEntryCandidates(project);

  const statePath = opts.state || path.join(qHome, 'migration-state.json');
  const stateResult = readMigrationState(statePath);
  STATE_CTX = {
    force: !!opts.force,
    forceUser: !!opts.forceUser,
    userItems: collectUserStateItems(stateResult.data),
    projectItems: collectProjectStateItems(stateResult.data, candidates),
  };
  plan.stateFile = {
    path: statePath,
    exists: stateResult.exists,
    error: stateResult.error || null,
    force: !!opts.force,
    forceUser: !!opts.forceUser,
    userItemCount: STATE_CTX.userItems.size,
    projectItemCount: STATE_CTX.projectItems.size,
  };
  if (stateResult.error) {
    add(plan, 'reportOnly', {
      source: statePath,
      path: '',
      reason: `迁移状态文件无法解析，已按无状态处理: ${stateResult.error}`,
    });
  }

  const targetMcpIndex = buildTargetMcpIndex(plan, qHome, qProject, project);
  const targetSettingsIndex = buildTargetSettingsIndex(qHome, qProject);

  const settingSources = [
    { path: path.join(cHome, 'settings.json'), sourceScope: 'user', targetScope: 'user' },
    { path: path.join(cProject, 'settings.json'), sourceScope: 'project', targetScope: 'project' },
    { path: path.join(cProject, 'settings.local.json'), sourceScope: 'local', targetScope: 'local' },
  ];
  for (const source of settingSources) {
    const result = readJson(source.path);
    if (!result.exists) continue;
    add(plan, 'sourcesFound', { path: source.path, kind: `${scopeLabel(source.sourceScope)} settings` });
    if (result.error) {
      add(plan, 'unsupported', { source: source.path, path: '', reason: result.error });
    } else {
      analyzeSettings(
        plan,
        source.path,
        source.sourceScope,
        source.targetScope,
        result.parsed,
        targetMcpIndex,
        targetSettingsIndex,
      );
    }
  }

  analyzeClaudeState(plan, claudeStatePath(home), project, candidates, targetMcpIndex);

  const legacyQoderJson = path.join(home, '.qoder.json');
  if (exists(legacyQoderJson)) {
    add(plan, 'reportOnly', {
      source: legacyQoderJson,
      path: '',
      reason: '当前 Claude Code -> Qoder CLI 迁移目标不包含该文件；不会读取或写入',
    });
  }

  const rootMcp = path.join(project, '.mcp.json');
  const rootMcpResult = readJson(rootMcp);
  if (rootMcpResult.exists) {
    add(plan, 'sourcesFound', { path: rootMcp, kind: '项目 MCP' });
    if (rootMcpResult.error) {
      add(plan, 'unsupported', { source: rootMcp, path: '', reason: rootMcpResult.error });
    } else if (rootMcpResult.parsed?.mcpServers) {
      analyzeMcpServers(plan, rootMcp, 'project', rootMcp, rootMcpResult.parsed.mcpServers, {
        compatibleInPlace: true,
      });
    } else {
      add(plan, 'unsupported', {
        source: rootMcp,
        path: 'mcpServers',
        reason: '缺少顶层 mcpServers 对象',
      });
    }
  }

  compareFile(plan, path.join(cHome, 'CLAUDE.md'), path.join(qHome, 'AGENTS.md'), '用户级记忆文件', { scope: 'user' });
  compareFile(plan, path.join(project, 'CLAUDE.md'), path.join(project, 'AGENTS.md'), '项目级记忆文件', { scope: 'project' });
  compareFile(plan, path.join(project, 'CLAUDE.local.md'), path.join(project, 'AGENTS.local.md'), '项目本地记忆文件', { scope: 'local' });

  for (const name of ['commands', 'skills', 'agents', 'output-styles', 'rules']) {
    compareDir(plan, path.join(cHome, name), path.join(qHome, name), `用户级 ${name}`, 'user');
    compareDir(plan, path.join(cProject, name), path.join(qProject, name), `项目级 ${name}`, 'project');
  }

  const projectId = sanitizeProjectId(project);
  const claudeMemDir = path.join(cHome, 'projects', projectId, 'memory');
  const qoderMemDir = path.join(qHome, 'projects', projectId, 'memory');
  const memItems = listTopLevelItems(claudeMemDir);
  if (memItems.length > 0) {
    add(plan, 'sourcesFound', { path: claudeMemDir, kind: '项目 memory' });
    compareDir(plan, claudeMemDir, qoderMemDir, '项目 memory', 'local', { requiresDecision: true, items: memItems });
  } else {
    add(plan, 'reportOnly', {
      source: claudeMemDir,
      path: '',
      reason: '未发现当前项目的 Claude memory（该路径不存在或为空）；如果预期存在，请确认项目目录名是否匹配',
    });
  }

  const keybindings = path.join(cHome, 'keybindings.json');
  if (exists(keybindings)) {
    add(plan, 'reportOnly', {
      source: keybindings,
      path: '',
      reason: 'keybindings schema 不兼容，需要手动重映射',
    });
  }

  return plan;
}

function renderList(items, renderItem) {
  if (!items.length) return '- 无\n';
  return items.map((item) => `- ${renderItem(item)}`).join('\n') + '\n';
}

function renderMarkdown(plan) {
  const lines = [];
  lines.push('# Claude Code 到 Qoder CLI 迁移检查');
  lines.push('');
  lines.push(`项目: \`${plan.project}\``);
  lines.push(`Qoder 配置目录: \`${plan.qoderHome}\``);
  lines.push(`生成时间: \`${plan.generatedAt}\``);
  if (plan.stateFile) {
    const sf = plan.stateFile;
    const flags = sf.force ? '（--force：忽略全部状态）' : sf.forceUser ? '（--force-user：忽略用户级状态）' : '';
    const status = sf.error ? `解析失败，已按无状态处理` : sf.exists ? `已存在` : `尚未创建`;
    lines.push(`迁移状态文件: \`${sf.path}\` (${status}；用户级已记录 ${sf.userItemCount} 项，项目级 ${sf.projectItemCount} 项)${flags}`);
  }
  lines.push('');
  lines.push('## 发现的源文件');
  lines.push(renderList(plan.sourcesFound, (x) => `\`${x.path}\` (${x.kind})`));
  lines.push('## 已在兼容位置');
  lines.push(renderList(plan.compatibleInPlace, (x) => x.server ? `MCP server \`${x.server}\` 已位于 Qoder 可读取的项目 MCP 位置: \`${x.source}\`` : JSON.stringify(x)));
  lines.push('## 可迁移');
  lines.push(renderList(plan.migratable, (x) => x.server ? `MCP server \`${x.server}\`: \`${x.source}\` -> \`${x.target}\`` : `${x.label || x.path || '条目'}: \`${x.source}\` -> \`${x.target}\`${x.files ? ` (${x.files} 个文件)` : ''}`));
  lines.push('## 需要确认');
  lines.push(renderList(plan.needsDecision, (x) => `${x.sensitive ? '【敏感·需显式确认】' : ''}${x.label || x.path || x.server || '条目'} 来自 \`${x.source}\`${x.target ? ` -> \`${x.target}\`` : ''}${x.reason ? ` (${x.reason})` : ''}${x.existingTargets ? `；已存在: ${x.existingTargets.map((p) => `\`${p}\``).join(', ')}` : ''}`));
  lines.push('## 冲突');
  lines.push(renderList(plan.conflicts, (x) => `${x.label || '条目'}: \`${x.source}\` -> \`${x.target}\`${x.count ? ` (${x.count} 个冲突)` : ''}${x.existingTargets ? `；已存在: ${x.existingTargets.map((p) => `\`${p}\``).join(', ')}` : ''}`));
  lines.push('## 已迁移（本次跳过）');
  lines.push(renderList(plan.alreadyMigrated, (x) => `[${scopeLabel(x.sourceScope)}] ${x.label || '条目'}: \`${x.source}\` -> \`${x.target}\``));
  if (plan.alreadyMigrated.length) {
    lines.push('> 以上项已在迁移状态文件中记录且目标仍存在，本次自动跳过。如需重新迁移，用 `--force-user`（仅用户级）或 `--force`（全部）。');
    lines.push('');
  }
  lines.push('## 插件计划');
  lines.push(renderList(plan.pluginPlan, (x) => {
    let text = `\`${x.path}\` 位于 \`${x.source}\`: ${x.recommendation}`;
    if (x.commands?.length) {
      text += `\n  建议命令:\n${x.commands.map((cmd) => `  - \`${cmd}\``).join('\n')}`;
    }
    if (x.notes?.length) {
      text += `\n  说明:\n${x.notes.map((note) => `  - ${note}`).join('\n')}`;
    }
    return text;
  }));
  lines.push('## 只报告');
  lines.push(renderList(plan.reportOnly, (x) => `\`${x.source}\`${x.path ? ` ${x.path}` : ''}: ${x.reason}`));
  lines.push('## 不支持');
  lines.push(renderList(plan.unsupported, (x) => `\`${x.source}\`${x.path ? ` ${x.path}` : ''}: ${x.reason}`));
  lines.push('## 未知');
  lines.push(renderList(plan.unknown, (x) => `\`${x.source}\` ${x.path}: ${x.summary}`));
  lines.push('## 空值已跳过');
  lines.push(renderList(plan.emptySkipped, (x) => `\`${x.source}\` ${x.path}`));
  lines.push('## 确认要求');
  lines.push('- 按用户级、项目共享级、项目本地级分别列出要迁移和不迁移的内容，并让用户确认对应源路径、目标路径和资源类型。');
  lines.push('- permissions、hooks、MCP secrets/env/headers、插件 marketplace/install 命令以及所有冲突必须单独确认。');
  lines.push('');
  lines.push('## 模型配置提醒');
  lines.push('- 如果 skills、agents、hooks、commands、plugins 或 output styles 中有 Claude 模型名、provider、auth 或模型相关环境变量，需要转换成 Qoder 支持的模型配置，不能假定两边相同。');
  lines.push('');
  lines.push('## 下一步');
  lines.push('把这个计划展示给用户。用户确认相关资源组之前，不要写文件或运行插件命令。');
  lines.push('');
  return lines.join('\n');
}

try {
  const opts = parseArgs(process.argv.slice(2));
  const plan = inspect(opts);
  if (opts.format === 'json') console.log(JSON.stringify(plan, null, 2));
  else process.stdout.write(renderMarkdown(plan));
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
