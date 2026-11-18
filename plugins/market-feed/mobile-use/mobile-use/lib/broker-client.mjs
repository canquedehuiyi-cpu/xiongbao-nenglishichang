import { lstat, readFile, readdir } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";

const MAX_RECORD_BYTES = 32 * 1024;
const MAX_RESPONSE_BYTES = 8 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 10_000;
const BROKER_ID = /^mobile-use-[1-9][0-9]*-[0-9a-f]{24}$/u;
const PLATFORMS = new Set(["android", "harmony", "ios"]);
const RUNTIME_KINDS = new Set(["emulator", "physical", "previewer", "remote", "simulator"]);

export function resolveRegistryDirectory(env = process.env) {
  const override = env.MOBILE_USE_REGISTRY_DIR?.trim()
    || env.MOBILE_SIMULATOR_REGISTRY_DIR?.trim();
  if (override) return path.resolve(override);
  const dataRoot = env.AICODING_HOME?.trim() || path.join(homedir(), ".qoder");
  return path.resolve(dataRoot, "canvas", "phone-use-brokers");
}

export async function listLiveSessions(options = {}) {
  const records = await readBrokerRecords(options);
  const discovered = await Promise.all(records.map(async (record) => {
    try {
      const sessions = await requestBrokerJson(record, "GET", "", undefined, options);
      if (!Array.isArray(sessions)) return [];
      return sessions.flatMap((candidate) => {
        const session = parseSession(candidate, record);
        return session ? [session] : [];
      });
    } catch {
      return [];
    }
  }));
  return discovered.flat().sort((left, right) => (
    left.surfaceId.localeCompare(right.surfaceId) || left.sessionId.localeCompare(right.sessionId)
  ));
}

export async function listLiveTargets(options = {}) {
  const records = await readBrokerRecords(options);
  const discovered = await Promise.all(records.map(async (record) => {
    try {
      const targets = await requestBrokerUrlJson(record, phoneTargetsUrl(record), "GET", undefined, options);
      if (!Array.isArray(targets)) return [];
      return targets.flatMap((candidate) => {
        const target = parseTarget(candidate, record);
        return target ? [target] : [];
      });
    } catch {
      return [];
    }
  }));
  return discovered.flat().sort((left, right) => (
    left.surfaceId.localeCompare(right.surfaceId) || left.targetId.localeCompare(right.targetId)
  ));
}

export async function inspectLiveBrokers(options = {}) {
  const records = await readBrokerRecords(options);
  const surfaces = await Promise.all(records.map(async (record) => {
    const [sessions, targets] = await Promise.all([
      inspectBrokerRequest(() => requestBrokerJson(record, "GET", "", undefined, options)),
      inspectBrokerRequest(() => requestBrokerUrlJson(record, phoneTargetsUrl(record), "GET", undefined, options)),
    ]);
    const successfulChecks = [sessions, targets].filter((check) => check.ok).length;
    return Object.freeze({
      surfaceId: record.brokerId,
      platform: record.platform,
      runtimeKind: record.runtimeKind,
      status: successfulChecks === 2 ? "ready" : successfulChecks === 0 ? "unavailable" : "degraded",
      sessions,
      targets,
    });
  }));
  return Object.freeze({
    schemaVersion: 1,
    scope: "live_canvas_brokers",
    summary: Object.freeze({
      brokerRecordCount: records.length,
      readyCount: surfaces.filter((surface) => surface.status === "ready").length,
      degradedCount: surfaces.filter((surface) => surface.status === "degraded").length,
      unavailableCount: surfaces.filter((surface) => surface.status === "unavailable").length,
    }),
    surfaces: Object.freeze(surfaces),
    note: records.length === 0
      ? "No live Mobile Use broker records were found. Open the canonical project entry in Canvas before inferring anything about machine-wide SDKs or devices."
      : "Diagnostics are credential-free and describe only brokers published by live Canvas surfaces.",
  });
}

export async function startPhoneUseSession(surfaceId, targetId, options = {}) {
  const records = await readBrokerRecords(options);
  const record = records.find((candidate) => candidate.brokerId === surfaceId);
  if (!record) throw brokerError("device.surface.stale", "Phone-use Simulator surface is stale or unavailable. Call list_targets again.");
  const targets = await requestBrokerUrlJson(record, phoneTargetsUrl(record), "GET", undefined, options);
  const target = Array.isArray(targets)
    ? targets.map((candidate) => parseTarget(candidate, record)).find((candidate) => candidate?.targetId === targetId)
    : undefined;
  if (!target) throw brokerError("device.target.not-found", "Phone-use device target is stale or does not belong to this surface. Call list_targets again.");
  const value = await requestBrokerJson(record, "POST", "", {
    adapterId: target.adapterId,
    operationId: operationId(),
    targetId: target.targetId,
    actor: { kind: "agent", id: "mobile-use-cli" },
  }, {
    ...options,
    timeoutMs: options.timeoutMs ?? startTimeoutMs(record.platform),
  });
  const session = parseSession(value, record);
  if (!session) throw brokerError("phone.broker.invalid-session", "Phone-use broker returned an invalid session.");
  return session;
}

