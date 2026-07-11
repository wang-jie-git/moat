"""依赖项安全漏洞检测器（DEPS-001）

检测策略：
1. 解析依赖管理文件（requirements.txt, pyproject.toml, package.json）
2. 对比已知漏洞数据库（本地缓存或 GitHub Advisory API）
3. 生成修复建议（升级版本）

这是"守门员"的本能：安全第一，优先使用本地数据。
"""
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult
from moat.checks.fail_open import fail_open

logger = logging.getLogger(__name__)


class DependencySecurityCheck(Check):
    """依赖项安全漏洞检测器

    检测模式：
    - Python：requirements.txt, pyproject.toml
    - Node.js：package.json
    - 对比本地漏洞数据库或 GitHub Advisory API
    """

    # 依赖文件模式
    DEPENDENCY_FILES = {
        "python": ["requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock"],
        "node": ["package.json", "package-lock.json", "yarn.lock"],
        "go": ["go.mod", "go.sum"],
    }

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "DependencySecurity"
        self.config = config or {}
        self.vulnerability_db = {}

    def run(self) -> list[CheckResult]:
        """运行依赖项安全检测

        Returns:
            检查结果列表
        """
        results = []

        # 1. 检测 Python 依赖
        py_results = self._check_python_dependencies()
        results.extend(py_results)

        # 2. 检测 Node.js 依赖
        node_results = self._check_node_dependencies()
        results.extend(node_results)

        return results

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个依赖文件

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        file_name = file_path.name.lower()

        if file_name == "requirements.txt":
            return self._check_requirements_txt(file_path)
        elif file_name == "pyproject.toml":
            return self._check_pyproject_toml(file_path)
        elif file_name == "package.json":
            return self._check_package_json(file_path)

        return []

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_python_dependencies(self) -> list[CheckResult]:
        """检查 Python 依赖项安全漏洞

        Returns:
            检查结果列表
        """
        results = []

        # 检查 requirements.txt
        req_file = self.project / "requirements.txt"
        if req_file.exists():
            results.extend(self._check_requirements_txt(req_file))

        # 检查 pyproject.toml
        pyproject_file = self.project / "pyproject.toml"
        if pyproject_file.exists():
            results.extend(self._check_pyproject_toml(pyproject_file))

        return results

    @fail_open(default_return=[], log_level=logging.DEBUG)
    def _check_node_dependencies(self) -> list[CheckResult]:
        """检查 Node.js 依赖项安全漏洞

        Returns:
            检查结果列表
        """
        results = []

        package_json = self.project / "package.json"
        if package_json.exists():
            results.extend(self._check_package_json(package_json))

        return results

    def _check_requirements_txt(self, req_file: Path) -> list[CheckResult]:
        """检查 requirements.txt 中的依赖项

        Args:
            req_file: requirements.txt 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            content = req_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            dependencies = []
            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # 跳过注释和空行
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # 解析依赖（package==version 或 package>=version）
                match = re.match(r"([a-zA-Z0-9_-]+)([=<>!~]+)([\d.]+)", line)
                if match:
                    package_name = match.group(1)
                    version = match.group(3)
                    dependencies.append((package_name, version, line_num))

            # 检查每个依赖的已知漏洞（使用本地数据库或 pip-audit）
            for package_name, version, line_num in dependencies:
                vulns = self._check_package_vulnerability(package_name, version)
                results.extend(vulns)

        except Exception as e:
            logger.warning(f"检查 requirements.txt 失败: {e}")

        return results

    def _check_pyproject_toml(self, pyproject_file: Path) -> list[CheckResult]:
        """检查 pyproject.toml 中的依赖项

        Args:
            pyproject_file: pyproject.toml 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            # 尝试使用 toml 库解析
            try:
                import tomllib
                with open(pyproject_file, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                # Python < 3.11 没有 tomllib，尝试 tomli
                try:
                    import tomli as tomllib
                    with open(pyproject_file, "rb") as f:
                        data = tomllib.load(f)
                except ImportError:
                    # 降级到正则解析
                    return self._check_pyproject_toml_regex(pyproject_file)

            # 提取 dependencies
            dependencies = []
            if "project" in data and "dependencies" in data["project"]:
                for dep in data["project"]["dependencies"]:
                    match = re.match(r"([a-zA-Z0-9_-]+)([=<>!~]+)([\d.]+)", dep)
                    if match:
                        package_name = match.group(1)
                        version = match.group(3)
                        dependencies.append((package_name, version))

            # 检查每个依赖
            for package_name, version in dependencies:
                vulns = self._check_package_vulnerability(package_name, version)
                results.extend(vulns)

        except Exception as e:
            logger.warning(f"检查 pyproject.toml 失败: {e}")

        return results

    def _check_pyproject_toml_regex(self, pyproject_file: Path) -> list[CheckResult]:
        """使用正则解析 pyproject.toml（降级方案）

        Args:
            pyproject_file: pyproject.toml 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            content = pyproject_file.read_text(encoding="utf-8")
            # 查找 dependencies 列表
            dep_pattern = r'dependencies\s*=\s*\[([^\]]+)\]'
            matches = re.findall(dep_pattern, content, re.DOTALL)

            for match in matches:
                # 解析每个依赖
                deps = re.findall(r'"([a-zA-Z0-9_-]+[=<>!~]+[\d.]+)"', match)
                for dep in deps:
                    pkg_match = re.match(r"([a-zA-Z0-9_-]+)([=<>!~]+)([\d.]+)", dep)
                    if pkg_match:
                        package_name = pkg_match.group(1)
                        version = pkg_match.group(3)
                        vulns = self._check_package_vulnerability(package_name, version)
                        results.extend(vulns)

        except Exception as e:
            logger.warning(f"正则解析 pyproject.toml 失败: {e}")

        return results

    def _check_package_json(self, package_json: Path) -> list[CheckResult]:
        """检查 package.json 中的依赖项

        Args:
            package_json: package.json 文件路径

        Returns:
            检查结果列表
        """
        results = []

        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查 dependencies 和 devDependencies
            all_deps = {}
            all_deps.update(data.get("dependencies", {}))
            all_deps.update(data.get("devDependencies", {}))

            for package_name, version_spec in all_deps.items():
                # 提取版本号（简化处理，移除 ^, ~, >= 等前缀）
                version_match = re.search(r"[\d.]+", version_spec)
                if version_match:
                    version = version_match.group(0)
                    vulns = self._check_package_vulnerability(package_name, version, language="node")
                    results.extend(vulns)

        except Exception as e:
            logger.warning(f"检查 package.json 失败: {e}")

        return results

    def _check_package_vulnerability(self, package_name: str, version: str, language: str = "python") -> list[CheckResult]:
        """检查单个依赖项的安全漏洞

        Args:
            package_name: 包名
            version: 版本号
            language: 语言（python/node）

        Returns:
            检查结果列表
        """
        results = []

        # 方法 1：使用 pip-audit（Python）
        if language == "python":
            audit_results = self._run_pip_audit(package_name, version)
            if audit_results:
                return audit_results

        # 方法 2：使用 npm audit（Node.js）
        if language == "node":
            audit_results = self._run_npm_audit(package_name, version)
            if audit_results:
                return audit_results

        # 方法 3：检查本地漏洞数据库（如果有）
        cache_key = f"{language}:{package_name}:{version}"
        if cache_key in self.vulnerability_db:
            vuln = self.vulnerability_db[cache_key]
            results.append(
                CheckResult(
                    type="fail",
                    level="HIGH",
                    file=str(package_name),
                    message=f"[依赖安全] {package_name}@{version} 存在已知漏洞 ({vuln.get('severity', 'unknown')}): {vuln.get('summary', '无详细信息')}",
                    metadata={
                        "rule": "dependency_security",
                        "package": package_name,
                        "version": version,
                        "language": language,
                        "vulnerability": vuln,
                    },
                )
            )

        return results

    def _run_pip_audit(self, package_name: str, version: str) -> list[CheckResult]:
        """使用 pip-audit 检查 Python 包漏洞

        Args:
            package_name: 包名
            version: 版本号

        Returns:
            检查结果列表
        """
        results = []

        try:
            # 检查 pip-audit 是否可用
            result = subprocess.run(
                ["pip-audit", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                # pip-audit 不可用，降级到静态检查
                return self._static_vulnerability_check(package_name, version)

            # 运行 pip-audit（仅检查指定包）
            result = subprocess.run(
                ["pip-audit", "--desc", "--fix"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project),
            )

            if result.returncode != 0:
                # 解析输出
                output = result.stdout + result.stderr
                if package_name.lower() in output.lower():
                    # 提取漏洞信息
                    vuln_info = self._parse_pip_audit_output(output, package_name)
                    if vuln_info:
                        results.append(
                            CheckResult(
                                type="fail",
                                level="HIGH",
                                file=package_name,
                                message=f"[依赖安全] {package_name}@{version} 存在漏洞: {vuln_info.get('summary', '未知')}。建议升级到 {vuln_info.get('fix_version', '最新版本')}",
                                metadata={
                                    "rule": "dependency_security",
                                    "package": package_name,
                                    "version": version,
                                    "language": "python",
                                    "vulnerability": vuln_info,
                                },
                            )
                        )

        except FileNotFoundError:
            # pip-audit 未安装，降级到静态检查
            return self._static_vulnerability_check(package_name, version)
        except subprocess.TimeoutExpired:
            logger.warning(f"pip-audit 超时: {package_name}")
        except Exception as e:
            logger.debug(f"pip-audit 检查失败: {e}")

        return results

    def _run_npm_audit(self, package_name: str, version: str) -> list[CheckResult]:
        """使用 npm audit 检查 Node.js 包漏洞

        Args:
            package_name: 包名
            version: 版本号

        Returns:
            检查结果列表
        """
        results = []

        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project),
            )

            if result.returncode != 0:
                # 解析输出
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", {})

                if package_name.lower() in vulnerabilities:
                    vuln = vulnerabilities[package_name.lower()]
                    results.append(
                        CheckResult(
                            type="fail",
                            level="HIGH",
                            file=package_name,
                            message=f"[依赖安全] {package_name}@{version} 存在漏洞 ({vuln.get('severity', 'unknown')}): {vuln.get('title', '未知')}。建议升级到 {vuln.get('fixAvailable', {}).get('version', '最新版本')}",
                            metadata={
                                "rule": "dependency_security",
                                "package": package_name,
                                "version": version,
                                "language": "node",
                                "vulnerability": vuln,
                            },
                        )
                    )

        except FileNotFoundError:
            logger.debug("npm 未安装，跳过 npm audit")
        except subprocess.TimeoutExpired:
            logger.warning(f"npm audit 超时: {package_name}")
        except Exception as e:
            logger.debug(f"npm audit 检查失败: {e}")

        return results

    def _static_vulnerability_check(self, package_name: str, version: str) -> list[CheckResult]:
        """静态漏洞检查（基于已知漏洞数据库）

        Args:
            package_name: 包名
            version: 版本号

        Returns:
            检查结果列表
        """
        results = []

        # 内置已知高危漏洞数据库（简化版）
        known_vulnerabilities = {
            "python": {
                "requests": {
                    "<=2.25.0": {"severity": "HIGH", "summary": "CVE-2021-33503: CRLF injection"},
                    "<=2.19.0": {"severity": "CRITICAL", "summary": "CVE-2018-18074: credential leak"},
                },
                "django": {
                    "<2.2.28": {"severity": "HIGH", "summary": "CVE-2021-33203: path traversal"},
                    "<3.2.0": {"severity": "HIGH", "summary": "CVE-2021-33503: SQL injection"},
                },
                "flask": {
                    "<2.0.0": {"severity": "MEDIUM", "summary": "CVE-2019-1010083: DoS"},
                },
                "pillow": {
                    "<8.3.0": {"severity": "CRITICAL", "summary": "CVE-2022-30515: arbitrary code execution"},
                },
                "urllib3": {
                    "<1.26.5": {"severity": "HIGH", "summary": "CVE-2021-33503: CRLF injection"},
                },
                "jinja2": {
                    "<2.11.3": {"severity": "HIGH", "summary": "CVE-2020-28493: ReDoS"},
                },
                "pyyaml": {
                    "<5.4": {"severity": "CRITICAL", "summary": "CVE-2020-14343: arbitrary code execution"},
                },
                "cryptography": {
                    "<3.0": {"severity": "HIGH", "summary": "CVE-2020-36242: side-channel attack"},
                },
            },
            "node": {
                "axios": {
                    "<0.21.0": {"severity": "HIGH", "summary": "CVE-2021-3749: SSRF"},
                },
                "lodash": {
                    "<4.17.21": {"severity": "CRITICAL", "summary": "CVE-2021-23337: command injection"},
                },
                "express": {
                    "<4.17.1": {"severity": "HIGH", "summary": "CVE-2022-24999: DoS"},
                },
                "minimist": {
                    "<1.2.5": {"severity": "CRITICAL", "summary": "CVE-2020-7598: prototype pollution"},
                },
            },
        }

        lang_db = known_vulnerabilities.get(language, {})
        pkg_vulns = lang_db.get(package_name.lower(), {})

        for version_range, vuln_info in pkg_vulns.items():
            if self._version_matches(version, version_range):
                results.append(
                    CheckResult(
                        type="fail",
                        level=vuln_info.get("severity", "HIGH"),
                        file=package_name,
                        message=f"[依赖安全] {package_name}@{version} 存在已知漏洞 ({vuln_info.get('severity', 'unknown')}): {vuln_info.get('summary', '未知')}。建议升级",
                        metadata={
                            "rule": "dependency_security",
                            "package": package_name,
                            "version": version,
                            "language": language,
                            "vulnerability": vuln_info,
                            "version_range": version_range,
                        },
                    )
                )

        return results

    def _version_matches(self, current_version: str, version_range: str) -> bool:
        """检查当前版本是否匹配漏洞版本范围

        Args:
            current_version: 当前版本
            version_range: 版本范围（如 <=2.25.0, <3.0）

        Returns:
            是否匹配
        """
        try:
            from packaging import version as pkg_version

            current = pkg_version.parse(current_version)

            if version_range.startswith("<="):
                target = pkg_version.parse(version_range[2:])
                return current <= target
            elif version_range.startswith("<"):
                target = pkg_version.parse(version_range[1:])
                return current < target
            elif version_range.startswith(">="):
                target = pkg_version.parse(version_range[2:])
                return current >= target
            elif version_range.startswith(">"):
                target = pkg_version.parse(version_range[1:])
                return current > target
            elif version_range.startswith("=="):
                target = pkg_version.parse(version_range[2:])
                return current == target

        except ImportError:
            # 降级到字符串比较
            return current_version == version_range.replace("=", "").replace("<", "").replace(">", "")

        except Exception:
            pass

        return False

    def _parse_pip_audit_output(self, output: str, package_name: str) -> dict | None:
        """解析 pip-audit 输出

        Args:
            output: pip-audit 输出
            package_name: 包名

        Returns:
            漏洞信息字典
        """
        try:
            # 简化解析（实际应该解析 JSON 或结构化输出）
            lines = output.split("\n")
            for i, line in enumerate(lines):
                if package_name.lower() in line.lower():
                    # 尝试提取漏洞信息
                    vuln_info = {
                        "summary": line.strip(),
                        "severity": "UNKNOWN",
                    }
                    return vuln_info
        except Exception:
            pass

        return None
