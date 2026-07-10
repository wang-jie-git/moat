#!/usr/bin/env python3
"""
契约测试系统集成验证

验证完整的 OpenAPI → Pact → One Memory 流程
"""

import sys
import json
from pathlib import Path

# 直接导入（绕过 pytest 权限问题）
sys.path.insert(0, str(Path(__file__).parent.parent))

from moat.immune.contract.contracts import (
    ContractGenerator,
    ContractStorage,
    ContractBaseline,
    APIContract,
)
from datetime import datetime


def test_openapi_to_contracts():
    """测试 1: OpenAPI → APIContract"""
    print("📋 测试 1: OpenAPI 规范 → APIContract")

    # 模拟一个真实的 OpenAPI spec
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Moat API", "version": "1.0.0"},
        "paths": {
            "/api/users": {
                "get": {
                    "summary": "获取用户列表",
                    "operationId": "getUsers",
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "users": {
                                                "type": "array",
                                                "items": {
                                                }
                                            },
                                            "total": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "创建用户",
                    "operationId": "createUser",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name", "email"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string", "format": "email"},
                                        "age": {"type": "integer", "minimum": 0},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "创建成功",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "400": {
                            "description": "请求参数错误",
                        },
                    },
                },
            },
            "/api/users/{user_id}": {
                "get": {
                    "summary": "获取单个用户",
                    "operationId": "getUserById",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "404": {
                            "description": "用户不存在",
                        },
                    },
                },
                "delete": {
                    "summary": "删除用户",
                    "operationId": "deleteUser",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"204": {"description": "删除成功"}, "404": {"description": "用户不存在"}},
                },
            },
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                }
            }
        },
    }

    generator = ContractGenerator()
    contracts = generator.from_openapi(openapi_spec)

    assert len(contracts) == 4, f"应该生成 4 个契约，实际生成 {len(contracts)}"
    print(f"   ✅ 生成了 {len(contracts)} 个契约")

    for contract in contracts:
        print(f"   - {contract.method:6s} {contract.endpoint:25s} | {contract.description}")

    return contracts


def test_pact_generation(contracts):
    """测试 2: Pact 文件生成"""
    print("\n📋 测试 2: Pact 文件生成")

    generator = ContractGenerator()

    for contract in contracts:
        pact = generator.generate_pact(contract)

        assert "consumer" in pact, "Pact 缺少 consumer"
        assert "provider" in pact, "Pact 缺少 provider"
        assert "interactions" in pact, "Pact 缺少 interactions"
        assert len(pact["interactions"]) > 0, "Pact 缺少 interaction"

        print(f"   ✅ {contract.method} {contract.endpoint}")
        print(f"      - Interaction: {pact['interactions'][0]['description']}")
        print(f"      - Status: {pact['interactions'][0]['response']['status']}")


def test_contract_hashing(contracts):
    """测试 3: 契约哈希计算"""
    print("\n📋 测试 3: 契约哈希计算")

    for contract in contracts:
        hash1 = contract.compute_hash()
        hash2 = contract.compute_hash()

        assert hash1 == hash2, f"相同契约应该生成相同的哈希"
        assert len(hash1) == 16, f"哈希长度应该是 16 字符"

        print(f"   ✅ {contract.method} {contract.endpoint}")
        print(f"      - Hash: {hash1}")


def test_baseline_operations(contracts):
    """测试 4: 契约基线操作"""
    print("\n📋 测试 4: 契约基线操作")

    baseline = ContractBaseline(
        service_name="test-api",
        version="1.0.0",
        contracts=contracts,
        created_at=datetime.now().isoformat(),
    )

    # 基线哈希
    baseline_hash = baseline.compute_hash()
    assert len(baseline_hash) == 16
    print(f"   ✅ 基线创建成功")
    print(f"      - Service: {baseline.service_name}")
    print(f"      - Contracts: {len(baseline.contracts)}")
    print(f"      - Baseline Hash: {baseline_hash}")

    # 查找契约
    contract = baseline.find_contract("/api/users", "GET")
    assert contract is not None, "应该能找到 GET /api/users"
    assert contract.description == "获取用户列表"
    print(f"   ✅ 契约查找成功: {contract.method} {contract.endpoint}")

    not_found = baseline.find_contract("/api/nonexistent", "GET")
    assert not_found is None, "不存在的契约应该返回 None"
    print(f"   ✅ 不存在的契约正确返回 None")


