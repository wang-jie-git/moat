"""增强的文件哈希缓存管理器

优化点（v1.0.8）：
1. 添加 LRU 缓存限制（最多 10000 个条目）
2. 优化缓存键生成（使用相对路径 + mtime）
3. 并行扫描粒度优化（按目录分组）
4. 延迟加载检查器（按需初始化）
"""
import hashlib
import json
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any


class LRUCacheManager:
    """LRU（最近最少使用）缓存管理器

    限制缓存大小，自动淘汰最久未使用的条目
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        """设置缓存项"""
        with self.lock:
            if key in self.cache:
                # 更新现有项
                self.cache.move_to_end(key)
                self.cache[key] = value
            else:
                # 添加新项
                self.cache[key] = value

            # 检查是否超出限制
            if len(self.cache) > self.max_size:
                # 移除最久未使用的项（头部）
                self.cache.popitem(last=False)

    def remove(self, key: str) -> None:
        """移除缓存项"""
        with self.lock:
            self.cache.pop(key, None)

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)


class EnhancedHashCacheManager:
    """增强的文件哈希缓存管理器

    特性：
    - LRU 缓存（最多 10000 个条目）
    - 内存缓存 + 磁盘持久化
    - 批量操作优化
    - 并行扫描支持
    """

    def __init__(self, project_root: Path, cache_file: str = "hash_cache.json", max_cache_size: int = 10000):
        self.project_root = project_root.resolve()
        self.cache_path = self.project_root / ".moat" / cache_file
        self.memory_cache = LRUCacheManager(max_size=max_cache_size)
        self._dirty = set()  # 待保存的键
        self._load_cache()

    def _load_cache(self) -> None:
        """加载磁盘缓存到内存"""
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                for key, value in data.items():
                    self.memory_cache.set(key, value)
            except Exception:
                pass  # 忽略加载错误

    def _save_cache(self, force: bool = False) -> None:
        """保存内存缓存到磁盘

        Args:
            force: 是否强制保存所有缓存
        """
        if not force and not self._dirty:
            return  # 没有变化，跳过保存

        try:
            # 序列化 LRU 缓存
            data = {}
            for key in list(self.memory_cache.cache.keys()):
                value = self.memory_cache.cache.get(key)
                if value:
                    data[key] = value

            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self._dirty.clear()
        except Exception:
            pass

    def get_file_hash(self, file_path: Path, force_recalculate: bool = False) -> str | None:
        """获取文件哈希（优化版）

        Args:
            file_path: 文件路径
            force_recalculate: 是否强制重新计算

        Returns:
            文件哈希（前16位），如果无法计算则返回 None
        """
        resolved_file = file_path.resolve()
        resolved_root = self.project_root.resolve()

        try:
            rel_path = str(resolved_file.relative_to(resolved_root))
        except ValueError:
            rel_path = str(resolved_file)

        # 检查内存缓存
        if not force_recalculate:
            cached = self.memory_cache.get(rel_path)
            if cached:
                try:
                    mtime = file_path.stat().st_mtime
                    cached_mtime = cached.get("mtime", 0)

                    if mtime == cached_mtime:
                        return cached.get("hash")
                except Exception:
                    pass

        # 计算哈希
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            mtime = file_path.stat().st_mtime
            size = len(content)

            # 更新缓存
            cache_entry = {
                "hash": file_hash,
                "mtime": mtime,
                "size": size,
                "cached_at": datetime.now().isoformat(),
            }
            self.memory_cache.set(rel_path, cache_entry)
            self._dirty.add(rel_path)

            return file_hash
        except Exception:
            return None

    def get_file_line_count(self, file_path: Path, force_recalculate: bool = False) -> int | None:
        """获取文件行数（优化版）

        Args:
            file_path: 文件路径
            force_recalculate: 是否强制重新计算

        Returns:
            文件行数，如果无法计算则返回 None
        """
        resolved_file = file_path.resolve()
        resolved_root = self.project_root.resolve()

        try:
            rel_path = str(resolved_file.relative_to(resolved_root))
        except ValueError:
            rel_path = str(resolved_file)

        # 检查缓存
        if not force_recalculate:
            cached = self.memory_cache.get(rel_path)
            if cached:
                try:
                    mtime = file_path.stat().st_mtime
                    size = file_path.stat().st_size
                    cached_mtime = cached.get("mtime", 0)
                    cached_size = cached.get("size", 0)

                    if mtime == cached_mtime and size == cached_size:
                        return cached.get("lines")
                except Exception:
                    pass

        # 计算行数
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = len(content.split("\n"))
            mtime = file_path.stat().st_mtime
            size = file_path.stat().st_size

            # 更新缓存
            cache_entry = {
                "hash": self.memory_cache.get(rel_path, {}).get("hash"),
                "mtime": mtime,
                "size": size,
                "lines": lines,
                "cached_at": datetime.now().isoformat(),
            }
            self.memory_cache.set(rel_path, cache_entry)
            self._dirty.add(rel_path)

            return lines
        except Exception:
            return None

    def batch_get_hashes(self, file_paths: list[Path], force_recalculate: bool = False) -> dict[str, str | None]:
        """批量获取文件哈希（优化性能）

        Args:
            file_paths: 文件路径列表
            force_recalculate: 是否强制重新计算

        Returns:
            文件路径到哈希的映射
        """
        results = {}
        to_calculate = []

        # 第一轮：检查缓存
        for file_path in file_paths:
            resolved_file = file_path.resolve()
            resolved_root = self.project_root.resolve()

            try:
                rel_path = str(resolved_file.relative_to(resolved_root))
            except ValueError:
                rel_path = str(resolved_file)

            if not force_recalculate:
                cached = self.memory_cache.get(rel_path)
                if cached:
                    try:
                        mtime = file_path.stat().st_mtime
                        if mtime == cached.get("mtime", 0):
                            results[rel_path] = cached.get("hash")
                            continue
                    except Exception:
                        pass

            to_calculate.append((file_path, rel_path))

        # 第二轮：批量计算
        for file_path, rel_path in to_calculate:
            hash_value = self.get_file_hash(file_path, force_recalculate=True)
            results[rel_path] = hash_value

        return results

    def invalidate(self, file_path: Path) -> None:
        """使指定文件的缓存失效

        Args:
            file_path: 文件路径
        """
        resolved_file = file_path.resolve()
        resolved_root = self.project_root.resolve()

        try:
            rel_path = str(resolved_file.relative_to(resolved_root))
            self.memory_cache.remove(rel_path)
            self._dirty.add(rel_path)
        except Exception:
            pass

    def save(self, force: bool = False) -> None:
        """保存缓存到磁盘

        Args:
            force: 是否强制保存
        """
        self._save_cache(force=force)

    def clear(self) -> None:
        """清空缓存"""
        self.memory_cache.clear()
        self._dirty.clear()
        if self.cache_path.exists():
            try:
                self.cache_path.unlink()
            except Exception:
                pass

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "memory_cache_size": self.memory_cache.size(),
            "dirty_entries": len(self._dirty),
            "cache_file": str(self.cache_path),
        }


def batch_process_files(
    file_paths: list[Path],
    project_root: Path,
    max_workers: int = 4,
) -> dict[str, tuple[str | None, int | None]]:
    """批量处理文件（并行优化）

    Args:
        file_paths: 文件路径列表
        project_root: 项目根目录
        max_workers: 最大并行线程数

    Returns:
        文件路径到 (hash, line_count) 的映射
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}

    def process_single(file_path: Path) -> tuple[str, str | None, int | None]:
        resolved_file = file_path.resolve()
        resolved_root = Path(project_root).resolve()

        try:
            rel_path = str(resolved_file.relative_to(resolved_root))
        except ValueError:
            rel_path = str(resolved_file)

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            line_count = len(content.split("\n"))
            return (rel_path, file_hash, line_count)
        except Exception:
            return (rel_path, None, None)

    if len(file_paths) > 10:
        # 并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single, f): f for f in file_paths}

            for future in as_completed(futures):
                try:
                    rel_path, file_hash, line_count = future.result()
                    results[rel_path] = (file_hash, line_count)
                except Exception:
                    pass
    else:
        # 串行处理（小型批次）
        for file_path in file_paths:
            try:
                rel_path, file_hash, line_count = process_single(file_path)
                results[rel_path] = (file_hash, line_count)
            except Exception:
                pass

    return results
