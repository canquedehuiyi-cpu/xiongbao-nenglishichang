"""案例库的公共逻辑：归档 runs、重建 models 索引、只读查找案例。

README 是事实来源，索引是从 README 派生的缓存，只存于 models 根目录。
保存流程：取得写锁 → 校验源资料 → pending 复制校验 → 正式转正 → 重建索引。
查找流程：读取索引 → 与当前案例库核对 → 使用索引或现场扫描 → 匹配排序。

调用方必须先确认模型完成和真实用户保存授权。本模块只验证文件流程，
不能证明 CAD 几何正确、装配验收通过，或 README 中的授权声明真实。
"""

from __future__ import annotations

import filecmp
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

# 整个 models 共用一份索引；单个运行目录和案例快照不能携带该文件。
INDEX_NAME = "case-index.json"
# 结构发生不兼容变化时递增，旧索引会被查找流程判为无效。
SCHEMA_VERSION = 1
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"}
MANAGED_SKIP_DIRS = {".work"}
MANAGED_SKIP_FILES = {"runtime/workspace.lock"}
MANAGED_TEMP_NAME = re.compile(r"\.?run-files-[a-z0-9_]+\.tmp\Z")
# 捕获末尾的 8 位任务 UUID，用于构造 pending 目录名。
CASE_NAME = re.compile(r'[^\x00-\x1f<>:"/\\|?*]+__([0-9a-fA-F]{8})')


class CaseLibraryError(RuntimeError):
    """路径、快照或索引违反案例库约定时抛出的业务异常。"""


def assert_plain_path(path: Path) -> None:
    """检查路径及所有祖先，拒绝符号链接和 Windows 目录联接等重解析点。

    必须在 resolve 前检查，否则链接被解析成真实路径后，可能隐藏越界来源。
    尚未创建的路径允许通过，但已经存在的祖先仍然要逐级检查。
    """
    for part in (path, *path.parents):
        if os.path.lexists(part):
            info = os.lstat(part)
            attrs = getattr(info, "st_file_attributes", 0)
            if stat.S_ISLNK(info.st_mode) or attrs & getattr(
                stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024
            ):
                raise CaseLibraryError(f"拒绝链接或重解析点：{part}")


def _workspace(workspace: Path) -> Path:
    """校验工程根目录，返回真实存在的绝对路径。"""
    path = Path(workspace).absolute()
    assert_plain_path(path)
    if not path.is_dir():
        raise CaseLibraryError(f"工程目录不存在：{path}")
    return path.resolve(strict=True)


def _models(workspace: Path) -> Path:
    """从工程根推导唯一的 models 路径，不接受调用方指定任意归档位置。"""
    path = _workspace(workspace) / "generated" / "models"
    assert_plain_path(path)
    return path


def _excluded(name: str) -> bool:
    """按名称过滤凭据、缓存和元数据；同时用于文件和目录。

    此处只做名称过滤，不能识别普通文件内容中混入的密钥；调用方仍需核对资料。
    """
    return (
        name.upper().startswith("API_KEY")
        or name.lower() in SKIP_DIRS
        or name.lower().endswith((".pyc", ".pyo"))
    )


