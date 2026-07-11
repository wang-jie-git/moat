"""文件哈希缓存管理器

优化性能：避免重复计算未变更文件的哈希
- 缓存文件哈希到 .moat/hash_cache.json
- 基于文件修改时间判断是否需要重新计算
- 增量更新：只对修改的文件重新计算
- 支持并行扫描
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any


class HashCacheManager:
    """文件哈希缓存管理器"""

    def __init__(self, project_root: Path, cache_file: str = "hash_cache.json"):
        self.project_root = project_root.resolve()
        self.cache_path = self.project_root / ".moat" / cache_file
        self.cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """加载缓存"""
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        """保存缓存"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self.cache, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def get_file_hash(self, file_path: Path, force_recalculate: bool = False) -> str | None:
        """获取文件哈希（带缓存）

        Args:
            file_path: 文件路径
            force_recalculate: 是否强制重新计算

        Returns:
            文件哈希（前16位），如果无法计算则返回 None
        """
        # macOS 兼容：resolve() 解决 /var vs /private/var 符号链接问题
        resolved_file = file_path.resolve()
        resolved_root = self.project_root.resolve()

        try:
            rel_path = str(resolved_file.relative_to(resolved_root))
        except ValueError:
            # 如果文件不在 project_root 下（理论上不应发生），使用绝对路径
            rel_path = str(resolved_file)

        # 检查缓存
        if not force_recalculate and rel_path in self.cache:
            cache_entry = self.cache[rel_path]

            # 检查文件修改时间
            try:
                mtime = file_path.stat().st_mtime
                cached_mtime = cache_entry.get("mtime", 0)

                # 如果文件未修改，直接返回缓存
                if mtime == cached_mtime:
                    return cache_entry.get("hash")
            except Exception:
                pass

        # 计算哈希
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            mtime = file_path.stat().st_mtime

            # 更新缓存
            self.cache[rel_path] = {
                "hash": file_hash,
                "mtime": mtime,
                "size": len(content),
                "cached_at": datetime.now().isoformat(),
            }

            return file_hash
        except Exception:
            return None

    def get_file_line_count(self, file_path: Path, force_recalculate: bool = False) -> int | None:
        """获取文件行数（带缓存）

        Args:
            file_path: 文件路径
            force_recalculate: 是否强制重新计算

        Returns:
            文件行数，如果无法计算则返回 None
        """
        # macOS 兼容：resolve() 解决 /var vs /private/var 符号链接问题
        resolved_file = file_path.resolve()
        resolved_root = self.project_root.resolve()

        try:
            rel_path = str(resolved_file.relative_to(resolved_root))
        except ValueError:
            # 如果文件不在 project_root 下，使用绝对路径
            rel_path = str(resolved_file)

        # 检查缓存
        if not force_recalculate and rel_path in self.cache:
            cache_entry = self.cache[rel_path]

            # 检查文件修改时间和大小
            try:
                mtime = file_path.stat().st_mtime
                size = file_path.stat().st_size
                cached_mtime = cache_entry.get("mtime", 0)
                cached_size = cache_entry.get("size", 0)

                # 如果文件未修改，直接返回缓存
                if mtime == cached_mtime and size == cached_size:
                    return cache_entry.get("lines")
            except Exception:
                pass

        # 计算行数
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = len(content.split("\n"))
            mtime = file_path.stat().st_mtime
            size = file_path.stat().st_size  # 使用字节数（与缓存检查一致）

            # 更新缓存
            if rel_path in self.cache:
                self.cache[rel_path]["lines"] = lines
                self.cache[rel_path]["mtime"] = mtime
                self.cache[rel_path]["size"] = size  # 存储字节数
                self.cache[rel_path]["cached_at"] = datetime.now().isoformat()
            else:
                self.cache[rel_path] = {
                    "hash": None,
                    "mtime": mtime,
                    "size": size,  # 存储字节数
                    "lines": lines,
                    "cached_at": datetime.now().isoformat(),
                }

            return lines
        except Exception:
            return None

    def save(self) -> None:
        """保存缓存到磁盘"""
        self._save_cache()

    def clear(self) -> None:
        """清空缓存"""
        self.cache = {}
        if self.cache_path.exists():
            try:
                self.cache_path.unlink()
            except Exception:
                pass

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        total = len(self.cache)
        with_hash = sum(1 for v in self.cache.values() if v.get("hash"))
        with_lines = sum(1 for v in self.cache.values() if v.get("lines") is not None)

        return {
            "total_entries": total,
            "with_hash": with_hash,
            "with_lines": with_lines,
            "cache_file": str(self.cache_path),
        }


