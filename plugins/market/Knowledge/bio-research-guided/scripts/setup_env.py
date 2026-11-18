#!/usr/bin/env python3
"""Detect, install and verify one domain's Python and R environment.

The plugin ships guidance, not a runtime. This script reads a domain's
declarative requirements, creates a venv outside the plugin tree, installs
Python packages with pip, installs declared R packages into an isolated
library, then verifies that every declared package imports.

    python scripts/setup_env.py list
    python scripts/setup_env.py check --domain foundation
    python scripts/setup_env.py install --domain foundation [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ENV_DIR = PLUGIN_ROOT / "env"
MIN_PYTHON = (3, 9)
RECOMMENDED_PYTHON = (3, 10)
DEFAULT_ENV_ROOT = Path(
    os.environ.get("BIO_RESEARCH_ENV_ROOT")
    or (Path.home() / ".qoder" / "bio-research" / "env")
)

VERIFY_CODE = r"""
import importlib, json, sys

result = {}
for package, module in json.loads(sys.argv[1]).items():
    try:
        imported = importlib.import_module(module)
        result[package] = getattr(imported, "__version__", "unknown")
    except Exception as exc:
        result[package] = "ERROR: %s: %s" % (type(exc).__name__, exc)
print(json.dumps(result))
"""

R_CHECK_CODE = r"""
args <- commandArgs(TRUE)
lib <- args[1]
pkgs <- args[-1]
.libPaths(c(lib, .libPaths()))
for (p in pkgs) {
  ok <- suppressWarnings(requireNamespace(p, lib.loc = lib, quietly = TRUE))
  cat(p, "\t", if (ok) as.character(utils::packageVersion(p, lib.loc = lib)) else "MISSING", "\n", sep = "")
}
"""

R_INSTALL_CRAN_CODE = r"""
args <- commandArgs(TRUE)
lib <- args[1]
pkgs <- args[-1]
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
install.packages(pkgs, lib = lib, repos = "https://cloud.r-project.org")
missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), lib.loc = lib, quietly = TRUE)]
if (length(missing) > 0) {
  cat("missing:", paste(missing, collapse = ", "), "\n")
  quit(status = 1)
}
"""

R_INSTALL_BIOC_CODE = r"""
args <- commandArgs(TRUE)
lib <- args[1]
pkgs <- args[-1]
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
options(repos = c(CRAN = "https://cloud.r-project.org"))
if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", lib = lib, repos = "https://cloud.r-project.org")
}
BiocManager::install(pkgs, lib = lib, update = FALSE, ask = FALSE)
missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), lib.loc = lib, quietly = TRUE)]
if (length(missing) > 0) {
  cat("missing:", paste(missing, collapse = ", "), "\n")
  quit(status = 1)
}
"""

R_INSTALL_GITHUB_CODE = r"""
args <- commandArgs(TRUE)
lib <- args[1]
pkg <- args[2]
repo <- args[3]
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
options(repos = c(CRAN = "https://cloud.r-project.org"))
if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes", lib = lib)
}
remotes::install_github(repo, lib = lib, upgrade = "never", build_vignettes = FALSE)
if (!requireNamespace(pkg, lib.loc = lib, quietly = TRUE)) {
  cat("missing:", pkg, "\n")
  quit(status = 1)
}
"""


def r_package_names(spec: dict) -> list[str]:
    return (
        list(spec.get("cran", []))
        + list(spec.get("bioconductor", []))
        + [item["package"] for item in spec.get("github", [])]
    )


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def r_library(domain_root: Path) -> Path:
    return domain_root / "R" / "library"


def r_env(library: Path) -> dict[str, str]:
    env = os.environ.copy()
    value = str(library)
    env["R_LIBS_USER"] = value
    existing = env.get("R_LIBS")
    env["R_LIBS"] = value + (os.pathsep + existing if existing else "")
    return env


def parse_requirement_names(path: Path) -> list[str]:
    names: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if match:
            names.append(match.group(1))
    return sorted({normalize(name) for name in names})


def load_spec(domain: str) -> tuple[Path, Path, dict[str, str], list[dict], dict]:
    domain_path = ENV_DIR / domain
    if not domain_path.is_dir():
        raise SystemExit(f"unknown domain {domain!r}: {domain_path} does not exist")

    lock = domain_path / "requirements.lock"
    source = domain_path / "requirements.in"
    if lock.is_file():
        requirements = lock
    elif source.is_file():
        requirements = source
    else:
        raise SystemExit(
            f"domain {domain!r} has no requirements.in or requirements.lock"
        )

    verify_path = domain_path / "verify.json"
    verify = (
        json.loads(verify_path.read_text(encoding="utf-8"))
        if verify_path.is_file()
        else {}
    )

    system_path = domain_path / "system.json"
    system_tools = (
        json.loads(system_path.read_text(encoding="utf-8")).get("tools", [])
        if system_path.is_file()
        else []
    )

    r_path = domain_path / "r-packages.json"
    r_spec = (
        json.loads(r_path.read_text(encoding="utf-8"))
        if r_path.is_file()
        else {"cran": [], "bioconductor": []}
    )
    r_spec.setdefault("cran", [])
    r_spec.setdefault("bioconductor", [])
    r_spec.setdefault("github", [])
    for item in r_spec["github"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("package"), str)
            or not isinstance(item.get("repo"), str)
            or not item["package"] or not item["repo"]
        ):
            raise SystemExit(f"invalid GitHub R package declaration in {r_path}")

    return domain_path, requirements, verify, system_tools, r_spec


def run(
    cmd: list,
    *,
    dry_run: bool = False,
    capture: bool = False,
    env: dict[str, str] | None = None,
    label: str | None = None,
) -> str:
    printable = label or " ".join(shlex.quote(str(part)) for part in cmd)
    print(f"{'[dry-run] ' if dry_run else '+ '}{printable}", file=sys.stderr)
    if dry_run:
        return ""
    completed = subprocess.run(
        [str(part) for part in cmd],
        check=True,
        capture_output=capture,
        text=True,
        env=env,
    )
    return (completed.stdout or "") if capture else ""


def installed_packages(python: Path) -> dict[str, str]:
    try:
        output = run(
            [
                python,
                "-m",
                "pip",
                "list",
                "--format=json",
                "--disable-pip-version-check",
            ],
            capture=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"warning: could not list packages from {python}: {exc}", file=sys.stderr)
        return {}
    return {normalize(item["name"]): item["version"] for item in json.loads(output)}


def verify_imports(python: Path, mapping: dict[str, str]) -> dict[str, str]:
    if not mapping:
        return {}
    try:
        output = run(
            [python, "-c", VERIFY_CODE, json.dumps(mapping)],
            capture=True,
            label=f"python -c <verify imports: {', '.join(sorted(mapping))}>",
        )
    except subprocess.CalledProcessError as exc:
        return {package: f"ERROR: verification failed: {exc}" for package in mapping}
    return json.loads(output)


def rscript() -> str | None:
    return shutil.which("Rscript")


def r_version(executable: str) -> str:
    try:
        output = run([executable, "--version"], capture=True)
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    first = output.strip().splitlines()[0] if output.strip() else "unknown"
    match = re.search(r"version (\S+)", first)
    return match.group(1) if match else first


def check_r_packages(
    executable: str, library: Path, packages: list[str]
) -> dict[str, str]:
    if not packages:
        return {}
    try:
        output = run(
            [executable, "--vanilla", "-e", R_CHECK_CODE, str(library), *packages],
            capture=True,
            env=r_env(library),
            label=f"Rscript -e <check R packages: {', '.join(packages)}>",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        error = (
            f"Rscript exited with status {exc.returncode}"
            if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        )
        return {name: f"ERROR: {error}" for name in packages}
    result = {name: "ERROR: R returned no result for this package" for name in packages}
    for line in output.splitlines():
        if "\t" not in line:
            continue
        name, _, version = line.partition("\t")
        name, version = name.strip(), version.strip()
        if name in result:
            result[name] = (
                version
                if version == "MISSING" or re.fullmatch(r"\d+(?:[.-]\d+)*", version)
                else "ERROR: invalid package version returned by R"
            )
    return result


def host_r_install_candidates() -> list[list[str]]:
    if sys.platform == "darwin":
        return [["brew", "install", "r"]] if shutil.which("brew") else []
    if os.name == "nt":
        if shutil.which("winget"):
            return [
                [
                    "winget",
                    "install",
                    "--id",
                    "RProject.R",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ]
            ]
        return []
    for manager, command in (
        ("apt-get", ["sudo", "apt-get", "install", "-y", "r-base"]),
        ("dnf", ["sudo", "dnf", "install", "-y", "R"]),
        ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "r"]),
    ):
        if shutil.which(manager):
            return [command]
    return []


def sudo_available() -> bool:
    if os.name == "nt" or sys.platform == "darwin":
        return False
    try:
        return (
            subprocess.run(
                ["sudo", "-n", "true"],
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )
    except OSError:
        return False


def collect(domain: str, env_root: Path, include_r: bool = True) -> dict:
    _, requirements, verify, system_tools, r_spec = load_spec(domain)
    domain_root = env_root / domain
    venv = domain_root
    python = venv_python(venv)
    required = parse_requirement_names(requirements)
    r_packages = r_package_names(r_spec)

    info: dict = {
        "domain": domain,
        "plugin_root": str(PLUGIN_ROOT),
        "platform": f"{platform.system().lower()}/{platform.machine()}",
        "interpreter": {
            "path": sys.executable,
            "version": platform.python_version(),
            "minimum": ".".join(str(part) for part in MIN_PYTHON),
            "recommended": ".".join(str(part) for part in RECOMMENDED_PYTHON),
            "ok": sys.version_info[:2] >= MIN_PYTHON,
        },
        "requirements": {
            "path": str(requirements),
            "kind": requirements.suffix.lstrip("."),
            "declared": required,
        },
        "venv": {"path": str(venv), "exists": python.is_file()},
        "packages": {"installed": {}, "missing": required},
        "imports": {},
        "system_tools": {},
        "r": {
            "skipped": not include_r,
            "declared": r_spec,
            "executable": None,
            "version": None,
            "library": str(r_library(domain_root)),
            "packages": {"installed": {}, "missing": r_packages if include_r else []},
            "ok": True,
        },
        "ready": False,
    }

    for tool in system_tools:
        name = tool.get("name", "")
        found = shutil.which(name)
        info["system_tools"][name] = {
            "found": bool(found),
            "path": found,
            "why": tool.get("why", ""),
            "install": tool.get("install", {}),
        }

    if python.is_file():
        installed = installed_packages(python)
        info["packages"]["installed"] = {
            name: installed[name] for name in required if name in installed
        }
        info["packages"]["missing"] = [
            name for name in required if name not in installed
        ]
        info["imports"] = verify_imports(python, verify)

    if include_r and r_packages:
        executable = rscript()
        if executable:
            info["r"]["executable"] = executable
            info["r"]["version"] = r_version(executable)
            results = check_r_packages(executable, r_library(domain_root), r_packages)
            valid = {
                name: results[name]
                for name in r_packages
                if re.fullmatch(r"\d+(?:[.-]\d+)*", results.get(name, ""))
            }
            info["r"]["packages"] = {
                "installed": valid,
                "missing": [
                    name for name in r_packages if name not in valid
                ],
                "errors": {
                    name: results.get(name, "ERROR: R returned no result for this package")
                    for name in r_packages
                    if name not in valid and results.get(name) != "MISSING"
                },
            }
            info["r"]["ok"] = not info["r"]["packages"]["missing"]
        else:
            info["r"]["ok"] = False

    imports_ok = all(
        not str(value).startswith("ERROR") for value in info["imports"].values()
    )
    tools_ok = all(item["found"] for item in info["system_tools"].values())
    info["ready"] = bool(
        info["interpreter"]["ok"]
        and python.is_file()
        and not info["packages"]["missing"]
        and imports_ok
        and tools_ok
        and info["r"]["ok"]
    )
    return info


def print_report(info: dict) -> None:
    interpreter = info["interpreter"]
    print(f"domain       {info['domain']}")
    print(f"platform     {info['platform']}")
    print(f"interpreter  Python {interpreter['version']} ({interpreter['path']})")
    if not interpreter["ok"]:
        print(f"             needs Python {interpreter['minimum']}+")
    elif tuple(map(int, interpreter["version"].split(".")[:2])) < RECOMMENDED_PYTHON:
        print(f"             Python {interpreter['recommended']}+ recommended")

    requirements = info["requirements"]
    print(
        f"requirements {requirements['path']} "
        f"({len(requirements['declared'])} packages, {requirements['kind']})"
    )
    if requirements["kind"] == "in":
        print("             not a lock file; versions may drift")

    venv = info["venv"]
    print(f"venv         {venv['path']} ({'present' if venv['exists'] else 'missing'})")

    if info["packages"]["installed"]:
        rendered = ", ".join(
            f"{name}=={version}"
            for name, version in sorted(info["packages"]["installed"].items())
        )
        print(f"installed    {rendered}")
    if info["packages"]["missing"]:
        print(f"missing      {', '.join(info['packages']['missing'])}")

    for name, value in info["imports"].items():
        print(f"import       {name:12s} {value}")

    for name, state in info["system_tools"].items():
        mark = state["path"] if state["found"] else "missing"
        print(f"tool         {name:12s} {mark}")
        if not state["found"] and state["install"].get("guide"):
            print(f"install guide {PLUGIN_ROOT / state['install']['guide']}")

    r_info = info["r"]
    r_declared = r_package_names(r_info["declared"])
    if r_declared and r_info["skipped"]:
        print("R            skipped (--skip-r)")
    elif r_declared:
        executable = r_info["executable"] or "Rscript not found"
        print(f"R            {r_info['version'] or 'not installed'} ({executable})")
        print(f"R library    {r_info['library']}")
        if r_info["packages"]["installed"]:
            rendered = ", ".join(
                f"{name}=={version}"
                for name, version in sorted(r_info["packages"]["installed"].items())
            )
            print(f"R installed  {rendered}")
        if r_info["packages"]["missing"]:
            print(f"R missing    {', '.join(r_info['packages']['missing'])}")
        for name, error in r_info["packages"].get("errors", {}).items():
            print(f"R error      {name}: {error}")

    print(f"ready        {'yes' if info['ready'] else 'no'}")
    if not info["ready"]:
        print()
        print(
            "next: python scripts/setup_env.py install "
            f"--domain {info['domain']}"
        )


def command_list(args: argparse.Namespace) -> int:
    if not ENV_DIR.is_dir():
        print(f"no env directory at {ENV_DIR}")
        return 1
    rows = []
    for domain_path in sorted(ENV_DIR.iterdir()):
        if not domain_path.is_dir():
            continue
        lock = domain_path / "requirements.lock"
        source = domain_path / "requirements.in"
        requirements = lock if lock.is_file() else source
        if not requirements.is_file():
            continue
        r_path = domain_path / "r-packages.json"
        r_count = 0
        if r_path.is_file():
            spec = json.loads(r_path.read_text(encoding="utf-8"))
            r_count = len(r_package_names(spec))
        suffix = f", R {r_count}" if r_count else ""
        rows.append(
            (
                domain_path.name,
                requirements.suffix.lstrip("."),
                str(len(parse_requirement_names(requirements))),
                suffix,
            )
        )
    if not rows:
        print("no domains declared")
        return 1
    width = max(len(name) for name, _, _, _ in rows)
    for name, kind, count, suffix in rows:
        print(f"{name:{width}s}  {count:>3s} packages  ({kind}{suffix})")
    return 0


def command_check(args: argparse.Namespace) -> int:
    info = collect(args.domain, Path(args.env_root).expanduser(), include_r=not args.skip_r)
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print_report(info)
    return 0 if info["ready"] else 1


def ensure_r(executable: str | None, args: argparse.Namespace) -> str | None:
    if executable:
        return executable
    candidates = host_r_install_candidates()
    if not candidates:
        print(
            "warning: R is not installed and no supported package manager was found; "
            "install R from https://cran.r-project.org/ and rerun",
            file=sys.stderr,
        )
        return None
    if not args.install_r:
        rendered = " ; ".join(
            " ".join(shlex.quote(part) for part in command) for command in candidates
        )
        print(
            f"warning: R is not installed; rerun with --install-r or run: {rendered}",
            file=sys.stderr,
        )
        return None
    for command in candidates:
        if command[0] == "sudo" and not sudo_available():
            rendered = " ".join(shlex.quote(part) for part in command)
            print(
                f"warning: R installation needs administrator rights; run manually: {rendered}",
                file=sys.stderr,
            )
            continue
        try:
            run(command, dry_run=args.dry_run)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(
                f"warning: installing R failed ({exc}); configure a package "
                "mirror or install R manually from https://cran.r-project.org/",
                file=sys.stderr,
            )
            return None
    return rscript()


def install_r_packages(
    executable: str, library: Path, spec: dict, dry_run: bool
) -> None:
    cran = list(spec.get("cran", []))
    bioconductor = list(spec.get("bioconductor", []))
    github = list(spec.get("github", []))
    if not dry_run:
        current = check_r_packages(executable, library, r_package_names(spec))
        installed = {
            name for name, version in current.items()
            if re.fullmatch(r"\d+(?:[.-]\d+)*", version)
        }
        cran = [name for name in cran if name not in installed]
        bioconductor = [name for name in bioconductor if name not in installed]
        github = [item for item in github if item["package"] not in installed]
    env = r_env(library)
    try:
        if cran:
            run(
                [executable, "--vanilla", "-e", R_INSTALL_CRAN_CODE, str(library), *cran],
                dry_run=dry_run,
                env=env,
                label=f"Rscript -e <install CRAN: {', '.join(cran)}>",
            )
        if bioconductor:
            run(
                [executable, "--vanilla", "-e", R_INSTALL_BIOC_CODE, str(library), *bioconductor],
                dry_run=dry_run,
                env=env,
                label=f"Rscript -e <install Bioconductor: {', '.join(bioconductor)}>",
            )
        for item in github:
            run(
                [executable, "--vanilla", "-e", R_INSTALL_GITHUB_CODE,
                 str(library), item["package"], item["repo"]],
                dry_run=dry_run,
                env=env,
                label=f"Rscript -e <install GitHub: {item['repo']} ({item['package']})>",
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        error = (
            f"Rscript exited with status {exc.returncode}"
            if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        )
        hint = ""
        if sys.platform == "darwin":
            hint = (
                " On macOS, 'unknown architecture' or 'tapi error' during "
                "compilation means the default SDK is newer than the linker; "
                "rerun with SDKROOT pointing at an older CommandLineTools SDK."
            )
        raise SystemExit(
            f"R package installation failed ({error}); see the output above "
            f"for the packages R could not install.{hint}"
        ) from exc


def command_install(args: argparse.Namespace) -> int:
    if sys.version_info[:2] < MIN_PYTHON:
        raise SystemExit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
            f"found {platform.python_version()}"
        )
    if sys.version_info[:2] < RECOMMENDED_PYTHON:
        print(
            f"warning: Python {RECOMMENDED_PYTHON[0]}.{RECOMMENDED_PYTHON[1]}+ "
            f"is recommended, found {platform.python_version()}",
            file=sys.stderr,
        )

    _, requirements, _, _, r_spec = load_spec(args.domain)
    guide = ENV_DIR / args.domain / "README.md"
    if guide.is_file():
        print(
            f"Environment guide: {guide}. This command installs Python/R packages; "
            "external runtimes, system libraries and CLI tools follow that guide.",
            file=sys.stderr,
        )
    if requirements.suffix == ".in":
        print(
            "warning: installing from requirements.in, not a lock file; "
            "versions may drift between machines",
            file=sys.stderr,
        )

    env_root = Path(args.env_root).expanduser()
    domain_root = env_root / args.domain
    python = venv_python(domain_root)

    if not python.is_file():
        if not args.dry_run:
            env_root.mkdir(parents=True, exist_ok=True)
        try:
            run([sys.executable, "-m", "venv", str(domain_root)], dry_run=args.dry_run)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                "creating the venv failed; on Debian/Ubuntu install "
                f"python3-venv first ({exc})"
            ) from exc
        if not args.dry_run and not python.is_file():
            raise SystemExit(f"venv creation did not produce {python}")

    try:
        run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements),
            ],
            dry_run=args.dry_run,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"pip install failed ({exc}); see the output above") from exc

    r_packages = r_package_names(r_spec)
    if r_packages and not args.skip_r:
        executable = ensure_r(rscript(), args)
        if executable is None and args.dry_run:
            executable = "Rscript"
        if executable:
            library = r_library(domain_root)
            if not args.dry_run:
                library.mkdir(parents=True, exist_ok=True)
            install_r_packages(executable, library, r_spec, args.dry_run)

    if args.dry_run:
        print("[dry-run] install and verification were not executed", file=sys.stderr)
        return 0

    info = collect(args.domain, env_root, include_r=not args.skip_r)
    print_report(info)
    return 0 if info["ready"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install and verify one bio-research domain environment."
    )
    parser.add_argument("action", choices=["list", "check", "install"])
    parser.add_argument("--domain", help="domain directory name under env/")
    parser.add_argument(
        "--env-root",
        default=str(DEFAULT_ENV_ROOT),
        help=f"install root (default: {DEFAULT_ENV_ROOT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output for check",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print commands without creating a venv or installing",
    )
    parser.add_argument(
        "--install-r",
        action="store_true",
        help="install R with the platform package manager when missing",
    )
    parser.add_argument(
        "--skip-r",
        action="store_true",
        help="install Python packages only and ignore R packages",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action == "list":
        return command_list(args)
    if not args.domain:
        parser.error(f"{args.action} requires --domain")
    if args.action == "check":
        return command_check(args)
    return command_install(args)


if __name__ == "__main__":
    sys.exit(main())
