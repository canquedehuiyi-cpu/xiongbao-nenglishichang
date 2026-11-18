#!/usr/bin/env python3
"""Local setup checks for the Qoder STAROps plugin."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


CONFIG_DIR = ".starops"
CONFIG_FILE_NAME = "config.json"
CONFIG_PATH_ENV = "STAROPS_AGENT_CONFIG"
DEFAULT_ENDPOINT = "starops.cn-beijing.aliyuncs.com"
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_IDLE_TIMEOUT_SECONDS = 60.0

REQUIRED_VALUES = {
    "employeeId": "STAROPS_AGENT_EMPLOYEE",
}

OPTIONAL_CONTEXT_VALUES = {
    "workspace": "STAROPS_AGENT_WORKSPACE",
    "project": "STAROPS_AGENT_PROJECT",
}

COMMON_ALIAS_KEYS = {
    "employee",
    "digitalEmployeeId",
    "workspaceName",
}


@dataclass
class CheckResult:
    level: str
    message: str


class SetupError(RuntimeError):
    pass


def user_config_path() -> Path:
    return Path.home() / CONFIG_DIR / CONFIG_FILE_NAME


def local_config_path() -> Path:
    return Path(CONFIG_DIR) / CONFIG_FILE_NAME


def config_path_key(config_path: Path) -> str:
    try:
        return str(config_path.resolve())
    except OSError:
        return str(config_path)


def config_file_paths(explicit_path: Optional[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()

    def add_existing(config_path: Path) -> None:
        if not config_path.exists():
            return
        key = config_path_key(config_path)
        if key in seen:
            return
        seen.add(key)
        paths.append(config_path)

    add_existing(user_config_path())
    add_existing(local_config_path())

    selected_explicit_path = explicit_path or os.environ.get(CONFIG_PATH_ENV)
    if selected_explicit_path:
        config_path = Path(selected_explicit_path).expanduser()
        key = config_path_key(config_path)
        if key not in seen:
            seen.add(key)
            paths.append(config_path)
    return paths


def read_json_config_file(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise SetupError(f"STAROps config file does not exist: {config_path}")
    if not config_path.is_file():
        raise SetupError(f"STAROps config path is not a file: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
    except json.JSONDecodeError as exc:
        raise SetupError(f"STAROps config file is not valid JSON: {config_path}: {exc}") from exc
    except OSError as exc:
        raise SetupError(f"Failed to read STAROps config file {config_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SetupError(f"STAROps config file must contain a JSON object: {config_path}")
    return payload


def read_file_config(paths: list[Path], results: list[CheckResult]) -> dict[str, Any]:
    merged_config: dict[str, Any] = {}
    if not paths:
        results.append(CheckResult("info", "No STAROps config file found; environment variables may still provide values."))
        return merged_config

    for config_path in paths:
        try:
            payload = read_json_config_file(config_path)
        except SetupError as exc:
            results.append(CheckResult("error", str(exc)))
            continue
        alias_keys = sorted(COMMON_ALIAS_KEYS.intersection(payload.keys()))
        if alias_keys:
            results.append(
                CheckResult(
                    "warn",
                    f"{config_path} contains unsupported alias keys {alias_keys}; use exact keys such as employeeId, workspace, and project. The project key means SLS Project.",
                )
            )
        merged_config.update(payload)
        results.append(CheckResult("ok", f"Loaded STAROps config file: {config_path}"))
    return merged_config


def config_text_value(config: dict[str, Any], key: str) -> Optional[str]:
    value = config.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def config_credentials(config: dict[str, Any]) -> dict[str, Any]:
    credentials = config.get("credentials")
    return credentials if isinstance(credentials, dict) else {}


def config_credential_text_value(config: dict[str, Any], key: str) -> Optional[str]:
    return config_text_value(config, key) or config_text_value(config_credentials(config), key)


def resolve_text_value(env_name: str, config: dict[str, Any], config_key: str, default: Optional[str] = None) -> Optional[str]:
    env_value = os.environ.get(env_name)
    if env_value is not None:
        text = env_value.strip()
        if text:
            return text
    return config_text_value(config, config_key) or default


def resolve_float_value(
    env_name: str,
    config: dict[str, Any],
    config_key: str,
    default: float,
) -> float:
    value: Any = os.environ.get(env_name)
    if value is None or (isinstance(value, str) and not value.strip()):
        value = config.get(config_key)
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SetupError(f"{env_name} / {config_key} must be a number of seconds.") from exc
    if result <= 0:
        raise SetupError(f"{env_name} / {config_key} must be greater than 0.")
    return result


def check_python(results: list[CheckResult]) -> bool:
    if sys.version_info < (3, 9):
        results.append(CheckResult("error", "Python 3.9 or newer is required."))
        return False
    version = ".".join(str(part) for part in sys.version_info[:3])
    results.append(CheckResult("ok", f"Python version is {version}."))
    return True


def check_dependency(module_name: str, package_name: str, results: list[CheckResult], *, required: bool = True) -> bool:
    if importlib.util.find_spec(module_name) is None:
        level = "error" if required else "warn"
        results.append(CheckResult(level, f"Missing dependency {package_name}. Run: pip3 install -r scripts/requirements.txt"))
        return False
    results.append(CheckResult("ok", f"Dependency {package_name} is installed."))
    return True


def check_required_values(config: dict[str, Any], results: list[CheckResult]) -> bool:
    missing: list[str] = []
    for config_key, env_name in REQUIRED_VALUES.items():
        value = resolve_text_value(env_name, config, config_key)
        if value:
            source = "environment" if os.environ.get(env_name, "").strip() else "config"
            results.append(CheckResult("ok", f"Required value {config_key} is present from {source}."))
        else:
            missing.append(config_key)

    if missing:
        env_names = ", ".join(REQUIRED_VALUES[key] for key in missing)
        config_names = ", ".join(missing)
        results.append(
            CheckResult(
                "error",
                f"Missing required STAROps value: {config_names}. Set {env_names} or provide it in a config file.",
            )
        )
        return False
    return True


def check_optional_context_values(config: dict[str, Any], results: list[CheckResult]) -> None:
    present: list[str] = []
    for config_key, env_name in OPTIONAL_CONTEXT_VALUES.items():
        value = resolve_text_value(env_name, config, config_key)
        if value:
            source = "environment" if os.environ.get(env_name, "").strip() else "config"
            results.append(CheckResult("ok", f"Optional context value {config_key} is present from {source}."))
            present.append(config_key)

    if not present:
        results.append(
            CheckResult(
                "info",
                "No STAROps workspace / SLS Project context configured. This is OK; add it only when you know the target workspace or SLS Project.",
            )
        )


def check_optional_values(config: dict[str, Any], results: list[CheckResult]) -> None:
    endpoint = resolve_text_value("STAROPS_AGENT_ENDPOINT", config, "endpoint", DEFAULT_ENDPOINT)
    if endpoint:
        results.append(CheckResult("ok", f"STAROps endpoint is configured as {endpoint}."))

    timeout_seconds: Optional[float] = None
    idle_timeout_seconds: Optional[float] = None
    try:
        timeout_seconds = resolve_float_value("STAROPS_AGENT_TIMEOUT", config, "timeout", DEFAULT_TIMEOUT_SECONDS)
    except SetupError as exc:
        results.append(CheckResult("error", str(exc)))

    try:
        idle_timeout_seconds = resolve_float_value(
            "STAROPS_AGENT_IDLE_TIMEOUT",
            config,
            "idleTimeout",
            DEFAULT_IDLE_TIMEOUT_SECONDS,
        )
    except SetupError as exc:
        results.append(CheckResult("error", str(exc)))

    if timeout_seconds is None or idle_timeout_seconds is None:
        return
    if idle_timeout_seconds > timeout_seconds:
        results.append(CheckResult("warn", "idleTimeout is greater than timeout; runtime will clamp idle timeout to total timeout."))
    else:
        results.append(CheckResult("ok", f"Timeout values are valid: timeout={timeout_seconds:g}, idleTimeout={idle_timeout_seconds:g}."))


def check_config_credentials(config: dict[str, Any], results: list[CheckResult]) -> bool:
    access_key_id = config_credential_text_value(config, "accessKeyId")
    access_key_secret = config_credential_text_value(config, "accessKeySecret")
    security_token = config_credential_text_value(config, "securityToken")

    if access_key_id and access_key_secret:
        if security_token:
            results.append(CheckResult("ok", "STAROps config provides AK/SK and STS token values; all values are hidden."))
        else:
            results.append(CheckResult("ok", "STAROps config provides AK/SK values; values are hidden."))
        return True

    if access_key_id or access_key_secret or security_token:
        results.append(
            CheckResult(
                "error",
                "STAROps config credential values must include both accessKeyId and accessKeySecret. "
                "securityToken is optional and only valid with AK/SK.",
            )
        )
        return False

    results.append(CheckResult("info", "No direct AK/SK values found in STAROps config. Preferred setup is accessKeyId/accessKeySecret in private .starops/config.json; checking Alibaba Cloud Credentials default chain as fallback."))
    return False


def call_or_none(obj: Any, method_name: str) -> Any:
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    return method()


def check_credential_chain(results: list[CheckResult]) -> None:
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
    except Exception as exc:
        raise SetupError(f"Alibaba Cloud Credentials SDK could not be imported: {exc}") from exc

    try:
        credential = CredentialClient().get_credential()
    except Exception as exc:
        raise SetupError(f"Alibaba Cloud Credentials default chain could not resolve credentials: {exc}") from exc

    access_key_id = call_or_none(credential, "get_access_key_id")
    access_key_secret = call_or_none(credential, "get_access_key_secret")
    security_token = call_or_none(credential, "get_security_token")
    if not access_key_id or not access_key_secret:
        raise SetupError("Alibaba Cloud Credentials default chain did not return an AccessKey ID and secret.")

    if security_token:
        results.append(CheckResult("ok", "Alibaba Cloud Credentials default chain resolved AK/SK and STS token values; all values are hidden."))
    else:
        results.append(CheckResult("ok", "Alibaba Cloud Credentials default chain resolved AK/SK values; values are hidden."))


def emit_results(results: list[CheckResult], as_json: bool) -> None:
    if as_json:
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, separators=(",", ":")))
        return

    for result in results:
        print(f"[{result.level}] {result.message}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local setup checks for the Qoder STAROps plugin.")
    parser.add_argument("--config", help="Path to an explicit STAROps JSON config file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON results.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    results: list[CheckResult] = []
    try:
        check_python(results)
        check_dependency("requests", "requests", results)
        config = read_file_config(config_file_paths(args.config), results)
        check_required_values(config, results)
        check_optional_context_values(config, results)
        check_optional_values(config, results)
        config_credentials_ok = check_config_credentials(config, results)
        credentials_ok = check_dependency(
            "alibabacloud_credentials",
            "alibabacloud-credentials",
            results,
            required=not config_credentials_ok,
        )
        if not config_credentials_ok and credentials_ok:
            try:
                check_credential_chain(results)
            except SetupError as exc:
                results.append(CheckResult("error", str(exc)))
        results.append(CheckResult("info", "Local check only: real diagnosis calls verify STAROps OpenAPI access, RAM permissions, credential validity, and employee access to STAROps workspace / SLS Project."))
        error_count = sum(1 for result in results if result.level == "error")
        emit_results(results, args.json)
        return 1 if error_count else 0
    except Exception as exc:
        results.append(CheckResult("error", f"Unexpected setup check failure: {exc}"))
        results.append(CheckResult("info", "Local check only: no STAROps OpenAPI call was made."))
        emit_results(results, args.json)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
