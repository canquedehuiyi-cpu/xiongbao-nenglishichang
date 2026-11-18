import {
  invokePhoneUse,
  invokeSessionOperation,
  invokeTargetOperation,
  inspectLiveBrokers,
  listLiveSessions,
  listLiveTargets,
  startPhoneUseSession,
  stopPhoneUseSession,
} from "./broker-client.mjs";
import { CLI_COMMAND_DESCRIPTORS } from "./command-descriptors.mjs";
import {
  SESSION_OPERATION_COMMANDS,
  TARGET_OPERATION_COMMANDS,
  operationAndInput,
  sessionSelection,
  targetAndInput,
  targetSelection,
} from "./phone-arguments.mjs";
import { executePhoneInventory, executePhonePlan } from "./phone-plan.mjs";

export const CORE_PHONE_COMMANDS = Object.freeze(Object.entries(CLI_COMMAND_DESCRIPTORS)
  .filter(([, descriptor]) => !["cache", "introspection", "operation"].includes(descriptor.category))
  .map(([command]) => command));

export const OPERATIONAL_PHONE_COMMANDS = Object.freeze(Object.entries(CLI_COMMAND_DESCRIPTORS)
  .filter(([, descriptor]) => descriptor.category === "operation")
  .map(([command]) => command));

export const PHONE_COMMANDS = Object.freeze([
  ...CORE_PHONE_COMMANDS,
  ...OPERATIONAL_PHONE_COMMANDS,
]);

export async function executePhoneCommand(command, args = {}, dependencies = {}) {
  if (!PHONE_COMMANDS.includes(command)) {
    throw commandError("phone.command.unknown", `Unknown Mobile Use command: ${command}`);
  }

  const listSessions = dependencies.listLiveSessions ?? listLiveSessions;
  const listTargets = dependencies.listLiveTargets ?? listLiveTargets;
  const startSession = dependencies.startPhoneUseSession ?? startPhoneUseSession;
  const stopSession = dependencies.stopPhoneUseSession ?? stopPhoneUseSession;
  const invoke = dependencies.invokePhoneUse ?? invokePhoneUse;
  const invokeSession = dependencies.invokeSessionOperation ?? invokeSessionOperation;
  const invokeTarget = dependencies.invokeTargetOperation ?? invokeTargetOperation;
  const inspectBrokers = dependencies.inspectLiveBrokers ?? inspectLiveBrokers;

  const invokeCommand = (nextCommand, nextArgs = {}) => executePhoneCommand(nextCommand, nextArgs, dependencies);

  if (command === "inventory") return executePhoneInventory(invokeCommand);
  if (command === "doctor") return inspectBrokers();
  if (command === "run_plan") return executePhonePlan(args.plan, invokeCommand);

  if (command === "list_targets") return listTargets();
  if (command === "start_session") {
    const target = targetSelection(args);
    return startSession(target.surfaceId, target.targetId);
  }
  if (command === "stop_session") {
    const target = sessionSelection(args);
    return stopSession(target.surfaceId, target.sessionId);
  }
  if (command === "list_sessions") return listSessions();
  if (TARGET_OPERATION_COMMANDS[command]) {
    const target = operationAndInput(command, args);
    return invokeTarget(target.surfaceId, target.targetId, target.operation, target.capability, target.input);
  }
  if (SESSION_OPERATION_COMMANDS[command]) {
    const target = operationAndInput(command, args);
    const receipt = await invokeSession(target.surfaceId, target.sessionId, target.operation, target.capability, target.input);
    if (command === "project_build_status" || command === "wait_project_build") {
      requireProjectBuildReceipt(receipt, command === "wait_project_build");
    }
    return receipt;
  }

  const target = targetAndInput(command, args);
  if (command === "tap" || command === "long_press") {
    return summarizePerformResult(await invoke(target.surfaceId, target.sessionId, "perform", target.input));
  }
  return invoke(target.surfaceId, target.sessionId, command, target.input);
}

function requireProjectBuildReceipt(receipt, requireSucceededBuild) {
  if (receipt?.status !== "succeeded") {
    const error = commandError(
      receipt?.error?.code ?? "phone.project-build.wait-failed",
      receipt?.error?.message ?? "Project live-build wait did not succeed.",
    );
    if (receipt?.error?.details && typeof receipt.error.details === "object") error.details = receipt.error.details;
    throw error;
  }
  const output = receipt?.output;
  if (!output || typeof output !== "object" || !Number.isSafeInteger(output.cycle)) {
    throw commandError("phone.project-build.invalid-result", "Project live-build operation returned an invalid result.");
  }
  if (!requireSucceededBuild && ["failed", "pending", "running", "succeeded"].includes(output.status)) return;
  if (requireSucceededBuild && output.status === "succeeded") return;
  if (output.status === "failed") {
    const error = commandError(
      "phone.project-build.failed",
      output.error ?? `Project live-build cycle ${output.cycle} failed.`,
    );
    error.details = Object.freeze({ liveBuild: output });
    throw error;
  }
  throw commandError("phone.project-build.invalid-result", "Project live-build wait did not return a newer terminal cycle.");
}

function summarizePerformResult(value) {
  const observation = value?.observation;
  const element = value?.element;
  const receipt = value?.receipt;
  return Object.freeze({
    uiChanged: value?.uiChanged === true,
    ...(element && typeof element === "object" ? { element: Object.freeze({
      ...(typeof element.ref === "string" ? { ref: element.ref } : {}),
      ...(typeof element.identifier === "string" ? { identifier: element.identifier } : {}),
      ...(typeof element.label === "string" ? { label: element.label } : {}),
      ...(typeof element.role === "string" ? { role: element.role } : {}),
      ...(typeof element.type === "string" ? { type: element.type } : {}),
    }) } : {}),
    observation: Object.freeze({
      uiRevision: observation?.uiRevision,
      snapshotId: observation?.snapshotId,
      platform: observation?.platform,
      source: observation?.source,
      screen: observation?.screen,
      truncated: observation?.truncated === true,
      elementCount: Array.isArray(observation?.elements) ? observation.elements.length : 0,
    }),
    ...(receipt && typeof receipt === "object" ? { receipt: Object.freeze({
      operationId: receipt.operationId,
      operation: receipt.operation,
      status: receipt.status,
      ...(receipt.output === undefined ? {} : { output: receipt.output }),
    }) } : {}),
  });
}

function commandError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}
