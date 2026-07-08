"""Go 专项检查测试

覆盖：
- GoErrorHandlingCheck
- GoGoroutineLeakCheck
- GoConcurrencySafetyCheck
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from moat.checks.go.error_handling import GoErrorHandlingCheck
from moat.checks.go.goroutine_leak import GoGoroutineLeakCheck
from moat.checks.go.concurrency_safety import GoConcurrencySafetyCheck
from moat.checks.base import CheckResult


class TestGoErrorHandlingCheck:
    """Go error 处理检查测试"""

    def test_check_initialized(self, tmp_path):
        """检查初始化"""
        check = GoErrorHandlingCheck(tmp_path)
        assert check.name == "go_error_handling"
        assert check.description == "Go error 处理完整性检查"

    def test_no_go_files(self, tmp_path):
        """项目无 Go 文件时应跳过"""
        check = GoErrorHandlingCheck(tmp_path)
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"
        assert "Go 文件" in results[0].message

    def test_clean_go_code(self, tmp_path):
        """无错误的 Go 代码应通过"""
        go_file = tmp_path / "main.go"
        go_file.write_text("""
package main

func safeFunction() error {
    return nil
}

func main() {
    err := safeFunction()
    if err != nil {
        return
    }
}
""")
        check = GoErrorHandlingCheck(tmp_path)
        results = check.run()
        # 应该有通过的结果
        assert any(r.type == "pass" for r in results)

    def test_panic_usage(self, tmp_path):
        """检测 panic 使用"""
        go_file = tmp_path / "panic.go"
        go_file.write_text("""
package main

func dangerous() {
    panic("something went wrong")
}
""")
        check = GoErrorHandlingCheck(tmp_path)
        results = check.run()
        # 应检测到 panic
        assert any("panic" in r.message.lower() for r in results)

    def test_multiple_issues(self, tmp_path):
        """检测多个问题"""
        go_file = tmp_path / "multi.go"
        go_file.write_text("""
package main

func issue1() (string, error) {
    return "", nil
}

func caller1() {
    result, _ := issue1()
    _ = result
}

func issue2() {
    panic("test")
}
""")
        check = GoErrorHandlingCheck(tmp_path)
        results = check.run()
        # 应检测到多个问题
        assert len(results) >= 2  # pass + 至少 2 个问题

    def test_skip_vendor_directory(self, tmp_path):
        """应跳过 vendor 目录"""
        vendor_dir = tmp_path / "vendor"
        vendor_dir.mkdir()
        go_file = vendor_dir / "vendor.go"
        go_file.write_text("""
package vendor

func bad() (string, error) {
    return "", nil
}
""")
        check = GoErrorHandlingCheck(tmp_path)
        results = check.run()
        # vendor 目录应被跳过
        assert not any("vendor" in r.file for r in results if r.file)

    def test_skip_venv_directory(self, tmp_path):
        """应跳过 .venv 目录"""
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        go_file = venv_dir / "test.go"
        go_file.write_text("func bad() {}")
        check = GoErrorHandlingCheck(tmp_path)
        results = check.run()
        # .venv 目录应被跳过
        assert not any(".venv" in r.file for r in results if r.file)


class TestGoGoroutineLeakCheck:
    """Go goroutine 泄露检查测试"""

    def test_check_initialized(self, tmp_path):
        """检查初始化"""
        check = GoGoroutineLeakCheck(tmp_path)
        assert check.name == "go_goroutine_leak"
        assert check.description == "Go goroutine 泄露检测"

    def test_no_go_files(self, tmp_path):
        """项目无 Go 文件时应跳过"""
        check = GoGoroutineLeakCheck(tmp_path)
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_goroutine_without_context(self, tmp_path):
        """检测未使用 context 的 goroutine"""
        go_file = tmp_path / "leak.go"
        go_file.write_text("""
package main

func badGoroutine() {
    go func() {
        for {
            // 无限循环，没有 context
        }
    }()
}
""")
        check = GoGoroutineLeakCheck(tmp_path)
        results = check.run()
        # 应检测到 goroutine 问题
        assert any("goroutine_without_context" in r.message or "goroutine" in r.message.lower()
                   for r in results)

    def test_potential_goroutine_leak(self, tmp_path):
        """检测潜在的 goroutine 泄露"""
        go_file = tmp_path / "leak2.go"
        go_file.write_text("""
package main

