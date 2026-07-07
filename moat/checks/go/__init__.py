"""Go 专项检查模块

包含 3 个基础检查：
1. error 处理完整性
2. goroutine 泄露检测
3. 并发安全检测
"""
from moat.checks.go.error_handling import GoErrorHandlingCheck
from moat.checks.go.goroutine_leak import GoGoroutineLeakCheck
from moat.checks.go.concurrency_safety import GoConcurrencySafetyCheck

__all__ = [
    "GoErrorHandlingCheck",
    "GoGoroutineLeakCheck",
    "GoConcurrencySafetyCheck",
]
