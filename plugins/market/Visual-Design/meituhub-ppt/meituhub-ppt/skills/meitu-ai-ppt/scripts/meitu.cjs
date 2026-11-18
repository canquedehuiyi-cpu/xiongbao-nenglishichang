'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const profile = JSON.parse(fs.readFileSync(path.join(__dirname, 'profile.json'), 'utf8'));
const pluginVersion = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../.qoder-plugin/plugin.json'), 'utf8')).version;
const channel = 'qoder';
const registry = 'https://registry.npmjs.org/';
const runtime = path.join(os.homedir(), '.meituhub-qoder', 'runtime');
const channelRoot = path.join(runtime, 'channels', channel);
const statePath = path.join(channelRoot, 'state.json');
const lockPath = path.join(channelRoot, 'update.lock');
const args = process.argv.slice(2);
const env = { ...process.env };
if (Number(process.versions.node.split('.')[0]) < 20) { console.error('Node.js 20+ required'); process.exit(2); }
// Private npm and its lifecycle scripts use this runner's Node executable.
const pathKey = Object.keys(env).find(key => key.toLowerCase() === 'path') || 'PATH';
const nodePath = path.dirname(process.execPath) + path.delimiter + (env[pathKey] || '');
if (!['cn', 'intl'].includes(profile.partition)) throw new Error('Invalid partition');
for (const key of ['MEITU_IAM_BASE_URL','MEITU_IAM_CLIENT_TYPE','MEITU_IAM_OVERSEAS',
  'MEITU_OPENAPI_BASE_URL','MEITU_OPENAPI_IMAGE_BASE_URL','MEITU_OPENAPI_STRATEGY_BASE_URL',
  'MEITU_OPENAPI_ORG_BASE_URL','MEITU_OPENAPI_ACCOUNT_BASE_URL','MEITU_OPENAPI_RECHARGE_BASE_URL',
  'MEITU_SKILLS_REGISTRY_URL','MEITU_WORKFLOW_REGISTRY_URL','MEITU_SKILLS_PACKAGE_REGISTRY_URL',
  'MEITU_ACCOUNT_COMMAND_REGISTRY_URL']) delete env[key];
Object.assign(env,{MEITU_IAM_CLIENT_ID:String(profile.clientId || ''), MEITU_OPENAPI_AUTH_MODE:'iam',
  MEITU_CLI_PARTITION:profile.partition,MEITU_CLI_OUTPUT_FORMAT:'full'});
