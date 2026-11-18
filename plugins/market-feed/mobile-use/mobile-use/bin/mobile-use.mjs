#!/usr/bin/env node

import { readFileSync, realpathSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  CLI_COMMANDS,
  canonicalCommandName,
  commandDescriptor,
  normalizeCommandName,
  publicCommandCatalog,
  publicCommandDescriptor,
} from "../lib/command-descriptors.mjs";
import { executePhoneCommand } from "../lib/phone-command.mjs";
import { SWIFT_CACHE_COMMANDS, executeSwiftCacheCommand } from "../lib/swift-cache.mjs";

const SCHEMA_VERSION = 1;
const CLI_VERSION = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")).version;

export async function runCli(argv, options = {}) {
  const stdout = options.stdout ?? process.stdout;
  const stderr = options.stderr ?? process.stderr;
  let command;
  try {
    const parsed = parseArguments(argv);
    command = parsed.command;
    if (parsed.help) {
      stdout.write(`${helpText(command)}\n`);
      return 0;
    }
    if (parsed.version) {
      stdout.write(`${CLI_VERSION}\n`);
      return 0;
    }
    if (SWIFT_CACHE_COMMANDS.includes(command) && (options.platform ?? process.platform) !== "darwin") {
      throw cliError("swift.cache.host.unsupported", "Swift preview cache commands are supported only on macOS hosts that can run iOS previews.");
    }
    const data = command === "commands"
      ? Object.freeze({ schemaVersion: 1, commands: publicCommandCatalog() })
      : command === "describe"
        ? publicCommandDescriptor(parsed.params.command)
        : SWIFT_CACHE_COMMANDS.includes(command)
          ? await executeSwiftCacheCommand(command, parsed.params)
          : await executePhoneCommand(command, parsed.params, options.dependencies);
    const envelope = { schemaVersion: SCHEMA_VERSION, ok: true, command, data };
    stdout.write(`${JSON.stringify(envelope, null, parsed.pretty ? 2 : 0)}\n`);
    return 0;
  } catch (error) {
    const normalized = normalizeError(error);
    const envelope = {
      schemaVersion: SCHEMA_VERSION,
      ok: false,
      ...(command ? { command } : {}),
      error: normalized,
    };
    stderr.write(`${JSON.stringify(envelope)}\n`);
    return exitCodeFor(normalized.code);
  }
}

export function parseArguments(argv) {
  const tokens = [...argv];
  if (tokens.length === 0 || tokens[0] === "--help" || tokens[0] === "-h") {
    return { help: true, params: {}, pretty: true };
  }
  if (tokens[0] === "help") {
    tokens.shift();
    if (tokens.length === 0) return { help: true, params: {}, pretty: true };
    if (tokens.length > 1) throw cliError("phone.cli.argument", "help accepts at most one command.");
    const command = requireCommand(tokens[0]);
    return { command, help: true, params: {}, pretty: true };
  }
  if (tokens[0] === "--version" || tokens[0] === "-v") {
    return { version: true, params: {}, pretty: false };
  }

  const rawCommand = tokens.shift();
  const command = requireCommand(rawCommand);
  const descriptor = commandDescriptor(command);

  const params = {};
  const parameterSources = new Map();
  let pretty = false;
  let help = false;
  let positionalIndex = 0;
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token === "--json") continue;
    if (token === "--pretty") {
      pretty = true;
      continue;
    }
    if (token === "--help" || token === "-h") {
      help = true;
      continue;
    }
    if (!token.startsWith("--")) {
      const positional = descriptor.positionals?.[positionalIndex];
      if (!positional) throw cliError("phone.cli.argument", `Unexpected argument: ${token}`);
      setParameter(params, parameterSources, positional.parameter, parsePositional(token, positional), `positional ${positional.parameter}`);
      positionalIndex += 1;
      continue;
    }

    const separator = token.indexOf("=");
    const rawName = separator === -1 ? token.slice(2) : token.slice(2, separator);
    const name = normalizeCommandName(rawName);
    let value = separator === -1 ? undefined : token.slice(separator + 1);
    if (name === "params_json") {
      if (value === undefined) {
        index += 1;
        value = tokens[index];
      }
      if (value === undefined || value.startsWith("--")) throw cliError("phone.cli.argument", `--${rawName} requires a value.`);
      const parsed = parseJson(value, rawName);
      if (!isRecord(parsed)) throw cliError("phone.cli.argument", `--${rawName} must contain a JSON object.`);
      for (const [parameter, parameterValue] of Object.entries(parsed)) {
        validateLogicalParameter(descriptor, parameter, parameterValue, rawName);
        setParameter(params, parameterSources, parameter, parameterValue, `--${rawName}`);
      }
      continue;
    }
    const option = descriptor.options[name];
    if (!option) {
      throw cliError("phone.cli.argument", `Unknown option --${rawName} for ${canonicalCommandName(command)}. Run mobile-use ${canonicalCommandName(command)} --help.`);
    }
    if (option.type === "boolean" && value === undefined) {
      const next = tokens[index + 1];
      if (next === "true" || next === "false") {
        value = next;
        index += 1;
      } else {
        value = "true";
      }
    } else if (value === undefined) {
      index += 1;
      value = tokens[index];
    }
    if (value === undefined || value.startsWith("--")) throw cliError("phone.cli.argument", `--${rawName} requires a value.`);
    const parameter = option.parameter ?? name;
    setParameter(params, parameterSources, parameter, parseOptionValue(value, rawName, option), `--${rawName}`);
  }
  if (!help) validateRequiredParameters(descriptor, params);
  return { command, params, pretty, help };
}

