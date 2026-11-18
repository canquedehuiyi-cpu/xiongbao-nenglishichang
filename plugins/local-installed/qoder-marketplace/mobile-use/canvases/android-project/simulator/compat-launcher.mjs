#!/usr/bin/env node

import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { execFileSync, spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdir, open, readFile, readdir, rename, stat, unlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DATA_KEY = "mobileSimulatorSurface.v1";
const DEFAULT_LEASE_TTL_MS = 5 * 60_000;
const DEFAULT_STARTUP_TTL_MS = 15 * 60_000;
// Qoder bounds Canvas runScript calls at 30 seconds. Return control before that
// host deadline while the detached daemon continues publishing build progress.
const DEFAULT_LAUNCH_READY_TIMEOUT_MS = 25_000;
const LAUNCH_STATE_POLL_MS = 50;
const HOST_STOP_GRACE_MS = 2_000;
const MAX_LOG_LINES = 12;
const MAX_PROJECTION_PATHS = 64;
const MAX_STDERR_CHARS = 8_192;
const scriptPath = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(scriptPath);

if (process.argv.includes("--daemon")) {
  await runDaemon().catch(async (error) => {
    await publishFailureFromDaemon(error).catch(() => undefined);
    process.stderr.write(`${normalizeError(error)}\n`);
    process.exitCode = 1;
  });
} else {
  await launchDaemon().catch(async (error) => {
    await publishFailureFromLauncher(error).catch(() => undefined);
    process.stderr.write(`${normalizeError(error)}\n`);
    process.exitCode = 1;
  });
}

async function launchDaemon() {
  const configuration = readLaunchConfiguration();
  await assertTargetFile(configuration.targetFilePath);
  await mkdir(configuration.runtimeRoot, { recursive: true, mode: 0o700 });
  await registerProjection(configuration);

  const [existing, activeLock] = await Promise.all([
    readCanonicalState(configuration.statePath),
    readJsonIfExists(configuration.lockPath),
  ]);
  if (
    existing?.schemaVersion === 1
    && existing.platform === configuration.platform
    && existing.targetFilePath === configuration.targetFilePath
    && typeof existing.pid === "number"
    && activeLock?.pid === existing.pid
    && activeLock?.generation === existing.generation
    && processIsAlive(existing.pid)
    && existing.status !== "failed"
    && existing.status !== "stopped"
  ) {
    await writeCanvasState(configuration.dataPath, existing);
    if (existing.status !== "ready" || typeof existing.url !== "string") {
      await waitForLaunchState(configuration, existing.pid, existing.generation);
    }
    return;
  }

  const generation = `${Date.now().toString(36)}-${randomBytes(8).toString("hex")}`;
  const generationStartedAt = Date.now();
  const lock = await acquireLaunchLock(configuration.lockPath, generation, generationStartedAt);
  if (!lock.acquired) {
    await waitForLaunchState(configuration, lock.pid, lock.generation);
    return;
  }

  let daemon;
  try {
    daemon = spawn(process.execPath, [scriptPath, "--daemon"], {
      cwd: path.dirname(configuration.targetFilePath),
      detached: true,
      env: {
        ...process.env,
        ELECTRON_RUN_AS_NODE: "1",
        CANVAS_SIMULATOR_COMPAT_GENERATION: generation,
        CANVAS_SIMULATOR_COMPAT_GENERATION_STARTED_AT: String(generationStartedAt),
        CANVAS_SIMULATOR_COMPAT_KEY: DATA_KEY,
        CANVAS_SIMULATOR_COMPAT_LOCK: configuration.lockPath,
        CANVAS_SIMULATOR_COMPAT_PLATFORM: configuration.platform,
        CANVAS_SIMULATOR_COMPAT_PROJECTIONS: configuration.projectionRoot,
        CANVAS_SIMULATOR_COMPAT_STATE: configuration.statePath,
        CANVAS_SIMULATOR_COMPAT_TARGET: configuration.targetFilePath,
      },
      stdio: "ignore",
      windowsHide: true,
    });
    if (!daemon.pid) throw new Error("The compatibility Simulator daemon did not start.");
    await writeLock(configuration.lockPath, daemon.pid, generation, generationStartedAt);
    daemon.unref();
  } catch (error) {
    await releaseLock(configuration.lockPath, daemon?.pid ?? process.pid);
    throw error;
  }
  await waitForLaunchState(configuration, daemon.pid, generation);
}

async function waitForLaunchState(configuration, expectedPid, expectedGeneration) {
  const timeoutMs = positiveInteger(
    process.env.MOBILE_USE_COMPAT_LAUNCH_READY_TIMEOUT_MS
      ?? process.env.MOBILE_SIMULATOR_COMPAT_LAUNCH_READY_TIMEOUT_MS,
  ) ?? DEFAULT_LAUNCH_READY_TIMEOUT_MS;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const state = await readCanonicalState(configuration.statePath);
    const matchesTarget = state?.schemaVersion === 1
      && state.platform === configuration.platform
      && state.targetFilePath === configuration.targetFilePath
      && (!expectedGeneration || state.generation === expectedGeneration);
    if (matchesTarget) {
      await writeCanvasState(configuration.dataPath, state);
      if (state.status === "ready" && typeof state.url === "string") return;
      if (state.status === "failed" || state.status === "stopped") return;
    }
    if (expectedPid && !processIsAlive(expectedPid)) return;
    await delay(LAUNCH_STATE_POLL_MS);
  }
}

