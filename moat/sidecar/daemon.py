"""Sidecar Daemon — Moat 实时感知守护进程

后台运行，监控文件变化，实时运行增量检查。
提供 HTTP API 供 VS Code 插件和其他工具调用。

Usage:
    moat sidecar start          # 启动守护进程
    moat sidecar stop           # 停止守护进程
    moat sidecar status         # 查看状态
    moat sidecar restart        # 重启守护进程

Features:
    - 实时文件监控（使用 watchdog）
    - 增量检查（只检查变更文件）
    - HTTP API（FastAPI）
    - 健康检查端点
    - PID 文件管理
    - 日志文件记录
"""
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from moat.sidecar.watcher import FileChangeHandler


class SidecarDaemon:
    """Sidecar 守护进程"""

    def __init__(self, project_root: Path):
        """初始化守护进程

        Args:
            project_root: 项目根目录
        """
        self.project = project_root.resolve()
        self.pid_file = self.project / ".moat" / "sidecar.pid"
        self.log_file = self.project / ".moat" / "sidecar.log"
        self.status_file = self.project / ".moat" / "sidecar.json"

    def start(self, foreground: bool = False) -> int:
        """启动守护进程

        Args:
            foreground: 是否在前台运行

        Returns:
            退出码
        """
        # 检查是否已在运行
        if self.is_running():
            print(f"⚠️  Sidecar 已在运行 (PID: {self.get_pid()})")
            return 1

        # 创建目录
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

        if foreground:
            # 前台运行
            print(f"🚀 启动 Sidecar（前台模式）...")
            return self._run_foreground()
        else:
            # 后台运行
            print(f"🚀 启动 Sidecar（后台模式）...")
            return self._run_background()

    def stop(self) -> int:
        """停止守护进程

        Returns:
            退出码
        """
        pid = self.get_pid()
        if not pid:
            print("ℹ️  Sidecar 未运行")
            return 0

        print(f"🛑 停止 Sidecar (PID: {pid})...")

        try:
            os.kill(pid, signal.SIGTERM)

            # 等待进程结束
            for _ in range(10):
                try:
                    os.kill(pid, 0)  # 检查进程是否存在
                    time.sleep(0.5)
                except ProcessLookupError:
                    break
            else:
                # 强制杀死
                print(f"⚠️  进程未响应，强制终止...")
                os.kill(pid, signal.SIGKILL)

            # 清理 PID 文件
            if self.pid_file.exists():
                self.pid_file.unlink()

            print(f"✅ Sidecar 已停止")
            return 0

        except ProcessLookupError:
            print(f"⚠️  进程不存在，清理 PID 文件")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return 0
        except PermissionError:
            print(f"❌ 权限不足，无法停止进程")
            return 1

    def restart(self) -> int:
        """重启守护进程

        Returns:
            退出码
        """
        self.stop()
        time.sleep(1)
        return self.start()

    def status(self) -> dict[str, Any]:
        """获取守护进程状态

        Returns:
            状态信息字典
        """
        pid = self.get_pid()
        is_running = self._check_process(pid) if pid else False

        status = {
            "running": is_running,
            "pid": pid,
            "project": str(self.project),
            "pid_file": str(self.pid_file),
            "log_file": str(self.log_file),
            "status_file": str(self.status_file),
        }

        # 加载详细状态
        if self.status_file.exists():
            try:
                with open(self.status_file) as f:
                    status_data = json.load(f)
                    status.update(status_data)
            except Exception:
                pass

        return status

    def get_pid(self) -> int | None:
        """获取守护进程 PID

        Returns:
            PID 或 None
        """
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            return pid
        except Exception:
            return None

    def is_running(self) -> bool:
        """检查守护进程是否在运行

        Returns:
            是否在运行
        """
        pid = self.get_pid()
        if not pid:
            return False
        return self._check_process(pid)

    def _check_process(self, pid: int) -> bool:
        """检查进程是否存在

        Args:
            pid: 进程 ID

        Returns:
            进程是否存在
        """
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # 进程存在但无法访问

    def _run_foreground(self) -> int:
        """前台运行

        Returns:
            退出码
        """
        self._write_pid()

        try:
            handler = FileChangeHandler(str(self.project))
            handler.start()

            print(f"✅ Sidecar 已启动")
            print(f"   监控目录: {self.project}")
            print(f"   日志文件: {self.log_file}")
            print(f"   按 Ctrl+C 停止\n")

            # 保持运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n🛑 收到停止信号")
        finally:
            try:
                handler.stop()
            except Exception:
                pass
            self._cleanup()
            return 0

    def _run_background(self) -> int:
        """后台运行

        Returns:
            退出码
        """
        # 使用 subprocess 启动后台进程
        script = f"""
import sys
import os

sys.path.insert(0, {str(self.project)!r})

from moat.sidecar.daemon import SidecarDaemon

daemon = SidecarDaemon({str(self.project)!r})
sys.exit(daemon._run_foreground())
"""

        # 启动后台进程
        process = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # 等待一下确保启动
        time.sleep(1)

        # 检查是否成功
        daemon = SidecarDaemon(self.project)
        if daemon.is_running():
            print(f"✅ Sidecar 已启动（后台）")
            print(f"   PID: {daemon.get_pid()}")
            print(f"   日志: {self.log_file}")
            print(f"\n使用 `moat sidecar status` 查看状态")
            print(f"使用 `moat sidecar stop` 停止")
            return 0
        else:
            print(f"❌ 启动失败")
            return 1

    def _write_pid(self) -> None:
        """写入 PID 文件"""
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

    def _cleanup(self) -> None:
        """清理资源"""
        if self.pid_file.exists():
            self.pid_file.unlink()
        if self.status_file.exists():
            self.status_file.unlink()


def print_status(status: dict[str, Any]) -> None:
    """打印状态信息

    Args:
        status: 状态字典
    """
    print(f"\n{'=' * 60}")
    print(f"  Moat Sidecar 状态")
    print(f"{'=' * 60}\n")

    if status.get("running"):
        print(f"✅ 状态: 运行中")
        print(f"🆔  PID: {status.get('pid')}")
    else:
        print(f"⭕ 状态: 已停止")

    print(f"📁  项目: {status.get('project')}")
    print(f"📄  PID 文件: {status.get('pid_file')}")
    print(f"📝  日志文件: {status.get('log_file')}")

    # 额外的状态信息
    if "last_check" in status:
        print(f"⏰  上次检查: {status.get('last_check')}")
    if "total_checks" in status:
        print(f"📊  总检查次数: {status.get('total_checks')}")
    if "errors_detected" in status:
        print(f"❌  检测到错误: {status.get('errors_detected')}")

    print(f"\n{'=' * 60}\n")
