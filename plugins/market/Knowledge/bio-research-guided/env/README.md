# Environment setup

The plugin ships method documents and scripts, not a prepared runtime. This
directory declares each domain's dependencies; `scripts/setup_env.py` detects,
installs and verifies them into `~/.qoder/bio-research/env/<domain>`, outside
the plugin tree.

Nothing is installed automatically. Run these yourself (or ask the agent to run
them) when you need a supported domain. Run these examples from the plugin root;
on macOS/Linux, use `python3` if `python` is unavailable:

```bash
python scripts/setup_env.py list
python scripts/setup_env.py check --domain foundation
python scripts/setup_env.py install --domain foundation --dry-run
python scripts/setup_env.py install --domain foundation --install-r
python scripts/setup_env.py check --domain foundation
```

Options: `--env-root DIR` changes the install root (default
`~/.qoder/bio-research/env`, also settable with `BIO_RESEARCH_ENV_ROOT`);
`--json` gives machine-readable `check` output.

## Choose the environment

| Profile (`--domain`) | Scope and validation |
| --- | --- |
| `foundation` | Core Python stack plus pheatmap/ComplexHeatmap; real macOS arm64 installation verified |
| `biomystery-full` | Supplied Dockerfile's Python/R dependencies, plus external system/CLI installation instructions; full installation and version resolution not verified |

For broader bioinformatics or BioMysteryBench tasks, read
[biomystery-full/README.md](biomystery-full/README.md) before running commands.
It contains the platform choices, conda package list, Ubuntu package list,
runtime version checks, uv/ossutil instructions, task-directory settings and
verification steps. Activate no full install merely because a Skill was invoked.
Other methods may require dependencies outside either profile.

## Notice before installing dependencies

If a check finds missing dependencies, explicitly tell the user that the selected
analysis needs additional dependencies. Before executing `install`, explain in the
user's language which Python/R packages will be installed, the actual environment
directory, and that downloading packages requires network access and disk space.
Explicitly warn that a full foundation environment is large: the tested macOS
arm64 environment occupies about 0.9 GB after installation. This excludes R itself,
package-manager dependencies and download/build caches; a setup that also needs R
and build dependencies can exceed 1 GB in total. These are installed-size examples,
not download-size measurements or an estimate of every incremental install.
Explain that downloads and compilation may take time, especially on a slow network.
For `biomystery-full`, do not reuse the 0.9 GB estimate: explicitly warn about
potentially multiple GB of packages, system tools and caches. The source Dockerfile
estimates a 10+ GB image; this is a source comment, not a measured host install or
download size. Follow that profile's guide and select only the needed stages.
Use the domain declarations and `install --dry-run` to describe the planned work.
If `--install-r` will install a missing R interpreter, also explain that the system
package manager will install R and its required system dependencies outside the
domain directory. For `--skip-r`, describe only the Python installation.

For example, when foundation needs both stacks:

> 当前分析需要安装一组体积较大的 Python 科学计算包和 R 包
>（pheatmap、ComplexHeatmap）。完整环境在本机安装后约占 0.9 GB，位于
> `~/.qoder/bio-research/env/foundation`。如果还需要安装 R 本体和系统依赖，
> 总占用可能超过 1 GB。安装需要联网，下载和编译可能耗时较长；
> 实际大小取决于平台和已有依赖。

Adapt the notice to the check results and any `--env-root` override. This notice
is part of the agent's workflow when using a Skill; installing the plugin itself
does not display a setup prompt or install any dependencies.

The script inherits pip's environment, so a mirror can be used without
changing the script:

```bash
PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    python scripts/setup_env.py install --domain foundation
```

## Domain layout

```
env/<domain>/
    requirements.in    minimum versions, the source of truth
    requirements.lock  optional lock file, used instead of .in when present
    verify.json        package -> import name, used for post-install checks
    r-packages.json    optional CRAN / Bioconductor / GitHub packages
    system.json        optional system tools to detect (never installed here)
    README.md          optional profile-specific installation instructions
```