def _process_file(file_path: Path, project_root: Path) -> tuple[str, str | None, int | None] | None:
    """处理单个文件（用于并行扫描）

    Args:
        file_path: 文件路径
        project_root: 项目根目录

    Returns:
        元组 (rel_path, hash, line_count) 或 None
    """
    import hashlib

    # macOS 兼容：使用 resolved 路径
    resolved_file = file_path.resolve()
    resolved_root = Path(project_root).resolve()
    rel_path = str(resolved_file.relative_to(resolved_root))

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        line_count = len(content.split("\n"))
        return (rel_path, file_hash, line_count)
    except Exception:
        return None


def capture_state_with_cache(
    project_root: Path,
    cache_mgr: HashCacheManager | None = None,
    parallel: bool = True,
    max_workers: int = 4,
) -> dict[str, Any]:
    """使用缓存捕获项目状态（支持并行扫描）

    Args:
        project_root: 项目根目录
        cache_mgr: 哈希缓存管理器（可选）
        parallel: 是否使用并行扫描
        max_workers: 最大并行线程数

    Returns:
        项目状态字典
    """
    py_files = []
    total_lines = 0
    file_hashes = {}
    line_counts = {}

    # 创建缓存管理器（如果未提供）
    if cache_mgr is None:
        cache_mgr = HashCacheManager(project_root)

    # 收集所有 Python 文件
    all_files = []
    for f in project_root.rglob("*.py"):
        # macOS 兼容：使用 resolved 路径确保一致性
        resolved_f = f.resolve()
        resolved_root = Path(project_root).resolve()

        rel = resolved_f.relative_to(resolved_root)
        parts = rel.parts

        # 跳过虚拟环境等
        if any(p in (".venv", "venv", "__pycache__", ".git", "node_modules",
                     "build", "dist") for p in parts):
            continue

        all_files.append(f)
        py_files.append(str(rel))

    # 并行扫描
    if parallel and len(all_files) > 10:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_process_file, f, project_root): f for f in all_files}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    rel_path, file_hash, line_count = result
                    if file_hash:
                        file_hashes[rel_path] = file_hash
                    if line_count is not None:
                        total_lines += line_count
                        line_counts[rel_path] = line_count

                    # 更新缓存
                    file_path = futures[future]
                    try:
                        mtime = file_path.stat().st_mtime
                        size = file_path.stat().st_size
                        cache_mgr.cache[rel_path] = {
                            "hash": file_hash,
                            "mtime": mtime,
                            "size": size,
                            "lines": line_count,
                            "cached_at": datetime.now().isoformat(),
                        }
                    except Exception:
                        pass
    else:
        # 串行扫描（小型项目）
        for f in all_files:
            # macOS 兼容：使用 resolved 路径
            resolved_f = f.resolve()
            resolved_root = Path(project_root).resolve()
            rel_path = str(resolved_f.relative_to(resolved_root))

            file_hash = cache_mgr.get_file_hash(f)
            if file_hash:
                file_hashes[rel_path] = file_hash

            line_count = cache_mgr.get_file_line_count(f)
            if line_count is not None:
                total_lines += line_count
                line_counts[rel_path] = line_count

    # 保存缓存
    cache_mgr.save()

    return {
        "py_files": sorted(py_files),
        "total_lines": total_lines,
        "file_hashes": file_hashes,
        "line_counts": line_counts,
    }

