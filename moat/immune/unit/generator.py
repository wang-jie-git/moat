"""
AI Test Gateway — AI 测试生成网关

职责：
- 通过 Claude API 生成单元测试
- 通过 Claude API 生成契约测试
- 通过 Claude API 生成 BDD 测试
- 集成 One Memory 存储测试模式

设计原则：
- 可选依赖（不安装 Claude SDK 也能使用 Moat）
- 失败不影响 Gatekeeper 拦截
- 异步生成（不阻塞主流程）
"""

import json
import os
from pathlib import Path
from typing import Optional


def _extract_text_from_response(message) -> str:
    """
    从 Claude API 响应中提取文本内容

    处理可能的 ThinkingBlock（扩展思维）和其他 content block 类型

    Args:
        message: Claude API 返回的 message 对象

    Returns:
        提取的文本内容

    Raises:
        ValueError: 如果无法提取有效文本
    """
    try:
        from anthropic.types import TextBlock, ThinkingBlock
    except ImportError:
        # 如果无法导入类型，使用字符串检查作为 fallback
        TextBlock = None
        ThinkingBlock = None

    test_code = None
    for content_block in message.content:
        # 方法 1: 使用 isinstance 检查（最可靠）
        if TextBlock and ThinkingBlock:
            if isinstance(content_block, TextBlock):
                test_code = content_block.text
                break
            elif isinstance(content_block, ThinkingBlock):
                # ThinkingBlock 不包含测试代码，跳过
                continue

        # 方法 2: 使用 hasattr 检查（兼容旧版本 SDK）
        if hasattr(content_block, 'text'):
            try:
                test_code = content_block.text
                break
            except AttributeError:
                # text 属性存在但访问失败（可能是 ThinkingBlock 的 bug）
                continue
        elif hasattr(content_block, 'thinking'):
            # ThinkingBlock 有 thinking 属性但没有 text
            continue

    if not test_code:
        raise ValueError("Claude API 未返回有效的文本内容")

    return test_code


class AITestGateway:
    """
    AI 测试生成网关

    使用示例：
        gateway = AITestGateway()
        gateway.generate_unit_test("services/user.py", file_content)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 AI 测试网关

        Args:
            api_key: Claude API Key（如果为 None，从环境变量 ANTHROPIC_API_KEY 读取）
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.enabled = bool(self.api_key)

        if not self.enabled:
            print("⚠️  AI Test Gateway 未启用（缺少 ANTHROPIC_API_KEY）")

    def generate_unit_test(self, file_path: str, file_content: str) -> Optional[str]:
        """
        生成单元测试

        Args:
            file_path: 业务代码文件路径
            file_content: 业务代码内容

        Returns:
            生成的测试代码，如果失败返回 None
        """
        if not self.enabled:
            return None

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            # 构建 prompt
            prompt = self._build_unit_test_prompt(file_path, file_content)

            # 调用 Claude API
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.2,  # 低温度确保代码质量
                system="你是一个专业的 Python 测试工程师。你只输出测试代码，不输出任何解释。",
                messages=[{"role": "user", "content": prompt}],
            )

            # 提取生成的测试代码
            # 处理可能的 ThinkingBlock（扩展思维）
            try:
                from anthropic.types import TextBlock, ThinkingBlock
            except ImportError:
                TextBlock = None
                ThinkingBlock = None

            test_code = None
            for content_block in message.content:
                # 方法 1: 使用 isinstance 检查（最可靠）
                if TextBlock and ThinkingBlock:
                    if isinstance(content_block, TextBlock):
                        test_code = content_block.text
                        break
                    elif isinstance(content_block, ThinkingBlock):
                        continue

                # 方法 2: 使用 hasattr 检查（兼容旧版本 SDK）
                if hasattr(content_block, 'text'):
                    try:
                        test_code = content_block.text
                        break
                    except AttributeError:
                        continue
                elif hasattr(content_block, 'thinking'):
                    continue

            if not test_code:
                raise ValueError("Claude API 未返回有效的文本内容")

            # 保存到测试文件
            self._save_test_file(file_path, test_code)

            # 记录到 One Memory
            self._record_test_generation(file_path, test_code)

            return test_code

        except Exception as e:
            print(f"⚠️  生成单元测试失败: {e}")
            return None

    def generate_contract_test(self, api_spec: dict) -> Optional[str]:
        """
        生成契约测试（Pact）

        Args:
            api_spec: API 规范（OpenAPI/GraphQL Schema）

        Returns:
            生成的契约测试代码
        """
        if not self.enabled:
            return None

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = self._build_contract_test_prompt(api_spec)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.2,
                system="你是一个专业的契约测试工程师。你只输出 Pact 测试代码，不输出任何解释。",
                messages=[{"role": "user", "content": prompt}],
            )

            # 提取生成的测试代码
            return _extract_text_from_response(message)

        except Exception as e:
            print(f"⚠️  生成契约测试失败: {e}")
            return None

    def generate_bdd_test(self, requirement: str, module: str) -> Optional[str]:
        """
        生成 BDD 测试（Gherkin + pytest-bdd）

        Args:
            requirement: 业务需求描述
            module: 所属模块

        Returns:
            生成的 BDD 测试代码（.feature + 步骤定义）
        """
        if not self.enabled:
            return None

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            prompt = self._build_bdd_test_prompt(requirement, module)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,  # BDD 需要更高的创造性
                system="你是一个专业的 BDD 测试工程师。你只输出 Gherkin 和 pytest-bdd 代码，不输出任何解释。",
                messages=[{"role": "user", "content": prompt}],
            )

            # 提取生成的测试代码
            return _extract_text_from_response(message)

        except Exception as e:
            print(f"⚠️  生成 BDD 测试失败: {e}")
            return None

    def _build_unit_test_prompt(self, file_path: str, file_content: str) -> str:
        """构建单元测试生成 prompt"""
        filename = Path(file_path).name

        return f"""为以下代码生成 pytest 单元测试：