## R packages

R packages are installed into an isolated library at
`<env-root>/<domain>/R/library` through `R_LIBS`, so removing the domain
directory removes them too. The script never installs R itself by default: it
reports `Rscript not found` with the platform command. Add `--install-r` to let
it use Homebrew (macOS), winget (Windows), or apt/dnf/pacman with passwordless
sudo (Linux); `--skip-r` installs or checks Python only and reports R as skipped.
The R interpreter itself is managed by the platform package manager, outside
the domain directory. Removing the domain directory removes its packages,
but does not uninstall R.

Bioconductor packages go through `BiocManager::install`, and every install is
verified with `requireNamespace` against the domain library. Repeated installs
reuse R packages that already load from that library. A failed R process,
missing package or incomplete check result makes `ready=no` and exits non-zero.
Compiler and download output is preserved for diagnosis. R runs with `--vanilla`
so user startup files do not change installation or verification.

GitHub R declarations use `{"package": "lionessR", "repo": "kuijjerlab/lionessR"}`
in the `github` array of `r-packages.json`. The script uses
`remotes::install_github` in the same isolated library and includes these packages
in readiness checks. Repository revisions are not pinned unless a ref is included
in the declaration; GitHub install failures exit non-zero.

When running a method, use the domain's Python interpreter
(`<env-root>/<domain>/bin/python`, or `Scripts/python.exe` on Windows).
For R, set `R_LIBS_USER` to `<env-root>/<domain>/R/library` before starting
`Rscript`, or prepend that directory with `.libPaths()` inside the script.

On macOS, an `unknown architecture` or `tapi error` can indicate an SDK/linker
mismatch. On the tested host, the macOS 27 SDK failed and the installed 26.5 SDK
worked. Point `SDKROOT` at a compatible SDK that exists on your machine; this
path is an example, not a required SDK version:

```bash
SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk \
    python scripts/setup_env.py install --domain foundation
```

If Homebrew bottle downloads fail, use a mirror for both the API and bottles:

```bash
HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles/api \
HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles \
    python scripts/setup_env.py install --domain foundation --install-r
```

Install a lock file for reproducible environments:

```bash
pip install pip-tools
pip-compile --output-file env/foundation/requirements.lock env/foundation/requirements.in
```

## Current coverage

`foundation` is the first slice: the core Python stack (numpy, pandas, scipy,
statsmodels, scikit-learn, matplotlib, seaborn, pymc, polars, pint), plus pheatmap
(CRAN) and ComplexHeatmap (Bioconductor). This does not cover every dependency
of all 15 foundation methods. Other domains do not yet have installer specs.
`biomystery-full` is an additional cross-domain dependency profile, not a new Skill.
It declares all 53 unique Python packages in the supplied Dockerfile, 25 packages
passed to BiocManager, tidyverse/remotes and GitHub lionessR. BiocManager is
bootstrapped by the installer. External dependencies are documented rather than
automatically installed by this script. This profile has regression and dry-run
coverage only; no complete dependency solve or live installation was performed.

Validation on macOS arm64: R 4.6.2, pheatmap 1.0.13 and ComplexHeatmap 2.28.0
installed into a fresh temporary R library using the compatible SDK above;
foundation's Python and R checks and a repeated install returned `ready=yes`.
Windows and Linux package-manager branches have unit coverage but have not
been exercised on native hosts. R package versions are not locked.

Run the installer regression tests with:

```bash
python scripts/test_setup_env.py
```

## What this does not do

- General system tools are only reported, with install hints from `system.json`.
  The explicit `--install-r` option is the exception for installing R itself.
- The script does not install conda/bioconda, general system libraries, uv or
  ossutil. Their installation steps are in the full profile's agent guide.
- No automatic reconstruction of container scripts, task data or a second system
  Python interpreter. See the full guide for the original Dockerfile's settings.
- No lock generation: produce `requirements.lock` with pip-tools or uv.
