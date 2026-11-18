#!/usr/bin/env node

import { createHash, randomUUID } from "node:crypto";
import { execFile, execFileSync, spawn } from "node:child_process";
import { existsSync, readFileSync, watch } from "node:fs";
import { copyFile, mkdir, open, readFile, rename, rm, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import {
  generatedPreviewConfiguration,
  generatedPreviewProject,
} from "./lib/swift-package-preview-project.mjs";

const execFileAsync = promisify(execFile);
const scriptRoot = path.dirname(fileURLToPath(import.meta.url));
const templateRoot = existsSync(path.join(scriptRoot, "templates"))
  ? path.join(scriptRoot, "templates")
  : path.resolve(scriptRoot, "../swift-package-preview");
const hostTarget = "QoderCanvasPreviewHost";
const reloadTarget = "QoderCanvasPreviewReload";
const notificationName = "dev.qoder.canvas.swiftui-preview.reload";
const documentDirectoryName = "qoder-swiftui-preview";
const maxHotReloadGenerations = 32;
const previewCacheSchemaVersion = 2;
const buildLockTimeoutMs = 15 * 60_000;
const terminationTimers = new WeakMap();
const templateNames = Object.freeze([
  "CanvasPreviewHost.swift",
  "CanvasPreviewReload.swift",
  "CanvasPreviewRegistry.swift",
]);

class PreviewStoppedError extends Error {}

if (path.resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  void main(process.argv.slice(2)).catch((error) => {
    if (error instanceof PreviewStoppedError) return;
    emit({ type: "preview-failed", error: error instanceof Error ? error.message : String(error) });
    process.exitCode = 1;
  });
}

async function main(argv) {
  const options = parseArguments(argv);
  const packageSwift = path.resolve(options.packageSwift);
  if (path.basename(packageSwift) !== "Package.swift" || !existsSync(packageSwift)) {
    throw new Error(`Swift package manifest not found: ${packageSwift}`);
  }
  const packageRoot = path.dirname(packageSwift);
  const configuration = resolvePackageConfiguration(packageRoot, options.packageTarget, options.filters);
  const cache = await resolvePreviewCacheLayout({
    cacheRoot: options.cacheRoot,
    configuration,
    device: options.device,
    packageRoot,
    packageSwift,
    sessionId: options.sessionId,
  });
  const {
    buildLockPath,
    buildRoot,
    bundleIdentifier,
    cacheIdentity,
    cacheMetadataPath,
    cacheReused,
    projectPath,
    projectRoot,
    sessionLeasePath,
    sourcePackagesRoot,
    sourcesRoot,
  } = cache;
  const logRoot = path.join(buildRoot, "logs");
  const state = {
    appPid: null,
    activeBuild: null,
    abortController: new AbortController(),
    buildLockPath,
    buildRoot,
    bundleIdentifier,
    dataContainer: null,
    device: options.device,
    hotReloadQueued: false,
    hotReloading: false,
    keepAlive: null,
    manifestChanged: false,
    packageRoot,
    projectPath,
    projectRoot,
    reloadCount: 0,
    reloadTimer: null,
    sessionId: options.sessionId,
    sessionLeasePath,
    stopResolve: null,
    stopEmitted: false,
    stopped: false,
    sourcePackagesRoot,
    targetRelativePath: configuration.targetRelativePath,
    watcher: null,
  };

  const stopped = new Promise((resolve) => { state.stopResolve = resolve; });
  const stop = () => stopPreview(state);
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.once(signal, stop);

  try {
    await registerCacheUse(cache);
    emit({
      type: "preview-progress",
      phase: "generating",
      cacheReused,
      message: cacheReused
        ? `Reusing the Swift build cache for ${configuration.moduleName}`
        : `Preparing the Swift build cache for ${configuration.moduleName}`,
    });
    await generateProject({
      bundleIdentifier,
      configuration,
      packageRoot,
      projectPath,
      projectRoot,
      sourcesRoot,
    });
    await ensureBooted(options.device, state);

    emit({ type: "preview-progress", phase: "building-host", message: "Compiling the SwiftUI preview host" });
    await runBuild({
      buildRoot,
      device: options.device,
      logPath: path.join(logRoot, "host.log"),
      projectPath,
      scheme: hostTarget,
      sourcePackagesRoot,
      state,
    });

    const appPath = path.join(buildRoot, "Build/Products/Debug-iphonesimulator", `${hostTarget}.app`);
    if (!existsSync(appPath)) throw new Error(`Preview host build did not produce ${appPath}`);
    emit({ type: "preview-progress", phase: "launching-host", message: "Installing the SwiftUI preview host" });
    await run("xcrun", ["simctl", "terminate", options.device, bundleIdentifier], { allowFailure: true, state });
    await run("xcrun", ["simctl", "install", options.device, appPath], { state });
    state.dataContainer = (await run(
      "xcrun",
      ["simctl", "get_app_container", options.device, bundleIdentifier, "data"],
      { state },
    )).stdout.trim();
    await rm(path.join(state.dataContainer, "Documents", documentDirectoryName), { recursive: true, force: true });
    const launch = await run("xcrun", ["simctl", "launch", options.device, bundleIdentifier], { state });
    state.appPid = parseLaunchPid(launch.stdout, bundleIdentifier);
    const initialStatus = await waitForStatus(state, {
      // A freshly installed Simulator app can spend well over ten seconds in
      // SpringBoard activation while the host Mac is locked or under load.
      attempts: 300,
      matches: (status) => status.phase === "running" && (!state.appPid || status.pid === state.appPid),
      failure: "Preview host launched but did not publish a running status",
    });
    state.appPid = initialStatus.pid;

    emit({
      type: "preview-ready",
      bundleIdentifier,
      module: configuration.moduleName,
      packageProduct: configuration.packageProduct,
      packageTarget: configuration.packageTarget,
      pid: state.appPid,
      projectPath,
      cacheIdentity,
      cacheReused,
      watching: options.watch,
    });

    if (options.watch) startWatching(state);
    else state.keepAlive = setInterval(() => undefined, 60_000);
    await stopped;
  } finally {
    stopPreview(state);
    for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.removeListener(signal, stop);
  }
}

function parseArguments(argv) {
  const options = { packageSwift: undefined, packageTarget: undefined, device: undefined, cacheRoot: undefined, filters: undefined, sessionId: undefined, watch: true };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (!argument.startsWith("-") && !options.packageSwift) options.packageSwift = argument;
    else if (argument === "--device") options.device = argv[++index];
    else if (argument === "--cache-root") options.cacheRoot = argv[++index];
    else if (argument === "--session-id") options.sessionId = argv[++index];
    else if (argument === "--no-watch") options.watch = false;
    else if (argument === "--package-target") options.packageTarget = argv[++index];
    else if (argument === "--preview-filter") {
      options.filters = argv[++index]?.split(",").map((value) => value.trim()).filter(Boolean);
    } else throw new Error(`Unknown Swift package preview argument: ${argument}`);
  }
  if (!options.packageSwift) throw new Error("A Package.swift path is required.");
  if (!options.device) throw new Error("--device <simulator-udid> is required.");
  if (!options.cacheRoot) throw new Error("--cache-root <directory> is required.");
  if (!options.sessionId) throw new Error("--session-id <unique-session-id> is required.");
  return options;
}

