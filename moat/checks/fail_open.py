"""Fail-open 装饰器

设计原则：对于辅助工具，不打扰比发现 Bug 更重要。

当检查器遇到以下情况时，应该"通过"而不是"阻塞"：
- Tree-sitter 解析失败
- 文件读取失败
- 网络超时（AI 接口）
- 任何未预期的异常

使用方式：
    @fail_open
    def check_something(self, file_path):
        ...
"""
import functools
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def fail_open(default_return=None, log_level=logging.WARNING):
    """Fail-open 装饰器

    当函数抛出异常时，返回 default_return 而不是向上抛出异常。
    对于辅助工具，不打扰比发现 Bug 更重要。

    Args:
        default_return: 异常时返回的默认值（默认 None）
        log_level: 异常时的日志级别（默认 WARNING）

    Example:
        @fail_open(default_return=[])
        def check_file(self, path):
            # 如果这里抛出异常，会返回 [] 而不是向上传播
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录警告（但不要阻断流程）
                logger.log(
                    log_level,
                    f"[{func.__name__}] 执行失败，已跳过（Fail-open）: {e}"
                )
                return default_return
        return wrapper
    return decorator


def fail_open_safe(default_return=None):
    """Fail-open 装饰器（静默模式）

    与 fail_open 相同，但不记录日志（完全静默）。
    用于极高频率调用的场景，避免日志污染。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception:
                return default_return
        return wrapper
    return decorator
