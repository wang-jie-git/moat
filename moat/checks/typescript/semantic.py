"""CodeGraph 语义检查模块

基于 CodeGraph 知识图谱的 TypeScript/JavaScript 语义分析。
提供变更影响分析、去重逻辑验证等功能。

使用示例:
    from moat.checks.typescript.semantic import SemanticDedupCheck

    check = SemanticDedupCheck(project_root, config)
    results = check.run()
"""
import sqlite3
import json
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult


class CodeGraphClient:
    """CodeGraph 数据库客户端（轻量级，不依赖 codegraph 包）

    直接读取 CodeGraph SQLite 数据库，提供语义查询能力。
    如果 CodeGraph 不可用，所有检查会 gracefully degrade 到 skip。
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> bool:
        """连接数据库"""
        if not self.db_path.exists():
            return False
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception:
            return False

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def query_nodes(self, kind: str | None = None, name_pattern: str | None = None,
                    file_pattern: str | None = None) -> list[sqlite3.Row]:
        """查询节点

        Args:
            kind: 节点类型过滤（function/class/variable...）
            name_pattern: 名称模糊匹配（SQL LIKE 模式）
            file_pattern: 文件路径模糊匹配

        Returns:
            匹配的节点列表
        """
        if not self.conn:
            return []

        query = "SELECT * FROM nodes WHERE 1=1"
        params: list[Any] = []

        if kind:
            query += " AND kind = ?"
            params.append(kind)

        if name_pattern:
            query += " AND name LIKE ?"
            params.append(f"%{name_pattern}%")

        if file_pattern:
            query += " AND file_path LIKE ?"
            params.append(f"%{file_pattern}%")

        query += " ORDER BY file_path, start_line"

        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def query_edges(self, source: str | None = None, target: str | None = None,
                    kind: str | None = None) -> list[sqlite3.Row]:
        """查询边（关系）

        Args:
            source: 源节点 ID
            target: 目标节点 ID
            kind: 关系类型（contains/calls/imports...）

        Returns:
            匹配的边列表
        """
        if not self.conn:
            return []

        query = "SELECT * FROM edges WHERE 1=1"
        params: list[Any] = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if target:
            query += " AND target = ?"
            params.append(target)

        if kind:
            query += " AND kind = ?"
            params.append(kind)

        query += " LIMIT 1000"

        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def find_symbols_by_name(self, name: str, language: str = "typescript") -> list[sqlite3.Row]:
        """按名称查找符号（精确匹配）

        Args:
            name: 符号名称
            language: 语言过滤

        Returns:
            匹配的符号节点
        """
        if not self.conn:
            return []

        query = """
            SELECT * FROM nodes
            WHERE name = ? AND language = ?
            ORDER BY file_path, start_line
        """
        cursor = self.conn.execute(query, (name, language))
        return cursor.fetchall()

    def find_callers(self, function_name: str, language: str = "typescript") -> list[sqlite3.Row]:
        """查找调用某个函数的所有位置

        Args:
            function_name: 函数名称
            language: 语言过滤

        Returns:
            调用该函数的节点列表
        """
        if not self.conn:
            return []

        # 1. 找到目标函数节点
        target_nodes = self.find_symbols_by_name(function_name, language)
        if not target_nodes:
            return []

        # 2. 找到所有 "calls" 关系的边
        callers = []
        for target in target_nodes:
            edges = self.query_edges(target=target["id"], kind="calls")
            for edge in edges:
                # 3. 获取源节点详情
                source_node = self.conn.execute(
                    "SELECT * FROM nodes WHERE id = ?", (edge["source"],)
                ).fetchone()
                if source_node:
                    callers.append(source_node)

        return callers

    def __enter__(self):
        """Context manager 支持"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 支持"""
        self.close()
        return False


class SemanticDedupCheck(Check):
    """基于 CodeGraph 的去重逻辑检查

    检测 TypeScript 代码中的去重/防抖逻辑，验证：
    - 是否包含动态窗口（而非硬编码固定值）
    - 是否有"为什么"注释
    """

    def run(self) -> list[CheckResult]:
        results: list[CheckResult] = []

        with CodeGraphClient(self.project / ".codegraph" / "codegraph.db") as cg:
            if not cg.conn:
                return [self.skip("CodeGraph 数据库不可用，跳过语义检查")]

            # 1. 查找所有去重相关函数
            dedup_keywords = ["isDuplicate", "debounce", "throttle", "deduplicate"]
            for keyword in dedup_keywords:
                nodes = cg.query_nodes(name_pattern=keyword, file_pattern="%.ts")

                for node in nodes:
                    source_code = node["signature"] or ""
                    file_path = node["file_path"]
                    line = node["start_line"]

                    # 检查是否有动态窗口
                    has_dynamic_window = any(
                        kw in source_code for kw in ["reconnect", "messageCount", "timestamp", "Date.now"]
                    )

                    if not has_dynamic_window and keyword == "isDuplicate":
                        results.append(self.fail(
                            f"{keyword} 缺少动态窗口（硬编码固定窗口容易导致竞态）",
                            file=file_path,
                            line=line,
                            keyword=keyword,
                        ))

                    # 检查是否有"为什么"注释
                    docstring = node["docstring"] or ""
                    has_why_comment = any(
                        kw in docstring.lower()
                        for kw in ["why", "reason", "purpose", "防止", "避免"]
                    )

                    if not has_why_comment:
                        results.append(self.warn(
                            f"{keyword} 缺少'为什么'注释（建议说明设计理由）",
                            file=file_path,
                            line=line,
                            keyword=keyword,
                        ))

        if not results:
            results.append(self.pass_check("语义去重检查通过"))

        return results


