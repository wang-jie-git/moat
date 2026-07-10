"""
Moat Immune — AI 工程化测试体系

模块结构：
- unit: 单元测试生成（pytest + Hypothesis）
- contract: 契约测试（Pact）
- bdd: BDD 测试（pytest-bdd + Gherkin）
- visual: 视觉测试（Playwright + GPT-4o）
- pipeline: 自动化测试流水线

使用示例：
    from moat.immune.unit.generator import AITestGateway

    gateway = AITestGateway()
    gateway.generate_unit_test("services/user.py", file_content)
"""

__version__ = "0.9.0-alpha"

from .unit.generator import AITestGateway

__all__ = ["AITestGateway"]