async function runDaemon() {
  const generation = requiredEnv("CANVAS_SIMULATOR_COMPAT_GENERATION");
  const generationStartedAt = requiredPositiveIntegerEnv("CANVAS_SIMULATOR_COMPAT_GENERATION_STARTED_AT");
  const lockPath = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_LOCK");
  const projectionRoot = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_PROJECTIONS");
  const statePath = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_STATE");
  const targetFilePath = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_TARGET");
  const platform = readPlatform(process.env.CANVAS_SIMULATOR_COMPAT_PLATFORM);
  const dataKey = process.env.CANVAS_SIMULATOR_COMPAT_KEY || DATA_KEY;
  const leaseTtlMs = positiveInteger(
    process.env.MOBILE_USE_COMPAT_LEASE_TTL_MS ?? process.env.MOBILE_SIMULATOR_COMPAT_LEASE_TTL_MS,
  ) ?? DEFAULT_LEASE_TTL_MS;
  const startupTtlMs = positiveInteger(
    process.env.MOBILE_USE_COMPAT_STARTUP_TTL_MS ?? process.env.MOBILE_SIMULATOR_COMPAT_STARTUP_TTL_MS,
  )
    ?? Math.max(DEFAULT_STARTUP_TTL_MS, leaseTtlMs);
  const hostScriptOverride = process.env.MOBILE_USE_COMPAT_HOST_SCRIPT
    ?? process.env.MOBILE_SIMULATOR_COMPAT_HOST_SCRIPT;
  const hostScript = hostScriptOverride
    ? path.resolve(hostScriptOverride)
    : path.join(scriptDir, "host.cjs");
  await Promise.all([assertTargetFile(targetFilePath), assertTargetFile(hostScript)]);
  await writeLock(lockPath, process.pid, generation, generationStartedAt);

  const startedAt = Date.now();
  const leaseToken = randomBytes(32).toString("base64url");
  let lastLeaseAt = Date.now();
  let ready = false;
  let embeddedSurfaceUrl;
  let stopping = false;
  let stopReason = "Compatibility lease expired";
  let host;
  let stderr = "";
  let stdoutBuffer = "";
  const logs = [];
  let publishQueue = Promise.resolve();

  const publish = (value) => {
    publishQueue = publishQueue
      .catch(() => undefined)
      .then(() => publishCanonicalState({
        dataKey,
        generation,
        generationStartedAt,
        lockPath,
        projectionRoot,
        statePath,
        state: {
        schemaVersion: 1,
        generation,
        generationStartedAt,
        platform,
        targetFilePath,
        pid: process.pid,
        ...value,
        updatedAt: new Date().toISOString(),
        },
      }));
    return publishQueue;
  };

  const leaseServer = createServer((request, response) => {
    const requestUrl = new URL(request.url ?? "/", "http://127.0.0.1");
    response.setHeader("access-control-allow-origin", "*");
    response.setHeader("access-control-allow-methods", "POST, OPTIONS");
    response.setHeader("cache-control", "no-store");
    if (request.method === "OPTIONS") {
      response.writeHead(204).end();
      return;
    }
    if (
      request.method !== "POST"
      || requestUrl.pathname !== "/lease"
      || !safeTokenEqual(requestUrl.searchParams.get("token"), leaseToken)
    ) {
      response.writeHead(404).end();
      return;
    }
    lastLeaseAt = Date.now();
    response.writeHead(204).end();
  });
  await new Promise((resolve, reject) => {
    leaseServer.once("error", reject);
    leaseServer.listen(0, "127.0.0.1", () => {
      leaseServer.off("error", reject);
      resolve();
    });
  });
  const address = leaseServer.address();
  if (!address || typeof address === "string") throw new Error("Unable to bind the compatibility lease server.");
  const leaseUrl = `http://127.0.0.1:${address.port}/lease?token=${encodeURIComponent(leaseToken)}`;

  const stopHost = async () => {
    if (!host || host.exitCode !== null) return;
    host.kill("SIGTERM");
    const exited = await Promise.race([
      new Promise((resolve) => host.once("exit", () => resolve(true))),
      new Promise((resolve) => setTimeout(() => resolve(false), HOST_STOP_GRACE_MS)),
    ]);
    if (!exited && host.exitCode === null) host.kill("SIGKILL");
  };

  const requestStop = (reason) => {
    if (stopping) return;
    stopping = true;
    stopReason = reason;
    void stopHost();
  };
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    process.once(signal, () => requestStop(`Compatibility daemon received ${signal}`));
  }

  const leaseTimer = setInterval(() => {
    if (ready && Date.now() - lastLeaseAt > leaseTtlMs) {
      requestStop("Compatibility lease expired");
    } else if (!ready && Date.now() - startedAt > startupTtlMs) {
      requestStop("Compatibility runtime startup timed out");
    }
  }, Math.min(5_000, Math.max(100, Math.floor(leaseTtlMs / 4))));

  try {
    await publish({
      status: "starting",
      progress: {
        phase: "runtime",
        status: "running",
        message: `Starting the ${platformLabel(platform)} compatibility runtime`,
        elapsedMs: Date.now() - startedAt,
        logs,
      },
    });

    host = spawn(process.execPath, [hostScript, targetFilePath], {
      cwd: path.dirname(targetFilePath),
      env: { ...process.env, ELECTRON_RUN_AS_NODE: "1" },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    async function handleHostLine(line) {
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        return;
      }
      if (!message || typeof message !== "object") return;
      if (message.type === "progress" && typeof message.message === "string") {
        logs.push(message.message);
        if (logs.length > MAX_LOG_LINES) logs.splice(0, logs.length - MAX_LOG_LINES);
        await publish({
          status: ready && embeddedSurfaceUrl ? "ready" : "starting",
          ...(ready && embeddedSurfaceUrl ? { url: embeddedSurfaceUrl } : {}),
          hostPid: host.pid,
          progress: {
            phase: typeof message.phase === "string" ? message.phase : "runtime",
            status: message.status === "failed" ? "failed" : message.status === "succeeded" ? "succeeded" : "running",
            message: message.message,
            elapsedMs: typeof message.elapsedMs === "number" ? message.elapsedMs : Date.now() - startedAt,
            logs: [...logs],
          },
        });
        return;
      }
      if (message.type === "ready" && typeof message.url === "string") {
        ready = true;
        lastLeaseAt = Date.now();
        const surfaceUrl = new URL(message.url);
        surfaceUrl.searchParams.set("canvas_compat_lease", leaseUrl);
        embeddedSurfaceUrl = surfaceUrl.toString();
        logs.push(`${platformLabel(platform)} compatibility runtime is ready`);
        if (logs.length > MAX_LOG_LINES) logs.splice(0, logs.length - MAX_LOG_LINES);
        await publish({
          status: "ready",
          url: embeddedSurfaceUrl,
          hostPid: host.pid,
          progress: {
            phase: "ready",
            status: "succeeded",
            message: `${platformLabel(platform)} device runtime is ready`,
            elapsedMs: Date.now() - startedAt,
            logs: [...logs],
          },
        });
      }
    }

    host.stderr.setEncoding("utf8");
    host.stderr.on("data", (chunk) => {
      stderr = `${stderr}${chunk}`.slice(-MAX_STDERR_CHARS);
    });
    host.stdout.setEncoding("utf8");
    host.stdout.on("data", (chunk) => {
      stdoutBuffer += chunk;
      while (true) {
        const newline = stdoutBuffer.indexOf("\n");
        if (newline < 0) break;
        const line = stdoutBuffer.slice(0, newline).trim();
        stdoutBuffer = stdoutBuffer.slice(newline + 1);
        if (line) void handleHostLine(line).catch(() => undefined);
      }
    });

    const result = await new Promise((resolve) => {
      host.once("error", (error) => resolve({ error }));
      host.once("exit", (code, signal) => resolve({ code, signal }));
    });
    const resultError = "error" in result ? normalizeError(result.error) : "";
    const exitSummary = resultError
      || `Simulator host exited (${result.signal ?? result.code ?? "unknown"})`;
    if (!stopping && (!ready || resultError || result.code !== 0)) {
      await publish({
        status: "failed",
        error: stderr.trim() || exitSummary,
        progress: {
          phase: "runtime",
          status: "failed",
          message: exitSummary,
          elapsedMs: Date.now() - startedAt,
          logs: [...logs],
        },
      });
    } else {
      if (!stopping) stopReason = "Simulator host stopped";
      await publish({
        status: "stopped",
        error: stopReason,
        progress: {
          phase: "runtime",
          status: "failed",
          message: stopReason,
          elapsedMs: Date.now() - startedAt,
          logs: [...logs],
        },
      });
    }
  } catch (error) {
    await publish({
      status: "failed",
      error: normalizeError(error),
      progress: {
        phase: "runtime",
        status: "failed",
        message: normalizeError(error),
        elapsedMs: Date.now() - startedAt,
        logs: [...logs],
      },
    }).catch(() => undefined);
    await stopHost();
  } finally {
    clearInterval(leaseTimer);
    await new Promise((resolve) => leaseServer.close(() => resolve()));
    await releaseLock(lockPath, process.pid);
  }
}