def test_change_detection():
    """测试 5: 变更检测"""
    print("\n📋 测试 5: 变更检测")

    # 创建旧契约
    old_contracts = [
        APIContract(
            endpoint="/api/users",
            method="GET",
            request_schema={},
            response_schema={"type": "object", "properties": {"users": {"type": "array"}}},
            status_code=200,
            description="获取用户列表（旧）",
            created_at="2026-01-01T00:00:00",
        ),
        APIContract(
            endpoint="/api/users/{user_id}",
            method="GET",
            request_schema={},
            response_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            status_code=200,
            description="获取单个用户",
            created_at="2026-01-01T00:00:00",
        ),
    ]

    # 新契约（有变更）
    new_contracts = [
        APIContract(
            endpoint="/api/users",
            method="GET",
            request_schema={},
            response_schema={"type": "object", "properties": {"users": {"type": "array"}, "total": {"type": "integer"}}},
            status_code=200,
            description="获取用户列表（新 - 添加了 total 字段）",
            created_at="2026-01-02T00:00:00",
        ),
        APIContract(
            endpoint="/api/users/{user_id}",
            method="GET",
            request_schema={},
            response_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
            status_code=200,
            description="获取单个用户（未变）",
            created_at="2026-01-01T00:00:00",
        ),
    ]

    storage = ContractStorage()
    changes = storage.detect_changes("test-api", new_contracts)

    assert len(changes) == 1, f"应该检测到 1 个变更，实际检测到 {len(changes)}"
    assert changes[0]["type"] == "modified", "应该是 modified 类型"
    assert changes[0]["endpoint"] == "/api/users"
    assert changes[0]["method"] == "GET"
    assert not changes[0]["is_breaking"], "添加字段不应该是破坏性变更"

    print(f"   ✅ 检测到 {len(changes)} 个变更")
    for change in changes:
        print(f"      - [{change['type']:10s}] {change['method']} {change['endpoint']}")
        print(f"        Breaking: {change['is_breaking']}")


def test_breaking_change_detection():
    """测试 6: 破坏性变更检测"""
    print("\n📋 测试 6: 破坏性变更检测")

    old = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={"type": "object", "properties": {"name": {"type": "string"}, "email": {"type": "string"}}},
        response_schema={"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}},
        status_code=201,
        description="创建用户",
    )

    # 场景 1: 删除请求字段（破坏性）
    new1 = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={"type": "object", "properties": {"name": {"type": "string"}}},  # 删除了 email
        response_schema=old.response_schema,
        status_code=201,
        description="创建用户（删除了 email 字段）",
    )

    assert storage._is_breaking_change(old, new1), "删除请求字段应该是破坏性变更"
    print(f"   ✅ 删除请求字段 → Breaking Change")

    # 场景 2: 删除响应字段（破坏性）
    new2 = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema=old.request_schema,
        response_schema={"type": "object", "properties": {"id": {"type": "integer"}}},  # 删除了 name
        status_code=201,
        description="创建用户（删除了响应 name 字段）",
    )

    assert storage._is_breaking_change(old, new2), "删除响应字段应该是破坏性变更"
    print(f"   ✅ 删除响应字段 → Breaking Change")

    # 场景 3: 状态码变更（破坏性）
    new3 = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema=old.request_schema,
        response_schema=old.response_schema,
        status_code=200,  # 从 201 改为 200
        description="创建用户（状态码变更）",
    )

    assert storage._is_breaking_change(old, new3), "状态码变更应该是破坏性变更"
    print(f"   ✅ 状态码变更 → Breaking Change")


if __name__ == "__main__":
    print("🧪 契约测试系统集成验证\n")
    print("=" * 60)

    try:
        contracts = test_openapi_to_contracts()
        test_pact_generation(contracts)
        test_contract_hashing(contracts)
        test_baseline_operations(contracts)
        test_change_detection()
        test_breaking_change_detection()

        print("\n" + "=" * 60)
        print("✅ 所有集成测试通过！")
        print("\n💡 下一步:")
        print("   - 使用真实的 OpenAPI spec 文件验证")
        print("   - 集成 Claude Code Hook（API 变更自动检查）")
        print("   - 实现 AI 契约自愈能力")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
