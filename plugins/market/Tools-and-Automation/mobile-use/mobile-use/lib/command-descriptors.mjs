const stringOption = (description, options = {}) => Object.freeze({ type: "string", description, ...options });
const numberOption = (description, options = {}) => Object.freeze({ type: "number", description, ...options });
const booleanOption = (description, options = {}) => Object.freeze({ type: "boolean", description, ...options });
const jsonObjectOption = (parameter, description, options = {}) => Object.freeze({
  type: "json-object",
  parameter,
  description,
  ...options,
});

const sessionOptions = Object.freeze({
  surface_id: stringOption("Live Canvas surface identifier.", { required: true }),
  session_id: stringOption("Live device session identifier.", { required: true }),
});
const targetOptions = Object.freeze({
  surface_id: stringOption("Live Canvas surface identifier.", { required: true }),
  target_id: stringOption("Published device target identifier.", { required: true }),
});
const descriptor = (category, summary, options = {}, metadata = {}) => Object.freeze({
  category,
  summary,
  options: Object.freeze(options),
  ...metadata,
});

export const CLI_COMMAND_DESCRIPTORS = Object.freeze({
  commands: descriptor("introspection", "List the available CLI commands."),
  describe: descriptor("introspection", "Describe one command's Agent-facing input contract.", {}, {
    positionals: Object.freeze([
      Object.freeze({ parameter: "command", type: "command", description: "Command to describe.", required: true }),
    ]),
  }),
  inventory: descriptor("discovery", "Summarize targets and sessions published by live Canvas surfaces."),
  doctor: descriptor("discovery", "Diagnose live broker reachability without exposing broker credentials."),
  list_targets: descriptor("lifecycle", "List targets published by live Canvas surfaces."),
  start_session: descriptor("lifecycle", "Start one exact published target.", targetOptions),
  stop_session: descriptor("lifecycle", "Stop one exact live session.", sessionOptions),
  list_sessions: descriptor("lifecycle", "List live device sessions."),
  observe: descriptor("semantic", "Capture a current accessibility observation.", {
    ...sessionOptions,
    mode: stringOption("Observation detail level.", { values: Object.freeze(["interactive", "full"]) }),
  }),
  tap: descriptor("semantic", "Resolve one selector on a fresh snapshot and tap it.", {
    ...sessionOptions,
    selector_json: jsonObjectOption("selector", "Unique native selector.", { required: true }),
  }),
  long_press: descriptor("semantic", "Resolve one selector on a fresh snapshot and long-press it.", {
    ...sessionOptions,
    selector_json: jsonObjectOption("selector", "Unique native selector.", { required: true }),
    duration_ms: numberOption("Long-press duration in milliseconds.", { integer: true, minimum: 1, maximum: 60_000 }),
  }),
  act: descriptor("semantic", "Dispatch a revision-bound low-level action.", {
    ...sessionOptions,
    ui_revision: numberOption("Positive UI revision returned by observe.", { required: true, integer: true, minimum: 1 }),
    action_json: jsonObjectOption("action", "Revision-bound action payload.", { required: true }),
  }),
  wait: descriptor("semantic", "Wait for a bounded semantic UI condition.", {
    ...sessionOptions,
    condition_json: jsonObjectOption("condition", "Wait condition payload.", { required: true }),
    timeout_ms: numberOption("Wait timeout in milliseconds.", { integer: true, minimum: 1, maximum: 20 * 60_000 }),
    poll_interval_ms: numberOption("Polling interval in milliseconds.", { integer: true, minimum: 1, maximum: 60_000 }),
  }),
  assert: descriptor("semantic", "Assert that one semantic selector is present or absent.", {
    ...sessionOptions,
    selector_json: jsonObjectOption("selector", "Unique native selector.", { required: true }),
    state: stringOption("Expected selector state.", { values: Object.freeze(["present", "absent"]) }),
  }),
  run_plan: descriptor("workflow", "Execute one bounded, versioned workflow against one exact session.", {
    plan_json: jsonObjectOption("plan", "Versioned workflow plan.", { required: true }),
  }, {
    inputContract: Object.freeze({
      schemaVersion: 1,
      session: Object.freeze({
        required: "exact surfaceId/sessionId or platform selector",
        policy: Object.freeze(["existing", "reuse-or-start"]),
        selectors: Object.freeze(["surfaceId", "sessionId", "targetId", "targetName", "runtimeKind", "platform"]),
      }),
      keepSession: "boolean; defaults to false for a plan-started session",
      evidence: Object.freeze({
        screenshots: Object.freeze(["off", "on-failure"]),
        recording: Object.freeze(["off", "native"]),
      }),
      steps: Object.freeze({
        minimum: 1,
        maximum: 64,
        kinds: Object.freeze(["observe", "tap", "long_press", "wait", "wait_project_build", "assert", "launch_app", "capture_screenshot", "run_native_test"]),
        waitProjectBuild: Object.freeze({
          afterCycle: "required non-negative integer from project-build-status",
          timeoutMs: "optional integer from 1 through 1200000",
        }),
      }),
    }),
  }),
  project_build_status: descriptor("operation", "Read the latest project live-build cycle owned by this session.", sessionOptions, {
    requiredCapability: "device.project.live-build.status",
  }),
  wait_project_build: descriptor("operation", "Wait for a newer terminal project live-build cycle.", {
    ...sessionOptions,
    after_cycle: numberOption("Last observed build cycle; the result must have a greater cycle.", { required: true, integer: true, minimum: 0, maximum: Number.MAX_SAFE_INTEGER }),
    timeout_ms: numberOption("Build wait timeout in milliseconds.", { integer: true, minimum: 1, maximum: 20 * 60_000 }),
  }, {
    requiredCapability: "device.project.live-build.wait",
  }),
  restart_target: descriptor("operation", "Restart one exact target when advertised.", targetOptions, {
    requiredCapability: "device.target.restart",
  }),
  manage_app: descriptor("operation", "List, install, launch, terminate, or uninstall an app.", {
    ...sessionOptions,
    action: stringOption("Application action.", { required: true, values: Object.freeze(["list", "install", "launch", "terminate", "uninstall"]) }),
    path: stringOption("Installable artifact path; required for install."),
    bundle_id: stringOption("Application bundle/package identifier; required for launch, terminate, or uninstall."),
    confirm: booleanOption("Explicit destructive confirmation; required for uninstall."),
  }, {
    capabilitiesByAction: Object.freeze({
      list: "device.app.list",
      install: "device.app.install",
      launch: "device.app.launch",
      terminate: "device.app.terminate",
      uninstall: "device.app.uninstall",
    }),
    destructiveWhen: Object.freeze({ action: "uninstall", confirm: true }),
  }),
  read_logs: descriptor("operation", "Read bounded device logs when advertised.", {
    ...sessionOptions,
    bundle_id: stringOption("Optional application bundle/package filter."),
    seconds: numberOption("Log lookback in seconds.", { integer: true, minimum: 1, maximum: 3_600 }),
    limit: numberOption("Maximum returned log records.", { integer: true, minimum: 1, maximum: 5_000 }),
  }, { requiredCapability: "device.logs.read" }),
  run_native_test: descriptor("operation", "Run one exact project-owned native test selector.", {
    ...sessionOptions,
    selector: stringOption("Exact platform-native test selector.", { required: true }),
    timeout_ms: numberOption("Native runner timeout in milliseconds.", { integer: true, minimum: 1_000, maximum: 20 * 60_000 }),
    test_target: stringOption("Optional platform test target override."),
    test_module: stringOption("Optional HarmonyOS test module override."),
    test_bundle_id: stringOption("Optional HarmonyOS test bundle override."),
    runner: stringOption("Optional repository-qualified runner override."),
  }, { requiredCapability: "device.test.run" }),
  capture_screenshot: descriptor("operation", "Capture a durable native screenshot artifact.", sessionOptions, {
    requiredCapability: "device.frame.screenshot",
  }),
  record_screen: descriptor("operation", "Start, inspect, or stop native screen recording.", {
    ...sessionOptions,
    action: stringOption("Recording action.", { required: true, values: Object.freeze(["start", "status", "stop"]) }),
  }, { requiredCapability: "device.recording.native" }),
  swift_cache_status: descriptor("cache", "Inspect the local Swift Package preview cache.", {
    cache_root: stringOption("Optional absolute cache root override."),
  }, { host: "darwin" }),
  swift_cache_prune: descriptor("cache", "Plan or apply bounded Swift Package preview cache pruning.", {
    cache_root: stringOption("Optional absolute cache root override."),
    max_age_days: numberOption("Maximum inactive cache age in days.", { integer: true, minimum: 1, maximum: 3_650 }),
    max_size_mb: numberOption("Maximum retained cache size in MiB.", { integer: true, minimum: 128, maximum: 1024 * 1024 }),
    include_legacy: booleanOption("Include recognized legacy cache directories."),
    apply: booleanOption("Apply the prune; omission is a dry run."),
  }, { host: "darwin" }),
  swift_cache_clean: descriptor("cache", "Remove one exact inactive Swift Package preview cache.", {
    cache_root: stringOption("Optional absolute cache root override."),
    package_swift: stringOption("Absolute Package.swift path identifying the cache."),
    cache_identity: stringOption("Exact cache identity."),
    confirm: booleanOption("Explicit cleanup confirmation.", { required: true }),
  }, {
    host: "darwin",
    destructiveWhen: Object.freeze({ confirm: true }),
  }),
});

