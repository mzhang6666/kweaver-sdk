"""L2: Schema management — object type and relation type CRUD.

Read-only tests use existing data. Write tests are marked destructive.
"""
from __future__ import annotations

import pytest

from kweaver import KWeaverClient

pytestmark = pytest.mark.e2e


def test_object_type_list(kweaver_client: KWeaverClient, kn_with_data):
    """SDK: list object types."""
    kn = kn_with_data["kn"]
    ots = kweaver_client.object_types.list(kn.id)
    assert isinstance(ots, list)
    assert len(ots) > 0


def test_object_type_get(kweaver_client: KWeaverClient, kn_with_data):
    """SDK: get object type by ID."""
    kn = kn_with_data["kn"]
    ot = kn_with_data["ot"]
    result = kweaver_client.object_types.get(kn.id, ot.id)
    assert result.id == ot.id
    assert result.name == ot.name


def test_relation_type_list(kweaver_client: KWeaverClient, kn_with_data):
    """SDK: list relation types."""
    kn = kn_with_data["kn"]
    rts = kweaver_client.relation_types.list(kn.id)
    assert isinstance(rts, list)


def test_relation_type_get_if_exists(kweaver_client: KWeaverClient, kn_with_data):
    """SDK: get relation type by ID (if any exist)."""
    kn = kn_with_data["kn"]
    rts = kweaver_client.relation_types.list(kn.id)
    if not rts:
        pytest.skip("No relation types exist to test get")
    rt = kweaver_client.relation_types.get(kn.id, rts[0].id)
    assert rt.id == rts[0].id
    assert rt.name == rts[0].name
