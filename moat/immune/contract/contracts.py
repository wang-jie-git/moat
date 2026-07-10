"""
Moat Immune — 契约测试系统

核心能力：
- 从 OpenAPI/GraphQL 规范生成 Pact 契约
- 在 One Memory 中存储"API 契约基线"
- 检测 API 变更并判断是否违反契约
- AI 自愈：自动重新生成契约文件

战略价值：
- 跨越服务边界的检查（Lint 工具做不到）
- 契约基线作为"架构宪法"
- 破坏性变更自动检测 + 告警
"""

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class APIContract:
    """API 契约定义"""
    endpoint: str
    method: str
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]
    status_code: int
    description: str
    version: str = "1.0.0"
    created_at: str = ""
    last_modified: str = ""
    author: str = ""

    def compute_hash(self) -> str:
        """计算契约内容的哈希值"""
        content = json.dumps({
            "endpoint": self.endpoint,
            "method": self.method,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
            "status_code": self.status_code,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ContractBaseline:
    """契约基线"""
    service_name: str
    version: str
    contracts: list[APIContract] = field(default_factory=list)
    created_at: str = ""
    baseline_hash: str = ""

    def compute_hash(self) -> str:
        """计算基线整体哈希"""
        contracts_data = [
            {
                "endpoint": c.endpoint,
                "method": c.method,
                "request_hash": hashlib.sha256(
                    json.dumps(c.request_schema, sort_keys=True).encode()
                ).hexdigest()[:8],
                "response_hash": hashlib.sha256(
                    json.dumps(c.response_schema, sort_keys=True).encode()
                ).hexdigest()[:8],
                "status_code": c.status_code,
            }
            for c in self.contracts
        ]
        content = json.dumps(contracts_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def find_contract(self, endpoint: str, method: str) -> APIContract | None:
        """查找指定端点的契约"""
        for contract in self.contracts:
            if contract.endpoint == endpoint and contract.method == method:
                return contract
        return None


class ContractStorage:
    """契约存储（One Memory 桥接）"""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else Path(".moat/memory.db")
        self._bridge = None

    def _get_bridge(self):
        """获取 One Memory 桥接器（延迟加载）"""
        if self._bridge is None:
            try:
                from ...memory.bridge import SharedStorageBridge, BridgeConfig
                self._bridge = SharedStorageBridge(
                    BridgeConfig(db_path=str(self.db_path))
                )
                self._bridge.initialize()
            except ImportError:
                self._bridge = False
        return self._bridge if self._bridge else None

    def save_baseline(self, baseline: ContractBaseline) -> bool:
        """保存契约基线到 One Memory"""
        bridge = self._get_bridge()
        if not bridge:
            return False

        try:
            baseline.baseline_hash = baseline.compute_hash()

            # 保存基线元数据
            bridge.store_contract_baseline(
                {
                    "service_name": baseline.service_name,
                    "version": baseline.version,
                    "baseline_hash": baseline.baseline_hash,
                    "created_at": baseline.created_at,
                    "contract_count": len(baseline.contracts),
                }
            )

            # 保存每个契约
            for contract in baseline.contracts:
                bridge.store_api_contract(
                    {
                        "service_name": baseline.service_name,
                        "version": baseline.version,
                        "endpoint": contract.endpoint,
                        "method": contract.method,
                        "request_schema": contract.request_schema,
                        "response_schema": contract.response_schema,
                        "status_code": contract.status_code,
                        "description": contract.description,
                        "contract_hash": contract.compute_hash(),
                        "created_at": contract.created_at,
                        "last_modified": contract.last_modified,
                    }
                )
            return True
        except Exception as e:
            print(f"⚠️  保存契约基线失败: {e}")
            return False

    def load_baseline(self, service_name: str) -> ContractBaseline | None:
        """从 One Memory 加载契约基线"""
        bridge = self._get_bridge()
        if not bridge:
            return None

        try:
            baseline_data = bridge.query_contract_baseline(service_name)
            if not baseline_data:
                return None

            contract_nodes = bridge.query_api_contracts(service_name)

            contracts = []
            for node in contract_nodes:
                data = node
                contract = APIContract(
                    endpoint=data["endpoint"],
                    method=data["method"],
                    request_schema=json.loads(data.get("request_schema", "{}") or "{}"),
                    response_schema=json.loads(data.get("response_schema", "{}") or "{}"),
                    status_code=data["status_code"],
                    description=data["description"],
                    created_at=data.get("created_at", ""),
                    last_modified=data.get("last_modified", ""),
                )
                contracts.append(contract)

            return ContractBaseline(
                service_name=service_name,
                version=baseline_data["version"],
                contracts=contracts,
                created_at=baseline_data["created_at"],
                baseline_hash=baseline_data["baseline_hash"],
            )
        except Exception as e:
            print(f"⚠️  加载契约基线失败: {e}")
            return None

    def detect_changes(
        self, service_name: str, new_contracts: list[APIContract]
    ) -> list[dict[str, Any]]:
        """检测契约变更"""
        old_baseline = self.load_baseline(service_name)
        if not old_baseline:
            return [
                {
                    "type": "added",
                    "endpoint": c.endpoint,
                    "method": c.method,
                    "new_contract": c,
                    "is_breaking": False,
                }
                for c in new_contracts
            ]

        changes = []
        old_contracts = {f"{c.method} {c.endpoint}": c for c in old_baseline.contracts}
        new_contracts_map = {f"{c.method} {c.endpoint}": c for c in new_contracts}

        for key, new_contract in new_contracts_map.items():
            if key not in old_contracts:
                changes.append({
                    "type": "added",
                    "endpoint": new_contract.endpoint,
                    "method": new_contract.method,
                    "new_contract": new_contract,
                    "is_breaking": False,
                })
            else:
                old_contract = old_contracts[key]
                if old_contract.compute_hash() != new_contract.compute_hash():
                    is_breaking = self._is_breaking_change(old_contract, new_contract)
                    changes.append({
                        "type": "modified",
                        "endpoint": new_contract.endpoint,
                        "method": new_contract.method,
                        "old_contract": old_contract,
                        "new_contract": new_contract,
                        "is_breaking": is_breaking,
                    })

        for key, old_contract in old_contracts.items():
            if key not in new_contracts_map:
                changes.append({
                    "type": "removed",
                    "endpoint": old_contract.endpoint,
                    "method": old_contract.method,
                    "old_contract": old_contract,
                    "is_breaking": True,
                })

        return changes

    def _is_breaking_change(self, old: APIContract, new: APIContract) -> bool:
        """判断是否破坏性变更

        检查项：
        1. 响应状态码变更
        2. 请求字段删除（包括 required 字段）
        3. 响应字段删除
        4. 字段类型变更（AI 最容易犯的错误）
        5. 字段格式变更（如 email → text）
        """
        if old.status_code != new.status_code:
            return True

        # 请求字段对比
        old_fields = old.request_schema.get("properties", {})
        new_fields = new.request_schema.get("properties", {})
        old_required = set(old.request_schema.get("required", []))
        new_required = set(new.request_schema.get("required", []))

        # 2. 请求字段删除
        if set(old_fields.keys()) - set(new_fields.keys()):
            return True

        # 2.5 请求 required 字段删除（AI 贪快最容易删掉的字段）
        if old_required - new_required:
            return True

        # 4. 字段类型变更（AI 不看 API 文档直接盲写）
        for field_name in old_fields.keys() & new_fields.keys():
            old_type = old_fields[field_name].get("type")
            new_type = new_fields[field_name].get("type")
            if old_type and new_type and old_type != new_type:
                return True

        # 5. 字段格式变更（如 email 格式被删除）
        for field_name in old_fields.keys() & new_fields.keys():
            old_format = old_fields[field_name].get("format")
            new_format = new_fields[field_name].get("format")
            if old_format and old_format != new_format:
                return True

        # 响应字段对比
        old_resp_fields = old.response_schema.get("properties", {})
        new_resp_fields = new.response_schema.get("properties", {})

        # 3. 响应字段删除
        if set(old_resp_fields.keys()) - set(new_resp_fields.keys()):
            return True

        # 响应字段类型变更
        for field_name in old_resp_fields.keys() & new_resp_fields.keys():
            old_type = old_resp_fields[field_name].get("type")
            new_type = new_resp_fields[field_name].get("type")
            if old_type and new_type and old_type != new_type:
                return True

        return False


class ContractGenerator:
    """契约生成器"""

    def __init__(self, ai_gateway=None):
        self.ai_gateway = ai_gateway

    def from_openapi(self, openapi_spec: dict) -> list[APIContract]:
        """从 OpenAPI 规范生成契约"""
        contracts = []

        paths = openapi_spec.get("paths", {})
        for path, methods in paths.items():
            for method, spec in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue

                contract = APIContract(
                    endpoint=path,
                    method=method.upper(),
                    request_schema=self._extract_schema(spec, "request"),
                    response_schema=self._extract_schema(spec, "response"),
                    status_code=spec.get("default", {}).get("status_code", 200),
                    description=spec.get("summary", ""),
                )
                contracts.append(contract)

        return contracts

    def _extract_schema(self, spec: dict, schema_type: str) -> dict:
        """提取 Schema"""
        if schema_type == "request":
            return spec.get("requestBody", {}).get("content", {})
        else:
            responses = spec.get("responses", {})
            success_response = responses.get("200", responses.get("201", {}))
            return success_response.get("content", {})

    def generate_pact(self, contract: APIContract) -> dict[str, Any]:
        """生成 Pact 契约文件"""
        return {
            "consumer": {"name": "unknown"},
            "provider": {"name": "unknown"},
            "interactions": [
                {
                    "description": f"{contract.method} {contract.endpoint}",
                    "request": {
                        "method": contract.method,
                        "path": contract.endpoint,
                    },
                    "response": {
                        "status": contract.status_code,
                        "body": contract.response_schema,
                    },
                }
            ],
            "metadata": {
                "pactSpecification": {
                    "version": "3.0.0"
                }
            },
        }


def cmd_contract(args) -> int:
    """契约测试命令"""
    if args.action == "init":
        return _cmd_init(args)
    elif args.action == "check":
        return _cmd_check(args)
    elif args.action == "generate":
        return _cmd_generate(args)
    else:
        print(f"❌ 未知操作: {args.action}")
        return 1


def _cmd_init(args) -> int:
    """初始化契约基线"""
    print("\n📋 初始化 API 契约基线")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_check(args) -> int:
    """检查契约变更"""
    print("\n🔍 检查 API 契约变更")
    print("   功能开发中，敬请期待")
    return 0


def _cmd_generate(args) -> int:
    """从 OpenAPI 规范生成 Pact 契约"""
    api_spec_path = Path(args.api)

    if not api_spec_path.exists():
        print(f"❌ API 规范文件不存在: {api_spec_path}")
        return 1

    try:
        with open(api_spec_path) as f:
            openapi_spec = json.load(f)

        generator = ContractGenerator()
        contracts = generator.from_openapi(openapi_spec)

        print(f"\n📋 从 {api_spec_path.name} 生成 {len(contracts)} 个契约")

        # 保存到 Pact 文件
        output_dir = Path("tests/integration/contracts")
        output_dir.mkdir(parents=True, exist_ok=True)

        for contract in contracts:
            filename = f"{contract.method.lower()}_{contract.endpoint.replace('/', '_')}.json"
            output_path = output_dir / filename

            pact = generator.generate_pact(contract)
            with open(output_path, "w") as f:
                json.dump(pact, f, indent=2, ensure_ascii=False)

            print(f"   ✅ {output_path}")

        # 保存到 One Memory 基线
        print(f"\n💾 保存契约基线到 One Memory...")
        from datetime import datetime

        baseline = ContractBaseline(
            service_name=Path.cwd().name,
            version="1.0.0",
            contracts=contracts,
            created_at=datetime.now().isoformat(),
        )

        storage = ContractStorage()
        if storage.save_baseline(baseline):
            print(f"   ✅ 契约基线已保存")
        else:
            print(f"   ⚠️  One Memory 不可用，跳过基线保存")

        return 0

    except Exception as e:
        print(f"❌ 生成契约失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def _detect_schema_diffs(old: APIContract, new: APIContract) -> list[str]:
    """检测两个契约之间的详细差异

    Args:
        old: 旧契约
        new: 新契约

    Returns:
        差异描述列表
    """
    diffs = []

    # 状态码变更
    if old.status_code != new.status_code:
        diffs.append(f"状态码变更: {old.status_code} → {new.status_code}")

    # 请求字段对比
    old_fields = old.request_schema.get("properties", {})
    new_fields = new.request_schema.get("properties", {})
    old_required = set(old.request_schema.get("required", []))
    new_required = set(new.request_schema.get("required", []))

    # 字段删除
    removed = set(old_fields.keys()) - set(new_fields.keys())
    if removed:
        diffs.append(f"删除请求字段: {', '.join(sorted(removed))}")

    # required 字段删除（AI 贪快最容易删掉的字段）
    if old_required - new_required:
        diffs.append(f"删除必选字段: {', '.join(sorted(old_required - new_required))}")

    # 字段类型变更（AI 不看 API 文档直接盲写）
    for field_name in old_fields.keys() & new_fields.keys():
        old_type = old_fields[field_name].get("type")
        new_type = new_fields[field_name].get("type")
        if old_type and new_type and old_type != new_type:
            diffs.append(f"字段类型变更 [{field_name}]: {old_type} → {new_type}")

    # 字段格式变更（如 email 格式被删除）
    for field_name in old_fields.keys() & new_fields.keys():
        old_format = old_fields[field_name].get("format")
        new_format = new_fields[field_name].get("format")
        if old_format and old_format != new_format:
            diffs.append(f"字段格式变更 [{field_name}]: {old_format} → {new_format}")

    # 响应字段对比
    old_resp_fields = old.response_schema.get("properties", {})
    new_resp_fields = new.response_schema.get("properties", {})

    # 响应字段删除
    removed_resp = set(old_resp_fields.keys()) - set(new_resp_fields.keys())
    if removed_resp:
        diffs.append(f"删除响应字段: {', '.join(sorted(removed_resp))}")

    # 响应字段类型变更
    for field_name in old_resp_fields.keys() & new_resp_fields.keys():
        old_type = old_resp_fields[field_name].get("type")
        new_type = new_resp_fields[field_name].get("type")
        if old_type and new_type and old_type != new_type:
            diffs.append(f"响应字段类型变更 [{field_name}]: {old_type} → {new_type}")

    return diffs


def _generate_fix_suggestions(change: dict[str, Any]) -> list[str]:
    """生成修复建议

    Args:
        change: 变更信息

    Returns:
        修复建议列表
    """
    suggestions = []
    change_type = change["type"]
    endpoint = f"{change['method']} {change['endpoint']}"

    if change_type == "removed":
        suggestions.append(f"端点 {endpoint} 已被删除，所有消费者将失效。")
        suggestions.append("建议：")
        suggestions.append("  1. 如果确实需要删除，请先发布弃用通知（deprecation notice）")
        suggestions.append("  2. 更新所有消费者代码")
        suggestions.append(f"  3. 运行 $ moat immune contract update 更新基线")

    elif change_type == "modified":
        old_c = change.get("old_contract")
        new_c = change.get("new_contract")

        if not old_c or not new_c:
            return suggestions

        diffs = _detect_schema_diffs(old_c, new_c)

        if diffs:
            suggestions.append(f"端点 {endpoint} 有以下破坏性变更：")
            for diff in diffs:
                suggestions.append(f"  • {diff}")

            # 针对具体问题的建议
            if any("字段类型变更" in d for d in diffs):
                suggestions.append("\n💡 字段类型变更修复建议：")
                suggestions.append("  1. 保持类型一致，恢复原来的类型")
                suggestions.append("  2. 如果确实需要变更，考虑版本化：/v2/api/products")

            if any("必选字段" in d for d in diffs):
                suggestions.append("\n💡 必选字段删除修复建议：")
                suggestions.append("  1. 恢复必选字段（保持向后兼容）")
                suggestions.append("  2. 如果确实不需要，请先标记为 optional")
                suggestions.append("  3. 更新前端代码并通知所有依赖方")

            if any("响应字段" in d for d in diffs):
                suggestions.append("\n💡 响应字段变更修复建议：")
                suggestions.append("  1. 恢复响应字段（保持向后兼容）")
                suggestions.append("  2. 使用版本化：/v2/api/users")

            suggestions.append(f"\n如果确认变更正确，请运行：")
            suggestions.append(f"  $ moat immune contract update")
            suggestions.append(f"\n这将更新基线并通知所有消费者。")

    return suggestions


def add_contract_parser(sub) -> None:
    """添加 contract 命令到 argparse"""
    p_contract = sub.add_parser("contract", help="契约测试")
    p_contract.add_argument("action", choices=["init", "check", "generate"],
                           help="操作")
    p_contract.add_argument("--api", help="OpenAPI 规范文件路径（仅 generate）")
