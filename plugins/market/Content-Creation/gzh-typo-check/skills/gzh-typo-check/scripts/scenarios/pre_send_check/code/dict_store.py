"""
dict_store.py —— 个人词典·本地存储(NON_GOALS:零上云,全部本地)

格式:一行一词、UTF-8、空白行忽略;文件不存在 = 空词典(首用时自动建)。
用户可用记事本直接编辑——本地资产用户可控。

路径解析(注入点,测试隔离用):
- 环境变量 GZH_TYPO_DICT 指定则用之;
- 否则默认 ~/.gzh-typo-check/dictionary.txt。

读写都是纯文件操作,判定不在这里(词典只影响白名单,不影响规则)。
"""

from __future__ import annotations

import os
from pathlib import Path


class DictStoreError(Exception):
    """词典文件读写失败(损坏/编码错/权限)。调用方降级,不炸主流程。"""


def default_dict_path() -> Path:
    env = os.environ.get("GZH_TYPO_DICT", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".gzh-typo-check" / "dictionary.txt"


def _normalize(raw_words: list[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for w in raw_words:
        w = w.strip()
        if w:
            seen[w] = None  # dict 保序去重
    return tuple(seen)


def load_words(path: Path | None = None) -> tuple[str, ...]:
    """读词典;文件不存在返回空;读不了(编码/权限)抛 DictStoreError。"""
    p = path or default_dict_path()
    if not p.exists():
        return ()
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DictStoreError(f"词典文件读不了,按空词典处理: {p} ({exc})") from exc
    return _normalize(text.splitlines())


def _write_words(path: Path, words: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(words) + ("\n" if words else ""), encoding="utf-8")
    tmp.replace(path)  # 原子替换:断电不留半文件


def add_words(words: tuple[str, ...], path: Path | None = None) -> int:
    """追加词条(去重),返回实际新增数。"""
    p = path or default_dict_path()
    current = load_words_or_empty(p)
    merged = _normalize([*current, *words])
    added = len(merged) - len(current)
    if added:
        _write_words(p, merged)
    return added


def remove_words(words: tuple[str, ...], path: Path | None = None) -> int:
    """删除词条,返回实际删除数。"""
    p = path or default_dict_path()
    current = load_words_or_empty(p)
    drop = {w.strip().lower() for w in words if w.strip()}
    kept = tuple(w for w in current if w.lower() not in drop)
    removed = len(current) - len(kept)
    if removed:
        _write_words(p, kept)
    return removed


def load_words_or_empty(p: Path) -> tuple[str, ...]:
    """load_words 的降级版:失败返回空(调用方自行决定是否提示)。"""
    try:
        return load_words(p)
    except DictStoreError:
        return ()
