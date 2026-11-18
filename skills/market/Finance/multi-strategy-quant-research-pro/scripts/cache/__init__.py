"""数据缓存层。

为K线数据提供内存+文件双层缓存，减少重复HTTP请求，提升批量筛选性能。

缓存策略：
- K线数据：写入后至"下一个自然日 15:30"前有效（收盘后拉取的数据为当日最终数据，
  当日夜间/次日盘中的重复提问直接命中缓存，不再全量重拉）
- 说明：15:30 后写入的缓存已在收盘后，次日盘中读取的仍是上一交易日收盘数据，
  对选股/回测场景足够。
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Optional


class KlineCacheManager:
    """
    K线数据缓存管理器。

    内存缓存 + 文件缓存双层架构：
    - L1 内存缓存：进程内 dict，毫秒级访问
    - L2 文件缓存：磁盘 JSON，跨进程复用

    缓存键：code + days → 文件名为 code_days.json
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """初始化缓存管理器。

        Args:
            cache_dir: 文件缓存目录，默认 scripts/../cache_data/
        """
        if cache_dir is None:
            # 默认缓存在项目 scripts 同级的 cache_data 目录
            base = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(os.path.dirname(base), "cache_data")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        # L1 内存缓存: {code_days: {"data": [], "cached_at": timestamp}}
        self._mem_cache: dict[str, dict] = {}

    def cleanup(self, max_age_days: int = 30, max_total_mb: int = 500) -> int:
        """清理过期/超量文件缓存，防止长期使用磁盘无限增长。

        规则：
        1. 删除超过 max_age_days 天的缓存文件；
        2. 若剩余总大小仍超过 max_total_mb，按修改时间从旧到新继续删除，
           直到总大小低于上限。

        Args:
            max_age_days: 缓存文件保留天数
            max_total_mb: 缓存总大小上限（MB）

        Returns:
            int: 清理的文件数
        """
        removed = 0
        try:
            files = []
            for fname in os.listdir(self.cache_dir):
                if not fname.startswith("kline_"):
                    continue
                fpath = os.path.join(self.cache_dir, fname)
                try:
                    files.append((os.path.getmtime(fpath), os.path.getsize(fpath), fpath))
                except OSError:
                    continue

            now = time.time()
            cutoff = now - max_age_days * 86400
            remaining = []
            for mtime, size, fpath in files:
                if mtime < cutoff:
                    try:
                        os.remove(fpath)
                        removed += 1
                    except OSError:
                        pass
                else:
                    remaining.append((mtime, size, fpath))

            # 超量清理：按旧到新删除
            total_bytes = sum(size for _, size, _ in remaining)
            limit_bytes = max_total_mb * 1024 * 1024
            if total_bytes > limit_bytes:
                for mtime, size, fpath in sorted(remaining):
                    if total_bytes <= limit_bytes:
                        break
                    try:
                        os.remove(fpath)
                        total_bytes -= size
                        removed += 1
                    except OSError:
                        pass
        except OSError:
            pass  # 清理失败不阻塞主流程（下次运行会再次尝试）
        return removed

    def _cache_key(self, code: str, days: int) -> str:
        """生成缓存键。"""
        return f"{code}_{days}"

    def _cache_file_path(self, cache_key: str) -> str:
        """生成文件缓存路径。"""
        # 用 md5 缩短路径避免非法字符
        safe_name = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"kline_{safe_name}.json")

    def get(self, code: str, days: int) -> Optional[list[dict]]:
        """从缓存中获取K线数据。

        Returns:
            list[dict] 或 None（缓存未命中或已过期）
        """
        cache_key = self._cache_key(code, days)

        # L1 内存缓存
        if cache_key in self._mem_cache:
            entry = self._mem_cache[cache_key]
            if not self._is_entry_expired(entry):
                return entry["data"]

        # L2 文件缓存
        file_path = self._cache_file_path(cache_key)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    entry = json.load(f)
                if not self._is_entry_expired(entry):
                    # 回填内存缓存
                    self._mem_cache[cache_key] = entry
                    return entry["data"]
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    def set(self, code: str, days: int, data: list[dict]):
        """将K线数据写入缓存。"""
        cache_key = self._cache_key(code, days)
        entry = {
            "code": code,
            "days": days,
            "data": data,
            "cached_at": time.time(),
            "cache_date": datetime.now().strftime("%Y-%m-%d"),
        }

        # L1 内存
        self._mem_cache[cache_key] = entry

        # L2 文件
        file_path = self._cache_file_path(cache_key)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False)
        except IOError:
            pass  # 文件写入失败不阻塞

    @staticmethod
    def _is_kline_expired(cached_at: float) -> bool:
        """K线缓存过期判断：写入后至"下一个自然日 15:30"前有效。

        过期规则：缓存写入日的次日 15:30 过期：
        - 当日 15:30 前写入 → 有效到次日 15:30（约1天）
        - 当日 15:30 后写入 → 有效到次日 15:30（已含当日收盘最终数据）

        Args:
            cached_at: 缓存时间戳

        Returns:
            bool: True 表示已过期
        """
        from datetime import timedelta
        cached_date = datetime.fromtimestamp(cached_at)
        now = datetime.now()
        # 缓存写入日的下一个自然日 15:30 为有效期截止
        next_day = (cached_date + timedelta(days=1)).replace(
            hour=15, minute=30, second=0, microsecond=0
        )
        return now >= next_day

    @classmethod
    def _is_entry_expired(cls, entry: dict) -> bool:
        """缓存条目过期判断（基础规则 + 盘中数据修正）。

        基础规则：写入日至"下一个自然日 15:30"前有效（_is_kline_expired）。

        盘中数据修正（分两类）：
        1. 最后一根K线日期 < 写入日日期，且**写入时刻处于交易时段（工作日
           9:30-15:00）**——此时当日K线尚未出现，数据不完整，该缓存仅有效至
           写入日 15:30（当日收盘后即失效，次日必然重新拉取，避免次日盘中
           命中不完整盘中K线）。
        2. 最后一根K线日期 == 写入日日期，且写入时刻处于交易时段——当日盘中
           K线已出现但尚未收盘（收盘价仍在变动），该缓存立即判定过期，保证
           盘中任何一次重新运行都重拉最新盘中数据，绝不复用陈旧盘中K线。
        非交易时段（收盘后/周末/节假日）写入时，最后K线日期早于写入日是
        正常现象（当日无交易/停牌），不应用盘中修正，走基础规则（至次日
        15:30），避免缓存刚写入即失效（收盘后/周末运行的缓存完全无法复用）。

        Args:
            entry: 缓存条目（含 cached_at / data 字段）

        Returns:
            bool: True 表示已过期
        """
        cached_at = entry.get("cached_at", 0)
        if not cached_at or cls._is_kline_expired(cached_at):
            return True
        data = entry.get("data")
        if isinstance(data, list) and data and isinstance(data[-1], dict):
            last_date = data[-1].get("date", "")
            if last_date:
                try:
                    write_date = datetime.fromtimestamp(cached_at).date()
                    last = datetime.strptime(last_date, "%Y-%m-%d").date()
                    wtime = datetime.fromtimestamp(cached_at)
                    minutes = wtime.hour * 60 + wtime.minute
                    in_trading_hours = (
                        wtime.weekday() < 5
                        and 9 * 60 + 30 <= minutes <= 15 * 60
                    )
                    if in_trading_hours:
                        if last == write_date:
                            # 当日盘中K线已出现但未收盘（收盘价仍在变动）：
                            # 立即过期，盘中重跑必重拉，绝不复用陈旧盘中K线
                            return True
                        if last < write_date:
                            # 交易时段写入（当日K线未完成）：有效至写入日 15:30
                            expire = datetime(
                                write_date.year, write_date.month, write_date.day,
                                15, 30, 0, 0,
                            )
                            return datetime.now() >= expire
                except ValueError:
                    pass
        return False
