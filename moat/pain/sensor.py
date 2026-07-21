"""
Moat Sensor — 运行时神经末梢

给函数装上传感器，异常时自动报警。

用法:
    from moat.pain.sensor import moat_sensor

    @moat_sensor(component_id="db.query", critical=True)
    def query_user(id: str):
        ...

    @moat_sensor  # 自动推断 component_id
    def list_projects():
        ...

传感器事件自动写入:
    1. 结构化日志 (logging.ERROR / WARNING)
    2. 内存事件总线 (Dashboard 消费)
    3. Webhook 告警 (仅 PANIC 级别)
"""

import functools
import json
import logging
import os
import threading
import time
import traceback
from collections import deque, OrderedDict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger("moat.sensor")

# ── 常量 ──────────────────────────────────────────────────

# 错误去重窗口（秒）
DEDUP_WINDOW = 10

# 事件总线容量
EVENT_BUS_MAX = 1000

# 错误去重 / 健康追踪的最大组件数
MAX_TRACKED_COMPONENTS = 500

# 正常事件上报阈值（ms，超过此阈值才写入日志避免高频噪音
# 可通过环境变量 MOAT_SENSOR_OK_THRESHOLD_MS 覆盖，设为 0 表示上报所有事件）
# 默认 30000ms（30 秒）：仅异常/错误才上报，正常无感
OK_REPORT_THRESHOLD_MS = int(os.environ.get(
    "MOAT_SENSOR_OK_THRESHOLD_MS",
    "30000"
))

# 共享事件文件（跨进程持久化）
SENSOR_DIR = os.environ.get(
    "MOAT_SENSOR_DIR",
    os.path.join(os.path.expanduser("~"), ".moat"),
)
EVENT_FILE = os.path.join(SENSOR_DIR, "events.jsonl")


# ── 状态枚举 ──────────────────────────────────────────────

class SensorStatus:
    OK = "OK"
    DEGRADED = "DEGRADED"
    PANIC = "PANIC"


# ── 数据类型 ──────────────────────────────────────────────

@dataclass
class SensorEvent:
    """一次传感器触发事件"""
    component_id: str
    status: str  # OK / DEGRADED / PANIC
    duration_ms: float
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ── 全局状态 ──────────────────────────────────────────────

# 错误去重记录（LRU，上限 MAX_TRACKED_COMPONENTS）
_error_history: OrderedDict[str, float] = OrderedDict()

# 内存事件总线（线程安全）
_lock = threading.Lock()
_event_bus: deque[SensorEvent] = deque(maxlen=EVENT_BUS_MAX)


# ── Component Health Tracker ──────────────────────────────

