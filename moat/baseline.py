"""基线管理 - L4检查 + 架构基线"""
import json
import shutil
from datetime import datetime
from pathlib import Path


class BaselineManager:
    """管理项目基线数据（L4检查 + 架构基线）"""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.baseline_path = self.project_root / ".moat" / "baseline.json"
        self.baselines_dir = self.project_root / ".moat" / "baselines"
        self.current_baseline_file = self.project_root / ".moat" / "current_baseline"
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

    # ========== L4 基线检查（原有功能）==========

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
        from moat.checks.l4_baseline import _capture_state
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

    # ========== 架构基线管理（新增功能）==========

    def create_architecture_baseline(
        self,
        name: str,
        description: str = "",
        verification_report=None,
    ) -> str:
        """
        创建架构基线

        Args:
            name: 基线名称（如 "v1.0.0"）
            description: 基线描述
            verification_report: 验收报告（可选）

        Returns:
            基线ID
        """
        timestamp = datetime.now()
        baseline_id = name

        # 创建基线目录
        baseline_dir = self.baselines_dir / baseline_id
        baseline_dir.mkdir(parents=True, exist_ok=True)

        # 收集基线数据
        baseline_data = {
            "id": baseline_id,
            "name": name,
            "description": description,
            "timestamp": timestamp.isoformat(),
            "project_path": str(self.project_root),
        }

        # 如果有验收报告，保存报告
        if verification_report:
            report_file = baseline_dir / "verification_report.json"
            with open(report_file, "w") as f:
                json.dump(verification_report.to_dict(), f, indent=2, ensure_ascii=False)

            baseline_data["overall_score"] = verification_report.overall_score
            baseline_data["passed"] = verification_report.passed

        # 复制相关文件到基线
        files_to_copy = [
            ".moat/truth_document.md",
            ".moat/architecture_report.md",
            ".moat/runtime_evidence.md",
            ".moat/gatekeeper_config.json",
        ]

        for file_path in files_to_copy:
            src = self.project_root / file_path
            if src.exists():
                dst = baseline_dir / Path(file_path).name
                dst.write_text(src.read_text())

        # 保存基线元数据
        metadata_file = baseline_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(baseline_data, f, indent=2, ensure_ascii=False)

        # 更新当前基线
        self._set_current_baseline(baseline_id)

        return baseline_id

    def list_architecture_baselines(self) -> list[dict]:
        """列出所有架构基线"""
        baselines = []

        if not self.baselines_dir.exists():
            return baselines

        for baseline_dir in sorted(self.baselines_dir.iterdir()):
            if not baseline_dir.is_dir():
                continue

            metadata_file = baseline_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                baselines.append(metadata)
            except Exception:
                continue

        return baselines

    def get_architecture_baseline(self, baseline_id: str) -> dict | None:
        """获取指定基线的详细信息"""
        baseline_dir = self.baselines_dir / baseline_id
        metadata_file = baseline_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file) as f:
                return json.load(f)
        except Exception:
            return None

    def diff_architecture_baselines(self, baseline_a: str, baseline_b: str) -> dict:
        """对比两个架构基线"""
        data_a = self.get_architecture_baseline(baseline_a)
        data_b = self.get_architecture_baseline(baseline_b)

        if not data_a or not data_b:
            return {"error": "基线不存在"}

        diff = {
            "baseline_a": baseline_a,
            "baseline_b": baseline_b,
            "timestamp_a": data_a.get("timestamp"),
            "timestamp_b": data_b.get("timestamp"),
            "changes": [],
        }

        # 对比关键字段
        fields_to_compare = [
            "overall_score",
            "passed",
            "description",
        ]

        for field in fields_to_compare:
            val_a = data_a.get(field)
            val_b = data_b.get(field)

            if val_a != val_b:
                diff["changes"].append({
                    "field": field,
                    "from": val_a,
                    "to": val_b,
                })

        return diff

    def rollback_architecture_baseline(self, baseline_id: str) -> bool:
        """回滚到指定架构基线"""
        baseline_dir = self.baselines_dir / baseline_id

        if not baseline_dir.exists():
            return False

        # 恢复基线文件
        files_to_restore = [
            ("truth_document.md", ".moat/truth_document.md"),
            ("architecture_report.md", ".moat/architecture_report.md"),
            ("runtime_evidence.md", ".moat/runtime_evidence.md"),
            ("gatekeeper_config.json", ".moat/gatekeeper_config.json"),
        ]

        restored = []
        for src_name, dst_path in files_to_restore:
            src = baseline_dir / src_name
            if src.exists():
                dst = self.project_root / dst_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(src.read_text())
                restored.append(dst_path)

        # 更新当前基线
        self._set_current_baseline(baseline_id)

        return len(restored) > 0

    def delete_architecture_baseline(self, baseline_id: str) -> bool:
        """删除指定架构基线"""
        baseline_dir = self.baselines_dir / baseline_id

        if not baseline_dir.exists():
            return False

        try:
            shutil.rmtree(baseline_dir)

            # 如果删除的是当前基线，更新当前基线文件
            if self._get_current_baseline() == baseline_id:
                self.current_baseline_file.unlink(missing_ok=True)

            return True
        except Exception:
            return False

    def get_current_architecture_baseline(self) -> str | None:
        """获取当前架构基线ID"""
        return self._get_current_baseline()

    def _get_current_baseline(self) -> str | None:
        """获取当前基线ID（内部方法）"""
        if not self.current_baseline_file.exists():
            return None

        try:
            return self.current_baseline_file.read_text().strip()
        except Exception:
            return None

    def _set_current_baseline(self, baseline_id: str) -> None:
        """设置当前基线（内部方法）"""
        self.current_baseline_file.write_text(baseline_id)