export async function stopPhoneUseSession(surfaceId, sessionId, options = {}) {
  const records = await readBrokerRecords(options);
  const record = records.find((candidate) => candidate.brokerId === surfaceId);
  if (!record) throw brokerError("device.surface.stale", "Phone-use Simulator surface is stale or unavailable. Call list_sessions again.");
  const sessions = await requestBrokerJson(record, "GET", "", undefined, options);
  if (!Array.isArray(sessions) || !sessions.some((candidate) => sessionIdOf(candidate) === sessionId)) {
    throw brokerError("device.session.not-found", "Phone-use device session is stale or does not belong to this surface. Call list_sessions again.");
  }
  return requestBrokerJson(record, "DELETE", `/${encodeURIComponent(sessionId)}`, undefined, options);
}

export async function invokePhoneUse(surfaceId, sessionId, method, input, options = {}) {
  if (!["observe", "act", "perform", "wait", "assert"].includes(method)) {
    throw new TypeError(`Unsupported Phone-use method: ${method}`);
  }
  const records = await readBrokerRecords(options);
  const record = records.find((candidate) => candidate.brokerId === surfaceId);
  if (!record) throw brokerError("device.surface.stale", "Phone-use Simulator surface is stale or unavailable. Call list_sessions again.");
  const sessions = await requestBrokerJson(record, "GET", "", undefined, options);
  if (!Array.isArray(sessions) || !sessions.some((candidate) => sessionIdOf(candidate) === sessionId)) {
    throw brokerError("device.session.not-found", "Phone-use device session is stale or does not belong to this surface. Call list_sessions again.");
  }
  return requestBrokerJson(record, "POST", `/${encodeURIComponent(sessionId)}/${method}`, input, options);
}

export async function invokeSessionOperation(surfaceId, sessionId, operation, capability, input, options = {}) {
  const { record, session } = await resolveOwnedSession(surfaceId, sessionId, options);
  const capabilityIds = sessionCapabilities(session);
  if (!capabilityIds.has(capability)) {
    throw brokerError("device.capability.unsupported", `Session does not advertise ${capability}. Call list_sessions again or choose another platform.`);
  }
  return requestBrokerJson(record, "POST", `/${encodeURIComponent(sessionId)}/operate`, {
    protocolVersion: 1,
    operationId: operationId(),
    operation,
    actor: { kind: "agent", id: "mobile-use-cli" },
    input,
    requiredCapabilities: [capability],
  }, { ...options, timeoutMs: options.timeoutMs ?? operationTimeoutMs(operation, input) });
}

export async function invokeTargetOperation(surfaceId, targetId, operation, capability, input = {}, options = {}) {
  const records = await readBrokerRecords(options);
  const record = records.find((candidate) => candidate.brokerId === surfaceId);
  if (!record) throw brokerError("device.surface.stale", "Phone-use Simulator surface is stale or unavailable. Call list_targets again.");
  const targets = await requestBrokerUrlJson(record, phoneTargetsUrl(record), "GET", undefined, options);
  const rawTarget = Array.isArray(targets) ? targets.find((candidate) => candidate?.target?.id === targetId) : undefined;
  const target = parseTarget(rawTarget, record);
  if (!target) throw brokerError("device.target.not-found", "Phone-use target is stale or does not belong to this surface. Call list_targets again.");
  if (!target.targetCapabilities.includes(capability)) {
    throw brokerError("device.capability.unsupported", `Target does not advertise ${capability}.`);
  }
  return requestBrokerUrlJson(record, phoneTargetOperationsUrl(record), "POST", {
    adapterId: target.adapterId,
    operation: {
      protocolVersion: 1,
      operationId: operationId(),
      operation,
      actor: { kind: "agent", id: "mobile-use-cli" },
      input: { targetId, ...input },
      requiredCapabilities: [capability],
    },
  }, { ...options, timeoutMs: options.timeoutMs ?? operationTimeoutMs(operation) });
}