def _digest(path: Path) -> str:
    """分块计算 SHA-256 内容指纹，避免大文件一次性占满内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _raise_walk_error(error: OSError) -> None:
    """让目录遍历的读取错误向上传递，不能静默遗漏文件。"""
    raise error


def validate_run_source(workspace: Path, source: Path) -> Path:
    """源必须是本工程 runs 的直接任务子目录，且名称符合任务 UUID 约定。

    相对源路径以 workspace 为基准，不以终端当前目录为基准。
    """
    workspace = _workspace(workspace)
    source = Path(source)
    if not source.is_absolute():
        source = workspace / source
    assert_plain_path(source)
    runs = workspace / "generated" / "runs"
    assert_plain_path(runs)
    if not source.is_dir() or source.resolve().parent != runs.resolve():
        raise CaseLibraryError("源必须是本工程 runs 的直接任务子目录")
    if (
        not CASE_NAME.fullmatch(source.name)
        or source.name.startswith(".")
        or source.name.endswith((" ", "."))
    ):
        raise CaseLibraryError("任务目录名必须为 <模型语义>__<8位UUID>")
    return source.resolve(strict=True)


def _strict_json(path: Path) -> dict:
    assert_plain_path(path)
    def reject_constant(value):
        raise ValueError("nonfinite JSON")
    try:
        value = json.loads(path.read_bytes(), parse_constant=reject_constant)
    except (ValueError, UnicodeError) as error:
        raise CaseLibraryError(f"新布局 JSON 损坏：{path.name}") from error
    if not isinstance(value, dict):
        raise CaseLibraryError(f"新布局 JSON 必须是对象：{path.name}")
    return value


def _layout_version(source: Path) -> int:
    """没有布局标记的旧任务为0；显式损坏/未知版本不能退回旧逻辑。"""
    path = source / "runtime" / "state.json"
    assert_plain_path(path)
    if not path.exists():
        return 0
    state = _strict_json(path)
    version = state.get("layout_version")
    if version is None:
        return 0
    if type(version) is not int or version != 1:
        raise CaseLibraryError("不支持或损坏的运行资料布局")
    return version


def _include_snapshot_path(source: Path, relative: str, *, layout_version=None) -> bool:
    version = _layout_version(source) if layout_version is None else layout_version
    if version != 1:
        return True
    folded = relative.casefold()
    top = folded.split("/", 1)[0]
    if top in MANAGED_SKIP_DIRS or folded in MANAGED_SKIP_FILES:
        return False
    return not (top in {"runtime", "analysis", "evidence", "reports"}
                and MANAGED_TEMP_NAME.fullmatch(PurePosixPath(relative).name))


def _validate_managed_archive(source: Path) -> None:
    """只查本地资料是否配套，不替代 CAD 验收和真实用户保存授权。"""
    if _layout_version(source) != 1:
        return
    state = _strict_json(source / "runtime/state.json")
    if (state.get("awaiting_result") is not False or state.get("execution_status") != "responded"
            or state.get("verification_status") != "passed"
            or state.get("verification_stage") != "final"):
        raise CaseLibraryError("新布局尚有等待、失败、未知或未完成的最终检查")
    managed = state.get("managed_files")
    fingerprints = state.get("input_fingerprint")
    if not isinstance(managed, dict) or not isinstance(fingerprints, dict):
        raise CaseLibraryError("新布局缺少文件登记或输入指纹")
    for key, relative in (("source", "model.crownscript.js"), ("parameters", "parameters.json"),
                          ("requirements", "operation_graph.json")):
        path = source / relative
        assert_plain_path(path)
        actual = _digest(path) if path.is_file() else None
        if actual != fingerprints.get(key) or (actual is None and key != "parameters"):
            raise CaseLibraryError(f"新布局输入指纹不配套：{relative}")
    for relative, entry in managed.items():
        if (not isinstance(relative, str) or "\\" in relative or ":" in relative
                or PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts
                or not isinstance(entry, dict)):
            raise CaseLibraryError("新布局受管文件登记无效")
        if not _include_snapshot_path(source, relative, layout_version=1):
            continue
        path = source / relative
        assert_plain_path(path)
        if not path.is_file() or _digest(path) != entry.get("sha256"):
            raise CaseLibraryError(f"新布局文件指纹不配套：{relative}")
    required = {"runtime/request.json", "runtime/submitted.crownscript.js", "runtime/response.json",
                "reports/verification.json", "reports/verification.md"}
    if not required.issubset(managed):
        raise CaseLibraryError("新布局缺少固定执行或报告文件")
    operation_id = state.get("operation_id")
    for relative in required:
        entry = managed[relative]
        if entry.get("status") != "valid" or entry.get("operation_id") != operation_id:
            raise CaseLibraryError("新布局执行与最终报告不属于同一状态")
    request = _strict_json(source / "runtime/request.json")
    response = _strict_json(source / "runtime/response.json")
    report = _strict_json(source / "reports/verification.json")
    if (not operation_id or request.get("operation_id") != operation_id
            or response.get("operation_id") != operation_id
            or request.get("document") != state.get("document")
            or request.get("input_fingerprint") != fingerprints
            or request.get("submitted_sha256") != state.get("submitted_sha256")
            or request.get("submitted_sha256") != _digest(source / "runtime/submitted.crownscript.js")
            or response.get("execution_status") != "responded"
            or report.get("stage") != "final" or report.get("scope") != "requirements_check"
            or report.get("status") != "passed" or report.get("completion_issues")):
        raise CaseLibraryError("新布局请求、返回或最终报告不配套")
    for relative in ("reports/verification.json", "reports/verification.md"):
        provenance = managed[relative].get("source", {})
        if (provenance.get("operation_id") != operation_id
                or provenance.get("input_fingerprint") != fingerprints
                or not isinstance(provenance.get("evidence"), dict)):
            raise CaseLibraryError("新布局报告缺少取证时的关联")
        for ref, digest in provenance["evidence"].items():
            entry = managed.get(ref, {})
            if (entry.get("sha256") != digest or entry.get("status") != "valid"
                    or entry.get("scope") != "current_model" or entry.get("operation_id") != operation_id):
                raise CaseLibraryError("新布局最终报告引用了失效证据")


def inventory_snapshot(source: Path) -> dict[str, str]:
    """生成待归档文件的清单：{任务内相对路径: SHA-256}。

    清单既描述文件集合，也描述文件内容；复制前后比较可发现缺文件或源变化。
    排除项不读取，不跟随链接，不记录空目录；错误直接抛出。
    """
    result = {}
    assert_plain_path(source)
    layout_version = _layout_version(source)
    for current, dirs, files in os.walk(
        source, topdown=True, followlinks=False, onerror=_raise_walk_error
    ):
        current = Path(current)
        # 原地修改 dirs，让 os.walk 不进入被排除的目录，尤其是凭据目录。
        dirs[:] = sorted(
            name for name in dirs if not _excluded(name)
            and _include_snapshot_path(source, (current / name).relative_to(source).as_posix(),
                                       layout_version=layout_version)
        )
        for name in dirs:
            assert_plain_path(current / name)
        for name in sorted(files):
            if _excluded(name):
                continue
            path = current / name
            if not _include_snapshot_path(source, path.relative_to(source).as_posix(),
                                          layout_version=layout_version):
                continue
            assert_plain_path(path)
            if not stat.S_ISREG(os.lstat(path).st_mode):
                raise CaseLibraryError(f"不是普通文件：{path}")
            if name.lower() == INDEX_NAME:
                raise CaseLibraryError("运行资料和案例快照内不允许包含 case-index.json")
            result[path.relative_to(source).as_posix()] = _digest(path)
    return result


def _validate_required(
    required_files: Sequence[str], inventory: dict[str, str]
) -> None:
    """核对必需文件属于清单；统一使用任务内的正斜杠相对路径。"""
    # README、操作图自动必需，最终脚本、响应和其他依赖由调用方传入。
    for text in {"README.md", "operation_graph.json", *required_files}:
        if not isinstance(text, str) or not text or "\\" in text or ":" in text:
            raise CaseLibraryError(f"引用路径无效：{text!r}")
        relative = PurePosixPath(text)
        if relative.is_absolute() or ".." in relative.parts or text not in inventory:
            raise CaseLibraryError(f"引用缺失、越界或被排除：{text}")


def validate_required_files(source: Path, required_files: Sequence[str]) -> None:
    """提供独立的必需文件预检入口，不创建或复制任何文件。"""
    _validate_required(required_files, inventory_snapshot(source))


def copy_confirmed_snapshot(
    workspace: Path, source: Path, required_files: Sequence[str]
) -> Path:
    """复制已获授权的任务，经校验后把 pending 转为正式快照。

    调用方需暂停源资料写入，并持有案例库写锁；save_case 已负责取得该锁。
    失败时保留 pending 供排查，不覆盖已有目标，也不删除原 runs。
    函数名中的 confirmed 是调用前提，并不表示此函数验证了用户授权。
    """
    source = validate_run_source(workspace, source)
    _validate_managed_archive(source)
    models = _models(workspace)
    models.mkdir(parents=True, exist_ok=True)
    target = models / source.name
    task_id = CASE_NAME.fullmatch(source.name).group(1).lower()
    pending = models / (".pending-" + task_id)
    # 固定复制前的文件集合与内容，后续检查都与这一份基准比较。
    before = inventory_snapshot(source)
    # 基线清单取得后再核对；避免先验通过后、首轮扫描前已切到 pending 状态。
    _validate_managed_archive(source)
    _validate_required(required_files, before)
    assert_plain_path(target)
    assert_plain_path(pending)
    if os.path.lexists(pending) or os.path.lexists(target):
        raise CaseLibraryError("目标或 pending 已存在，不覆盖")
    pending.mkdir()
    for relative in sorted(before):
        destination = pending / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    # 同时检查源是否被修改，以及副本是否少文件、多文件或内容不一致。
    if inventory_snapshot(source) != before or inventory_snapshot(pending) != before:
        raise CaseLibraryError("复制期间源变化或副本不完整；保留 pending")
    # 哈希核对后再做实际字节比较，不依赖文件大小或修改时间相同。
    for relative in before:
        if not filecmp.cmp(source / relative, pending / relative, shallow=False):
            raise CaseLibraryError(f"文件字节不一致：{relative}")
    if inventory_snapshot(source) != before:
        raise CaseLibraryError("源文件再次变化；保留 pending")
    if os.path.lexists(target):
        raise CaseLibraryError("正式目录已存在；保留 pending")
    _validate_managed_archive(pending)
    # 正式转正是最后一步。Windows rename 不覆盖已存在目标；其他受支持平台
    # 依靠案例库锁串行处理遵循本工具约定的写入方。
    pending.rename(target)
    return target


def parse_case_readme(text: str) -> dict:
    """从 README 的标题和固定字段提取检索信息，不猜测缺失标签。

    返回的完成/保存字段只是文本声明，不是验收或授权证据。
    缺字段的旧资料仍可全文搜索，issues 用来提示其记录不完整。
    """

    def field(label: str) -> str:
        """读取以“字段名：”或“字段名:”开头的首个匹配项。"""
        match = re.search(
            r"^" + re.escape(label) + r"[：:]\s*(.*)$", text, re.MULTILINE
        )
        return match.group(1).strip() if match else ""

    def values(label: str) -> list[str]:
        """按顿号、中文或英文逗号拆分标签，去空项并按原顺序去重。"""
        return list(
            dict.fromkeys(
                part.strip()
                for part in re.split(r"[、，,]", field(label))
                if part.strip()
            )
        )

    title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    issues = []
    for label in ("模型类型", "关键特征", "建模方法"):
        if not field(label):
            issues.append(f"缺少检索字段：{label}")
    # 只识别声明文字；即使文字匹配，也不能据此证明真实用户已授权。
    if field("保存决定") != "用户确认保存":
        issues.append("历史资料：保存授权来源未确认")
    return {
        "title": title.group(1).strip() if title else "",
        "modelType": field("模型类型"),
        "features": values("关键特征"),
        "methods": values("建模方法"),
        "completionDeclaration": field("任务进度"),
        "saveDeclaration": field("保存决定"),
        "issues": issues,
    }


def scan_case_library(workspace: Path) -> list[dict]:
    """扫描 models 的直接案例子目录，只读取每个目录根部的 README。

    跳过点号开头的内部目录（含 pending），避免读取依赖包内的其他 README。
    缺 README 的旧目录保留目录名检索记录；读取失败则报错，不冒充暂无案例。
    """
    models = _models(workspace)
    if not models.exists():
        return []
    cases = []
    for directory in sorted(models.iterdir(), key=lambda path: path.name):
        if directory.name.startswith("."):
            continue
        assert_plain_path(directory)
        if not directory.is_dir():
            continue
        readme = directory / "README.md"
        assert_plain_path(readme)
        # 默认记录兼容无 README 的历史目录；不修改或补写历史资料。
        entry = {
            "caseId": directory.name,
            "readmePath": None,
            "readmeSha256": None,
            "readmeText": "",
            **parse_case_readme(""),
        }
        if readme.exists():
            if not readme.is_file():
                raise CaseLibraryError(f"README 不是普通文件：{readme}")
            # 同一份字节用于哈希和文本解析；utf-8-sig 同时兼容带 BOM 的文件。
            data = readme.read_bytes()
            text = data.decode("utf-8-sig")
            entry.update(parse_case_readme(text))
            entry.update(
                readmePath=f"{directory.name}/README.md",
                readmeSha256=hashlib.sha256(data).hexdigest(),
                readmeText=text,
            )
        else:
            entry["issues"].append("历史资料：缺少 README")
        entry["title"] = entry["title"] or directory.name
        if not (directory / "operation_graph.json").is_file():
            entry["issues"].append("缺少 operation_graph.json")
        cases.append(entry)
    return cases


def build_case_index(workspace: Path) -> dict:
    """在内存中全量构造索引；此函数本身不写磁盘。"""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "cases": scan_case_library(workspace),
    }


def write_case_index_atomic(workspace: Path, index: dict) -> None:
    """先写完整临时文件，再原子替换 models 根部索引；调用方负责持有写锁。

    临时文件与正式文件位于同一目录，避免跨文件系统替换。
    替换前失败不会改写旧索引；finally 清理本次创建的临时文件。
    """
    models = _models(workspace)
    models.mkdir(parents=True, exist_ok=True)
    target = models / INDEX_NAME
    assert_plain_path(target)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=models,
            prefix=".case-index-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(index, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            # flush 刷新 Python 缓冲，fsync 请求将文件内容同步到磁盘。
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


@contextmanager
def case_library_lock(workspace: Path, timeout: float = 15) -> Iterator[None]:
    """串行化保存和显式索引重建，防止多个进程写回互相遗漏的索引。

    Windows 锁定文件首字节，其他平台使用 flock；最多等待 timeout 秒。
    锁文件可以留在磁盘，是否持锁由操作系统决定，不由文件是否存在决定。
    yield 内执行受保护操作；正常退出或抛异常都会释放锁。
    """
    models = _models(workspace)
    models.mkdir(parents=True, exist_ok=True)
    path = models / ".case-library.lock"
    assert_plain_path(path)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                # 字节锁需要可锁定的首字节；这不是业务数据。
                stream.write(b"0")
                stream.flush()

            def acquire():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise CaseLibraryError("案例库写锁等待超时") from error
                time.sleep(0.05)
        try:
            yield
        finally:
            release()


def rebuild_case_index(workspace: Path) -> dict:
    """显式重建入口：取得写锁、全量扫描、原子替换，不重新保存案例。"""
    with case_library_lock(workspace):
        index = build_case_index(workspace)
        write_case_index_atomic(workspace, index)
        return {"indexStatus": "updated", "caseCount": len(index["cases"])}


def save_case(workspace: Path, source: Path, required_files: Sequence[str]) -> dict:
    """保存流程总入口：在同一写锁内完成归档和索引重建。

    已有目标完全一致时返回 already_saved，但仍重建索引以恢复先前更新失败。
    目标不同则拒绝覆盖；新修订应另起任务 UUID。
    案例已转正而索引失败时，返回独立的失败状态，不回滚正式快照。
    """
    with case_library_lock(workspace):
        source = validate_run_source(workspace, source)
        _validate_managed_archive(source)
        target = _models(workspace) / source.name
        assert_plain_path(target)
        before = inventory_snapshot(source)
        _validate_managed_archive(source)
        _validate_required(required_files, before)
        if target.exists():
            # 重复调用按内容判断，不按目录存在就直接宣称保存成功。
            if not target.is_dir() or inventory_snapshot(target) != before:
                raise CaseLibraryError("正式案例与源不同，后续修订必须另起任务")
            for relative in before:
                if not filecmp.cmp(source / relative, target / relative, shallow=False):
                    raise CaseLibraryError("正式案例与源字节不同")
            if inventory_snapshot(source) != before:
                raise CaseLibraryError("核对期间源发生变化")
            status = "already_saved"
        else:
            target = copy_confirmed_snapshot(workspace, source, required_files)
            status = "saved"
        result = {
            "saveStatus": status,
            "casePath": str(target),
            "indexStatus": "updated",
        }
        try:
            # 只有正式快照建立或确认一致后，才生成包含它的全库索引。
            write_case_index_atomic(workspace, build_case_index(workspace))
        except (OSError, ValueError, CaseLibraryError) as error:
            # 此时案例已经保存，调用方应报告“案例已保存，索引更新失败”。
            result.update(indexStatus="failed", error=str(error))
        return result


def load_case_index(workspace: Path) -> dict:
    """读取并校验索引版本、字段类型、重复 ID 和相对 README 路径。

    结构校验只保证数据可以安全参与搜索；是否过期由 freshness 检查负责。
    """
    path = _models(workspace) / INDEX_NAME
    assert_plain_path(path)
    if path.exists() and not path.is_file():
        raise CaseLibraryError("索引路径不是普通文件")
    index = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(index, dict) or index.get("schemaVersion") != SCHEMA_VERSION:
        raise CaseLibraryError("索引版本或结构无效")
    cases = index.get("cases")
    if not isinstance(cases, list):
        raise CaseLibraryError("索引 cases 必须为列表")
    ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise CaseLibraryError("索引案例结构无效")
        for field in ("caseId", "title", "modelType", "readmeText"):
            if not isinstance(case.get(field), str):
                raise CaseLibraryError(f"索引字段无效：{field}")
        for field in ("features", "methods", "issues"):
            if not isinstance(case.get(field), list) or not all(
                isinstance(v, str) for v in case[field]
            ):
                raise CaseLibraryError(f"索引字段无效：{field}")
        case_id = case["caseId"]
        if (
            case_id in ids
            or not case_id
            or any(c in case_id for c in "/\\:")
            or case_id.startswith(".")
        ):
            raise CaseLibraryError("索引案例 ID 无效或重复")
        ids.add(case_id)
        if case.get("readmePath") not in (None, f"{case_id}/README.md"):
            raise CaseLibraryError("索引 README 路径无效")
    return index


def check_index_freshness(workspace: Path, index: dict) -> dict:
    """重新扫描 README，与索引的完整案例记录比较，返回新鲜度和当前数据。

    可发现案例增删、README 哈希变化和派生字段损坏。当前实现每次查找都会
    读全部 README，主要保证一致性，并未通过索引省掉文件扫描。
    """
    current = scan_case_library(workspace)
    # 哈希之外也比较派生字段，防止格式合法但内容错误的索引造成漏检。
    fresh = current == index["cases"]
    return {"fresh": fresh, "cases": current}


def search_cases(index: dict, terms: Sequence[str]) -> list[dict]:
    """在目录名、标题、标签和 README 全文中做任一关键词的包含匹配。

    不做同义词或语义推断；casefold 使英文等文字的匹配忽略大小写。
    先按命中词数，再按结构字段命中词数排序，最后按案例 ID 保证顺序稳定。
    返回命中位置和资料问题，让调用方继续阅读候选案例判断适用性。
    """
    terms = list(dict.fromkeys(term.strip() for term in terms if term.strip()))
    if not terms:
        raise CaseLibraryError("至少提供一个非空检索词")
    matches = []
    for case in index["cases"]:
        fields = {
            "caseId": case["caseId"],
            "title": case["title"],
            "modelType": case["modelType"],
            "features": " ".join(case["features"]),
            "methods": " ".join(case["methods"]),
            "readmeText": case["readmeText"],
        }
        locations = {
            term: [
                key
                for key, value in fields.items()
                if term.casefold() in value.casefold()
            ]
            for term in terms
        }
        locations = {term: value for term, value in locations.items() if value}
        if locations:
            # 同一个词命中多个结构字段也只计一次，避免字段重复抬高排名。
            structured = sum(
                any(field != "readmeText" for field in value)
                for value in locations.values()
            )
            matches.append(
                {
                    "caseId": case["caseId"],
                    "readmePath": case["readmePath"],
                    "title": case["title"],
                    "matchedTerms": list(locations),
                    "matchLocations": locations,
                    "issues": case["issues"],
                    "_structured": structured,
                }
            )
    matches.sort(
        # 负数让数量较多的排前面；caseId 保持升序作为最终排序依据。
        key=lambda item: (
            -len(item["matchedTerms"]),
            -item["_structured"],
            item["caseId"],
        )
    )
    for item in matches:
        # 排名辅助值只在内部使用，返回结果保留可解释的命中信息。
        del item["_structured"]
    return matches


def find_cases(workspace: Path, terms: Sequence[str]) -> dict:
    """只读查找入口：索引缺失、损坏或过期时退回现场 README 数据。

    回退只发生在内存中，不自动写回索引；写入由保存或显式重建触发。
    PermissionError 等真实读取错误不在回退异常中，避免把无法读取伪装成无匹配。
    """
    try:
        index = load_case_index(workspace)
    except (FileNotFoundError, ValueError, CaseLibraryError):
        index = build_case_index(workspace)
        source = "readme_scan"
    else:
        freshness = check_index_freshness(workspace, index)
        source = "index" if freshness["fresh"] else "readme_scan"
        if not freshness["fresh"]:
            # 复用 freshness 已扫描的数据，避免再读一遍所有 README。
            index = {"cases": freshness["cases"]}
    return {"source": source, "matches": search_cases(index, terms)}
