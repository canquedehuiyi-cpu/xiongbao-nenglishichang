# bio-research

Generated research guidance: 21 ordinary entry Skills and
152 internal method documents. Activate an entry Skill, read its
selection guide, then Read only the methods and resources relevant to the task.
Internal methods are not independently invocable Skills.

For a task matching a listed domain, call its entry with the Skill tool before
searching this plugin tree or writing analysis code. The entry provides the
selection guide and canonical file paths. Bash executes the selected workflow
after routing. This is a navigation instruction, not a runtime access control.

```bash
qodercli plugins validate /absolute/path/to/this/plugin --strict
qodercli plugins install /absolute/path/to/this/plugin --scope project
```

## Environment

This package ships guidance and scripts, not a runtime. Check and install one
domain's Python and R dependencies with:

```bash
python scripts/setup_env.py list
python scripts/setup_env.py check --domain foundation
python scripts/setup_env.py install --domain foundation --install-r
```

Nothing is installed automatically; `--install-r` installs R through the
platform package manager when it is missing, and `--skip-r` installs or checks
Python only. `foundation` covers the core Python stack and pheatmap/ComplexHeatmap.
The additional `biomystery-full` profile declares the supplied Dockerfile's 53
Python packages and CRAN/Bioconductor/GitHub R packages. Its
[full environment guide](env/biomystery-full/README.md) tells the agent how to
install the external runtimes, system libraries and bioinformatics CLI tools.
Read that guide before using `--domain biomystery-full`; the script installs its
Python/R stages, not every external component. Only foundation has passed a real
macOS arm64 installation; the full profile has not been installed end to end.
Windows and Linux have not been tested on native hosts.
See [env/README.md](env/README.md).

When required dependencies are missing, the agent must tell the user before
running the installer. For example, when both Python and R dependencies are needed:

> 当前分析需要安装一组体积较大的 Python/R 运行依赖。完整 foundation 环境
> 在本机安装后约占 0.9 GB，安装到 `~/.qoder/bio-research/env/foundation`。
> 如果本机缺少 R，还需额外安装 R 及系统依赖，总占用可能超过 1 GB。
> 安装需要联网，下载和编译可能耗时较长；实际大小取决于平台和已有依赖。

The notice must reflect the actual missing dependencies and install directory;
mention installing R itself only when it is missing and `--install-r` will be used.
The size above is installed disk usage, not a measured download size.
For `biomystery-full`, warn about a potentially multi-GB environment and follow
its guide; foundation's size measurement does not describe the full environment.

| Entry Skill | Internal methods |
| --- | ---: |
| `bio-research:seq-align-io` | 9 |
| `bio-research:read-align-qc` | 3 |
| `bio-research:expression-de` | 10 |
| `bio-research:single-cell-spatial` | 11 |
| `bio-research:chip-atac-chromatin` | 14 |
| `bio-research:variant-interp` | 5 |
| `bio-research:cnv-popgen` | 7 |
| `bio-research:crispr-engineering` | 8 |
| `bio-research:methylation` | 5 |
| `bio-research:metagenomics-microbiome` | 10 |
| `bio-research:genome-assembly` | 2 |
| `bio-research:proteomics-structure` | 5 |
| `bio-research:metabolomics-systems` | 5 |
| `bio-research:splicing-smallrna-tcr` | 5 |
| `bio-research:liquid-biopsy-cancer` | 5 |
| `bio-research:imaging-pathology` | 7 |
| `bio-research:flow-immunology` | 3 |
| `bio-research:clinical-healthcare` | 7 |
| `bio-research:databases-literature` | 8 |
| `bio-research:lab-platform` | 8 |
| `bio-research:foundation` | 15 |

Scientific packages, system tools, MCP and model authentication are not bundled.
See [environment guidance](resources/environment.md). Member source attribution,
license metadata and support files are retained. This packaging does not grant
additional rights over the upstream content.

`plugin-build.json` records source identity, complete file hashes, member mappings,
path rewrites and the runtime frontmatter that is documentary in this layout.
Its `reference_audit` lists upstream missing or non-packaged Markdown targets for
review; it is not proof that every scientific recipe executes. No model selection,
scientific accuracy or token-cost improvement is claimed by this build.