export async function readBrokerRecords(options = {}) {
  const registryDirectory = path.resolve(options.registryDirectory ?? resolveRegistryDirectory(options.env));
  let entries;
  try {
    const directoryStat = await lstat(registryDirectory);
    if (!directoryStat.isDirectory() || directoryStat.isSymbolicLink()) return [];
    if (process.platform !== "win32" && (directoryStat.mode & 0o077) !== 0) return [];
    if (typeof process.getuid === "function" && directoryStat.uid !== process.getuid()) return [];
    entries = await readdir(registryDirectory, { withFileTypes: true });
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }

  const records = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
    const recordPath = path.join(registryDirectory, entry.name);
    try {
      const recordStat = await lstat(recordPath);
      if (!recordStat.isFile() || recordStat.isSymbolicLink() || recordStat.size > MAX_RECORD_BYTES) continue;
      if (process.platform !== "win32" && (recordStat.mode & 0o077) !== 0) continue;
      if (typeof process.getuid === "function" && recordStat.uid !== process.getuid()) continue;
      const record = parseRecord(JSON.parse(await readFile(recordPath, "utf8")), entry.name);
      if (record && processIsAlive(record.processId)) records.push(record);
    } catch {
      // Ignore malformed, stale, or concurrently removed broker records.
    }
  }
  return records;
}

async function requestBrokerJson(record, method, suffix, body, options) {
  return requestBrokerUrlJson(record, `${record.phoneUseAdminUrl}${suffix}`, method, body, options);
}