function readLaunchConfiguration() {
  const scriptArgs = parseObject(process.env.AICODING_CANVAS_SCRIPT_ARGS || process.env.QODER_CANVAS_SCRIPT_ARGS || "{}");
  const platform = readPlatform(scriptArgs.platform);
  const targetFilePath = cleanPath(
    scriptArgs.targetFilePath
      || process.env.AICODING_CANVAS_TARGET_FILE
      || process.env.QODER_CANVAS_TARGET_FILE
      || "",
  );
  if (!path.isAbsolute(targetFilePath)) throw new Error("The compatibility Simulator target must be an absolute file path.");
  const dataPath = cleanPath(process.env.AICODING_CANVAS_DATA || process.env.QODER_CANVAS_DATA || "");
  if (!path.isAbsolute(dataPath)) throw new Error("The compatibility Simulator requires an absolute Canvas data path.");
  const dataRoot = cleanPath(process.env.AICODING_HOME || process.env.QODER_HOME || path.join(os.homedir(), ".qoder"));
  const runtimeRoot = path.join(dataRoot, "canvas", "mobile-use", "compat");
  const identity = createHash("sha256").update(`${platform}\u0000${targetFilePath}`).digest("hex").slice(0, 32);
  return {
    dataPath,
    lockPath: path.join(runtimeRoot, `${identity}.lock`),
    platform,
    projectionRoot: path.join(runtimeRoot, `${identity}.projections`),
    runtimeRoot,
    statePath: path.join(runtimeRoot, `${identity}.state.json`),
    targetFilePath,
  };
}

