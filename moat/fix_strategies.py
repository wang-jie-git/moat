"""Fix Strategies — 修复策略库

为不同类型的错误定义修复策略。
每个策略包含：
- pattern: 错误模式匹配
- suggestion: AI 修复建议模板
- auto_fix: 是否支持自动修复
- example: 修复示例
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class FixStrategy:
    """修复策略"""
    error_type: str
    pattern: str
    suggestion: str
    auto_fixable: bool
    example: str
    confidence: float = 0.8  # 修复置信度 0-1


# 预定义的修复策略库
FIX_STRATEGIES: list[FixStrategy] = [
    # Python 相关
    FixStrategy(
        error_type="syntax_error",
        pattern="SyntaxError",
        suggestion="检查语法错误，常见原因：缺少冒号、缩进错误、括号不匹配",
        auto_fixable=False,
        example="# 错误\nif True\n    print('hello')\n\n# 正确\nif True:\n    print('hello')",
        confidence=0.9,
    ),
    FixStrategy(
        error_type="import_error",
        pattern="ImportError|ModuleNotFoundError",
        suggestion="检查模块是否已安装，或拼写是否正确。使用 `pip install <module>` 安装缺失依赖",
        auto_fixable=False,
        example="# 安装缺失模块\npip install requests\n\n# 或使用相对导入\nfrom . import helper",
        confidence=0.95,
    ),
    FixStrategy(
        error_type="undefined_variable",
        pattern="NameError|undefined",
        suggestion="变量在使用前未定义。检查变量名拼写，或在使用前添加赋值",
        auto_fixable=False,
        example="# 错误\nprint(x)\n\n# 正确\nx = 10\nprint(x)",
        confidence=0.9,
    ),
    FixStrategy(
        error_type="type_error",
        pattern="TypeError",
        suggestion="类型不匹配。使用 type() 检查变量类型，或添加类型转换",
        auto_fixable=False,
        example="# 错误\nresult = '5' + 3\n\n# 正确\nresult = int('5') + 3",
        confidence=0.85,
    ),
    FixStrategy(
        error_type="indentation_error",
        pattern="IndentationError|unexpected indent",
        suggestion="缩进错误。Python 使用 4 个空格作为标准缩进，确保整个文件一致",
        auto_fixable=True,
        example="# 错误\nif True:\nprint('hello')\n\n# 正确\nif True:\n    print('hello')",
        confidence=0.95,
    ),

    # TypeScript 相关
    FixStrategy(
        error_type="ts_syntax_error",
        pattern="TS1005|TS1128|syntax error",
        suggestion="TypeScript 语法错误。检查分号、括号、类型注解是否正确",
        auto_fixable=False,
        example="// 错误\nconst x: number = 'hello'\n\n// 正确\nconst x: string = 'hello'",
        confidence=0.85,
    ),
    FixStrategy(
        error_type="ts_type_error",
        pattern="TS2345|TS2349|type.*incorrect",
        suggestion="类型不匹配。检查函数参数类型、返回值类型是否符合定义",
        auto_fixable=False,
        example="// 错误\nfunction add(a: number, b: number): number {\n  return a + b;\n}\nadd('1', '2');\n\n// 正确\nadd(1, 2);",
        confidence=0.9,
    ),
    FixStrategy(
        error_type="ts_undefined",
        pattern="TS2304|TS2552|TS2551|undefined",
        suggestion="变量或函数未定义。检查拼写、导入语句、或添加类型声明",
        auto_fixable=False,
        example="// 错误\nconsole.log(myVar);\n\n// 正确\nconst myVar = 'hello';\nconsole.log(myVar);",
        confidence=0.9,
    ),

    # 竞态条件
    FixStrategy(
        error_type="race_condition",
        pattern="race condition|pendingMessageRef|useEffect",
        suggestion="React hooks 竞态条件。使用清理函数或 AbortController 取消旧请求",
        auto_fixable=True,
        example="// 使用 AbortController\nuseEffect(() => {\n  const controller = new AbortController();\n  fetchData({ signal: controller.signal });\n  return () => controller.abort();\n}, []);",
        confidence=0.8,
    ),

    # 重复代码
    FixStrategy(
        error_type="code_duplication",
        pattern="duplicate|similar code",
        suggestion="提取公共逻辑到独立函数，减少重复代码",
        auto_fixable=False,
        example="# 错误 - 重复代码\ndef process_a():\n    # 验证\n    validate()\n    # 处理\n    handle()\n\ndef process_b():\n    # 验证\n    validate()\n    # 处理\n    handle()\n\n# 正确 - 提取公共逻辑\ndef process_a():\n    common_process()\n\ndef process_b():\n    common_process()",
        confidence=0.7,
    ),

    # 未使用的代码
    FixStrategy(
        error_type="unused_code",
        pattern="unused|dead code",
        suggestion="删除未使用的变量、函数或导入语句，保持代码整洁",
        auto_fixable=True,
        example="# 错误\nimport os\nimport sys  # 未使用\ndef unused_func():\n    pass\n\n# 正确\nimport os\n# 删除 sys 导入和 unused_func",
        confidence=0.95,
    ),

    # 性能问题
    FixStrategy(
        error_type="performance",
        pattern="slow|performance|N+1 query",
        suggestion="优化数据库查询或循环。使用批量操作、缓存、或添加索引",
        auto_fixable=False,
        example="# 错误 - N+1 查询\nfor user in users:\n    orders = db.query(Order).filter_by(user_id=user.id).all()\n\n# 正确 - 批量查询\nuser_ids = [u.id for u in users]\norders = db.query(Order).filter(Order.user_id.in_(user_ids)).all()",
        confidence=0.8,
    ),
]


def get_strategy(error_type: str, message: str) -> FixStrategy | None:
    """根据错误类型和消息获取修复策略

    Args:
        error_type: 错误类型
        message: 错误消息

    Returns:
        匹配的修复策略，如果没有匹配则返回 None
    """
    message_lower = message.lower()

    for strategy in FIX_STRATEGIES:
        # 精确匹配错误类型
        if strategy.error_type == error_type:
            return strategy

        # 模糊匹配错误消息 - 支持多个 pattern 用 | 分隔
        patterns = [p.strip().lower() for p in strategy.pattern.split('|')]
        if any(pattern in message_lower for pattern in patterns):
            return strategy

    return None


def get_all_strategies() -> list[FixStrategy]:
    """获取所有修复策略

    Returns:
        修复策略列表
    """
    return FIX_STRATEGIES.copy()
