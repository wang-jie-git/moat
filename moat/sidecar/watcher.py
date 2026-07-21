"""File Watcher — 文件变化监控

使用 watchdog 监控项目文件变化，触发增量检查。
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except ImportError:
    # watchdog 未安装（可选依赖）
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # 占位符
    FileSystemEvent = object  # 占位符
    Observer = None

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """文件变化处理器"""

    def __init__(self, project_root: str, debounce_seconds: float = 2.0):
        """初始化处理器

        Args:
            project_root: 项目根目录
            debounce_seconds: 防抖时间（秒），避免频繁触发
        """
        super().__init__()
        self.project = Path(project_root).resolve()
        self.debounce_seconds = debounce_seconds
        self.last_event_time: dict[str, float] = {}
        self.status_file = self.project / ".moat" / "sidecar.json"

        # 排除的文件/目录
        self.ignore_patterns = [
            "*/__pycache__/*",
            "*/node_modules/*",
            "*/.git/*",
            "*/dist/*",
            "*/build/*",
            "*/.pytest_cache/*",
            "*/venv/*",
            "*/.venv/*",
        ]

    def _auto_inject_new_file(self, file_path: Path) -> None:
        """自动为新创建的 Python 文件注入传感器"""
        try:
            from moat.pain.config import load_config
            from moat.ast.injector import inject_project

            config = load_config(str(self.project))
            sensor_cfg = config.get("sensor", {})
            if not sensor_cfg.get("auto_inject", False):
                return

            # 只注入这个新文件
            results = inject_project(
                project_root=str(self.project),
                config=config,
                dry_run=False,
            )
            matched = [r for r in (results if isinstance(results, list) else results[0]) if r.get("injected", 0) > 0 and str(file_path).endswith(r.get("file", ""))]
            if matched:
                total = sum(r["injected"] for r in matched)
                logger.info(f"✅ 自动注入 {total} 个传感器到 {file_path.name}")
        except Exception as e:
            logger.debug(f"自动注入失败: {e}")

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件"""
        if event.is_directory:
            return

        src_path = Path(str(event.src_path)).resolve()

        # 检查是否在忽略列表中
        if self._should_ignore(src_path):
            return

        # 防抖处理
        now = time.time()
        last_time = self.last_event_time.get(str(src_path), 0)
        if now - last_time < self.debounce_seconds:
            return

        self.last_event_time[str(src_path)] = now

        # 触发检查
        self._trigger_check(src_path, "modified")

    def on_created(self, event: FileSystemEvent) -> None:
        """文件创建事件"""
        if event.is_directory:
            return

        src_path = Path(str(event.src_path)).resolve()

        if self._should_ignore(src_path):
            return

        # 新 Python 文件：自动注入传感器
        if src_path.suffix == ".py":
            self._auto_inject_new_file(src_path)

        self._trigger_check(src_path, "created")

    def on_deleted(self, event: FileSystemEvent) -> None:
        """文件删除事件"""
        if event.is_directory:
            return

        src_path = Path(str(event.src_path)).resolve()

        if self._should_ignore(src_path):
            return

        self._trigger_check(src_path, "deleted")

    def on_moved(self, event: Any) -> None:
        """文件移动事件"""
        if event.is_directory:
            return

        src_path = Path(str(event.src_path)).resolve()
        dest_path = Path(str(event.dest_path)).resolve()

        if self._should_ignore(src_path) and self._should_ignore(dest_path):
            return

        # 新 Python 文件（重命名/移动）：自动注入传感器
        if dest_path.suffix == ".py" and not (self._should_ignore(dest_path)):
            self._auto_inject_new_file(dest_path)

        self._trigger_check(dest_path, "moved")

    def _should_ignore(self, path: Path) -> bool:
        """检查路径是否应该被忽略

        Args:
            path: 文件路径

        Returns:
            是否忽略
        """
        # 检查是否在项目内
        try:
            path.relative_to(self.project)
        except ValueError:
            return True

        path_str = str(path)

        # 检查忽略模式
        for pattern in self.ignore_patterns:
            # 简单模式匹配
            if pattern.replace("*/", "").replace("/*", "") in path_str:
                return True

        return False

    def _trigger_check(self, file_path: Path, event_type: str) -> None:
        """触发增量检查

        Args:
            file_path: 变更的文件路径
            event_type: 事件类型
        """
        logger.info(f"检测到 {event_type}: {file_path}")

        try:
            # 运行增量检查
            from moat.ast.diff import diff_project
            from moat.ast.builder import build_skeleton
            from moat.pain.scorer import calculate_total_pain

            # 1. 构建骨架图
            skeleton = build_skeleton(str(self.project))

            # 2. 对比变更
            changes = diff_project(str(self.project))

            if not changes:
                self._update_status(checked=True, errors=0)
                return

            # 3. Pain Score 评估
            errors_as_dict = [{"type": c["type"], "file": c["file"], "message": c.get("function", "")}
                              for c in changes]
            pain_result = calculate_total_pain(errors_as_dict)

            # 4. 更新状态
            self._update_status(
                checked=True,
                errors=pain_result["error_count"],
                pain_score=pain_result["total_score"],
                changes=changes,
            )

            # 5. 记录日志
            self._log_check(file_path, event_type, pain_result)

        except Exception as e:
            logger.error(f"检查失败: {e}", exc_info=True)
            self._update_status(checked=True, errors=-1, error_message=str(e))

    def _update_status(
        self,
        checked: bool = False,
        errors: int = 0,
        pain_score: int = 0,
        changes: list[dict[str, Any]] | None = None,
        error_message: str = "",
    ) -> None:
        """更新状态文件

        Args:
            checked: 是否已检查
            errors: 错误数量
            pain_score: 痛觉评分
            changes: 变更列表
            error_message: 错误消息
        """
        status = {
            "running": True,
            "last_check": datetime.now().isoformat(),
            "last_file": str(self.status_file),
            "total_checks": 0,
            "errors_detected": 0,
            "pain_score": 0,
        }

        # 加载现有状态
        if self.status_file.exists():
            try:
                with open(self.status_file) as f:
                    existing = json.load(f)
                    status.update(existing)
            except Exception:
                pass

        # 更新
        status["running"] = True
        status["last_check"] = datetime.now().isoformat()
        if checked:
            status["total_checks"] = status.get("total_checks", 0) + 1
            status["errors_detected"] = errors
            status["pain_score"] = pain_score

        # 保存
        try:
            with open(self.status_file, "w") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"无法保存状态文件: {e}")

    def _log_check(
        self,
        file_path: Path,
        event_type: str,
        pain_result: dict[str, Any],
    ) -> None:
        """记录检查日志

        Args:
            file_path: 文件路径
            event_type: 事件类型
            pain_result: 痛觉评分结果
        """
        log_line = (
            f"[{datetime.now().isoformat()}] "
            f"Event: {event_type} | "
            f"File: {file_path.name} | "
            f"Errors: {pain_result['error_count']} | "
            f"Pain Score: {pain_result['total_score']}/{pain_result['overall_level']}\n"
        )

        try:
            with open(self.project / ".moat" / "sidecar.log", "a") as f:
                f.write(log_line)
        except Exception:
            pass


class SidecarWatcher:
    """Sidecar 监控器"""

    def __init__(self, project_root: str):
        """初始化监控器

        Args:
            project_root: 项目根目录
        """
        self.project = Path(project_root).resolve()
        self.observer: Observer | None = None
        self.handler: FileChangeHandler | None = None

    def start(self) -> None:
        """启动监控"""
        if not WATCHDOG_AVAILABLE:
            logger.error("watchdog 未安装，无法启动文件监控")
            print("❌ watchdog 未安装")
            print("   安装: pip install watchdog")
            print("   或: pip install moat-ai[sidecar]")
            return

        self.handler = FileChangeHandler(str(self.project))
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.project), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """停止监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
