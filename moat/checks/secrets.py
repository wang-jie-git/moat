"""硬编码密钥检测守门员（SECRETS-001）

检测策略：
1. 正则模式匹配：检测 AWS/GitHub/通用 API Key/密码/私钥等常见模式
2. 上下文过滤：排除测试文件、示例文件、环境变量读取、占位符文本
3. 误报抑制：检测到密钥后检查是否为注释、字符串字面量示例等

这是"守门员"的本能：安全第一，宁可误报不可漏报。
"""
import logging
import re
from pathlib import Path
from typing import Any

from moat.checks.base import Check, CheckResult

logger = logging.getLogger(__name__)


class SecretsCheck(Check):
    """硬编码密钥检测器

    检测模式：
    - AWS Access Key ID: AKIA[0-9A-Z]{16}
    - GitHub Personal Access Token: ghp_[0-9a-zA-Z]{36}
    - 通用 API Key: api_key, apiKey, api-key
    - 密码明文: password, passwd, pwd
    - 私钥泄漏: RSA/ECDSA Private Key
    """

    # 密钥检测模式（模式名, 正则表达式, 严重性）
    SECRET_PATTERNS = [
        (
            "aws_access_key",
            r"AKIA[0-9A-Z]{16}",
            "CRITICAL",
            "AWS Access Key ID",
        ),
        (
            "github_token",
            r"ghp_[0-9a-zA-Z]{36}",
            "CRITICAL",
            "GitHub Personal Access Token",
        ),
        (
            "github_oauth",
            r"gho_[0-9a-zA-Z]{36}",
            "CRITICAL",
            "GitHub OAuth Token",
        ),
        (
            "slack_token",
            r"xox[baprs]-[0-9a-zA-Z]{10,48}",
            "CRITICAL",
            "Slack Token",
        ),
        (
            "google_api_key",
            r"AIza[0-9A-Za-z_-]{20,}",
            "CRITICAL",
            "Google API Key",
        ),
        (
            "openai_api_key",
            r'sk-[a-zA-Z0-9_-]{20,}',
            "CRITICAL",
            "OpenAI API Key (sk-)",
        ),
        (
            "stripe_api_key",
            r'(?:sk_live|pk_live|sk_test|pk_test)_[a-zA-Z0-9]{10,}',
            "CRITICAL",
            "Stripe API Key",
        ),
        (
            "generic_api_key",
            r'(?i)api[_-]key["\s:=]+["\x27]([a-zA-Z0-9_-]{16,})["\x27]',
            "HIGH",
            "Generic API Key",
        ),
        (
            "password_assignment",
            r'(?:password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']',
            "CRITICAL",
            "Hardcoded Password",
        ),
        (
            "secret_assignment",
            r'(?:secret|api_secret|app_secret)\s*[:=]\s*["\']([^"\']{8,})["\']',
            "CRITICAL",
            "Hardcoded Secret",
        ),
        (
            "private_key_rsa",
            r"-----BEGIN RSA PRIVATE KEY-----",
            "CRITICAL",
            "RSA Private Key",
        ),
        (
            "private_key_ecdsa",
            r"-----BEGIN EC PRIVATE KEY-----",
            "CRITICAL",
            "ECDSA Private Key",
        ),
        (
            "private_key_pkcs8",
            r"-----BEGIN PRIVATE KEY-----",
            "CRITICAL",
            "PKCS#8 Private Key",
        ),
        (
            "jwt_token",
            r'[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}',
            "HIGH",
            "JWT Token (possible)",
        ),
    ]

    # 环境变量读取模式（用于排除 false positive）
    ENV_VAR_PATTERNS = [
        r"os\.getenv\(",
        r"os\.environ\.get\(",
        r"process\.env\.",
        r'process\.env\[',
        r'getenv\(',
        r'ENV\[',
        r'ENV\.',
        r'\.env\(',
        r'config\[',
        r'settings\.',
        r'env\("',
        r'env\(\'',
    ]

    # 占位符模式（用于排除 false positive）
    PLACEHOLDER_PATTERNS = [
        r"YOUR_",
        r"_HERE$",
        r"<[^>]+>",
        r"\{\{.*\}\}",
        r"\[YOUR_",
        r"example[_-]?key",
        r"dummy[_-]?key",
        r"test[_-]?key",
        r"fake[_-]?key",
        r"placeholder",
        r"CHANGE_ME",
        r"REPLACE_ME",
        r"TODO",
        r"FIXME",
        r"\bxxx\b",
        r"\byyy\b",
        r"\bzzz\b",
    ]

    def __init__(self, project_root: Path, config: dict[str, Any] | None = None):
        super().__init__(project_root, config)
        self.name = "Secrets"

    def run(self) -> list[CheckResult]:
        """运行硬编码密钥检测

        Returns:
            检查结果列表
        """
        results = []

        # 扫描代码文件
        code_files = self._find_code_files()

        for file_path in code_files:
            # 跳过不应该检查的文件
            if self._should_skip(file_path):
                continue

            file_results = self._check_file(file_path)
            results.extend(file_results)

        return results

    def _find_code_files(self) -> list[Path]:
        """查找代码文件（包括 .py, .js, .ts, .pem 等）"""
        extensions = ["**/*.py", "**/*.js", "**/*.ts", "**/*.go", "**/*.java", "**/*.rb", "**/*.pem"]
        files = []
        for pattern in extensions:
            files.extend(self.project.rglob(pattern))
        return files


    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        # 跳过常见目录
        skip_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules", ".next", ".nuxt",
                     "build", "dist", "target", "vendor", ".tox", "htmlcov"}
        if any(part in skip_dirs for part in file_path.parts):
            return True

        # 跳过测试文件（只匹配文件名，不匹配路径中的 test_）
        file_name = file_path.name
        if file_name.startswith("test_") or file_name.endswith("_test.py"):
            return True

        # 跳过 tests/ 目录
        if "tests/" in str(file_path) or "/tests/" in str(file_path):
            return True

        # 跳过示例、演示、测试文件
        skip_keywords = ["example", "demo", "sample", "fixture", "mock", "stub", "fake"]
        if any(keyword in file_name.lower() for keyword in skip_keywords):
            return True

        # 跳过 .env 示例文件
        if file_name.startswith(".env."):
            return True

        return False

    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件

        Args:
            file_path: 文件路径

        Returns:
            检查结果列表
        """
        # 检查是否应该跳过
        if self._should_skip(file_path):
            return []

        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # 跳过注释行
            if self._is_comment_line(line):
                continue

            # 检查每个密钥模式
            for pattern_name, pattern, severity, description in self.SECRET_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)

                for match in matches:
                    matched_text = match.group(0)

                    # 提取实际的值部分（排除变量名和等号）
                    value = matched_text
                    if '=' in matched_text:
                        value = matched_text.split('=', 1)[1].strip().strip('"').strip("'")
                    elif ':' in matched_text:
                        value = matched_text.split(':', 1)[1].strip().strip('"').strip("'")

                    # 检查是否为占位符
                    if self._is_placeholder(value):
                        continue

                    # 检查是否在环境变量读取中
                    if self._is_env_var_assignment(line, file_path):
                        continue

                    # 检测到密钥
                    results.append(
                        CheckResult(
                            type="fail",
                            level=severity,
                            file=str(file_path.resolve().relative_to(self.project.resolve())),
                            line=line_num,
                            message=f"[{description}] 第 {line_num} 行检测到硬编码的 {description}。请使用环境变量或密钥管理服务",
                            metadata={
                                "rule": "secrets",
                                "pattern": pattern_name,
                                "severity": severity,
                                "matched": matched_text[:20] + "..." if len(matched_text) > 20 else matched_text,
                            },
                        )
                    )

        return results

    def _is_comment_line(self, line: str) -> bool:
        """检查是否为注释行"""
        stripped = line.strip()
        # Python/Shell/Bash 注释
        if stripped.startswith("#"):
            return True
        # JavaScript/TypeScript/Go/Java 单行注释
        if stripped.startswith("//"):
            return True
        # CSS/HTML 注释
        if stripped.startswith("/*") or stripped.startswith("*"):
            return True
        return False

    def _is_placeholder(self, text: str) -> bool:
        """检查是否为占位符文本"""
        text_lower = text.lower()

        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        return False

    def _is_env_var_assignment(self, line: str, file_path: Path) -> bool:
        """检查是否在环境变量赋值语句中

        Args:
            line: 当前行
            file_path: 文件路径

        Returns:
            是否为环境变量赋值
        """
        # 检查当前行是否包含环境变量读取模式
        for pattern in self.ENV_VAR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        # 检查前一行是否包含环境变量读取（用于多行赋值）
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            # 找到当前行在文件中的索引
            try:
                line_index = lines.index(line)
            except ValueError:
                return False

            # 检查前一行
            if line_index > 0:
                prev_line = lines[line_index - 1]
                for pattern in self.ENV_VAR_PATTERNS:
                    if re.search(pattern, prev_line, re.IGNORECASE):
                        return True
        except Exception:
            pass

        return False