export const CLI_COMMANDS = Object.freeze(Object.keys(CLI_COMMAND_DESCRIPTORS));

export function normalizeCommandName(value) {
  return typeof value === "string" ? value.replaceAll("-", "_") : value;
}

export function canonicalCommandName(value) {
  return value.replaceAll("_", "-");
}

export function commandDescriptor(command) {
  return CLI_COMMAND_DESCRIPTORS[normalizeCommandName(command)];
}

export function publicCommandCatalog() {
  return Object.freeze(CLI_COMMANDS.map((command) => Object.freeze({
    command: canonicalCommandName(command),
    category: CLI_COMMAND_DESCRIPTORS[command].category,
    summary: CLI_COMMAND_DESCRIPTORS[command].summary,
  })));
}

export function publicCommandDescriptor(command) {
  const normalized = normalizeCommandName(command);
  const source = CLI_COMMAND_DESCRIPTORS[normalized];
  if (!source) return undefined;
  return Object.freeze({
    schemaVersion: 1,
    command: canonicalCommandName(normalized),
    category: source.category,
    summary: source.summary,
    ...(source.host ? { host: source.host } : {}),
    ...(source.requiredCapability ? { requiredCapability: source.requiredCapability } : {}),
    ...(source.capabilitiesByAction ? { capabilitiesByAction: source.capabilitiesByAction } : {}),
    ...(source.destructiveWhen ? { destructiveWhen: source.destructiveWhen } : {}),
    ...(source.inputContract ? { inputContract: source.inputContract } : {}),
    ...(source.positionals ? { positionals: source.positionals.map(publicPositional) } : {}),
    options: Object.freeze([
      ...Object.entries(source.options).map(([name, option]) => publicOption(name, option)),
      ...(Object.keys(source.options).length > 0
        ? [Object.freeze({ name: "--params-json", parameter: "params", type: "json-object", required: false, description: "Complete command parameter object; conflicting duplicate parameters are rejected." })]
        : []),
      Object.freeze({ name: "--json", parameter: "json", type: "boolean", required: false, description: "Emit the versioned JSON envelope." }),
      Object.freeze({ name: "--pretty", parameter: "pretty", type: "boolean", required: false, description: "Pretty-print the JSON envelope." }),
    ]),
  });
}

function publicOption(name, option) {
  return Object.freeze({
    name: `--${canonicalCommandName(name)}`,
    parameter: option.parameter ?? name,
    type: option.type,
    required: option.required === true,
    description: option.description,
    ...(option.values ? { values: option.values } : {}),
    ...(option.integer ? { integer: true } : {}),
    ...(option.minimum === undefined ? {} : { minimum: option.minimum }),
    ...(option.maximum === undefined ? {} : { maximum: option.maximum }),
  });
}

function publicPositional(positional) {
  return Object.freeze({
    parameter: positional.parameter,
    type: positional.type,
    required: positional.required === true,
    description: positional.description,
  });
}
