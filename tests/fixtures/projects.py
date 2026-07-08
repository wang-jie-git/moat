"""临时项目，用于 L0-L4 检查测试"""
__all__ = [
    "create_temp_project",
    "create_fastapi_project",
    "create_react_project",
]

import tempfile
from pathlib import Path
from textwrap import dedent


def create_temp_project() -> Path:
    """创建最简测试项目（Python）"""
    tmp = Path(tempfile.mkdtemp())

    # 核心模块（模拟鉴权/支付）
    (tmp / "core").mkdir()
    (tmp / "core" / "__init__.py").write_text("")
    (tmp / "core" / "auth.py").write_text(dedent("""
        class AuthService:
            def login(self, user): pass
            def verify(self, token): pass
    """))

    (tmp / "core" / "payment.py").write_text(dedent("""
        class PaymentService:
            def charge(self, amount): pass
            def refund(self, id): pass
    """))

    # 边缘模块
    (tmp / "utils").mkdir()
    (tmp / "utils" / "__init__.py").write_text("")
    (tmp / "utils" / "logger.py").write_text("def log(msg): pass")

    # 有循环依赖的模块（用于 L3 测试）
    (tmp / "core" / "utils_cycle.py").write_text("from utils import logger")

    # 配置文件
    (tmp / ".moat").mkdir(exist_ok=True)
    (tmp / "requirements.txt").write_text("fastapi==0.100\nhttpx==0.27\n")

    return tmp


def create_fastapi_project() -> Path:
    """创建 FastAPI 项目（用于 L1 API 测试）"""
    tmp = create_temp_project()
    (tmp / "server.py").write_text(dedent("""
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/")
        def root(): return {"status": "ok"}

        @app.get("/api/users")
        def get_users(): return {"users": []}

        @app.post("/api/auth/login")
        def login(): return {"token": "xxx"}
    """))

    return tmp


def create_react_project() -> Path:
    """创建 React 项目（用于 TypeScript 检查测试）"""
    tmp = Path(tempfile.mkdtemp())

    (tmp / "src").mkdir()
    (tmp / "src" / "App.tsx").write_text(dedent("""
        import React from 'react';
        export const App = () => <div>Hello</div>;
    """))

    # 有重复组件的项目
    (tmp / "src" / "Button.tsx").write_text(dedent("""
        export const Button = () => <button>Click</button>;
    """))

    (tmp / "src" / "SubmitButton.tsx").write_text(dedent("""
        export const Button = () => <button>Submit</button>;
    """))

    (tmp / "package.json").write_text('{"name": "test"}')
    (tmp / "tsconfig.json").write_text('{"compilerOptions": {"strict": true}}')

    return tmp