async function requestBrokerUrlJson(record, url, method, body, options) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? REQUEST_TIMEOUT_MS);
  try {
    const response = await (options.fetch ?? fetch)(url, {
      method,
      headers: {
        authorization: `Bearer ${record.phoneUseAdminToken}`,
        ...(body === undefined ? {} : { "content-type": "application/json" }),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: controller.signal,
    });
    const contentLength = Number(response.headers.get("content-length") ?? "0");
    if (Number.isFinite(contentLength) && contentLength > MAX_RESPONSE_BYTES) {
      throw brokerError("phone.broker.response-too-large", "Phone-use broker response is too large.");
    }
    const text = await response.text();
    if (Buffer.byteLength(text) > MAX_RESPONSE_BYTES) throw brokerError("phone.broker.response-too-large", "Phone-use broker response is too large.");
    let value;
    try {
      value = text ? JSON.parse(text) : {};
    } catch {
      throw brokerError("phone.broker.invalid-json", "Phone-use broker returned invalid JSON.");
    }
    if (!response.ok) {
      const message = value?.error?.message;
      throw brokerError(
        typeof value?.error?.code === "string" ? value.error.code : "phone.broker.http-error",
        typeof message === "string" && message ? message : `Phone-use broker failed with HTTP ${response.status}.`,
        isRecord(value?.error?.details) ? value.error.details : undefined,
      );
    }
    return value;
  } catch (error) {
    if (typeof error?.code === "string") throw error;
    if (controller.signal.aborted || error?.name === "AbortError" || error?.code === "ABORT_ERR") {
      throw brokerError("phone.broker.timeout", "Phone-use broker request timed out.");
    }
    if (error instanceof TypeError) {
      throw brokerError("phone.broker.unreachable", "Phone-use broker could not be reached.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function inspectBrokerRequest(request) {
  try {
    const value = await request();
    if (!Array.isArray(value)) {
      return Object.freeze({
        ok: false,
        error: Object.freeze({ code: "phone.broker.invalid-response", message: "Broker discovery response was not an array." }),
      });
    }
    return Object.freeze({ ok: true, count: value.length });
  } catch (error) {
    return Object.freeze({
      ok: false,
      error: Object.freeze({
        code: typeof error?.code === "string" ? error.code : "phone.broker.failed",
        message: safeDiagnosticMessage(error instanceof Error ? error.message : String(error)),
      }),
    });
  }
}

function safeDiagnosticMessage(value) {
  return value.replace(/https?:\/\/\S+/giu, "[loopback-url]").slice(0, 500);
}

function phoneTargetsUrl(record) {
  const url = new URL(record.phoneUseAdminUrl);
  url.pathname = "/api/phone/targets";
  return url.toString();
}

function phoneTargetOperationsUrl(record) {
  const url = new URL(record.phoneUseAdminUrl);
  url.pathname = "/api/phone/targets/operations";
  return url.toString();
}

function startTimeoutMs(platform) {
  if (platform === "android") return 12 * 60_000;
  if (platform === "ios") return 4 * 60_000;
  return 6 * 60_000;
}

function operationTimeoutMs(operation, input = {}) {
  if (operation === "device.app.install") return 2 * 60_000;
  if (operation === "device.test.run") return 20 * 60_000;
  if (operation === "device.project.live-build.wait") {
    return Math.min(20 * 60_000 + 5_000, Number.isInteger(input?.timeoutMs) ? input.timeoutMs + 5_000 : 5 * 60_000 + 5_000);
  }
  if (operation === "device.target.boot" || operation === "device.target.restart") return 4 * 60_000;
  if (operation === "device.recording.stop") return 30_000;
  return REQUEST_TIMEOUT_MS;
}

function parseRecord(value, fileName) {
  if (!isRecord(value) || value.schemaVersion !== 1) return undefined;
  if (typeof value.brokerId !== "string" || !BROKER_ID.test(value.brokerId) || fileName !== `${value.brokerId}.json`) return undefined;
  if (!Number.isSafeInteger(value.processId) || value.processId < 1) return undefined;
  if (!PLATFORMS.has(value.platform) || !RUNTIME_KINDS.has(value.runtimeKind)) return undefined;
  if (typeof value.phoneUseAdminToken !== "string" || value.phoneUseAdminToken.length < 20) return undefined;
  if (typeof value.createdAt !== "string" || !Number.isFinite(Date.parse(value.createdAt))) return undefined;
  const phoneUseAdminUrl = loopbackAdminUrl(value.phoneUseAdminUrl);
  if (!phoneUseAdminUrl) return undefined;
  return Object.freeze({ ...value, phoneUseAdminUrl });
}

function parseSession(value, record) {
  if (!isRecord(value) || typeof value.sessionId !== "string" || !value.sessionId.trim()) return undefined;
  const target = isRecord(value.target) ? value.target : undefined;
  if (!target || typeof target.name !== "string") return undefined;
  const platform = PLATFORMS.has(target.platform) ? target.platform : record.platform;
  const runtimeKind = RUNTIME_KINDS.has(target.runtimeKind) ? target.runtimeKind : record.runtimeKind;
  return Object.freeze({
    surfaceId: record.brokerId,
    sessionId: value.sessionId,
    platform,
    targetName: target.name,
    runtimeKind,
    state: typeof value.state === "string" ? value.state : "unknown",
    openedAt: typeof value.openedAt === "string" ? value.openedAt : record.createdAt,
    targetId: typeof target.id === "string" ? target.id : "unknown",
    capabilities: capabilityIds(value.capabilities),
  });
}

function parseTarget(value, record) {
  if (!isRecord(value) || typeof value.adapterId !== "string" || !isRecord(value.target)) return undefined;
  const target = value.target;
  if (typeof target.id !== "string" || !target.id.trim() || typeof target.name !== "string") return undefined;
  const platform = PLATFORMS.has(target.platform) ? target.platform : record.platform;
  const runtimeKind = RUNTIME_KINDS.has(target.runtimeKind) ? target.runtimeKind : record.runtimeKind;
  return Object.freeze({
    surfaceId: record.brokerId,
    adapterId: value.adapterId,
    targetId: target.id,
    platform,
    targetName: target.name,
    runtimeKind,
    state: typeof target.state === "string" ? target.state : "unknown",
    targetCapabilities: capabilityIds(value.targetCapabilities),
  });
}

async function resolveOwnedSession(surfaceId, sessionId, options) {
  const records = await readBrokerRecords(options);
  const record = records.find((candidate) => candidate.brokerId === surfaceId);
  if (!record) throw brokerError("device.surface.stale", "Phone-use Simulator surface is stale or unavailable. Call list_sessions again.");
  const sessions = await requestBrokerJson(record, "GET", "", undefined, options);
  const session = Array.isArray(sessions) ? sessions.find((candidate) => sessionIdOf(candidate) === sessionId) : undefined;
  if (!session) throw brokerError("device.session.not-found", "Phone-use device session is stale or does not belong to this surface. Call list_sessions again.");
  return { record, session };
}

function sessionCapabilities(session) {
  return new Set(capabilityIds(session?.capabilities));
}

function capabilityIds(value) {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => typeof entry?.id === "string" ? [entry.id] : []);
}

function operationId() {
  return `mobile-use-cli-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function brokerError(code, message, details) {
  const error = new Error(message);
  error.code = code;
  if (details !== undefined) error.details = Object.freeze({ ...details });
  return error;
}

function sessionIdOf(value) {
  return isRecord(value) && typeof value.sessionId === "string" ? value.sessionId : undefined;
}

function loopbackAdminUrl(value) {
  if (typeof value !== "string") return undefined;
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" || (url.hostname !== "127.0.0.1" && url.hostname !== "[::1]")) return undefined;
    if (url.username || url.password || url.search || url.hash || url.pathname !== "/api/phone/sessions") return undefined;
    return url.toString().replace(/\/$/u, "");
  } catch {
    return undefined;
  }
}

function processIsAlive(processId) {
  try {
    process.kill(processId, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
