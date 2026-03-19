"""Fixtures for integration tests — full lifecycle from empty environment."""
from __future__ import annotations

import time
from typing import Any

import pytest

from kweaver import KWeaverClient


def _cleanup_stale(client: KWeaverClient, prefix: str) -> None:
    """Delete any leftover resources from previous test runs."""
    for kn in client.knowledge_networks.list():
        if kn.name.startswith(prefix):
            try:
                client.knowledge_networks.delete(kn.id)
            except Exception:
                pass
    for ds in client.datasources.list(keyword=prefix):
        try:
            client.datasources.delete(ds.id)
        except Exception:
            pass


@pytest.fixture(scope="module")
def lifecycle_env(
    kweaver_client: KWeaverClient,
    db_config: dict[str, Any],
):
    """Build a complete knowledge network from scratch for integration testing.

    Creates: datasource -> dataview -> KN -> object type -> build -> wait.
    Yields a dict with all created resources.
    Cleans up everything at the end.

    Uses timestamped names to avoid collisions with stale resources.
    """
    client = kweaver_client
    created: dict[str, Any] = {}
    tag = str(int(time.time()))[-6:]  # 6-digit suffix for uniqueness

    # 0. Clean up stale resources from previous runs
    _cleanup_stale(client, "e2e_integ_")

    # 1. Datasource
    ds = client.datasources.create(name=f"e2e_integ_ds_{tag}", **db_config)
    created["ds"] = ds

    # 2. Discover tables
    tables = client.datasources.list_tables(ds.id)
    assert tables, "No tables found in test database"
    table = tables[0]
    created["table"] = table

    # 3. Dataview — use the new datasource so no name collision
    dv = client.dataviews.create(
        name=f"e2e_integ_{table.name}_{tag}",
        datasource_id=ds.id,
        table=table.name,
        columns=table.columns,
    )
    created["dv"] = dv

    # 4. Knowledge network
    kn = client.knowledge_networks.create(name=f"e2e_integ_kn_{tag}")
    created["kn"] = kn

    # 5. Object type — use dataview fields for pk/display to ensure mapping exists
    dv_fields = [f.name for f in dv.fields] if dv.fields else [c.name for c in table.columns]
    pk_col = dv_fields[0]
    display_col = dv_fields[1] if len(dv_fields) > 1 else pk_col
    ot = client.object_types.create(
        kn.id,
        name=f"e2e_integ_{table.name}_{tag}",
        dataview_id=dv.id,
        primary_keys=[pk_col],
        display_key=display_col,
    )
    created["ot"] = ot
    created["pk_col"] = pk_col

    # 6. Build and wait
    try:
        job = client.knowledge_networks.build(kn.id)
        status = job.wait(timeout=300)
        created["build_status"] = status.state
    except Exception as exc:
        created["build_status"] = f"error: {exc}"

    yield created

    # Cleanup (reverse order, best-effort)
    for delete_fn in [
        lambda: client.knowledge_networks.delete(created["kn"].id),
        lambda: client.datasources.delete(created["ds"].id),
    ]:
        try:
            delete_fn()
        except Exception:
            pass