async function publishFailureFromLauncher(error) {
  const configuration = readLaunchConfiguration();
  await writeCanvasState(configuration.dataPath, {
    schemaVersion: 1,
    status: "failed",
    platform: configuration.platform,
    targetFilePath: configuration.targetFilePath,
    error: normalizeError(error),
    progress: {
      phase: "runtime",
      status: "failed",
      message: normalizeError(error),
      elapsedMs: 0,
      logs: [],
    },
    updatedAt: new Date().toISOString(),
  });
}

async function publishFailureFromDaemon(error) {
  const generation = requiredEnv("CANVAS_SIMULATOR_COMPAT_GENERATION");
  const generationStartedAt = requiredPositiveIntegerEnv("CANVAS_SIMULATOR_COMPAT_GENERATION_STARTED_AT");
  const lockPath = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_LOCK");
  const projectionRoot = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_PROJECTIONS");
  const statePath = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_STATE");
  const targetFilePath = requiredAbsoluteEnv("CANVAS_SIMULATOR_COMPAT_TARGET");
  const platform = readPlatform(process.env.CANVAS_SIMULATOR_COMPAT_PLATFORM);
  try {
    await publishCanonicalState({
      dataKey: process.env.CANVAS_SIMULATOR_COMPAT_KEY || DATA_KEY,
      generation,
      generationStartedAt,
      lockPath,
      projectionRoot,
      statePath,
      state: {
        schemaVersion: 1,
        generation,
        generationStartedAt,
        status: "failed",
        platform,
        targetFilePath,
        pid: process.pid,
        error: normalizeError(error),
        progress: {
          phase: "runtime",
          status: "failed",
          message: normalizeError(error),
          elapsedMs: 0,
          logs: [],
        },
        updatedAt: new Date().toISOString(),
      },
    });
  } finally {
    await releaseLock(lockPath, process.pid);
  }
}

