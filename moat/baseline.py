"""基线管理"""
import json
from pathlib import Path


class BaselineManager:
    """管理项目基线数据"""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.baseline_path = self.project_root / ".moat" / "baseline.json"

    def save(self):
        """捕获并保存基线"""
        from moat.checks.l4_baseline import capture_baseline
        data = capture_baseline(self.project_root)
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        self.baseline_path.write_text(json.dumps(data, indent=2))
        return data

    def load(self) -> dict | None:
        """加载已有基线"""
        if self.baseline_path.exists():
            try:
                return json.loads(self.baseline_path.read_text())
            except Exception:
                pass
        return None

    def show(self):
        """显示基线"""
        data = self.load()
        if not data:
            print("❌ 没有基线数据。运行: moat baseline save")
            return
        print(f"基线 ({data.get('timestamp', 'N/A')}):")
        print(f"  文件数: {data.get('file_count', '?')}")
        print(f"  代码行数: {data.get('total_lines', '?')}")

    def diff(self):
        """对比当前状态与基线"""
        from moat.checks.l4_baseline import run_baseline_check, _capture_state
        baseline = self.load()
        if not baseline:
            print("❌ 没有基线数据。运行: moat baseline save")
            return

        current = _capture_state(self.project_root)
        print(f"基线   | 当前   | 变化")
        print(f"-------|--------|------")
        print(f"{baseline.get('file_count', '?'):>6} | {len(current['py_files']):>6} | "
              f"{len(current['py_files']) - baseline.get('file_count', 0):>+6}")
        print(f"{baseline.get('total_lines', '?'):>6} | {current['total_lines']:>6} | "
              f"{current['total_lines'] - baseline.get('total_lines', 0):>+6}")