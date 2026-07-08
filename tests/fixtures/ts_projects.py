"""临时 TypeScript 项目工厂

为 TypeScript 检查测试提供隔离的临时项目。
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from textwrap import dedent


def create_ts_project() -> Path:
    """创建含 TypeScript 文件的测试项目。"""
    tmp = Path(tempfile.mkdtemp())

    (tmp / "src").mkdir()
    (tmp / "src" / "utils.ts").write_text(dedent("""\
        export function debounce(fn: Function, delay: number): Function {
            let timer: NodeJS.Timeout | null = null;
            return (...args: any[]) => {
                if (timer) clearTimeout(timer);
                timer = setTimeout(() => fn(...args), delay);
            };
        }

        export function throttle(fn: Function, limit: number): Function {
            let inThrottle = false;
            return (...args: any[]) => {
                if (!inThrottle) {
                    fn(...args);
                    inThrottle = true;
                    setTimeout(() => (inThrottle = false), limit);
                }
            };
        }
    """))

    (tmp / "src" / "api.ts").write_text(dedent("""\
        export async function fetchUser(id: string): Promise<User> {
            const res = await fetch(`/api/users/${id}`);
            return res.json();
        }

        export async function createUser(data: UserInput): Promise<User> {
            const res = await fetch("/api/users", {
                method: "POST",
                body: JSON.stringify(data),
            });
            return res.json();
        }
    """))

    (tmp / "tsconfig.json").write_text(dedent("""\
        {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "strict": true,
                "esModuleInterop": true
            }
        }
    """))

    return tmp


def create_ts_project_with_duplicates() -> Path:
    """创建含重复导出名称的 TypeScript 项目。"""
    tmp = create_ts_project()

    (tmp / "src" / "Button.tsx").write_text(dedent("""\
        export const Button: React.FC<ButtonProps> = ({ children }) => {
            return <button>{children}</button>;
        };
    """))

    (tmp / "src" / "SubmitButton.tsx").write_text(dedent("""\
        export const Button: React.FC<SubmitButtonProps> = ({ children }) => {
            return <button type="submit">{children}</button>;
        };
    """))

    return tmp


def create_ts_project_with_race_condition() -> Path:
    """创建含竞态条件风险的 TypeScript 项目。"""
    tmp = create_ts_project()

    (tmp / "src" / "search.ts").write_text(dedent("""\
        let pendingRequest: AbortController | null = null;

        export async function search(query: string): Promise<Result[]> {
            // 竞态条件：未取消上一次请求
            const res = await fetch(`/api/search?q=${query}`);
            return res.json();
        }

        export async function searchWithPending(query: string): Promise<Result[]> {
            // 使用 pendingRequest 但缺少 why 注释
            if (pendingRequest) {
                pendingRequest.abort();
            }
            pendingRequest = new AbortController();
            const res = await fetch(`/api/search?q=${query}`, {
                signal: pendingRequest.signal,
            });
            return res.json();
        }
    """))

    return tmp


def create_ts_project_without_tsconfig() -> Path:
    """创建无 tsconfig.json 的 TypeScript 项目。"""
    tmp = Path(tempfile.mkdtemp())

    (tmp / "src").mkdir()
    (tmp / "src" / "simple.ts").write_text("export const x = 1;\n")

    return tmp


def create_ts_project_with_syntax_error() -> Path:
    """创建含语法错误的 TypeScript 项目。"""
    tmp = create_ts_project()

    (tmp / "src" / "broken.ts").write_text(dedent("""\
        export const broken = {
            name: "test",
            // 缺少闭合括号
        };
    """))

    return tmp