function requireCommand(value) {
  const command = normalizeCommandName(value);
  if (!CLI_COMMANDS.includes(command)) {
    throw cliError("phone.command.unknown", `Unknown command: ${value}. Run mobile-use --help.`);
  }
  return command;
}

function parsePositional(value, positional) {
  if (positional.type === "command") return requireCommand(value);
  return value;
}

function parseOptionValue(value, name, option) {
  if (option.type === "json-object") {
    const parsed = parseJson(value, name);
    if (!isRecord(parsed)) throw cliError("phone.cli.argument", `--${name} must contain a JSON object.`);
    return parsed;
  }
  if (option.type === "number") {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) throw cliError("phone.cli.argument", `--${name} must be a number.`);
    validateOptionValue(parsed, name, option);
    return parsed;
  }
  if (option.type === "boolean") {
    if (value !== "true" && value !== "false") throw cliError("phone.cli.argument", `--${name} must be true or false.`);
    return value === "true";
  }
  validateOptionValue(value, name, option);
  return value;
}

function validateLogicalParameter(descriptor, parameter, value, sourceName) {
  const option = Object.entries(descriptor.options)
    .find(([name, candidate]) => (candidate.parameter ?? name) === parameter)?.[1];
  if (!option) throw cliError("phone.cli.argument", `Unknown parameter ${parameter} in --${sourceName}.`);
  if (option.type === "json-object" && !isRecord(value)) {
    throw cliError("phone.cli.argument", `Parameter ${parameter} in --${sourceName} must be an object.`);
  }
  if (option.type === "string" && typeof value !== "string") {
    throw cliError("phone.cli.argument", `Parameter ${parameter} in --${sourceName} must be a string.`);
  }
  if (option.type === "number" && typeof value !== "number") {
    throw cliError("phone.cli.argument", `Parameter ${parameter} in --${sourceName} must be a number.`);
  }
  if (option.type === "boolean" && typeof value !== "boolean") {
    throw cliError("phone.cli.argument", `Parameter ${parameter} in --${sourceName} must be a boolean.`);
  }
  validateOptionValue(value, parameter, option);
}

function validateOptionValue(value, name, option) {
  if (option.values && !option.values.includes(value)) {
    throw cliError("phone.cli.argument", `--${canonicalCommandName(name)} must be one of: ${option.values.join(", ")}.`);
  }
  if (option.integer && !Number.isInteger(value)) {
    throw cliError("phone.cli.argument", `--${canonicalCommandName(name)} must be an integer.`);
  }
  if (option.minimum !== undefined && value < option.minimum) {
    throw cliError("phone.cli.argument", `--${canonicalCommandName(name)} must be at least ${option.minimum}.`);
  }
  if (option.maximum !== undefined && value > option.maximum) {
    throw cliError("phone.cli.argument", `--${canonicalCommandName(name)} must be at most ${option.maximum}.`);
  }
}

function setParameter(params, sources, parameter, value, source) {
  if (sources.has(parameter)) {
    throw cliError("phone.cli.argument", `Parameter ${parameter} was provided more than once (${sources.get(parameter)} and ${source}).`);
  }
  params[parameter] = value;
  sources.set(parameter, source);
}

function validateRequiredParameters(descriptor, params) {
  for (const [name, option] of Object.entries(descriptor.options)) {
    const parameter = option.parameter ?? name;
    if (option.required && params[parameter] === undefined) {
      throw cliError("phone.cli.argument", `--${canonicalCommandName(name)} is required.`);
    }
  }
  for (const positional of descriptor.positionals ?? []) {
    if (positional.required && params[positional.parameter] === undefined) {
      throw cliError("phone.cli.argument", `${positional.parameter} is required.`);
    }
  }
}

