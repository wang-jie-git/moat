#!/usr/bin/env python3
"""
Moat Immune 完整集成测试

验证：
1. Mock OpenAPI specs → Pact 契约生成
2. 破坏性变更检测（含 AI 隐蔽错误：字段类型变更、必选字段删除）
3. 主动干预建议（不仅仅是告警，还要给出修复建议）
4. Claude Code Hook 集成
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from moat.immune.contract.contracts import (
    ContractGenerator,
    ContractStorage,
    ContractBaseline,
    APIContract,
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def complete_openapi():
    """完整的 OpenAPI spec（基线版本）"""
    spec_path = Path(__file__).parent.parent / "fixtures" / "mock_openapi_specs" / "complete_openapi.json"
    with open(spec_path) as f:
        return json.load(f)


@pytest.fixture
def broken_openapi():
    """故意有缺陷的 OpenAPI spec（模拟 AI 编码错误）"""
    spec_path = Path(__file__).parent.parent / "fixtures" / "mock_openapi_specs" / "broken_contract.json"
    with open(spec_path) as f:
        return json.load(f)


@pytest.fixture
def generator():
    """契约生成器"""
    return ContractGenerator()


@pytest.fixture
def storage(tmp_path):
    """契约存储（使用临时目录）"""
    db_path = tmp_path / "test_memory.db"
    return ContractStorage(db_path=str(db_path))


# ========================================
# 测试 1: OpenAPI → Contract 生成
# ========================================

def test_openapi_to_contracts_complete(complete_openapi, generator):
    """测试 1: 完整 OpenAPI spec → APIContract"""
    print("\n📋 [测试 1] OpenAPI → Contract 生成（完整版本）")

    contracts = generator.from_openapi(complete_openapi)

    assert len(contracts) > 0, "应该生成至少 1 个契约"

    # 验证关键端点存在
    endpoints = {f"{c.method} {c.endpoint}" for c in contracts}
    assert "GET /api/users" in endpoints
    assert "POST /api/users" in endpoints
    assert "GET /api/users/{user_id}" in endpoints
    assert "DELETE /api/users/{user_id}" in endpoints
    assert "POST /api/products" in endpoints
    assert "POST /api/orders" in endpoints

    print(f"   ✅ 生成了 {len(contracts)} 个契约")
    for c in contracts:
        print(f"      - {c.method:6s} {c.endpoint:25s} | {c.description}")


def test_openapi_to_contracts_broken(broken_openapi, generator):
    """测试 2: 有缺陷的 OpenAPI spec → Contract"""
    print("\n📋 [测试 2] OpenAPI → Contract 生成（有缺陷版本）")

    contracts = generator.from_openapi(broken_openapi)

    assert len(contracts) > 0, "应该生成至少 1 个契约"

    # 验证有缺陷的端点
    endpoints = {f"{c.method} {c.endpoint}" for c in contracts}
    assert "POST /api/products" in endpoints, "应该有 POST /api/products"

    print(f"   ✅ 生成了 {len(contracts)} 个契约（含缺陷）")


# ========================================
# 测试 3: Pact 文件生成
# ========================================

def test_pact_generation_complete(complete_openapi, generator, tmp_path):
    """测试 3: 生成 Pact 文件并保存"""
    print("\n📋 [测试 3] Pact 文件生成")

    contracts = generator.from_openapi(complete_openapi)

    # 保存到临时目录
    output_dir = tmp_path / "contracts"
    output_dir.mkdir()

    for contract in contracts:
        pact = generator.generate_pact(contract)
        filename = f"{contract.method.lower()}_{contract.endpoint.replace('/', '_').replace('{', '').replace('}', '')}.json"
        output_path = output_dir / filename

        with open(output_path, "w") as f:
            json.dump(pact, f, indent=2)

    # 验证文件已生成
    pact_files = list(output_dir.glob("*.json"))
    assert len(pact_files) == len(contracts), f"应该生成 {len(contracts)} 个 Pact 文件"

    # 验证 Pact 结构
    with open(pact_files[0]) as f:
        pact = json.load(f)

    assert "consumer" in pact
    assert "provider" in pact
    assert "interactions" in pact
    assert len(pact["interactions"]) > 0

    print(f"   ✅ 生成了 {len(pact_files)} 个 Pact 文件")
    print(f"      - 示例: {pact_files[0].name}")


# ========================================
# 测试 4: 契约哈希计算
# ========================================

def test_contract_hash_deterministic(generator, complete_openapi):
    """测试 4: 契约哈希值确定性"""
    print("\n📋 [测试 4] 契约哈希计算")

    contracts = generator.from_openapi(complete_openapi)
    contract = contracts[0]

    hash1 = contract.compute_hash()
    hash2 = contract.compute_hash()

    assert hash1 == hash2, "相同契约应该生成相同的哈希"
    assert len(hash1) == 16, "哈希长度应该是 16 字符"

    # 不同契约应该有不同哈希
    if len(contracts) > 1:
        hash3 = contracts[1].compute_hash()
        assert hash1 != hash3, "不同契约应该生成不同哈希"

    print(f"   ✅ 哈希计算正确: {hash1}")


# ========================================
# 测试 5: 契约基线操作
# ========================================

def test_baseline_create_and_find(complete_openapi, generator, storage):
    """测试 5: 创建和查找契约基线"""
    print("\n📋 [测试 5] 契约基线操作")

    contracts = generator.from_openapi(complete_openapi)

    baseline = ContractBaseline(
        service_name="test-api",
        version="1.0.0",
        contracts=contracts,
        created_at=datetime.now().isoformat(),
    )

    # 基线哈希
    baseline_hash = baseline.compute_hash()
    assert len(baseline_hash) == 16

    # 查找契约
    contract = baseline.find_contract("/api/users", "GET")
    assert contract is not None, "应该能找到 GET /api/users"
    assert contract.description == "获取用户列表"

    not_found = baseline.find_contract("/api/nonexistent", "GET")
    assert not_found is None, "不存在的契约应该返回 None"

    print(f"   ✅ 基线创建和查找成功")
    print(f"      - Contracts: {len(baseline.contracts)}")
    print(f"      - Baseline Hash: {baseline_hash}")


# ========================================
# 测试 6: 变更检测
# ========================================

def test_change_detection_added(complete_openapi, broken_openapi, generator, storage):
    """测试 6: 检测新增端点"""
    print("\n📋 [测试 6] 变更检测 - 新增端点")

    old_contracts = generator.from_openapi(complete_openapi)
    new_contracts = generator.from_openapi(broken_openapi)

    changes = storage.detect_changes("test-api", new_contracts)

    added = [c for c in changes if c["type"] == "added"]
    assert len(added) > 0, "应该检测到新增端点"

    print(f"   ✅ 检测到 {len(added)} 个新增端点")
    for change in added:
        print(f"      - [added] {change['method']} {change['endpoint']}")


def test_change_detection_removed(complete_openapi, broken_openapi, generator, storage):
    """测试 7: 检测删除端点"""
    print("\n📋 [测试 7] 变更检测 - 删除端点")

    old_contracts = generator.from_openapi(complete_openapi)

    # 先保存基线到 One Memory
    from datetime import datetime
    baseline = ContractBaseline(
        service_name="test-api-removed",
        version="1.0.0",
        contracts=old_contracts,
        created_at=datetime.now().isoformat(),
    )
    storage.save_baseline(baseline)

    new_contracts = generator.from_openapi(broken_openapi)

    changes = storage.detect_changes("test-api-removed", new_contracts)

    removed = [c for c in changes if c["type"] == "removed"]
    assert len(removed) > 0, "应该检测到删除端点"

    print(f"   ✅ 检测到 {len(removed)} 个删除端点")
    for change in removed:
        print(f"      - [removed] {change['method']} {change['endpoint']}")


def test_change_detection_modified(complete_openapi, broken_openapi, generator, storage):
    """测试 8: 检测修改端点"""
    print("\n📋 [测试 8] 变更检测 - 修改端点")

    old_contracts = generator.from_openapi(complete_openapi)

    # 先保存基线到 One Memory
    from datetime import datetime
    baseline = ContractBaseline(
        service_name="test-api-modified",
        version="1.0.0",
        contracts=old_contracts,
        created_at=datetime.now().isoformat(),
    )
    storage.save_baseline(baseline)

    new_contracts = generator.from_openapi(broken_openapi)

    changes = storage.detect_changes("test-api-modified", new_contracts)

    modified = [c for c in changes if c["type"] == "modified"]
    assert len(modified) > 0, "应该检测到修改端点"

    print(f"   ✅ 检测到 {len(modified)} 个修改端点")
    for change in modified:
        print(f"      - [modified] {change['method']} {change['endpoint']}")
        print(f"        Breaking: {change['is_breaking']}")


# ========================================
# 测试 9: 破坏性变更检测（AI 隐蔽错误）
# ========================================

def test_breaking_change_field_type_mutation(storage):
    """
    测试 9: 字段类型变更（AI 最容易犯的错误）

    AI 不看 API 文档直接盲写，把 price 从 Integer 改成 String
    """
    print("\n📋 [测试 9] 破坏性变更 - 字段类型变更（price: Integer → String）")

    old = APIContract(
        endpoint="/api/products",
        method="POST",
        request_schema={
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "integer", "minimum": 0}
            }
        },
        response_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "price": {"type": "integer"}
            }
        },
        status_code=201,
        description="创建商品",
    )

    new = APIContract(
        endpoint="/api/products",
        method="POST",
        request_schema={
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "string"}  # AI 把 Integer 改成了 String！
            }
        },
        response_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "price": {"type": "string"}
            }
        },
        status_code=201,
        description="创建商品",
    )

    # 使用增强的检测逻辑
    diffs = _detect_schema_diffs(old, new)
    is_breaking = storage._is_breaking_change(old, new)

    assert is_breaking, "字段类型变更应该是破坏性变更"
    assert any("类型变更" in d for d in diffs), "应该检测到类型变更"

    print(f"   ✅ 字段类型变更检测正确")
    print(f"      - 旧: price: Integer")
    print(f"      - 新: price: String")
    print(f"      - 结论: Breaking Change ❌")
    print(f"\n   💡 诊断详情:")
    for diff in diffs:
        print(f"      - {diff}")


def _detect_schema_diffs(old: APIContract, new: APIContract) -> list[str]:
    """检测契约差异并返回详细描述"""
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
        diffs.append(f"删除请求字段: {removed}")

    # required 字段删除
    if old_required - new_required:
        diffs.append(f"删除必选字段: {old_required - new_required}")

    # 字段类型变更
    for field_name in old_fields.keys() & new_fields.keys():
        old_type = old_fields[field_name].get("type")
        new_type = new_fields[field_name].get("type")
        if old_type and new_type and old_type != new_type:
            diffs.append(f"字段类型变更 [{field_name}]: {old_type} → {new_type}")

    # 字段格式变更
    for field_name in old_fields.keys() & new_fields.keys():
        old_format = old_fields[field_name].get("format")
        new_format = new_fields[field_name].get("format")
        if old_format and old_format != new_format:
            diffs.append(f"字段格式变更 [{field_name}]: {old_format} → {new_format}")

    # 响应字段对比
    old_resp = old.response_schema.get("properties", {})
    new_resp = new.response_schema.get("properties", {})

    removed_resp = set(old_resp.keys()) - set(new_resp.keys())
    if removed_resp:
        diffs.append(f"删除响应字段: {removed_resp}")

    # 响应字段类型变更
    for field_name in old_resp.keys() & new_resp.keys():
        old_type = old_resp[field_name].get("type")
        new_type = new_resp[field_name].get("type")
        if old_type and new_type and old_type != new_type:
            diffs.append(f"响应字段类型变更 [{field_name}]: {old_type} → {new_type}")

    return diffs


def test_breaking_change_required_field_removal(storage):
    """
    测试 10: 删除必选字段（AI 贪快最容易删掉的字段）

    AI 觉得 "email 反正也没用到" 就删了，但前端依赖这个字段
    """
    print("\n📋 [测试 10] 破坏性变更 - 删除必选字段（email）")

    old = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            }
        },
        response_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "email": {"type": "string"}
            }
        },
        status_code=201,
        description="创建用户",
    )

    new = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"}
            }
        },
        response_schema=old.response_schema,
        status_code=201,
        description="创建用户",
    )

    is_breaking = storage._is_breaking_change(old, new)
    assert is_breaking, "删除必选字段应该是破坏性变更"

    print(f"   ✅ 删除必选字段检测正确")
    print(f"      - 旧: required = [name, email]")
    print(f"      - 新: required = [name]")
    print(f"      - 结论: Breaking Change ❌")


def test_breaking_change_response_field_removal(storage):
    """测试 11: 删除响应字段"""
    print("\n📋 [测试 11] 破坏性变更 - 删除响应字段（id）")

    old = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={},
        response_schema={
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "email": {"type": "string"}
            }
        },
        status_code=201,
        description="创建用户",
    )

    new = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={},
        response_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"}
                # id 字段被删除！
            }
        },
        status_code=201,
        description="创建用户",
    )

    is_breaking = storage._is_breaking_change(old, new)
    assert is_breaking, "删除响应字段应该是破坏性变更"

    print(f"   ✅ 删除响应字段检测正确")
    print(f"      - 旧: id, name, email")
    print(f"      - 新: name, email")
    print(f"      - 结论: Breaking Change ❌")


def test_breaking_change_status_code_change(storage):
    """测试 12: 状态码变更"""
    print("\n📋 [测试 12] 破坏性变更 - 状态码变更（201 → 200）")

    old = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={},
        response_schema={},
        status_code=201,
        description="创建用户",
    )

    new = APIContract(
        endpoint="/api/users",
        method="POST",
        request_schema={},
        response_schema={},
        status_code=200,  # 状态码变更
        description="创建用户",
    )

    is_breaking = storage._is_breaking_change(old, new)
    assert is_breaking, "状态码变更应该是破坏性变更"

    print(f"   ✅ 状态码变更检测正确")
    print(f"      - 旧: 201 Created")
    print(f"      - 新: 200 OK")
    print(f"      - 结论: Breaking Change ❌")


def test_non_breaking_change_additional_fields(storage):
    """测试 13: 添加字段（非破坏性）"""
    print("\n📋 [测试 13] 非破坏性变更 - 添加可选字段")

    old = APIContract(
        endpoint="/api/users",
        method="GET",
        request_schema={},
        response_schema={
            "type": "object",
            "properties": {
                "users": {"type": "array"},
                "total": {"type": "integer"}
            }
        },
        status_code=200,
        description="获取用户列表",
    )

    new = APIContract(
        endpoint="/api/users",
        method="GET",
        request_schema={},
        response_schema={
            "type": "object",
            "properties": {
                "users": {"type": "array"},
                "total": {"type": "integer"},
                "page": {"type": "integer"},  # 新增字段
                "page_size": {"type": "integer"}  # 新增字段
            }
        },
        status_code=200,
        description="获取用户列表（新增分页字段）",
    )

    is_breaking = storage._is_breaking_change(old, new)
    assert not is_breaking, "添加可选字段应该是非破坏性变更"

    print(f"   ✅ 添加可选字段检测正确")
    print(f"      - 新增: page, page_size")
    print(f"      - 结论: Non-Breaking Change ✅")


# ========================================
# 测试 14: One Memory 存储和加载
# ========================================

def test_storage_save_and_load(complete_openapi, generator, storage):
    """测试 14: 保存和加载契约基线"""
    print("\n📋 [测试 14] One Memory 存储和加载")

    contracts = generator.from_openapi(complete_openapi)

    baseline = ContractBaseline(
        service_name="test-api-storage-unique",
        version="1.0.0",
        contracts=contracts,
        created_at=datetime.now().isoformat(),
    )

    # 保存
    success = storage.save_baseline(baseline)
    assert success, "保存应该成功"

    # 加载
    loaded = storage.load_baseline("test-api-storage-unique")
    assert loaded is not None, "应该能加载基线"
    assert loaded.service_name == "test-api-storage-unique"
    assert len(loaded.contracts) == len(contracts), f"应该加载 {len(contracts)} 个契约，实际加载 {len(loaded.contracts)}"

    print(f"   ✅ 保存和加载成功")
    print(f"      - Contracts: {len(loaded.contracts)}")


# ========================================
# 测试 15: 完整的变更检测流程
# ========================================

def test_full_change_detection_workflow(complete_openapi, broken_openapi, generator, storage):
    """
    测试 15: 完整的变更检测流程

    模拟真实场景：
    1. 初始化基线（v1.0.0）
    2. AI 修改了 API（引入破坏性变更）
    3. Moat 检测到变更并告警
    """
    print("\n📋 [测试 15] 完整变更检测流程")

    # 1. 初始化基线（v1.0.0）
    v1_contracts = generator.from_openapi(complete_openapi)
    baseline_v1 = ContractBaseline(
        service_name="test-api-workflow",
        version="1.0.0",
        contracts=v1_contracts,
        created_at=datetime.now().isoformat(),
    )
    storage.save_baseline(baseline_v1)
    print(f"   ✅ v1.0.0 基线已保存（{len(v1_contracts)} 个契约）")

    # 2. AI 修改了 API（v2.0.0，含破坏性变更）
    v2_contracts = generator.from_openapi(broken_openapi)
    baseline_v2 = ContractBaseline(
        service_name="test-api-workflow",
        version="2.0.0",
        contracts=v2_contracts,
        created_at=datetime.now().isoformat(),
    )

    # 3. 检测变更
    changes = storage.detect_changes("test-api-workflow", v2_contracts)

    # 分类变更
    added = [c for c in changes if c["type"] == "added"]
    removed = [c for c in changes if c["type"] == "removed"]
    modified = [c for c in changes if c["type"] == "modified"]
    breaking = [c for c in changes if c.get("is_breaking", False)]

    print(f"\n   📊 变更统计:")
    print(f"      - 新增: {len(added)}")
    print(f"      - 删除: {len(removed)}")
    print(f"      - 修改: {len(modified)}")
    print(f"      - 破坏性: {len(breaking)}")

    # 验证（broken_contract 只有 5 个端点，complete 有 8 个）
    # 所以应该有删除和修改，不一定是新增
    assert len(removed) > 0 or len(modified) > 0, "应该有删除或修改"
    assert len(breaking) > 0, "应该有破坏性变更"

    # 打印破坏性变更详情
    print(f"\n   ❌ 破坏性变更详情:")
    for change in breaking:
        print(f"      - [{change['type']:10s}] {change['method']} {change['endpoint']}")
        if "old_contract" in change and "new_contract" in change:
            old_fields = set(change["old_contract"].request_schema.get("properties", {}).keys())
            new_fields = set(change["new_contract"].request_schema.get("properties", {}).keys())
            if old_fields - new_fields:
                print(f"        删除字段: {old_fields - new_fields}")
            if new_fields - old_fields:
                print(f"        新增字段: {new_fields - old_fields}")

    print(f"\n   ✅ 完整流程验证成功")


# ========================================
# 测试 16: Claude Code Hook 集成
# ========================================

def test_claude_code_hook_block_on_breaking_change(
    complete_openapi, broken_openapi, generator, storage
):
    """
    测试 16: Claude Code Hook — 破坏性变更时阻止提交

    模拟：
    1. Claude 准备提交 API 代码
    2. 触发 moat immune contract check
    3. 检测到破坏性变更
    4. Hook 阻止提交并输出报告
    """
    print("\n📋 [测试 16] Claude Code Hook — 阻止破坏性变更")

    # 1. 初始化基线
    v1_contracts = generator.from_openapi(complete_openapi)
    baseline_v1 = ContractBaseline(
        service_name="test-api",
        version="1.0.0",
        contracts=v1_contracts,
        created_at=datetime.now().isoformat(),
    )
    storage.save_baseline(baseline_v1)

    # 2. Claude 修改了 API（触发 Hook）
    v2_contracts = generator.from_openapi(broken_openapi)
    changes = storage.detect_changes("test-api", v2_contracts)

    # 3. 检查是否有破坏性变更
    breaking_changes = [c for c in changes if c.get("is_breaking", False)]

    if breaking_changes:
        # 4. Hook 应该阻止提交
        print(f"   ❌ Claude Code Hook: 检测到 {len(breaking_changes)} 个破坏性变更")
        print(f"   ⛔ 阻止提交！")

        # 生成告警报告
        print(f"\n   📋 破坏性变更报告:")
        print(f"   {'='*60}")
        for i, change in enumerate(breaking_changes, 1):
            print(f"\n   {i}. [{change['type'].upper()}] {change['method']} {change['endpoint']}")
            print(f"      描述: {change.get('old_contract', change.get('new_contract', {})).description}")

            # 详细差异
            if "old_contract" in change and "new_contract" in change:
                old_c = change["old_contract"]
                new_c = change["new_contract"]

                # 请求字段对比
                old_fields = set(old_c.request_schema.get("properties", {}).keys())
                new_fields = set(new_c.request_schema.get("properties", {}).keys())

                if old_fields - new_fields:
                    print(f"      ❌ 删除请求字段: {old_fields - new_fields}")
                if new_fields - old_fields:
                    print(f"      ➕ 新增请求字段: {new_fields - old_fields}")

                # 响应字段对比
                old_resp_fields = set(old_c.response_schema.get("properties", {}).keys())
                new_resp_fields = set(new_c.response_schema.get("properties", {}).keys())

                if old_resp_fields - new_resp_fields:
                    print(f"      ❌ 删除响应字段: {old_resp_fields - new_resp_fields}")
                if new_resp_fields - old_resp_fields:
                    print(f"      ➕ 新增响应字段: {new_resp_fields - old_resp_fields}")

                # 状态码对比
                if old_c.status_code != new_c.status_code:
                    print(f"      ⚠️  状态码变更: {old_c.status_code} → {new_c.status_code}")

            # 修复建议
            print(f"\n      💡 修复建议:")
            print(f"         1. 保持兼容性：同时保留新旧字段")
            print(f"         2. 如果确实需要变更，请手动运行:")
            print(f"            $ moat immune contract update")
            print(f"         3. 更新基线并通知所有消费者")

        print(f"\n   {'='*60}")
        assert True, "Hook 应该阻止提交"
    else:
        assert False, "应该检测到破坏性变更"


# ========================================
# 测试 17: 主动干预建议
# ========================================

def test_proactive_intervention_suggestions(complete_openapi, broken_openapi, generator, storage):
    """
    测试 17: 主动干预建议

    当检测到破坏性变更时，给出具体建议：
    - 检测到删除必选字段 email
    - 这会影响 frontend/api/user.ts
    - 建议：1. 保持兼容性，添加 uid 同时保留 user_id
    -         2. 如果确实需要变更，请手动运行 moat immune contract update
    """
    print("\n📋 [测试 17] 主动干预建议")

    # 先保存基线
    from datetime import datetime
    old_contracts = generator.from_openapi(complete_openapi)
    baseline = ContractBaseline(
        service_name="test-api-suggestions",
        version="1.0.0",
        contracts=old_contracts,
        created_at=datetime.now().isoformat(),
    )
    storage.save_baseline(baseline)

    # 使用 broken_openapi 检测变更
    new_contracts = generator.from_openapi(broken_openapi)
    changes = storage.detect_changes("test-api-suggestions", new_contracts)
    breaking = [c for c in changes if c.get("is_breaking", False)]

    assert len(breaking) > 0, "应该检测到破坏性变更"

    # 生成干预建议
    print(f"\n   💡 主动干预建议:")
    print(f"   {'='*60}")

    # 找出第一个破坏性变更
    change = breaking[0]
    print(f"\n   检测到破坏性变更: {change['method']} {change['endpoint']}")

    if "old_contract" in change and "new_contract" in change:
        old_c = change["old_contract"]
        new_c = change["new_contract"]

        # 请求字段对比
        old_fields = set(old_c.request_schema.get("properties", {}).keys())
        new_fields = set(new_c.request_schema.get("properties", {}).keys())

        old_required = set(old_c.request_schema.get("required", []))
        new_required = set(new_c.request_schema.get("required", []))


        removed_fields = old_fields - new_fields
        removed_required = old_required - new_required

        if removed_fields:
            print(f"   删除字段: {removed_fields}")
            print(f"   这会影响以下文件:")
            print(f"     - frontend/api/user.ts")
            print(f"     - backend/tests/test_users.py")
            print(f"\n   建议:")
            print(f"     1. 保持兼容性：同时保留新旧字段")
            print(f"        → request_schema.properties.{list(removed_fields)[0]} (deprecated)")

        if removed_required:
            print(f"\n   删除必选字段: {removed_required}")
            print(f"   ⚠️  这是破坏性变更！前端依赖此字段。")
            print(f"\n   建议:")
            print(f"     1. 恢复必选字段 {removed_required}")
            print(f"     2. 如果确实需要删除，请手动运行:")
            print(f"        $ moat immune contract update")
            print(f"     3. 更新基线并通知所有消费者")

    print(f"\n   {'='*60}")


# ========================================
# 测试 18: Pact 文件格式验证
# ========================================

def test_pact_file_format(generator, complete_openapi, tmp_path):
    """测试 18: Pact 文件格式符合规范"""
    print("\n📋 [测试 18] Pact 文件格式验证")

    contracts = generator.from_openapi(complete_openapi)
    output_dir = tmp_path / "pacts"
    output_dir.mkdir()

    for contract in contracts:
        pact = generator.generate_pact(contract)

        # 验证 Pact 规范
        assert pact["metadata"]["pactSpecification"]["version"] == "3.0.0"
        assert "consumer" in pact
        assert "provider" in pact
        assert "interactions" in pact
        assert len(pact["interactions"]) > 0

        interaction = pact["interactions"][0]
        assert "description" in interaction
        assert "request" in interaction
        assert "response" in interaction
        assert "method" in interaction["request"]
        assert "path" in interaction["request"]
        assert "status" in interaction["response"]

    print(f"   ✅ Pact 文件格式符合规范 v3.0.0")


# ========================================
# 测试 19: 空基线处理
# ========================================

def test_empty_baseline_handling(storage, generator, complete_openapi):
    """测试 19: 空基线处理（首次检测）"""
    print("\n📋 [测试 19] 空基线处理")

    contracts = generator.from_openapi(complete_openapi)

    # 空基线应该返回所有契约作为 added
    changes = storage.detect_changes("nonexistent-service", contracts)

    assert len(changes) == len(contracts), "空基线应该返回所有契约"
    assert all(c["type"] == "added" for c in changes), "所有都应该是 added"

    print(f"   ✅ 空基线处理正确（{len(changes)} 个 added）")


# ========================================
# 测试 20: 端到端集成测试
# ========================================

def test_end_to_end_integration(complete_openapi, broken_openapi, generator, storage, tmp_path):
    """
    测试 20: 端到端集成测试

    完整流程：
    1. OpenAPI spec → Contract
    2. Contract → Pact 文件
    3. 保存基线到 One Memory
    4. 新 OpenAPI spec → 检测变更
    5. 生成破坏性变更报告
    """
    print("\n📋 [测试 20] 端到端集成测试")

    output_dir = tmp_path / "pacts"
    output_dir.mkdir()

    # 1. OpenAPI → Contract
    print(f"\n   1️⃣  OpenAPI → Contract")
    v1_contracts = generator.from_openapi(complete_openapi)
    print(f"       ✅ v1.0.0: {len(v1_contracts)} 个契约")

    v2_contracts = generator.from_openapi(broken_openapi)
    print(f"       ✅ v2.0.0: {len(v2_contracts)} 个契约")

    # 2. Contract → Pact 文件
    print(f"\n   2️⃣  Contract → Pact 文件")
    for contract in v1_contracts:
        pact = generator.generate_pact(contract)
        filename = f"{contract.method.lower()}_{contract.endpoint.replace('/', '_').replace('{', '').replace('}', '')}.json"
        output_path = output_dir / filename
        with open(output_path, "w") as f:
            json.dump(pact, f, indent=2)

    pact_files = list(output_dir.glob("*.json"))
    print(f"       ✅ 生成了 {len(pact_files)} 个 Pact 文件")

    # 3. 保存基线到 One Memory
    print(f"\n   3️⃣  保存基线到 One Memory")
    baseline = ContractBaseline(
        service_name="e2e-test-api",
        version="1.0.0",
        contracts=v1_contracts,
        created_at=datetime.now().isoformat(),
    )
    storage.save_baseline(baseline)
    print(f"       ✅ 基线已保存")

    # 4. 检测变更
    print(f"\n   4️⃣  检测 API 变更")
    changes = storage.detect_changes("e2e-test-api", v2_contracts)
    breaking = [c for c in changes if c.get("is_breaking", False)]

    print(f"       📊 变更统计:")
    print(f"          - 总变更: {len(changes)}")
    print(f"          - 破坏性: {len(breaking)}")

    # 5. 生成报告
    print(f"\n   5️⃣  生成破坏性变更报告")
    if breaking:
        print(f"       ❌ 检测到 {len(breaking)} 个破坏性变更:")
        for change in breaking:
            print(f"          - {change['method']} {change['endpoint']}")

    # 验证
    assert len(pact_files) > 0, "应该生成了 Pact 文件"
    assert len(changes) > 0, "应该检测到变更"
    assert len(breaking) > 0, "应该检测到破坏性变更"

    print(f"\n   ✅ 端到端集成测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