文件：{filename}
代码：
```python
{file_content}
```

要求：
1. 使用 pytest 框架
2. 覆盖正常路径、边界条件、异常处理
3. 使用 pytest-mock 隔离依赖（mocker fixture）
4. 添加类型提示
5. 使用 descriptive test names（如 test_user_registration_with_valid_email）
6. 不输出任何 markdown 代码块标记，直接输出 Python 代码

测试文件名：test_{filename}"""

    def _build_contract_test_prompt(self, api_spec: dict) -> str:
        """构建契约测试生成 prompt"""
        spec_json = json.dumps(api_spec, indent=2, ensure_ascii=False)

        return f"""根据以下 API 规范生成 Pact 契约测试：

API 规范：
```json
{spec_json}
```

要求：
1. 使用 pact-python 框架
2. 生成消费者驱动契约
3. 包含成功路径和错误路径
4. 不输出任何 markdown 代码块标记"""

    def _build_bdd_test_prompt(self, requirement: str, module: str) -> str:
        """构建 BDD 测试生成 prompt"""
        return f"""根据以下业务需求生成 BDD 测试场景：

模块：{module}
需求：{requirement}

要求：
1. 使用 Gherkin 语法（Feature / Scenario / Given / When / Then）
2. 覆盖正常流程和 3-5 个异常场景
3. 生成对应的 pytest-bdd 步骤定义代码（Python）
4. 保存到 tests/features/{module}.feature
5. 不输出任何 markdown 代码块标记"""

    def _save_test_file(self, business_file: str, test_code: str) -> None:
        """
        保存生成的测试代码到文件

        Args:
            business_file: 业务代码文件路径
            test_code: 生成的测试代码
        """
        project_root = Path.cwd()
        business_path = Path(business_file)

        # 计算相对路径
        try:
            relative_path = business_path.relative_to(project_root)
        except ValueError:
            relative_path = business_path

        # 构建测试文件路径
        parts = relative_path.parts
        if len(parts) < 2:
            return

        top_dir = parts[0]
        filename = relative_path.name
        test_filename = f"test_{filename}"

        test_file_path = project_root / "tests" / "unit" / top_dir / test_filename

        # 创建目录（如果不存在）
        test_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        test_file_path.write_text(test_code, encoding="utf-8")

        print(f"✅  AI 生成测试文件: {test_file_path.relative_to(project_root)}")

    def _record_test_generation(self, file_path: str, test_code: str) -> None:
        """记录测试生成到 One Memory"""
        try:
            from ...memory.bridge import SharedStorageBridge, BridgeConfig

            bridge = SharedStorageBridge(
                BridgeConfig(db_path=str(Path(".moat/memory.db")))
            )
            bridge.initialize()

            # 记录 AI 生成的测试
            bridge.store_node(
                node_type="ai_generated_test",
                content={
                    "business_file": file_path,
                    "test_length": len(test_code),
                    "timestamp": str(Path(".moat").stat().st_mtime),
                },
            )

            bridge.close()
        except Exception:
            pass  # 记录失败不影响主流程


# CLI 入口（用于调试）
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m moat.gatekeeper.ai_test.gateway <business_file>")
        sys.exit(1)

    business_file = sys.argv[1]
    if not Path(business_file).exists():
        error_msg = "Error: File not found"
        error_msg += business_file
        print(error_msg)
        sys.exit(1)

    file_content = Path(business_file).read_text(encoding="utf-8")

    gateway = AITestGateway()
    test_code = gateway.generate_unit_test(business_file, file_content)

    if test_code:
        print("\n生成的测试代码：")
        print(test_code)
    else:
        print("❌ 生成失败")