function parseJson(value, name) {
  if (Buffer.byteLength(value) > 1024 * 1024) throw cliError("phone.cli.argument", `--${name} exceeds the 1 MiB limit.`);
  try {
    return JSON.parse(value);
  } catch (error) {
    throw cliError("phone.cli.argument", `--${name} is not valid JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function normalizeError(error) {
  const message = error instanceof Error ? error.message : String(error);
  const explicitCode = typeof error?.code === "string" ? error.code : undefined;
  let code = explicitCode ?? (error instanceof TypeError ? "phone.cli.argument" : "phone.command.failed");
  if (!explicitCode && !(error instanceof TypeError) && /stale|not found|does not belong|no live session/iu.test(message)) code = "phone.session.unavailable";
  if (!explicitCode && !(error instanceof TypeError) && /revision|assert/iu.test(message)) code = "phone.revision.failed";
  const recovery = recoveryFor(code);
  return {
    code,
    message,
    retryable: recovery.retryable,
    recovery: Object.freeze({ kind: recovery.kind }),
    ...(code.includes("revision") ? { retry: "observe" } : {}),
    ...(isRecord(error?.details) ? { details: error.details } : {}),
  };
}

function recoveryFor(code) {
  if (code.includes("project-build.failed")) return { retryable: false, kind: "fix_project" };
  if (code.includes("revision")) return { retryable: true, kind: "reobserve" };
  if (code.includes("selector.ambiguous")) return { retryable: true, kind: "refine_selector" };
  if (code.includes("selector") || code.includes("assert")) return { retryable: true, kind: "reobserve" };
  if (code.includes("surface") || code.includes("session") || code.includes("target")) return { retryable: true, kind: "refresh_inventory" };
  if (code.includes("wait.timeout") || code.includes("wait-timeout")) return { retryable: true, kind: "wait_for_readiness" };
  if (code.includes("broker")) return { retryable: true, kind: "run_doctor" };
  if (code.includes("capability")) return { retryable: false, kind: "do_not_retry" };
  if (code.includes("argument") || code.includes("command.unknown") || code.includes("plan.invalid")) {
    return { retryable: false, kind: "fix_arguments" };
  }
  return { retryable: false, kind: "do_not_retry" };
}

function exitCodeFor(code) {
  if (code === "swift.cache.argument" || code === "swift.cache.command.unknown" || code === "swift.cache.confirmation.required") return 2;
  if (code === "swift.cache.active") return 3;
  if (code === "phone.cli.argument" || code === "phone.command.unknown" || code === "phone.plan.invalid" || code === "phone.plan.step-invalid") return 2;
  if (code.includes("surface") || code.includes("session") || code.includes("target")) return 3;
  if (code.includes("revision") || code.includes("assert") || code.includes("selector") || code.includes("wait.timeout") || code.includes("wait-timeout")) return 4;
  if (code.includes("capability")) return 5;
  if (code.includes("broker")) return 6;
  return 1;
}

function helpText(command) {
  if (command) return commandHelpText(command);
  const groups = new Map();
  for (const item of publicCommandCatalog()) {
    const commands = groups.get(item.category) ?? [];
    commands.push(item.command);
    groups.set(item.category, commands);
  }
  return [
    `Mobile Use CLI ${CLI_VERSION}`,
    "",
    "Usage:",
    "  mobile-use <command> [options] [--json]",
    "  mobile-use <command> --help",
    "  mobile-use describe <command> --json",
    "",
    ...[...groups.entries()].flatMap(([category, commands]) => [
      `${category}:`,
      `  ${commands.join(", ")}`,
      "",
    ]),
    "Common options:",
    "  --params-json <object>   Complete command parameter object",
    "  --pretty                 Pretty-print the JSON envelope",
    "",
    "The command prints a versioned JSON envelope and never exposes broker credentials.",
  ].join("\n");
}

function commandHelpText(command) {
  const info = publicCommandDescriptor(command);
  const positionalUsage = (info.positionals ?? []).map((item) => `<${item.parameter}>`).join(" ");
  const lines = [
    `Mobile Use CLI ${CLI_VERSION}`,
    "",
    `${info.command}: ${info.summary}`,
    "",
    `Usage: mobile-use ${info.command}${positionalUsage ? ` ${positionalUsage}` : ""} [options]`,
  ];
  if (info.requiredCapability) lines.push("", `Required capability: ${info.requiredCapability}`);
  if (info.capabilitiesByAction) {
    lines.push("", `Capabilities by action: ${Object.entries(info.capabilitiesByAction).map(([action, capability]) => `${action}=${capability}`).join(", ")}`);
  }
  if (info.destructiveWhen) lines.push("", `Destructive confirmation: ${JSON.stringify(info.destructiveWhen)}`);
  if (info.options.length) {
    lines.push("", "Options:");
    for (const option of info.options) {
      const constraints = [
        option.required ? "required" : undefined,
        option.values ? option.values.join("|") : undefined,
        option.integer ? "integer" : undefined,
      ].filter(Boolean).join(", ");
      lines.push(`  ${option.name}${constraints ? ` (${constraints})` : ""}  ${option.description}`);
    }
  }
  lines.push("", "Use --json for the stable envelope; use describe for the machine-readable contract.");
  return lines.join("\n");
}

function cliError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

const isEntrypoint = process.argv[1]
  && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
if (isEntrypoint) {
  const exitCode = await runCli(process.argv.slice(2));
  process.exitCode = exitCode;
}
