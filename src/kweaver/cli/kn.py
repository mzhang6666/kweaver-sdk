"""CLI: knowledge network commands."""

from __future__ import annotations

from typing import Any

import click

from kweaver.cli._helpers import error_exit, handle_errors, make_client, pp

# PK/display key heuristics (moved from BuildKnSkill)
_PK_CANDIDATES = {"id", "pk", "key"}
_PK_TYPES = {"integer", "unsigned integer", "string", "varchar", "bigint", "int"}
_DISPLAY_HINTS = {"name", "title", "label", "display_name", "description"}


def _detect_primary_key(table: Any) -> str:
    for col in table.columns:
        if col.name.lower() in _PK_CANDIDATES and col.type.lower() in _PK_TYPES:
            return col.name
    for col in table.columns:
        if col.type.lower() in _PK_TYPES:
            return col.name
    return table.columns[0].name if table.columns else "id"


def _detect_display_key(table: Any, primary_key: str) -> str:
    for col in table.columns:
        if any(hint in col.name.lower() for hint in _DISPLAY_HINTS):
            return col.name
    return primary_key


@click.group("kn")
def kn_group() -> None:
    """Manage knowledge networks."""


@kn_group.command("list")
@click.option("--name", default=None, help="Filter by name.")
def list_kns(name: str | None) -> None:
    """List knowledge networks."""
    client = make_client()
    kns = client.knowledge_networks.list(name=name)
    pp([kn.model_dump() for kn in kns])


@kn_group.command("get")
@click.argument("kn_id")
def get_kn(kn_id: str) -> None:
    """Get knowledge network details."""
    client = make_client()
    kn = client.knowledge_networks.get(kn_id)
    pp(kn.model_dump())


@kn_group.command("export")
@click.argument("kn_id")
def export_kn(kn_id: str) -> None:
    """Export full knowledge network definition."""
    client = make_client()
    data = client.knowledge_networks.export(kn_id)
    pp(data)


@kn_group.command("build")
@click.argument("kn_id")
@click.option("--wait/--no-wait", default=True, help="Wait for build to complete.")
@click.option("--timeout", default=300, type=int, help="Wait timeout in seconds.")
def build_kn(kn_id: str, wait: bool, timeout: int) -> None:
    """Trigger a full build for a knowledge network."""
    client = make_client()
    job = client.knowledge_networks.build(kn_id)
    click.echo(f"Build started for {kn_id}")
    if wait:
        click.echo("Waiting for build to complete ...")
        status = job.wait(timeout=timeout)
        click.echo(f"Build {status.state}")
        if status.state_detail:
            click.echo(f"Detail: {status.state_detail}")
    else:
        click.echo("Build triggered (not waiting).")


@kn_group.command("delete")
@click.argument("kn_id")
@click.confirmation_option(prompt="Are you sure you want to delete this KN?")
def delete_kn(kn_id: str) -> None:
    """Delete a knowledge network."""
    client = make_client()
    client.knowledge_networks.delete(kn_id)
    click.echo(f"Deleted {kn_id}")


@kn_group.command("create")
@click.argument("datasource_id")
@click.option("--name", required=True, help="Knowledge network name.")
@click.option("--tables", default=None, help="Comma-separated table names (default: all).")
@click.option("--build/--no-build", default=True, help="Build after creation.")
@click.option("--timeout", default=300, type=int, help="Build timeout in seconds.")
@handle_errors
def create_kn(
    datasource_id: str, name: str, tables: str | None, build: bool, timeout: int,
) -> None:
    """Create a knowledge network from a datasource."""
    client = make_client()
    all_tables = client.datasources.list_tables(datasource_id)
    table_map = {t.name: t for t in all_tables}
    if tables:
        target_names = [n.strip() for n in tables.split(",")]
        target_tables = [table_map[n] for n in target_names if n in table_map]
    else:
        target_tables = all_tables
    if not target_tables:
        error_exit("没有可用的表")
    view_map: dict[str, str] = {}
    for t in target_tables:
        dv = client.dataviews.create(
            name=t.name, datasource_id=datasource_id, table=t.name,
            columns=t.columns,
        )
        view_map[t.name] = dv.id
    kn = client.knowledge_networks.create(name=name)
    ot_results: list[dict[str, Any]] = []
    for t in target_tables:
        pk = _detect_primary_key(t)
        dk = _detect_display_key(t, pk)
        ot = client.object_types.create(
            kn.id,
            name=t.name,
            dataview_id=view_map[t.name],
            primary_keys=[pk],
            display_key=dk,
        )
        ot_results.append({
            "name": ot.name, "id": ot.id, "field_count": len(t.columns),
        })
    status_str = "skipped"
    if build:
        click.echo("Building ...", err=True)
        job = client.knowledge_networks.build(kn.id)
        status = job.wait(timeout=timeout)
        status_str = status.state
    pp({
        "kn_id": kn.id, "kn_name": kn.name,
        "object_types": ot_results, "status": status_str,
    })