class ComponentHealthTracker:
    """组件健康追踪器（主动记录模式）

    用于非函数粒度的场景——比如你想手动记录某个服务的健康状态，
    或者需要根据组件健康情况生成诊断报告。

    用法:
        tracker = ComponentHealthTracker()

        # 记录成功/失败
        tracker.record_success("secret_sanitization")
        tracker.record_failure("memory_bridge", "Connection timeout")

        # 查询
        tracker.is_healthy("secret_sanitization")  # True/False
        tracker.get_health_summary()               # dict
        tracker.build_health_section()             # markdown 文本
    """

    FAILURE_THRESHOLD = 2  # 连续失败 N 次标记为不健康

    def __init__(self):
        self._lock = threading.Lock()
        # OrderedDict 实现 LRU，超出上限时淘汰最旧组件
        self._state: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def record_success(self, component_id: str):
        """记录一次成功"""
        with self._lock:
            entry = self._state.setdefault(component_id, {
                "last_success": 0.0,
                "last_failure": 0.0,
                "consecutive_failures": 0,
                "last_error": "",
            })
            # LRU: 移动到末尾
            self._state.move_to_end(component_id)
            entry["last_success"] = time.time()
            entry["consecutive_failures"] = 0
            self._evict_oldest()

    def record_failure(self, component_id: str, error: str = ""):
        """记录一次失败"""
        with self._lock:
            entry = self._state.setdefault(component_id, {
                "last_success": 0.0,
                "last_failure": 0.0,
                "consecutive_failures": 0,
                "last_error": "",
            })
            # LRU: 移动到末尾
            self._state.move_to_end(component_id)
            entry["last_failure"] = time.time()
            entry["consecutive_failures"] += 1
            entry["last_error"] = error
            self._evict_oldest()

    def _evict_oldest(self):
        """超过上限时淘汰最久未使用的组件"""
        while len(self._state) > MAX_TRACKED_COMPONENTS:
            self._state.popitem(last=False)

    def is_healthy(self, component_id: str) -> bool:
        """组件是否健康"""
        entry = self._state.get(component_id)
        if entry is None:
            return True
        return entry["consecutive_failures"] < self.FAILURE_THRESHOLD

    def get_component_state(self, component_id: str) -> dict[str, Any]:
        """获取单个组件状态"""
        return self._state.get(component_id, {
            "last_success": 0.0,
            "last_failure": 0.0,
            "consecutive_failures": 0,
            "last_error": "",
        })

    def get_health_summary(self) -> dict[str, Any]:
        """获取完整健康状态"""
        with self._lock:
            healthy = []
            degraded = []
            details = {}

            for cid, entry in self._state.items():
                details[cid] = dict(entry)
                if entry["consecutive_failures"] < self.FAILURE_THRESHOLD:
                    healthy.append(cid)
                else:
                    degraded.append(cid)

            return {
                "healthy": sorted(healthy),
                "degraded": sorted(degraded),
                "details": details,
            }

    def build_health_section(self, include_healthy: bool = True) -> str:
        """构建可在 system prompt 中注入的健康状态段落"""
        summary = self.get_health_summary()
        if not summary["healthy"] and not summary["degraded"]:
            return ""

        lines = ["# 组件健康状态\n"]

        for cid in summary["healthy"]:
            if include_healthy:
                lines.append(f"- ✅ **{cid}**: 正常运行")

        for cid in summary["degraded"]:
            entry = summary["details"][cid]
            ago = self._format_ago(entry["last_failure"])
            error = entry.get("last_error", "未知错误")
            lines.append(f"- ⚠️ **{cid}**: 失败 ({ago})")
            lines.append(f"  - 📋 错误: {error}")

        if summary["degraded"]:
            lines.append("")
            lines.append("💡 **提示**: 如有组件失败，可以尝试重启后端服务或检查日志。")

        return "\n".join(lines)

    def reset(self):
        """清空所有记录"""
        with self._lock:
            self._state.clear()

    @staticmethod
    def _format_ago(timestamp: float) -> str:
        """格式化时间差"""
        diff = time.time() - timestamp
        if diff < 60:
            return f"距现在 {int(diff)} 秒前"
        elif diff < 3600:
            return f"距现在 {int(diff // 60)} 分钟前"
        elif diff < 86400:
            return f"距现在 {int(diff // 3600)} 小时前"
        else:
            return f"距现在 {int(diff // 86400)} 天前"


# 全局单例
health_tracker = ComponentHealthTracker()


def _should_report(component_id: str) -> bool:
    """10 秒内同一个组件只报一次"""
    now = time.monotonic()
    last = _error_history.get(component_id, 0.0)
    if now - last < DEDUP_WINDOW:
        return False
    # LRU: 移动到末尾表示最近使用
    if component_id in _error_history:
        _error_history.move_to_end(component_id)
    _error_history[component_id] = now
    # 超过上限时淘汰最旧记录
    if len(_error_history) > MAX_TRACKED_COMPONENTS:
        _error_history.popitem(last=False)
    return True


# ── 装饰器 ────────────────────────────────────────────────

def moat_sensor(
    func: Optional[Callable] = None,
    *,
    component_id: Optional[str] = None,
    capture_context: bool = True,
    critical: bool = False,
):
    """组件传感器装饰器

    可以无参数使用::

        @moat_sensor
        def my_func(): ...

    也可以带参数::

        @moat_sensor(component_id="db.query", critical=True)
        def my_func(): ...

    Args:
        func: 被装饰的函数（无参数调用时自动传入）
        component_id: 组件标识，默认使用 ``module.qualname``
        capture_context: 异常时是否捕获上下文快照
        critical: 是否为关键路径（PANIC 时触发 webhook 告警）
    """
    if func is not None:
        # 无参数模式: @moat_sensor
        return _build_wrapper(
            func,
            component_id=component_id,
            capture_context=capture_context,
            critical=critical,
        )

    # 带参数模式: @moat_sensor(...)
    def decorator(f: Callable) -> Callable:
        return _build_wrapper(
            f,
            component_id=component_id,
            capture_context=capture_context,
            critical=critical,
        )

    return decorator