class SemanticRaceConditionCheck(Check):
    """基于 CodeGraph 的竞态条件检查

    检测 TypeScript 代码中的竞态条件风险：
    - pendingMessageRef 等可变引用
    - handleStop 等关键函数
    - setState 的异步调用
    """

    def run(self) -> list[CheckResult]:
        results: list[CheckResult] = []

        with CodeGraphClient(self.project / ".codegraph" / "codegraph.db") as cg:
            if not cg.conn:
                return [self.skip("CodeGraph 数据库不可用，跳过语义检查")]

            # 1. 查找竞态关键符号
            race_keywords = ["pendingMessageRef", "handleStop", "pendingRequest", "isLoading"]
            for keyword in race_keywords:
                nodes = cg.query_nodes(name_pattern=keyword, file_pattern="%.ts")

                for node in nodes:
                    source_code = node["signature"] or ""
                    docstring = node["docstring"] or ""
                    file_path = node["file_path"]
                    line = node["start_line"]

                    # 检查是否有时序注释
                    has_timing_doc = any(
                        kw in docstring.lower()
                        for kw in ["时序", "timing", "sequence", "race condition", "竞态"]
                    )

                    if not has_timing_doc:
                        results.append(self.warn(
                            f"{keyword} 缺少时序注释（竞态关键逻辑应说明时序依赖）",
                            file=file_path,
                            line=line,
                            keyword=keyword,
                        ))

            # 2. 查找 setState 调用
            setstate_nodes = cg.find_callers("setState", language="typescript")
            for node in setstate_nodes[:10]:  # 限制数量，避免过多噪音
                file_path = node["file_path"]
                line = node["start_line"]

                # 检查是否在异步函数中
                is_async = node["is_async"]

                if is_async:
                    results.append(self.warn(
                        "异步函数中调用 setState（建议说明时序保证）",
                        file=file_path,
                        line=line,
                    ))

        if not results:
            results.append(self.pass_check("语义竞态检查通过"))

        return results


class ChangeImpactAnalyzer:
    """变更影响分析器

    基于 CodeGraph 分析代码变更的影响范围。
    用于回答："如果修改了 X，会影响哪些地方？"
    """

    def __init__(self, cg: CodeGraphClient):
        self.cg = cg

    def analyze(self, symbol_name: str, language: str = "typescript") -> dict[str, Any]:
        """分析符号变更的影响

        Args:
            symbol_name: 符号名称
            language: 语言

        Returns:
            影响分析结果：
            {
                "symbol": symbol_name,
                "direct_callers": [...],  # 直接调用者
                "indirect_callers": [...],  # 间接调用者（依赖图 2 层）
                "files_affected": [...],  # 受影响的文件
                "risk_level": "high|medium|low"
            }
        """
        if not self.cg.conn:
            return {"error": "CodeGraph not available"}

        # 1. 查找目标符号
        target_nodes = self.cg.find_symbols_by_name(symbol_name, language)
        if not target_nodes:
            return {"error": f"Symbol '{symbol_name}' not found"}

        # 2. 找到直接调用者
        direct_callers: set[str] = set()
        for target in target_nodes:
            callers = self.cg.find_callers(symbol_name, language)
            for caller in callers:
                direct_callers.add(caller["file_path"])

        # 3. 找到间接调用者（依赖图 2 层）
        indirect_callers: set[str] = set()
        for caller_file in direct_callers:
            # 查找调用 caller_file 中函数的地方
            edges = self.cg.query_edges(target=f"file:{caller_file}", kind="contains")
            for edge in edges:
                node = self.cg.conn.execute(
                    "SELECT * FROM nodes WHERE id = ?", (edge["source"],)
                ).fetchone()
                if node and node["kind"] in ("function", "method"):
                    indirect = self.cg.find_callers(node["name"], language)
                    for ind_node in indirect:
                        indirect_callers.add(ind_node["file_path"])

        # 4. 评估风险级别
        total_affected = len(direct_callers) + len(indirect_callers)
        if total_affected > 10:
            risk_level = "high"
        elif total_affected > 3:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "symbol": symbol_name,
            "direct_callers": sorted(direct_callers),
            "indirect_callers": sorted(indirect_callers),
            "files_affected": sorted(direct_callers | indirect_callers),
            "risk_level": risk_level,
            "total_affected": total_affected,
        }