func leakingGoroutine() {
    go func() {
        select {
        case <-time.After(time.Hour):
        }
    }()
}
""")
        check = GoGoroutineLeakCheck(tmp_path)
        results = check.run()
        # 可能检测到潜在的泄露
        assert any("leak" in r.message.lower() for r in results)

    def test_multiple_goroutines(self, tmp_path):
        """检测多个 goroutine"""
        go_file = tmp_path / "multi.go"
        go_file.write_text("""
package main

func multipleGoroutines() {
    go func() { for {} }()
    go func() { for {} }()
    go func() { for {} }()
}
""")
        check = GoGoroutineLeakCheck(tmp_path)
        results = check.run()
        # 应检测到多个问题
        assert len(results) >= 2  # pass + 多个问题


class TestGoConcurrencySafetyCheck:
    """Go 并发安全检测测试"""

    def test_check_initialized(self, tmp_path):
        """检查初始化"""
        check = GoConcurrencySafetyCheck(tmp_path)
        assert check.name == "go_concurrency_safety"
        assert check.description == "Go 并发安全检测"

    def test_no_go_files(self, tmp_path):
        """项目无 Go 文件时应跳过"""
        check = GoConcurrencySafetyCheck(tmp_path)
        results = check.run()
        assert len(results) == 1
        assert results[0].type == "skip"

    def test_safe_concurrent_code(self, tmp_path):
        """安全的并发代码"""
        go_file = tmp_path / "safe.go"
        go_file.write_text("""
package main

import "sync"

type SafeMap struct {
    mu    sync.Mutex
    data  map[string]string
}

func NewSafeMap() *SafeMap {
    return &SafeMap{data: make(map[string]string)}
}

func (sm *SafeMap) Set(key, value string) {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    sm.data[key] = value
}
""")
        check = GoConcurrencySafetyCheck(tmp_path)
        results = check.run()
        # 应该通过
        assert any(r.type == "pass" for r in results)

    def test_unsync_map_write(self, tmp_path):
        """检测未同步的 map 写入"""
        go_file = tmp_path / "unsafe.go"
        go_file.write_text("""
package main

type UnsafeStruct struct {
    data map[string]string
}

func (us *UnsafeStruct) concurrentWrite(key, value string) {
    us.data[key] = value  // 未加锁
}
""")
        check = GoConcurrencySafetyCheck(tmp_path)
        results = check.run()
        # 应检测到并发安全问题
        assert any("unsync_map_write" in r.message or "并发" in r.message
                   for r in results)

    def test_mutex_protected_map(self, tmp_path):
        """检测使用 mutex 保护的 map"""
        go_file = tmp_path / "protected.go"
        go_file.write_text("""
package main

import "sync"

type ProtectedMap struct {
    mu   sync.Mutex
    data map[string]int
}

func (pm *ProtectedMap) SafeWrite(key string, value int) {
    pm.mu.Lock()
    defer pm.mu.Unlock()
    pm.data[key] = value
}
""")
        check = GoConcurrencySafetyCheck(tmp_path)
        results = check.run()
        # 应通过检查
        assert any(r.type == "pass" for r in results)


class TestGoChecksIntegration:
    """Go 检查集成测试"""

    def test_all_go_checks_on_sample_project(self, tmp_path):
        """在示例 Go 项目上运行所有检查"""
        # 创建示例 Go 项目
        go_file = tmp_path / "main.go"
        go_file.write_text("""
package main

import (
    "context"
    "sync"
)

type Server struct {
    mu    sync.Mutex
    data  map[string]string
    ctx   context.Context
    cancel context.CancelFunc
}

func NewServer() *Server {
    ctx, cancel := context.WithCancel(context.Background())
    return &Server{
        data: make(map[string]string),
        ctx: ctx,
        cancel: cancel,
    }
}

func (s *Server) Set(key, value string) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.data[key] = value
}

func (s *Server) Get(key string) string {
    s.mu.Lock()
    defer s.mu.Unlock()
    return s.data[key]
}

func (s *Server) BackgroundTask() {
    go func() {
        <-s.ctx.Done()
    }()
}

func safeOperation() error {
    return nil
}

func caller() {
    result, _ := safeOperation()
    _ = result
}
""")

        # 运行所有 Go 检查
        error_check = GoErrorHandlingCheck(tmp_path)
        goroutine_check = GoGoroutineLeakCheck(tmp_path)
        concurrency_check = GoConcurrencySafetyCheck(tmp_path)

        error_results = error_check.run()
        goroutine_results = goroutine_check.run()
        concurrency_results = concurrency_check.run()

        # 至少有一些检查完成了
        all_results = error_results + goroutine_results + concurrency_results
        assert len(all_results) > 0
        assert any(r.type in ("pass", "warn", "skip") for r in all_results)