def _build_wrapper(
    func: Callable,
    component_id: Optional[str],
    capture_context: bool,
    critical: bool,
) -> Callable:
    """构建传感器包装器"""
    sensor_id = component_id or f"{func.__module__}.{func.__qualname__}"

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000

            # 正常执行：仅慢操作写日志，避免高频噪音
            if duration > OK_REPORT_THRESHOLD_MS:
                _emit(SensorEvent(
                    component_id=sensor_id,
                    status=SensorStatus.OK,
                    duration_ms=round(duration, 2),
                ))
            return result

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            status = SensorStatus.PANIC if critical else SensorStatus.DEGRADED

            event = SensorEvent(
                component_id=sensor_id,
                status=status,
                duration_ms=round(duration, 2),
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
                context=_capture_snapshot() if capture_context else {},
            )

            if _should_report(sensor_id):
                _emit(event)
                if critical:
                    _trigger_alert(event)

            raise  # 不吞异常

    return wrapper


# ── 异步支持 ──────────────────────────────────────────────

def moat_sensor_async(
    func: Optional[Callable] = None,
    *,
    component_id: Optional[str] = None,
    capture_context: bool = True,
    critical: bool = False,
):
    """异步函数版传感器（用法同 moat_sensor）"""
    if func is not None:
        return _build_async_wrapper(
            func,
            component_id=component_id,
            capture_context=capture_context,
            critical=critical,
        )

    def decorator(f: Callable) -> Callable:
        return _build_async_wrapper(
            f,
            component_id=component_id,
            capture_context=capture_context,
            critical=critical,
        )

    return decorator


def _build_async_wrapper(
    func: Callable,
    component_id: Optional[str],
    capture_context: bool,
    critical: bool,
) -> Callable:
    """构建异步传感器包装器"""
    import asyncio

    sensor_id = component_id or f"{func.__module__}.{func.__qualname__}"

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000

            if duration > OK_REPORT_THRESHOLD_MS:
                _emit(SensorEvent(
                    component_id=sensor_id,
                    status=SensorStatus.OK,
                    duration_ms=round(duration, 2),
                ))
            return result

        except asyncio.CancelledError:
            # Task 被取消是正常生命周期的一部分，不报
            raise

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            status = SensorStatus.PANIC if critical else SensorStatus.DEGRADED

            event = SensorEvent(
                component_id=sensor_id,
                status=status,
                duration_ms=round(duration, 2),
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
                context=_capture_snapshot() if capture_context else {},
            )

            if _should_report(sensor_id):
                _emit(event)
                if critical:
                    _trigger_alert(event)

            raise

    return wrapper


# ── 内部函数 ──────────────────────────────────────────────

def _ensure_sensor_dir():
    """确保传感器目录存在"""
    os.makedirs(SENSOR_DIR, exist_ok=True)


def _append_to_file(event: SensorEvent):
    """追加事件到共享 JSONL 文件（跨进程持久化）"""
    try:
        _ensure_sensor_dir()
        line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
        # 追加写，不锁文件（单行写入通常原子）
        with open(EVENT_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        logger.exception("[SENSOR] 写入事件文件失败")


def _read_events_from_file(limit: int = 200) -> list[dict[str, Any]]:
    """从共享文件读取最近事件"""
    try:
        if not os.path.exists(EVENT_FILE):
            return []
        events: list[dict[str, Any]] = []
        with open(EVENT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events[-limit:]
    except Exception:
        logger.exception("[SENSOR] 读取事件文件失败")
        return []


def _emit(event: SensorEvent):
    """写入日志 + 推入事件总线 + 写入共享文件"""
    # 1. 结构化日志
    level = logging.ERROR if event.status == SensorStatus.PANIC else logging.WARNING
    logger.log(
        level,
        "[SENSOR:%(component)s] status=%(status)s duration=%(duration)sms error=%(error)s",
        {
            "component": event.component_id,
            "status": event.status,
            "duration": event.duration_ms,
            "error": event.error or "",
        },
    )

    # 2. 事件总线（内存）
    with _lock:
        _event_bus.append(event)

    # 3. 共享文件（跨进程）
    _append_to_file(event)


def _trigger_alert(event: SensorEvent):
    """PANIC 级错误触发即时告警"""
    alert_url = os.environ.get("MOAT_ALERT_WEBHOOK")
    if not alert_url:
        return

    payload = json.dumps({
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🚨 [PANIC] {event.component_id}",
                }
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": (
                    f"**组件**: `{event.component_id}`\n"
                    f"**状态**: {event.status}\n"
                    f"**错误**: `{event.error}`\n"
                    f"**耗时**: {event.duration_ms}ms\n"
                    f"**类型**: {event.error_type}"
                )}},
            ],
        },
    })

    try:
        from moat.notifier import _detect_platform, _send_webhook
        platform = _detect_platform(alert_url)
        _send_webhook(alert_url, payload, platform)
    except Exception:
        logger.exception("[SENSOR] 告警发送失败")