const validVersion = v => typeof v === 'string' && /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(v);
function readState() { try { return JSON.parse(fs.readFileSync(statePath, 'utf8')); } catch { return {}; } }
function installed(version) {
  if (!validVersion(version)) return null;
  const prefix = path.join(runtime, 'versions', version);
  return inspect(prefix, version) || inspect(path.join(runtime, version), version);
}
function inspect(prefix, version) {
  try {
    const root = process.platform === 'win32' ? path.join(prefix,'node_modules','meitu-cli') : path.join(prefix,'lib','node_modules','meitu-cli');
    const pkg = JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));
    const rel = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin?.meitu;
    if (pkg.name !== 'meitu-cli' || pkg.version !== version || !rel) return null;
    const bin = path.resolve(root, rel);
    if (!bin.startsWith(root + path.sep) || !fs.existsSync(bin)) return null;
    return {version, prefix, bin};
  } catch { return null; }
}
function local(state) { return installed(state.version) || installed('2.1.30'); }
let privateNpm;
function npm(argv, timeout) {
  const options = {env, encoding:'utf8', timeout, maxBuffer:8*1024*1024, windowsHide:true};
  // Windows .cmd wrappers require a shell. Use private npm through Node instead,
  // so paths with spaces/metacharacters remain ordinary argv on every platform.
  if (!privateNpm && process.platform !== 'win32') {
    const result = spawnSync('npm', argv, options);
    if (result.error?.code !== 'ENOENT') return result;
  }
  if (!privateNpm) {
    const [major, minor] = process.versions.node.split('.').map(Number);
    if (major === 20 && minor < 5) throw new Error('Automatic npm preparation requires Node.js 20.5+; current Node is ' + process.versions.node);
    const bootstrap = spawnSync(process.execPath, [path.join(__dirname, 'bootstrap-npm.cjs'), runtime],
      {...options, timeout:90000});
    if (bootstrap.status !== 0) throw new Error(bootstrap.stderr?.trim() || `Automatic npm preparation failed: ${bootstrap.error?.code || 'unknown error'}`);
    privateNpm = bootstrap.stdout.trim();
    if (bootstrap.stderr) console.error(bootstrap.stderr.trim());
  }
  return spawnSync(process.execPath, [privateNpm, ...argv], {...options, env:{...env, [pathKey]:nodePath}});
}
function writeState(state) {
  const temp = statePath + '.' + process.pid + '.tmp';
  fs.writeFileSync(temp, JSON.stringify(state,null,2)+'\n');
  fs.renameSync(temp, statePath);
}
function ensure(force) {
  let state = readState();
  let current = local(state);
  const interval = state.lastError ? 3600000 : 86400000;
  if (!force && current && Date.now() - (state.checkedAt || 0) < interval) return current;
  fs.mkdirSync(channelRoot,{recursive:true});
  try { fs.mkdirSync(lockPath); }
  catch (e) {
    if (e.code !== 'EEXIST') throw e;
    // Never remove a lock held by a live process, including during npm bootstrap.
    let owner;
    try { owner=JSON.parse(fs.readFileSync(path.join(lockPath,'owner.json'),'utf8')); } catch {}
    let alive = true;
    if (owner?.pid) { try { process.kill(owner.pid,0); } catch (err) { if(err.code==='ESRCH') alive=false; } }
    if ((!owner && Date.now()-fs.statSync(lockPath).mtimeMs>300000) || (owner && !alive)) {
      fs.rmSync(lockPath,{recursive:true,force:true});
      return ensure(force);
    }
    if (current) { console.error('CLI update already in progress; using installed version.'); return current; }
    throw new Error('CLI setup in progress; retry after it finishes.');
  }
  fs.writeFileSync(path.join(lockPath,'owner.json'),JSON.stringify({pid:process.pid}));
  let staging;
  try {
    state=readState(); current=local(state);
    const result = npm(['view',`meitu-cli@${channel}`,'version','--json','--registry',registry,'--fetch-retries=0','--fetch-timeout=10000'],15000);
    if(result.error) throw new Error(`Cannot run npm: ${result.error.code || result.error.message}`);
    if(result.status!==0) throw new Error('Cannot resolve public meitu-cli@qoder (registry unavailable or missing tag).');
    let target;
    try { target=JSON.parse(result.stdout); } catch { throw new Error('Invalid npm version response.'); }
    if(!validVersion(target)) throw new Error('Invalid qoder channel version.');
    let selected=installed(target);
    if(!selected) {
      staging=fs.mkdtempSync(path.join(channelRoot,'install-'));
      const install=npm(['install','--global','--prefix',staging,'--registry',registry,`meitu-cli@${target}`,'--no-audit','--no-fund','--fetch-retries=0','--fetch-timeout=30000'],180000);
      if(install.status!==0) throw new Error('CLI install failed; keeping previous runtime.');
      selected=inspect(staging,target);
      if(!selected) throw new Error('Installed CLI metadata/bin validation failed.');
      const probe=spawnSync(process.execPath,[selected.bin,'--version'],{env,encoding:'utf8',timeout:10000});
      if(probe.status!==0 || probe.stdout.trim()!==target) throw new Error('Installed CLI version check failed.');
      const destination=path.join(runtime,'versions',target);
      fs.mkdirSync(path.dirname(destination),{recursive:true});
      if(fs.existsSync(destination)) throw new Error('Invalid existing version directory; previous runtime preserved.');
      fs.renameSync(staging,destination); staging=null;
      selected=installed(target);
    }
    writeState({channel,version:target,checkedAt:Date.now()});
    if(current?.version!==target) console.error(`CLI ${channel} channel selected ${target}.`);
    return selected;
  } catch(error) {
    writeState({channel,version:current?.version || null,checkedAt:Date.now(),lastError:error.message});
    if(!current) throw error;
    console.error(`${error.message} Using installed CLI ${current.version}.`);
    return current;
  } finally {
    if(staging) fs.rmSync(staging,{recursive:true,force:true});
    fs.rmSync(lockPath,{recursive:true,force:true});
  }
}
if(args[0]==='info') {
  const state=readState(), current=local(state);
  console.log(JSON.stringify({pluginVersion,cliChannel:channel,cliVersion:current?.version || null,registry,
    partition:profile.partition,clientId:profile.clientId,clientMode:profile.clientMode,
    configured:Number.isSafeInteger(profile.clientId)&&profile.clientId>0,
    runtimeReady:Boolean(current),nodeVersion:process.versions.node,
    npmPreparation:'automatic',
    installPrefix:current?.prefix || null,
    checkedAt:state.checkedAt || null,lastUpdateError:state.lastError || null},null,2)); process.exit(0);
}
if(!Number.isSafeInteger(profile.clientId)||profile.clientId<=0) {console.error('Missing regional IAM client ID');process.exit(2);}
let selected;
try { selected=ensure(args[0]==='setup'); } catch(e) {console.error(e.message);process.exit(2);}
// Account entries are owned by CLI >= 2.1.39; never synthesize a URL here.
const accountEntry = args[0]==='account' && args[1]==='entry';
function supportsAccountEntry(version) {
  if(!/^\d+\.\d+\.\d+$/.test(version)) return false;
  const [major,minor,patch]=version.split('.').map(Number);
  return major>2 || (major===2 && (minor>1 || (minor===1 && patch>=39)));
}
if(accountEntry && !supportsAccountEntry(selected.version)) {
  selected=ensure(true);
  if(!supportsAccountEntry(selected.version)) {
    console.log(JSON.stringify({ok:false,code:'CLI_UPDATE_REQUIRED',minimumCliVersion:'2.1.39',
      message:'Account entry requires an updated qoder CLI. No entry is available from this version.'}));
    process.exit(3);
  }
}
if(args[0]==='setup') {console.log(JSON.stringify({channel,version:selected.version,updateError:readState().lastError || null}));process.exit(0);}
// Catalog discovery is authenticated in the public CLI. Its bootstrap otherwise
// hides missing IAM sessions behind a generic registry/cache error.
const staticRoots = new Set(['auth','config','org','account','api-key','task','skills','update','workflow','batch']);
const catalogDiscovery = (args[0]==='tools' && ['list','info','update'].includes(args[1])) ||
  (args.length>1 && !staticRoots.has(args[0]) && args[0]!=='tools' &&
    (args.includes('--help') || args.includes('-h') || args[0]==='help'));