function resolvePackageConfiguration(packageRoot, requestedTarget, filters) {
  const dump = runJson("swift", ["package", "dump-package", "--package-path", packageRoot]);
  const description = runJson("swift", ["package", "--package-path", packageRoot, "describe", "--type", "json"]);
  const regularTargets = (dump.targets ?? []).filter((target) => target.type === "regular");
  if (regularTargets.length === 0) throw new Error("Swift package has no regular library target to preview.");

  const describedTargets = new Map((description.targets ?? []).map((target) => [target.name, target]));
  const candidates = regularTargets.map((target) => {
    const described = describedTargets.get(target.name);
    return {
      name: target.name,
      moduleName: described?.c99name,
      previewCount: countPreviewSources(packageRoot, described),
      targetRelativePath: described?.path ?? `Sources/${target.name}`,
    };
  });
  const selected = requestedTarget
    ? candidates.find((target) => target.name === requestedTarget)
    : candidates.filter((target) => target.previewCount > 0)
      .sort((left, right) => right.previewCount - left.previewCount || left.name.localeCompare(right.name))[0]
      ?? (candidates.length === 1 ? candidates[0] : undefined);
  if (!selected) {
    throw new Error(`Cannot choose a Swift package preview target from: ${candidates.map(({ name }) => name).join(", ")}. Set CANVAS_IOS_PACKAGE_TARGET.`);
  }
  if (!selected.moduleName) throw new Error(`Swift package target ${selected.name} has no importable module name.`);

  const products = (dump.products ?? []).filter((product) =>
    product.type?.library != null
      && !product.type.library.includes("dynamic")
      && (product.targets ?? []).includes(selected.name)
  );
  const product = products.find(({ name }) => name === selected.name)
    ?? products.sort((left, right) =>
      (left.targets?.length ?? 0) - (right.targets?.length ?? 0) || left.name.localeCompare(right.name)
    )[0];
  if (!product) throw new Error(`Swift package target ${selected.name} is not exported by a non-dynamic library product.`);

  const iosPlatform = (dump.platforms ?? []).find((platform) => platform.platformName === "ios");
  const requestedDeployment = Number.parseFloat(iosPlatform?.version ?? "17.0");
  return Object.freeze({
    deploymentTarget: String(Math.max(Number.isFinite(requestedDeployment) ? requestedDeployment : 17, 17)),
    filters: filters?.length ? filters : null,
    moduleName: selected.moduleName,
    packageProduct: product.name,
    packageTarget: selected.name,
    targetRelativePath: selected.targetRelativePath,
  });
}

