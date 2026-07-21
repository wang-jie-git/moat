"""
Moat SecretsCheck — 硬编码密钥检测

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
            "EC Private Key",
        ),
        (
            "private_key_openssh",
            r"-----BEGIN OPENSSH PRIVATE KEY-----",
            "CRITICAL",
            "OpenSSH Private Key",
        ),
        (
            "private_key_pkcs8",
            r"-----BEGIN PRIVATE KEY-----",
            "CRITICAL",
            "PKCS8 Private Key",
        ),
        (
            "jwt_token",
            r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}",
            "HIGH",
            "JWT Token",
        ),
    ]

    # 占位符模式（降低误报）
    PLACEHOLDER_PATTERNS = [
        r"^your[-_]?(api|secret|password|token|key)",
        r"^(your|my|example|test|demo|sample)[-_]?(api|secret|password|token)",
        r"^(placeholder|changeme|replace_me|dummy|fake)",
        r"^<[^>]+>$",  # <your-api-key>
        r"^\{[^}]+\}$",  # {api_key}
        r"^\$\([^)]+\)$",  # $(API_KEY)
        r"^\$\{[^}]+\}$",  # ${API_KEY}
        r"^%[^%]+%$",  # %API_KEY%
    ]

    # 排除目录（不遍历这些目录）
    EXCLUDED_DIRS = {
        ".git", "__pycache__", "node_modules", ".next", ".nuxt",
        "build", "dist", "target", "vendor", ".tox", "htmlcov",
    }

    def run(self) -> list[CheckResult]:
        """运行硬编码密钥检测

        Returns:
            检查结果列表
        """
        results = []

        # 快速模式：只检查 target_files（config 传入的修改文件列表）
        # 即使 target_files 是空列表，也跳过全量扫描（无变更时不扫描）
        target_files = self.config.get("target_files")
        if target_files is not None:
            # 显式传入 target_files（包括空列表）→ 只扫描这些文件
            code_files = [Path(f) if isinstance(f, str) else f for f in target_files]
        else:
            code_files = self._find_code_files()

        for file_path in code_files:
            # 跳过不应该检查的文件
            if self._should_skip(file_path):
                continue

            file_results = self._check_file(file_path)
            results.extend(file_results)

        return results

    def _find_code_files(self) -> list[Path]:
        """查找代码文件（排除大目录 node_modules/.venv/.git 等）

        修复：使用显式递归遍历，跳过排除目录，避免 rglob 遍历 node_modules 等大目录。
        """
        extensions = {".py", ".js", ".ts", ".go", ".java", ".rb", ".pem"}
        files = []

        def _walk(path: Path):
            try:
                for entry in path.iterdir():
                    if entry.is_dir():
                        name = entry.name
                        if name in self.EXCLUDED_DIRS:
                            continue
                        if name.startswith(".venv") or name == "venv":
                            continue
                        if name == "site-packages":
                            continue
                        _walk(entry)
                    elif entry.suffix in extensions:
                        files.append(entry)
            except PermissionError:
                pass
            except OSError:
                pass

        _walk(self.project)
        return files

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        for part in file_path.parts:
            if part in self.EXCLUDED_DIRS:
                return True
            if part.startswith(".venv") or part == "venv":
                return True

        file_name = file_path.name
        if file_name.startswith("test_") or file_name.endswith("_test.py"):
            return True

        if "tests/" in str(file_path) or "/tests/" in str(file_path):
            return True

        skip_keywords = ["example", "demo", "sample", "fixture", "mock", "stub", "fake"]
        if any(keyword in file_name.lower() for keyword in skip_keywords):
            return True

        if file_name.startswith(".env."):
            return True

        return False

    def _check_file(self, file_path: Path) -> list[CheckResult]:
        """检查单个文件"""
        if self._should_skip(file_path):
            return []

        results = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            if self._is_comment_line(line):
                continue

            for pattern_name, pattern, severity, description in self.SECRET_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)

                for match in matches:
                    matched_text = match.group(0)

                    value = matched_text
                    if '=' in matched_text:
                        value = matched_text.split('=', 1)[1].strip().strip('"').strip("'")
                    elif ':' in matched_text:
                        value = matched_text.split(':', 1)[1].strip().strip('"').strip("'")

                    if self._is_placeholder(value):
                        continue

                    if self._is_env_var_assignment(line, file_path):
                        continue

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
        stripped = line.strip()
        if stripped.startswith("#"):
            return True
        if stripped.startswith("//"):
            return True
        if stripped.startswith("/*") or stripped.startswith("*"):
            return True
        return False

    def _is_placeholder(self, text: str) -> bool:
        text_lower = text.lower()
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _is_env_var_assignment(self, line: str, file_path: Path) -> bool:
        if re.search(r'(?:os|environ)\.(?:getenv|environ(?:\[|\.get))', line):
            return True
        if 'load_dotenv' in line or 'dotenv' in line:
            return True
        if 'from dotenv' in line or 'import dotenv' in line:
            return True
        if 'add_argument' in line and 'env' in line.lower():
            return True
        return False