if(catalogDiscovery) {
  const status=spawnSync(process.execPath,[selected.bin,'auth','status','--json'],
    {env,encoding:'utf8',timeout:15000,maxBuffer:1024*1024,windowsHide:true});
  // Never print status output: it may contain account details. Only a valid,
  // explicit unauthenticated response is grounds for requesting authorization.
  if(status.status===0) {
    let auth;
    try { auth=JSON.parse(status.stdout); } catch {}
    if(auth?.iam_session?.logged_in===false && auth?.execution_auth_available===false) {
      const message=profile.partition==='cn'
        ? '请先登录 MeituHub，再获取工具列表或命令帮助。运行环境已就绪，无需重新安装。'
        : 'Sign in to MeituHub before loading the tool catalog or command help. The runtime is ready; no reinstall is needed.';
      const nextAction={command:'auth',args:['login','--force','--no-open-browser','--no-poll-progress']};
      if(args.includes('--json')) console.log(JSON.stringify({ok:false,code:'AUTH_REQUIRED',message,
        partition:profile.partition,client_id:profile.clientId,next_action:nextAction}));
      else { console.error(message); console.error('meitu '+nextAction.command+' '+nextAction.args.join(' ')); }
      process.exit(3);
    }
  }
}
// Every invocation keeps its selected immutable version, even if another invocation updates the channel.
const result=spawnSync(process.execPath,[selected.bin,...args],{env,stdio:'inherit',shell:false});
if(result.error) console.error(result.error.message);process.exit(result.status??1);