function countPreviewSources(packageRoot, target) {
  if (!target) return 0;
  let count = 0;
  for (const source of target.sources ?? []) {
    const choices = [
      path.resolve(packageRoot, source),
      path.resolve(packageRoot, target.path ?? "", source),
    ];
    const sourcePath = choices.find((candidate) => existsSync(candidate));
    if (!sourcePath || !sourcePath.endsWith(".swift")) continue;
    try {
      const contents = readFileSync(sourcePath, "utf8");
      count += (contents.match(/#Preview\b|\bPreviewProvider\b/gu) ?? []).length;
    } catch {
      // A source can disappear while package metadata is being read; the build reports it later.
    }
  }
  return count;
}

async function generateProject({ bundleIdentifier, configuration, packageRoot, projectPath, projectRoot, sourcesRoot }) {
  await mkdir(projectPath, { recursive: true });
  await mkdir(sourcesRoot, { recursive: true });
  await Promise.all(templateNames.map(async (name) => writeFileIfChanged(
    path.join(sourcesRoot, name),
    await readFile(path.join(templateRoot, name)),
  )));
  await writeFileIfChanged(
    path.join(sourcesRoot, "CanvasPreviewConfiguration.swift"),
    generatedPreviewConfiguration(configuration.moduleName, configuration.filters),
  );
  await writeFileIfChanged(path.join(projectPath, "project.pbxproj"), generatedPreviewProject({
    bundleIdentifier,
    deploymentTarget: configuration.deploymentTarget,
    hostTarget,
    packageProduct: configuration.packageProduct,
    packageRelativePath: path.relative(projectRoot, packageRoot) || ".",
    reloadTarget,
  }));
}

async function ensureBooted(device, state) {
  const listing = runJson("xcrun", ["simctl", "list", "devices", "available", "-j"]);
  const target = Object.values(listing.devices ?? {}).flat().find((candidate) => candidate.udid === device);
  if (!target) throw new Error(`Simulator not found: ${device}`);
  if (target.state !== "Booted") await run("xcrun", ["simctl", "boot", device], { allowFailure: true, state });
  await run("xcrun", ["simctl", "bootstatus", device, "-b"], { timeoutMs: 120_000, state });
}

async function runBuild({ buildRoot, device, logPath, projectPath, scheme, sourcePackagesRoot, state }) {
  if (state.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
  const releaseLock = await acquireBuildLock(state.buildLockPath, state);
  try {
    await run("xcodebuild", [
      "-project", projectPath,
      "-scheme", scheme,
      "-configuration", "Debug",
      "-destination", `id=${device}`,
      "-sdk", "iphonesimulator",
      "-derivedDataPath", buildRoot,
      "-clonedSourcePackagesDirPath", sourcePackagesRoot,
      "CODE_SIGNING_ALLOWED=NO",
      "build",
    ], { cwd: path.dirname(projectPath), timeoutMs: 900_000, outputFile: logPath, state });
  } finally {
    await releaseLock();
  }
}

function startWatching(state) {
  state.watcher = watch(state.packageRoot, { recursive: true }, (_event, fileName) => {
    if (state.stopped || (fileName && !shouldTriggerPreviewReload(state, String(fileName)))) return;
    if (fileName && ["Package.swift", "Package.resolved"].includes(path.basename(String(fileName)))) {
      state.manifestChanged = true;
    }
    clearTimeout(state.reloadTimer);
    state.reloadTimer = setTimeout(() => {
      state.reloadTimer = null;
      void queueReload(state);
    }, 300);
  });
  state.watcher.on("error", (error) => emit({ type: "preview-reload-failed", phase: "watch", error: error.message }));
}

function shouldTriggerPreviewReload(state, fileName) {
  const normalized = fileName.replaceAll("\\", "/").replace(/^\.\//u, "");
  const components = normalized.split("/").filter(Boolean);
  const ignoredDirectories = new Set([
    ".build", ".git", ".qoder", ".swiftpm", "deriveddata", "dist", "node_modules", "out", "xcuserdata",
  ]);
  if (components.some((component) => ignoredDirectories.has(component.toLowerCase()))) return false;
  const baseName = components.at(-1)?.toLowerCase() ?? "";
  if (!baseName || baseName === ".ds_store" || [".swp", ".swo", ".tmp", ".xcuserstate", "~"].some((suffix) => baseName.endsWith(suffix))) {
    return false;
  }
  if (baseName === "package.swift" || baseName === "package.resolved") return true;
  const targetRoot = path.isAbsolute(state.targetRelativePath)
    ? path.relative(state.packageRoot, state.targetRelativePath)
    : state.targetRelativePath;
  const normalizedTarget = targetRoot.replaceAll("\\", "/").replace(/^\.\//u, "").replace(/\/$/u, "");
  return normalized === normalizedTarget || normalized.startsWith(`${normalizedTarget}/`);
}

async function queueReload(state) {
  if (state.stopped) return;
  if (state.hotReloading) {
    state.hotReloadQueued = true;
    return;
  }
  state.hotReloading = true;
  do {
    state.hotReloadQueued = false;
    await reload(state).catch((error) => {
      emit({ type: "preview-reload-failed", phase: "reload", error: error instanceof Error ? error.message : String(error) });
    });
  } while (state.hotReloadQueued && !state.stopped);
  state.hotReloading = false;
}

async function reload(state) {
  if (state.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
  if (state.reloadCount >= maxHotReloadGenerations) {
    throw new Error(`SwiftUI Preview reached ${maxHotReloadGenerations} hot reload generations. Reopen the Canvas to reset the preview host safely.`);
  }
  if (state.manifestChanged) {
    state.manifestChanged = false;
    throw new Error("Package.swift or Package.resolved changed. Reopen the Canvas to regenerate the preview project safely.");
  }
  const startedAt = Date.now();
  const token = randomUUID();
  emit({ type: "preview-reload", phase: "building", token, message: "Compiling SwiftUI preview changes" });
  await runBuild({
    buildRoot: state.buildRoot,
    device: state.device,
    logPath: path.join(state.buildRoot, "logs", "reload.log"),
    projectPath: state.projectPath,
    scheme: reloadTarget,
    sourcePackagesRoot: state.sourcePackagesRoot,
    state,
  });
  const dylib = path.join(state.buildRoot, "Build/Products/Debug-iphonesimulator", `lib${reloadTarget}.dylib`);
  if (!existsSync(dylib)) throw new Error(`Preview reload build did not produce ${dylib}`);
  const reloadDirectory = path.join(state.dataContainer, "Documents", documentDirectoryName);
  await mkdir(reloadDirectory, { recursive: true });
  const injectedDylib = path.join(reloadDirectory, `lib${reloadTarget}-${token}.dylib`);
  await copyFile(dylib, injectedDylib);
  await writeFile(path.join(reloadDirectory, "reload.json"), JSON.stringify({ token, dylibPath: injectedDylib }));
  emit({ type: "preview-reload", phase: "injecting", token, message: "Injecting the preview dylib into the running host" });
  let status;
  try {
    await run("xcrun", ["simctl", "spawn", state.device, "notifyutil", "-p", notificationName], { state });
    status = await waitForStatus(state, {
      attempts: 300,
      matches: (candidate) => candidate.phase === "reloaded" && candidate.token === token,
      statusError: (candidate) => candidate.phase === "error" && candidate.token === token ? candidate.error : undefined,
      failure: "Timed out waiting for the preview host to load the new dylib",
    });
  } finally {
    await rm(injectedDylib, { force: true });
  }
  if (status.pid !== state.appPid) throw new Error(`SwiftUI hot reload changed host PID from ${state.appPid} to ${status.pid}`);
  state.reloadCount += 1;
  emit({ type: "preview-reloaded", token, pid: status.pid, durationMs: Date.now() - startedAt });
}

async function waitForStatus(state, options) {
  const statusPath = path.join(state.dataContainer, "Documents", documentDirectoryName, "status.json");
  for (let attempt = 0; attempt < options.attempts; attempt += 1) {
    if (state.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
    await delay(100);
    let status;
    try { status = JSON.parse(await readFile(statusPath, "utf8")); } catch { continue; }
    const statusError = options.statusError?.(status);
    if (statusError) throw new Error(`Preview host rejected the reload: ${statusError}`);
    if (options.matches(status)) return status;
  }
  throw new Error(options.failure);
}

function parseLaunchPid(stdout, bundleIdentifier) {
  const escaped = bundleIdentifier.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = stdout.match(new RegExp(`${escaped}:\\s*(\\d+)`));
  return match ? Number(match[1]) : null;
}

function runJson(command, args) {
  try {
    return JSON.parse(execFileSync(command, args, { encoding: "utf8", maxBuffer: 20 * 1024 * 1024 }));
  } catch (error) {
    throw new Error(`${command} ${args.join(" ")} failed: ${error.stderr || error.stdout || error.message}`);
  }
}

async function run(command, args, options = {}) {
  if (options.outputFile) return runToFile(command, args, options);
  if (options.state?.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
  try {
    const result = await execFileAsync(command, args, {
      cwd: options.cwd,
      encoding: "utf8",
      maxBuffer: 20 * 1024 * 1024,
      timeout: options.timeoutMs ?? 30_000,
      ...(options.state ? { signal: options.state.abortController.signal } : {}),
    });
    return { stdout: result.stdout ?? "", stderr: result.stderr ?? "" };
  } catch (error) {
    if (options.state?.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
    if (options.allowFailure) return { stdout: error.stdout ?? "", stderr: error.stderr ?? "" };
    throw new Error(`${command} ${args.join(" ")} failed: ${error.stderr || error.stdout || error.message}`);
  }
}

async function runToFile(command, args, options) {
  if (options.state?.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
  await mkdir(path.dirname(options.outputFile), { recursive: true });
  const output = await open(options.outputFile, "w");
  let result;
  try {
    result = await new Promise((resolve, reject) => {
      const child = spawn(command, args, {
        cwd: options.cwd,
        stdio: ["ignore", output.fd, output.fd],
      });
      if (options.state) options.state.activeBuild = child;
      const timeout = setTimeout(() => terminateChild(child), options.timeoutMs ?? 30_000);
      child.once("error", reject);
      child.once("close", (code, signal) => {
        clearTimeout(timeout);
        clearTerminationTimer(child);
        if (options.state?.activeBuild === child) options.state.activeBuild = null;
        resolve({ code, signal });
      });
    });
  } finally {
    await output.close();
  }
  if (options.state?.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
  if (result.code !== 0) {
    throw new Error(`${command} ${args.join(" ")} ${result.signal ? `ended by ${result.signal}` : `exited ${result.code}`}; log: ${options.outputFile}`);
  }
  return { stdout: "", stderr: "" };
}

function stopPreview(state) {
  if (state.stopped) return;
  state.stopped = true;
  if (!state.stopEmitted) {
    state.stopEmitted = true;
    emit({ type: "preview-stopped" });
  }
  clearTimeout(state.reloadTimer);
  state.reloadTimer = null;
  clearInterval(state.keepAlive);
  state.keepAlive = null;
  state.hotReloadQueued = false;
  state.watcher?.close();
  state.watcher = null;
  if (state.sessionLeasePath) void unlink(state.sessionLeasePath).catch(() => undefined);
  state.abortController.abort(new PreviewStoppedError("Swift package preview stopped."));
  if (state.activeBuild) terminateChild(state.activeBuild);
  state.stopResolve?.();
}

function terminateChild(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  if (terminationTimers.has(child)) return;
  const timer = setTimeout(() => {
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
    terminationTimers.delete(child);
  }, 2_000);
  timer.unref();
  terminationTimers.set(child, timer);
}

function clearTerminationTimer(child) {
  const timer = terminationTimers.get(child);
  if (timer) clearTimeout(timer);
  terminationTimers.delete(child);
}

function emit(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function resolvePreviewCacheLayout({ cacheRoot, configuration, device, packageRoot, packageSwift, sessionId, toolchain: providedToolchain }) {
  const resolvedCacheRoot = path.resolve(cacheRoot);
  const packageIdentity = digestJson({
    packageSwift,
    module: configuration.moduleName,
    packageProduct: configuration.packageProduct,
    packageTarget: configuration.packageTarget,
    filters: configuration.filters,
  }).slice(0, 16);
  const [manifestDigest, generatorDigest] = await Promise.all([
    digestFiles([
      packageSwift,
      path.join(packageRoot, "Package.resolved"),
    ], { allowMissing: true }),
    digestFiles([
      path.join(scriptRoot, "lib/swift-package-preview-project.mjs"),
      ...templateNames.map((name) => path.join(templateRoot, name)),
    ]),
  ]);
  const toolchain = providedToolchain ?? readToolchainFingerprint();
  const cacheIdentity = digestJson({
    schemaVersion: previewCacheSchemaVersion,
    packageIdentity,
    manifestDigest,
    generatorDigest,
    deploymentTarget: configuration.deploymentTarget,
    toolchain,
  }).slice(0, 24);
  const sessionIdentity = digestJson({ device, sessionId, pid: process.pid }).slice(0, 16);
  const deviceIdentity = digestJson({ device }).slice(0, 16);
  const cacheEntryRoot = path.join(resolvedCacheRoot, "packages", packageIdentity, "entries", cacheIdentity);
  const projectRoot = path.join(cacheEntryRoot, "GeneratedPreviewHost");
  const projectPath = path.join(projectRoot, `${hostTarget}.xcodeproj`);
  const buildRoot = path.join(cacheEntryRoot, "DerivedData", deviceIdentity);
  const cacheMetadataPath = path.join(cacheEntryRoot, "cache-metadata.json");
  return Object.freeze({
    buildLockPath: path.join(buildRoot, ".build.lock"),
    buildRoot,
    bundleIdentifier: `dev.qoder.canvas.preview.${cacheIdentity}`,
    cacheEntryRoot,
    cacheIdentity,
    cacheMetadataPath,
    cacheReused: existsSync(cacheMetadataPath) && existsSync(projectPath) && existsSync(path.join(buildRoot, "Build")),
    configuration,
    device,
    generatorDigest,
    manifestDigest,
    packageIdentity,
    packageSwift,
    projectPath,
    projectRoot,
    sessionId,
    sessionLeasePath: path.join(cacheEntryRoot, "sessions", `${sessionIdentity}.json`),
    sourcePackagesRoot: path.join(cacheEntryRoot, "SourcePackages"),
    sourcesRoot: path.join(projectRoot, "Sources"),
    toolchain,
  });
}

async function registerCacheUse(cache) {
  const now = new Date().toISOString();
  const existing = await readJsonIfExists(cache.cacheMetadataPath);
  await writeJsonAtomic(cache.cacheMetadataPath, {
    schemaVersion: 1,
    kind: "swiftui-package-preview",
    cacheIdentity: cache.cacheIdentity,
    packageIdentity: cache.packageIdentity,
    packageSwift: cache.packageSwift,
    packageTarget: cache.configuration.packageTarget,
    packageProduct: cache.configuration.packageProduct,
    module: cache.configuration.moduleName,
    filters: cache.configuration.filters,
    deploymentTarget: cache.configuration.deploymentTarget,
    manifestDigest: cache.manifestDigest,
    generatorDigest: cache.generatorDigest,
    toolchain: cache.toolchain,
    createdAt: typeof existing?.createdAt === "string" ? existing.createdAt : now,
    lastUsedAt: now,
  });
  await writeJsonAtomic(cache.sessionLeasePath, {
    schemaVersion: 1,
    pid: process.pid,
    sessionId: cache.sessionId,
    device: cache.device,
    cacheIdentity: cache.cacheIdentity,
    startedAt: now,
  });
}

async function acquireBuildLock(lockPath, state) {
  const token = randomUUID();
  const deadline = Date.now() + buildLockTimeoutMs;
  await mkdir(path.dirname(lockPath), { recursive: true });
  while (Date.now() < deadline) {
    if (state.stopped) throw new PreviewStoppedError("Swift package preview stopped.");
    try {
      const handle = await open(lockPath, "wx", 0o600);
      let writeError;
      try {
        await handle.writeFile(`${JSON.stringify({ pid: process.pid, sessionId: state.sessionId, token, createdAt: new Date().toISOString() })}\n`);
      } catch (error) {
        writeError = error;
      } finally {
        await handle.close();
      }
      if (writeError) {
        await unlink(lockPath).catch(() => undefined);
        throw writeError;
      }
      return async () => {
        const current = await readJsonIfExists(lockPath);
        if (current?.pid === process.pid && current.token === token) await unlink(lockPath).catch(() => undefined);
      };
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      const owner = await readJsonIfExists(lockPath);
      if (!processIsAlive(owner?.pid)) {
        await unlink(lockPath).catch((unlinkError) => {
          if (unlinkError?.code !== "ENOENT") throw unlinkError;
        });
        continue;
      }
      await delay(250);
    }
  }
  throw new Error(`Timed out waiting for the Swift build cache lock: ${lockPath}`);
}

async function writeFileIfChanged(filePath, contents) {
  const next = Buffer.isBuffer(contents) ? contents : Buffer.from(contents);
  try {
    const current = await readFile(filePath);
    if (current.equals(next)) return false;
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
  await mkdir(path.dirname(filePath), { recursive: true });
  const tempPath = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
  await writeFile(tempPath, next);
  await rename(tempPath, filePath);
  return true;
}

async function writeJsonAtomic(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  const tempPath = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
  await writeFile(tempPath, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  await rename(tempPath, filePath);
}

async function readJsonIfExists(filePath) {
  try {
    const value = JSON.parse(await readFile(filePath, "utf8"));
    return value && typeof value === "object" && !Array.isArray(value) ? value : undefined;
  } catch (error) {
    if (error?.code === "ENOENT" || error instanceof SyntaxError) return undefined;
    throw error;
  }
}

async function digestFiles(filePaths, options = {}) {
  const hash = createHash("sha256");
  for (const filePath of [...filePaths].sort()) {
    hash.update(path.basename(filePath));
    hash.update("\0");
    try {
      hash.update(await readFile(filePath));
    } catch (error) {
      if (!options.allowMissing || error?.code !== "ENOENT") throw error;
      hash.update("<missing>");
    }
    hash.update("\0");
  }
  return hash.digest("hex");
}

function readToolchainFingerprint() {
  return Object.freeze({
    architecture: process.arch,
    simulatorSdkBuild: execFileSync("xcrun", ["--sdk", "iphonesimulator", "--show-sdk-build-version"], { encoding: "utf8" }).trim(),
    xcodeVersion: execFileSync("xcodebuild", ["-version"], { encoding: "utf8" }).trim(),
  });
}

function digestJson(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function processIsAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

export { parseArguments, resolvePreviewCacheLayout, shouldTriggerPreviewReload, writeFileIfChanged };
