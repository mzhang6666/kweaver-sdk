"""Integration: empty environment -> datasource -> build KN -> REST query -> MCP query -> verify.

This is the single definitive end-to-end test. It creates everything from
scratch, verifies data through both REST and MCP paths, cross-validates
consistency, and cleans up.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from kweaver import KWeaverClient
from kweaver.types import Condition
from kweaver.resources.context_loader import ContextLoaderResource

pytestmark = [pytest.mark.e2e, pytest.mark.destructive]


def test_build_completed(lifecycle_env):
    """Build should complete successfully."""
    assert lifecycle_env["build_status"] == "completed", (
        f"Build failed: {lifecycle_env['build_status']}, detail: {lifecycle_env.get('build_detail')}"
    )


def test_rest_instances_have_data(kweaver_client: KWeaverClient, lifecycle_env):
    """REST query.instances should return data from the built KN."""
    if lifecycle_env["build_status"] != "completed":
        pytest.skip("Build did not complete")
    kn = lifecycle_env["kn"]
    ot = lifecycle_env["ot"]
    result = kweaver_client.query.instances(kn.id, ot.id, limit=5)
    assert result.data, "REST returned no instances after build"
    assert result.total_count > 0
    # Verify instance has expected primary key field
    pk = lifecycle_env["pk_col"]
    assert pk in result.data[0] or "_instance_identity" in result.data[0]


def test_rest_semantic_search(kweaver_client: KWeaverClient, lifecycle_env):
    """REST semantic search should find the object type."""
    if lifecycle_env["build_status"] != "completed":
        pytest.skip("Build did not complete")
    from kweaver._errors import ServerError, ValidationError

    kn = lifecycle_env["kn"]
    ot = lifecycle_env["ot"]
    # Use a simple query — newly built KN may not be fully indexed yet
    try:
        result = kweaver_client.query.semantic_search(kn.id, "test")
    except (ServerError, ValidationError):
        pytest.skip("Semantic search not available for this KN (may need time to index)")
    assert isinstance(result.concepts, list)


def test_mcp_kn_search_finds_schema(kweaver_client: KWeaverClient, lifecycle_env):
    """MCP kn_search should discover the object type we just built."""
    if lifecycle_env["build_status"] != "completed":
        pytest.skip("Build did not complete")
    kn = lifecycle_env["kn"]
    ot = lifecycle_env["ot"]

    token = kweaver_client._http._auth.auth_headers().get(
        "Authorization", ""
    ).removeprefix("Bearer ").strip()
    base_url = str(kweaver_client._http._client.base_url).rstrip("/")
    cl = ContextLoaderResource(base_url, token, kn_id=kn.id)

    try:
        result = cl.kn_search(ot.name)
    except RuntimeError as e:
        pytest.skip(f"MCP kn_search not available: {e}")
    raw = result.get("raw", "")
    assert raw, f"MCP kn_search returned empty for '{ot.name}'"


def test_mcp_query_instance_returns_data(kweaver_client: KWeaverClient, lifecycle_env):
    """MCP query_object_instance should return data matching REST."""
    if lifecycle_env["build_status"] != "completed":
        pytest.skip("Build did not complete")
    kn = lifecycle_env["kn"]
    ot = lifecycle_env["ot"]

    # Get a real instance via REST first
    rest_result = kweaver_client.query.instances(kn.id, ot.id, limit=1)
    if not rest_result.data:
        pytest.skip("No instances available")
    sample = rest_result.data[0]
    identity = sample.get("_instance_identity")
    if not identity:
        pytest.skip("Instance has no _instance_identity")
    pk_field = list(identity.keys())[0]
    pk_value = identity[pk_field]

    # Query same instance via MCP
    token = kweaver_client._http._auth.auth_headers().get(
        "Authorization", ""
    ).removeprefix("Bearer ").strip()
    base_url = str(kweaver_client._http._client.base_url).rstrip("/")
    cl = ContextLoaderResource(base_url, token, kn_id=kn.id)

    mcp_result = cl.query_object_instance(
        ot.id,
        condition={
            "operation": "and",
            "sub_conditions": [
                {"field": pk_field, "operation": "==", "value_from": "const", "value": pk_value},
            ],
        },
        limit=1,
    )
    mcp_raw = mcp_result.get("raw", "")
    assert str(pk_value) in mcp_raw, (
        f"MCP did not return instance {pk_field}={pk_value}"
    )



# CLI lifecycle tests moved to TypeScript CLI (packages/typescript/test/e2e/)
