#!/usr/bin/env python3
"""
契约测试系统验证脚本
"""

import sys
import json
import pytest
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from moat.immune.contract.contracts import ContractGenerator, ContractStorage, ContractBaseline, APIContract


@pytest.fixture
def contracts():
    """创建测试契约"""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/api/users": {
                "get": {
                    "summary": "获取用户列表",
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "users": {"type": "array"},
                                            "total": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            },
        },
    }

    generator = ContractGenerator()
    contracts = generator.from_openapi(openapi_spec)
    return contracts


def test_contract_generation(contracts):
    """测试契约生成"""
    print("📋 测试 1: 契约生成")

    # contracts fixture 已经生成了契约
    assert len(contracts) >= 1, "应该至少生成 1 个契约"
    print(f"   ✅ 生成了 {len(contracts)} 个契约")

    for contract in contracts:
        print(f"   - {contract.method} {contract.endpoint}")


def test_pact_generation(contracts):
    """测试 Pact 文件生成"""
    print("\n📋 测试 2: Pact 文件生成")

    generator = ContractGenerator()
    pact = generator.generate_pact(contracts[0])

    assert "consumer" in pact, "Pact 应该包含 consumer"
    assert "provider" in pact, "Pact 应该包含 provider"
    assert "interactions" in pact, "Pact 应该包含 interactions"
    assert len(pact["interactions"]) > 0, "Pact 应该至少有一个 interaction"

    print(f"   ✅ Pact 文件生成成功")
    print(f"   - Consumer: {pact['consumer']['name']}")
    print(f"   - Provider: {pact['provider']['name']}")
    print(f"   - Interactions: {len(pact['interactions'])}")


def test_contract_hash(contracts):
    """测试契约哈希计算"""
    print("\n📋 测试 3: 契约哈希计算")

    contract1 = contracts[0]
    hash1 = contract1.compute_hash()
    hash2 = contract1.compute_hash()

    assert hash1 == hash2, "相同契约应该生成相同的哈希"
    assert len(hash1) == 16, "哈希长度应该是 16 字符"

    print(f"   ✅ 哈希计算正确: {hash1}")


def test_baseline(contracts):
    """测试契约基线"""
    print("\n📋 测试 4: 契约基线")

    baseline = ContractBaseline(
        service_name="test-service",
        version="1.0.0",
        contracts=contracts,
        created_at=datetime.now().isoformat(),
    )

    baseline_hash = baseline.compute_hash()
    assert len(baseline_hash) == 16, "基线哈希长度应该是 16 字符"

    print(f"   ✅ 基线创建成功")
    print(f"   - Service: {baseline.service_name}")
    print(f"   - Contracts: {len(baseline.contracts)}")
    print(f"   - Hash: {baseline_hash}")


if __name__ == "__main__":
    print("🧪 契约测试系统验证\n")
    print("=" * 50)

    try:
        contracts = test_contract_generation()
        test_pact_generation(contracts)
        test_contract_hash(contracts)
        test_baseline(contracts)

        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
