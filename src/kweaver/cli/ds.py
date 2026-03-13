"""CLI: datasource commands."""
from __future__ import annotations

import click

from kweaver.cli._helpers import handle_errors, make_client, pp


@click.group("ds")
def ds_group() -> None:
    """Manage datasources."""


@ds_group.command("list")
@click.option("--keyword", default=None, help="Filter by keyword.")
@click.option("--type", "ds_type", default=None, help="Filter by database type.")
@handle_errors
def list_ds(keyword: str | None, ds_type: str | None) -> None:
    """List datasources."""
    client = make_client()
    sources = client.datasources.list(keyword=keyword, type=ds_type)
    pp([ds.model_dump() for ds in sources])


@ds_group.command("get")
@click.argument("datasource_id")
@handle_errors
def get_ds(datasource_id: str) -> None:
    """Get datasource details."""
    client = make_client()
    ds = client.datasources.get(datasource_id)
    pp(ds.model_dump())


@ds_group.command("delete")
@click.argument("datasource_id")
@click.confirmation_option(prompt="Are you sure you want to delete this datasource?")
@handle_errors
def delete_ds(datasource_id: str) -> None:
    """Delete a datasource."""
    client = make_client()
    client.datasources.delete(datasource_id)
    click.echo(f"Deleted {datasource_id}")


@ds_group.command("tables")
@click.argument("datasource_id")
@click.option("--keyword", default=None, help="Filter tables by keyword.")
@handle_errors
def tables(datasource_id: str, keyword: str | None) -> None:
    """List tables with columns for a datasource."""
    client = make_client()
    tables = client.datasources.list_tables(datasource_id, keyword=keyword)
    pp([
        {
            "name": t.name,
            "columns": [
                {"name": c.name, "type": c.type, "comment": c.comment}
                for c in t.columns
            ],
        }
        for t in tables
    ])