def _capture_snapshot() -> dict[str, Any]:
    """捕获当前上下文快照（轻量级）"""
    return {
        "thread": threading.current_thread().name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── 公共查询接口 ──────────────────────────────────────────

def get_recent_events(
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """获取最近传感器事件

    Args:
        status: 筛选状态（None 返回全部）
        limit: 最多返回条数

    Returns:
        事件字典列表
    """
    with _lock:
        memory_events = list(_event_bus)

    # 合并文件中的事件（跨进程）
    file_events = _read_events_from_file(limit=limit)

    # 以文件事件为主（包含其他进程的事件），去重合并
    seen_ids: set[str] = set()
    merged: list[dict[str, Any]] = []

    for e in reversed(file_events):
        uid = e.get("timestamp", "") + e.get("component_id", "")
        if uid not in seen_ids:
            seen_ids.add(uid)
            merged.append(e)

    for e in reversed(memory_events):
        uid = e.timestamp + e.component_id
        if uid not in seen_ids:
            seen_ids.add(uid)
            merged.append(e.to_dict())

    merged.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    if status:
        merged = [e for e in merged if e.get("status") == status]

    return merged[:limit]


def get_component_stats(component_id: str) -> dict[str, Any]:
    """获取组件统计

    Returns:
        {
            "component_id": ...,
            "total_events": ...,
            "panic_count": ...,
            "degraded_count": ...,
            "last_event": ...,
            "last_error": ...,
        }
    """
    with _lock:
        events = [e for e in _event_bus if e.component_id == component_id]

    if not events:
        return {"component_id": component_id, "total_events": 0}

    last = events[-1]
    return {
        "component_id": component_id,
        "total_events": len(events),
        "panic_count": sum(1 for e in events if e.status == "PANIC"),
        "degraded_count": sum(1 for e in events if e.status == "DEGRADED"),
        "last_event": {
            "status": last.status,
            "duration_ms": last.duration_ms,
            "error": last.error,
            "timestamp": last.timestamp,
        },
    }


def get_health_summary() -> dict[str, Any]:
    """获取全局健康摘要

    Returns:
        {
            "healthy_components": [...],
            "degraded_components": [...],
            "panic_components": [...],
            "total_events": ...,
        }
    """
    with _lock:
        events = list(_event_bus)

    if not events:
        return {
            "healthy_components": [],
            "degraded_components": [],
            "panic_components": [],
            "total_events": 0,
        }

    # 按组件聚合最新状态
    latest: dict[str, SensorEvent] = {}
    for e in events:
        latest[e.component_id] = e

    result = {
        "healthy_components": [],
        "degraded_components": [],
        "panic_components": [],
        "total_events": len(events),
    }

    for cid, ev in latest.items():
        entry = {
            "component_id": cid,
            "last_seen": ev.timestamp,
            "last_duration_ms": ev.duration_ms,
        }
        if ev.status == "OK":
            result["healthy_components"].append(entry)
        elif ev.status == "DEGRADED":
            result["degraded_components"].append(entry)
        elif ev.status == "PANIC":
            result["panic_components"].append(entry)

    return result


def reset_event_bus():
    """清空事件总线 + 共享文件（测试用）"""
    global _event_bus, _error_history
    with _lock:
        _event_bus = deque(maxlen=EVENT_BUS_MAX)
        _error_history = OrderedDict()
    try:
        if os.path.exists(EVENT_FILE):
            os.remove(EVENT_FILE)
    except Exception:
        pass
