"""
算子7：实施真元文档生成

目标：将验收结果收口成可引用的权威文档

输出：
- 框架与语言
- 目录责任
- 新增模块规范
- 接口响应规范
- 框架利用原则
- 运行证据
- 架构变更记录
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..types import (
    OperatorResult,
    Severity,
    VerificationContext,
    Violation,
)

if TYPE_CHECKING:
    pass


class TruthDocumentGeneratorOperator:
    """
    算子7：实施真元文档生成

    生成架构实施真元文档
    """

    name = "truth_document"
    description = "生成架构实施真元文档"

    def verify(self, context: VerificationContext) -> OperatorResult:
        """生成实施真元文档"""
        print(f"   📝 生成实施真元文档...")

        violations = []
        evidence = {}
        suggestions = []

        project_path = context.project_path
        output_path = project_path / ".moat" / "truth_document.md"

        # 生成文档内容
        doc_content = self._generate_truth_document(context)

        # 保存文档
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(doc_content, encoding="utf-8")

            evidence["truth_document_path"] = str(output_path)
            evidence["document_size"] = len(doc_content)

            suggestions.append(f"实施真元文档已生成: {output_path}")

            passed = True

        except Exception as e:
            violations.append(
                Violation(
                    rule="truth_document_generation",
                    message=f"生成实施真元文档失败: {e}",
                    severity=Severity.ERROR,
                    suggestion="检查写入权限和磁盘空间",
                )
            )
            passed = False

        return OperatorResult(
            operator_name=self.name,
            passed=passed,
            evidence=evidence,
            violations=violations,
            suggestions=suggestions,
        )

    def _generate_truth_document(self, context: VerificationContext) -> str:
        """生成实施真元文档内容"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        doc = f"""# 后端架构实施真元文档

**版本**: v1.0.0
**创建时间**: {timestamp}
**最后更新**: {timestamp}
**对应架构基线**: 待分配

## 1. 框架与语言

- **语言**: 待检测
- **框架**: 待检测
- **规则来源**: 待检测

## 2. 目录责任

（此部分由算子1：目录责任验收生成）

## 3. 新增模块规范

（此部分由算子2：最小模块演练生成）

## 4. 接口响应规范

（此部分由算子3：接口响应规范验收生成）

## 5. 框架利用原则

- **参数校验**: 必须使用框架推荐机制
- **错误处理**: 必须使用框架机制
- **认证授权**: 必须使用框架中间件
- **日志**: 优先使用框架内置机制
- **自定义封装**: 需说明原因，并更新本文档

## 6. 运行证据

- **依赖安装**: 待填写
- **启动命令**: 待填写
- **服务端口**: 待填写
- **健康检查**: 待填写
- **数据库连接**: 待填写
- **最后验证**: {timestamp}

## 7. 架构变更记录

- **v1.0.0** ({timestamp}): 初始架构基线

---

## 附录：验收记录

（此部分由算子6：架构健康度评分生成）

---

**注意**: 本文档是架构的最高权威来源。所有代码变更必须符合本文档的规则。
"""

        return doc
