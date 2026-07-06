"""实时日志监控"""
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime


# 颜色代码
COLORS = {
    "ERROR": "\033[91m",      # 红
    "WARNING": "\033[93m",   # 黄
    "INFO": "\033[94m",      # 蓝
    "OK": "\033[92m",        # 绿
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}


def start_monitor(log_path: Path, color: bool = True, filter_pattern: str = "ERROR|Traceback"):
    """启动实时监控"""
    if not log_path.exists():
        print(f"❌ 日志文件不存在: {log_path}")
        return

    # 先统计已有的错误
    existing = _count_existing_errors(log_path, filter_pattern)
    if existing > 0:
        msg = f"发现 {existing} 个已有错误"
        if color:
            print(f"{COLORS['WARNING']}{msg}{COLORS['RESET']}")
        else:
            print(f"⚠ {msg}")

    print(f"🔍 监控中: {log_path}")
    print(f"   过滤: {filter_pattern}")
    print(f"   按 Ctrl+C 停止\n")

    try:
        process = subprocess.Popen(
            ["tail", "-f", "-n", "0", str(log_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        pattern = re.compile(filter_pattern)
        error_count = existing

        while True:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue

            line = line.strip()
            if not line:
                continue

            if pattern.search(line):
                error_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")

                # 判断级别
                if "ERROR" in line or "Traceback" in line:
                    level = "ERROR"
                elif "WARNING" in line or "WARN" in line:
                    level = "WARNING"
                else:
                    level = "INFO"

                if color:
                    c = COLORS.get(level, COLORS["INFO"])
                    print(f"{c}[{timestamp}][{level}] {line}{COLORS['RESET']}")
                else:
                    print(f"[{timestamp}][{level}] {line}")

    except KeyboardInterrupt:
        print(f"\n\n📊 本次监控共发现 {error_count - existing} 个新错误")
    finally:
        process.terminate()


def _count_existing_errors(log_path: Path, pattern: str) -> int:
    """统计日志中已有的错误数量"""
    try:
        result = subprocess.run(
            ["grep", "-c", "-E", pattern, str(log_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
        return 0
    except Exception:
        return 0


def read_recent_errors(log_path: Path, lines: int = 50,
                        filter_pattern: str = "ERROR|Traceback") -> list[dict]:
    """读取最近的错误"""
    if not log_path.exists():
        return []

    try:
        result = subprocess.run(
            ["tail", "-n", str(lines * 3), str(log_path)],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.split("\n")
    except Exception:
        return []

    pattern = re.compile(filter_pattern)
    errors = []
    for line in output:
        if pattern.search(line):
            errors.append({
                "timestamp": datetime.now().isoformat(),
                "message": line.strip(),
                "level": "ERROR" if "ERROR" in line else "WARN",
            })

    return errors[-lines:]