"""Prepare the isolated Python environment used by the Miaoda CLI."""

import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


def _python_in(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _prepare_runtime(cache: Path, prefix: str, requirements: Path) -> Path:
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    for candidate in sorted(cache.glob(f"{prefix}-*")):
        interpreter = _python_in(candidate)
        if (candidate / ".ready").is_file() and interpreter.is_file():
            return interpreter

    # Each first run installs into its own directory. Other runs can reuse it
    # only after pip finishes and the marker has been created.
    environment = Path(tempfile.mkdtemp(prefix=f"{prefix}-", dir=cache))
    install_env = os.environ.copy()
    install_env.pop("MIAODA_API_KEY", None)
    install_env["PIP_CONFIG_FILE"] = os.devnull
    print("Preparing Miaoda's Python dependencies…", file=sys.stderr, flush=True)
    try:
        subprocess.run(
            [sys.executable, "-I", "-m", "venv", str(environment)],
            env=install_env, stdout=sys.stderr, check=True, timeout=90,
        )
        interpreter = _python_in(environment)
        subprocess.run(
            [str(interpreter), "-I", "-m", "pip", "--isolated",
             "--disable-pip-version-check", "install", "--no-input",
             "--index-url", "https://pypi.org/simple", "--require-hashes",
             "--only-binary=:all:", "-r", str(requirements)],
            env=install_env, stdout=sys.stderr, check=True, timeout=180,
        )
        (environment / ".ready").touch()
        return interpreter
    except BaseException:
        shutil.rmtree(environment, ignore_errors=True)
        raise


def use_plugin_runtime() -> None:
    if sys.version_info < (3, 10):
        sys.exit("Miaoda requires Python 3.10 or newer. Select a supported Python and retry.")

    requirements = Path(__file__).resolve().parent.parent / "requirements.txt"
    cache = (Path.home() / ".miaoda-app-builder" / "python").resolve()
    try:
        lock_hash = hashlib.sha256(requirements.read_bytes()).hexdigest()[:16]
        prefix = f"{sys.implementation.name}-{platform.machine()}-{platform.python_version()}-{lock_hash}"
        current = Path(sys.prefix).resolve()
        if current.parent == cache and current.name.startswith(f"{prefix}-") and (current / ".ready").is_file():
            return

        interpreter = _prepare_runtime(cache, prefix, requirements)
        result = subprocess.run([str(interpreter), "-E", "-s", *sys.argv])
    except subprocess.TimeoutExpired:
        sys.exit("Miaoda dependency setup timed out. Check access to pypi.org and retry.")
    except subprocess.CalledProcessError:
        sys.exit("Miaoda could not install its Python dependencies. See the installer error above and retry.")
    except OSError as error:
        sys.exit(f"Miaoda could not prepare its Python environment: {error}")
    sys.exit(result.returncode)