async function acquireLaunchLock(lockPath, generation, generationStartedAt) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const handle = await open(lockPath, "wx", 0o600);
      let writeError;
      try {
        await handle.writeFile(`${JSON.stringify({
          pid: process.pid,
          generation,
          generationStartedAt,
          createdAt: new Date().toISOString(),
        })}\n`);
      } catch (error) {
        writeError = error;
      } finally {
        await handle.close();
      }
      if (writeError) {
        await unlink(lockPath).catch(() => undefined);
        throw writeError;
      }
      return { acquired: true };
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      const lock = await readJsonIfExists(lockPath);
      if (typeof lock?.pid === "number" && processIsAlive(lock.pid)) {
        if (!lock.generation && await stopLegacyCompatibilityDaemon(lock.pid)) {
          await unlink(lockPath).catch((unlinkError) => {
            if (unlinkError?.code !== "ENOENT") throw unlinkError;
          });
          continue;
        }
        return { acquired: false, generation: lock.generation, pid: lock.pid };
      }
      await unlink(lockPath).catch((unlinkError) => {
        if (unlinkError?.code !== "ENOENT") throw unlinkError;
      });
    }
  }
  throw new Error("Unable to acquire the compatibility Simulator launch lock.");
}

async function writeLock(lockPath, pid, generation, generationStartedAt) {
  const tempPath = `${lockPath}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(tempPath, `${JSON.stringify({
    pid,
    generation,
    generationStartedAt,
    updatedAt: new Date().toISOString(),
  })}\n`, { mode: 0o600 });
  await rename(tempPath, lockPath);
}

async function releaseLock(lockPath, ownerPid) {
  const lock = await readJsonIfExists(lockPath);
  if (lock?.pid !== ownerPid) return;
  await unlink(lockPath).catch((error) => {
    if (error?.code !== "ENOENT") throw error;
  });
}

async function writeCanvasState(dataPath, state, dataKey = DATA_KEY) {
  await mkdir(path.dirname(dataPath), { recursive: true });
  const existing = await readJsonIfExists(dataPath) ?? {};
  const next = { ...existing, [dataKey]: state };
  const tempPath = path.join(path.dirname(dataPath), `.${path.basename(dataPath)}.${process.pid}.${Date.now()}.tmp`);
  await writeFile(tempPath, `${JSON.stringify(next, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await rename(tempPath, dataPath);
}

async function registerProjection(configuration) {
  await mkdir(configuration.projectionRoot, { recursive: true, mode: 0o700 });
  const projectionId = createHash("sha256").update(configuration.dataPath).digest("hex");
  const projectionPath = path.join(configuration.projectionRoot, `${projectionId}.json`);
  await writeJsonAtomic(projectionPath, {
    dataPath: configuration.dataPath,
    updatedAt: new Date().toISOString(),
  });
}

async function publishCanonicalState({ dataKey, generation, generationStartedAt, lockPath, projectionRoot, statePath, state }) {
  const lock = await readJsonIfExists(lockPath);
  if (lock?.pid !== process.pid || lock.generation !== generation) return false;
  const existing = await readCanonicalState(statePath);
  if (
    existing?.generation !== generation
    && typeof existing?.generationStartedAt === "number"
    && existing.generationStartedAt > generationStartedAt
  ) return false;
  await writeJsonAtomic(statePath, state);
  const projectionPaths = await readProjectionPaths(projectionRoot);
  const firstAttempt = await Promise.allSettled(projectionPaths.map((dataPath) => writeCanvasState(dataPath, state, dataKey)));
  const failedPaths = projectionPaths.filter((_dataPath, index) => firstAttempt[index].status === "rejected");
  if (failedPaths.length) {
    await delay(25);
    await Promise.allSettled(failedPaths.map((dataPath) => writeCanvasState(dataPath, state, dataKey)));
  }
  return true;
}

async function readProjectionPaths(projectionRoot) {
  let entries;
  try {
    entries = await readdir(projectionRoot, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
  const records = [];
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
    const recordPath = path.join(projectionRoot, entry.name);
    const record = await readJsonIfExists(recordPath);
    const expectedName = typeof record?.dataPath === "string"
      ? `${createHash("sha256").update(record.dataPath).digest("hex")}.json`
      : "";
    if (!path.isAbsolute(record?.dataPath ?? "") || entry.name !== expectedName) {
      await unlink(recordPath).catch(() => undefined);
      continue;
    }
    records.push({
      dataPath: record.dataPath,
      recordPath,
      updatedAt: Date.parse(record.updatedAt ?? "") || 0,
    });
  }
  records.sort((left, right) => right.updatedAt - left.updatedAt || left.dataPath.localeCompare(right.dataPath));
  await Promise.allSettled(records.slice(MAX_PROJECTION_PATHS).map(({ recordPath }) => unlink(recordPath)));
  return [...new Set(records.slice(0, MAX_PROJECTION_PATHS).map(({ dataPath }) => dataPath))];
}

async function readCanonicalState(statePath) {
  const state = await readJsonIfExists(statePath);
  return state && typeof state === "object" && !Array.isArray(state) ? state : undefined;
}

async function writeJsonAtomic(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true, mode: 0o700 });
  const tempPath = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
  await writeFile(tempPath, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await rename(tempPath, filePath);
}

async function readJsonIfExists(filePath) {
  try {
    const parsed = JSON.parse(await readFile(filePath, "utf8"));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : undefined;
  } catch (error) {
    if (error?.code === "ENOENT" || error instanceof SyntaxError) return undefined;
    throw error;
  }
}

async function assertTargetFile(filePath) {
  const info = await stat(filePath);
  if (!info.isFile()) throw new Error(`Compatibility Simulator path is not a file: ${filePath}`);
}

function requiredAbsoluteEnv(name) {
  const value = cleanPath(process.env[name] || "");
  if (!path.isAbsolute(value)) throw new Error(`${name} must be an absolute path.`);
  return value;
}

function requiredEnv(name) {
  const value = String(process.env[name] ?? "").trim();
  if (!value) throw new Error(`${name} is required.`);
  return value;
}

function requiredPositiveIntegerEnv(name) {
  const value = positiveInteger(process.env[name]);
  if (value === undefined) throw new Error(`${name} must be a positive integer.`);
  return value;
}

function cleanPath(value) {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  return trimmed.startsWith("file://") ? fileURLToPath(trimmed) : path.resolve(trimmed);
}

function parseObject(value) {
  try {
    const parsed = JSON.parse(String(value));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function readPlatform(value) {
  if (value === "android" || value === "harmony" || value === "ios") return value;
  throw new Error(`Unsupported compatibility Simulator platform: ${String(value || "missing")}`);
}

function platformLabel(platform) {
  if (platform === "android") return "Android";
  if (platform === "harmony") return "HarmonyOS";
  return "iOS";
}

function processIsAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function stopLegacyCompatibilityDaemon(pid) {
  const command = processCommand(pid);
  if (!command || !/compat(?:ibility)?-launcher\.mjs|canvas-simulator-compat-launcher\.mjs/u.test(command) || !command.includes("--daemon")) {
    return false;
  }
  try {
    process.kill(pid, "SIGTERM");
  } catch {
    return !processIsAlive(pid);
  }
  const deadline = Date.now() + HOST_STOP_GRACE_MS;
  while (Date.now() < deadline && processIsAlive(pid)) await delay(50);
  if (processIsAlive(pid)) {
    try { process.kill(pid, "SIGKILL"); } catch { /* The exact managed process may have exited. */ }
    const killDeadline = Date.now() + 1_000;
    while (Date.now() < killDeadline && processIsAlive(pid)) await delay(25);
  }
  return !processIsAlive(pid);
}

function processCommand(pid) {
  try {
    if (process.platform === "win32") {
      const command = `(Get-CimInstance Win32_Process -Filter \"ProcessId = ${pid}\").CommandLine`;
      return execFileSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", command], { encoding: "utf8" }).trim();
    }
    return execFileSync("ps", ["-p", String(pid), "-o", "command="], { encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function positiveInteger(value) {
  if (!value) return undefined;
  const parsed = Number.parseInt(value, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function safeTokenEqual(actual, expected) {
  if (typeof actual !== "string") return false;
  const left = Buffer.from(actual);
  const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

function normalizeError(error) {
  return error instanceof Error ? error.stack || error.message : String(error);
}
