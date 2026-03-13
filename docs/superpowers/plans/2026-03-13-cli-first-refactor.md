# CLI-First Architecture Refactor — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete all Skill classes, make CLI the sole orchestration layer, add new `ds`/`kn create`/`query subgraph`/`agent sessions|history` commands, rewrite SKILL.md and E2E tests, bump to 0.6.0.

**Architecture:** CLI commands in `src/kweaver/cli/` call resource methods from `src/kweaver/resources/` directly. Skills layer is removed entirely. All orchestration logic (PK detection, multi-step create flows) lives in CLI commands. A shared `handle_errors` decorator provides consistent error handling.

**Tech Stack:** Python 3.10+, Click (CLI framework), Pydantic (types), httpx (HTTP), pytest + click.testing.CliRunner (tests)

**Spec:** `docs/superpowers/specs/2026-03-13-cli-first-refactor-design.md`

---

## Chunk 1: `ds` Command Group + `kn create` + Error Handler

### Task 1: CLI Error Handler

**Files:**
- Modify: `src/kweaver/cli/_helpers.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing test for handle_errors decorator**

Add to `tests/unit/test_cli.py`:

```python
# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------


def test_handle_errors_adp_error(runner):
    """handle_errors should catch ADPError and exit with error message."""
    from kweaver.cli._helpers import handle_errors

    @cli.command("_test_error")
    @handle_errors
    def _test_error():
        from kweaver._errors import ADPError
        raise ADPError("something broke", status_code=500)

    result = runner.invoke(cli, ["_test_error"])
    assert result.exit_code != 0
    assert "something broke" in result.output or "something broke" in (result.stderr or "")


def test_handle_errors_auth_error(runner):
    """handle_errors should catch AuthenticationError."""
    from kweaver.cli._helpers import handle_errors

    @cli.command("_test_auth_error")
    @handle_errors
    def _test_auth_error():
        from kweaver._errors import AuthenticationError
        raise AuthenticationError("bad token")

    result = runner.invoke(cli, ["_test_auth_error"])
    assert result.exit_code != 0
    assert "认证失败" in result.output or "bad token" in result.output or "认证失败" in (result.stderr or "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_cli.py::test_handle_errors_adp_error -v`
Expected: FAIL — `handle_errors` not defined

- [ ] **Step 3: Implement handle_errors in _helpers.py**

Add to `src/kweaver/cli/_helpers.py`:

```python
from functools import wraps

from kweaver._errors import ADPError, AuthenticationError, AuthorizationError, NotFoundError


def handle_errors(fn):
    """Decorator: catch SDK errors and exit with a user-friendly message."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AuthenticationError as e:
            error_exit(f"认证失败: {e.message}")
        except AuthorizationError as e:
            error_exit(f"无权限: {e.message}")
        except NotFoundError as e:
            error_exit(f"未找到: {e.message}")
        except ADPError as e:
            error_exit(f"错误: {e.message}")
    return wrapper
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_handle_errors_adp_error tests/unit/test_cli.py::test_handle_errors_auth_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/_helpers.py tests/unit/test_cli.py
git commit -m "feat(cli): add handle_errors decorator for consistent error handling"
```

---

### Task 2: `ds` Command Group — `list`, `get`, `delete`

**Files:**
- Create: `src/kweaver/cli/ds.py`
- Modify: `src/kweaver/cli/main.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing tests for ds list, get, delete**

Add to `tests/unit/test_cli.py`:

```python
# ---------------------------------------------------------------------------
# DS subcommands
# ---------------------------------------------------------------------------


def test_ds_list(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        mock_ds = MagicMock()
        mock_ds.model_dump.return_value = {"id": "ds1", "name": "mydb", "type": "mysql"}
        client.datasources.list.return_value = [mock_ds]
        mock_make.return_value = client

        result = runner.invoke(cli, ["ds", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["id"] == "ds1"


def test_ds_list_with_filters(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        client.datasources.list.return_value = []
        mock_make.return_value = client

        result = runner.invoke(cli, ["ds", "list", "--keyword", "test", "--type", "mysql"])
        assert result.exit_code == 0
        client.datasources.list.assert_called_once_with(keyword="test", type="mysql")


def test_ds_get(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        mock_ds = MagicMock()
        mock_ds.model_dump.return_value = {"id": "ds1", "name": "mydb"}
        client.datasources.get.return_value = mock_ds
        mock_make.return_value = client

        result = runner.invoke(cli, ["ds", "get", "ds1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "ds1"


def test_ds_delete(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        mock_make.return_value = client

        result = runner.invoke(cli, ["ds", "delete", "ds1"], input="y\n")
        assert result.exit_code == 0
        client.datasources.delete.assert_called_once_with("ds1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli.py::test_ds_list -v`
Expected: FAIL — `ds` command not found

- [ ] **Step 3: Create ds.py with list, get, delete commands**

Create `src/kweaver/cli/ds.py`:

```python
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
```

- [ ] **Step 4: Register ds_group in main.py**

Add to `src/kweaver/cli/main.py`:

```python
from kweaver.cli.ds import ds_group
# ...
cli.add_command(ds_group, "ds")
```

- [ ] **Step 5: Update test_cli_help to include "ds"**

In `tests/unit/test_cli.py`, update the `test_cli_help` test:

```python
def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ("auth", "kn", "query", "action", "agent", "call", "ds"):
        assert cmd in result.output
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_ds_list tests/unit/test_cli.py::test_ds_list_with_filters tests/unit/test_cli.py::test_ds_get tests/unit/test_cli.py::test_ds_delete tests/unit/test_cli.py::test_cli_help -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/kweaver/cli/ds.py src/kweaver/cli/main.py tests/unit/test_cli.py
git commit -m "feat(cli): add ds list/get/delete commands"
```

---

### Task 3: `ds tables` Command

**Files:**
- Modify: `src/kweaver/cli/ds.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_cli.py`:

```python
def test_ds_tables(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        mock_table = MagicMock()
        mock_col = MagicMock()
        mock_col.name = "id"
        mock_col.type = "integer"
        mock_col.comment = None
        mock_table.name = "users"
        mock_table.columns = [mock_col]
        client.datasources.list_tables.return_value = [mock_table]
        mock_make.return_value = client

        result = runner.invoke(cli, ["ds", "tables", "ds1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["name"] == "users"
        assert data[0]["columns"][0]["name"] == "id"


def test_ds_tables_with_keyword(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        client.datasources.list_tables.return_value = []
        mock_make.return_value = client

        result = runner.invoke(cli, ["ds", "tables", "ds1", "--keyword", "user"])
        assert result.exit_code == 0
        client.datasources.list_tables.assert_called_once_with("ds1", keyword="user")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_cli.py::test_ds_tables -v`
Expected: FAIL — `tables` command not found

- [ ] **Step 3: Add tables command to ds.py**

Append to `src/kweaver/cli/ds.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_ds_tables tests/unit/test_cli.py::test_ds_tables_with_keyword -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/ds.py tests/unit/test_cli.py
git commit -m "feat(cli): add ds tables command"
```

---

### Task 4: `ds connect` Command

**Files:**
- Modify: `src/kweaver/cli/ds.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_cli.py`:

```python
def test_ds_connect(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        mock_ds = MagicMock()
        mock_ds.id = "ds1"
        client.datasources.test.return_value = True
        client.datasources.create.return_value = mock_ds

        mock_table = MagicMock()
        mock_col = MagicMock()
        mock_col.name = "id"
        mock_col.type = "integer"
        mock_col.comment = None
        mock_table.name = "users"
        mock_table.columns = [mock_col]
        client.datasources.list_tables.return_value = [mock_table]
        mock_make.return_value = client

        result = runner.invoke(cli, [
            "ds", "connect", "mysql", "localhost", "3306", "testdb",
            "--account", "root", "--password", "secret",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["datasource_id"] == "ds1"
        assert data["tables"][0]["name"] == "users"
        client.datasources.test.assert_called_once()
        client.datasources.create.assert_called_once()


def test_ds_connect_with_schema_and_name(runner):
    with patch("kweaver.cli.ds.make_client") as mock_make:
        client = _mock_client()
        mock_ds = MagicMock()
        mock_ds.id = "ds2"
        client.datasources.test.return_value = True
        client.datasources.create.return_value = mock_ds
        client.datasources.list_tables.return_value = []
        mock_make.return_value = client

        result = runner.invoke(cli, [
            "ds", "connect", "postgresql", "db.host", "5432", "mydb",
            "--account", "admin", "--password", "pw",
            "--schema", "public", "--name", "my-datasource",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["datasource_id"] == "ds2"
        # Verify name was passed to create
        call_kwargs = client.datasources.create.call_args
        assert call_kwargs[1].get("name") == "my-datasource" or call_kwargs.kwargs.get("name") == "my-datasource"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli.py::test_ds_connect -v`
Expected: FAIL — `connect` command not found

- [ ] **Step 3: Add connect command to ds.py**

Add to `src/kweaver/cli/ds.py`:

```python
@ds_group.command("connect")
@click.argument("db_type")
@click.argument("host")
@click.argument("port", type=int)
@click.argument("database")
@click.option("--account", required=True, help="Database account.")
@click.option("--password", required=True, help="Database password.")
@click.option("--schema", default=None, help="Database schema.")
@click.option("--name", default=None, help="Datasource name (defaults to database name).")
@handle_errors
def connect(
    db_type: str, host: str, port: int, database: str,
    account: str, password: str, schema: str | None, name: str | None,
) -> None:
    """Connect a database: test, register, and discover tables."""
    client = make_client()

    # 1. Test connectivity
    click.echo("Testing connectivity ...", err=True)
    client.datasources.test(
        type=db_type, host=host, port=port,
        database=database, account=account, password=password, schema=schema,
    )

    # 2. Register datasource
    ds_name = name or database
    ds = client.datasources.create(
        name=ds_name, type=db_type, host=host, port=port,
        database=database, account=account, password=password, schema=schema,
    )

    # 3. Discover tables
    found_tables = client.datasources.list_tables(ds.id)

    pp({
        "datasource_id": ds.id,
        "tables": [
            {
                "name": t.name,
                "columns": [
                    {"name": c.name, "type": c.type, "comment": c.comment}
                    for c in t.columns
                ],
            }
            for t in found_tables
        ],
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_ds_connect tests/unit/test_cli.py::test_ds_connect_with_schema_and_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/ds.py tests/unit/test_cli.py
git commit -m "feat(cli): add ds connect command"
```

---

### Task 5: `kn create` Command

This is the most complex new command — it replicates `BuildKnSkill` orchestration including PK/display key heuristics.

**Files:**
- Modify: `src/kweaver/cli/kn.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_cli.py`:

```python
def test_kn_create(runner):
    with patch("kweaver.cli.kn.make_client") as mock_make:
        client = _mock_client()

        # Mock table with columns
        mock_col_id = MagicMock()
        mock_col_id.name = "id"
        mock_col_id.type = "integer"
        mock_col_name = MagicMock()
        mock_col_name.name = "name"
        mock_col_name.type = "varchar"
        mock_table = MagicMock()
        mock_table.name = "users"
        mock_table.columns = [mock_col_id, mock_col_name]
        client.datasources.list_tables.return_value = [mock_table]

        # Mock dataview
        mock_dv = MagicMock()
        mock_dv.id = "dv1"
        client.dataviews.create.return_value = mock_dv

        # Mock KN
        mock_kn = MagicMock()
        mock_kn.id = "kn1"
        mock_kn.name = "test_kn"
        client.knowledge_networks.create.return_value = mock_kn

        # Mock OT
        mock_ot = MagicMock()
        mock_ot.id = "ot1"
        mock_ot.name = "users"
        client.object_types.create.return_value = mock_ot

        # Mock build
        mock_job = MagicMock()
        mock_status = MagicMock()
        mock_status.state = "completed"
        mock_job.wait.return_value = mock_status
        client.knowledge_networks.build.return_value = mock_job

        mock_make.return_value = client

        result = runner.invoke(cli, [
            "kn", "create", "ds1", "--name", "test_kn",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["kn_id"] == "kn1"
        assert data["status"] == "completed"
        assert len(data["object_types"]) == 1
        assert data["object_types"][0]["name"] == "users"

        # Verify PK detection: "id" column should be picked as PK
        ot_call = client.object_types.create.call_args
        assert ot_call.kwargs["primary_keys"] == ["id"]
        assert ot_call.kwargs["display_key"] == "name"


def test_kn_create_no_build(runner):
    with patch("kweaver.cli.kn.make_client") as mock_make:
        client = _mock_client()

        mock_col = MagicMock()
        mock_col.name = "key"
        mock_col.type = "varchar"
        mock_table = MagicMock()
        mock_table.name = "items"
        mock_table.columns = [mock_col]
        client.datasources.list_tables.return_value = [mock_table]

        mock_dv = MagicMock()
        mock_dv.id = "dv1"
        client.dataviews.create.return_value = mock_dv

        mock_kn = MagicMock()
        mock_kn.id = "kn2"
        mock_kn.name = "no_build_kn"
        client.knowledge_networks.create.return_value = mock_kn

        mock_ot = MagicMock()
        mock_ot.id = "ot1"
        mock_ot.name = "items"
        client.object_types.create.return_value = mock_ot

        mock_make.return_value = client

        result = runner.invoke(cli, [
            "kn", "create", "ds1", "--name", "no_build_kn", "--no-build",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "skipped"
        client.knowledge_networks.build.assert_not_called()


def test_kn_create_with_tables_filter(runner):
    with patch("kweaver.cli.kn.make_client") as mock_make:
        client = _mock_client()

        mock_col = MagicMock()
        mock_col.name = "id"
        mock_col.type = "integer"
        mock_t1 = MagicMock()
        mock_t1.name = "users"
        mock_t1.columns = [mock_col]
        mock_t2 = MagicMock()
        mock_t2.name = "orders"
        mock_t2.columns = [mock_col]
        client.datasources.list_tables.return_value = [mock_t1, mock_t2]

        mock_dv = MagicMock()
        mock_dv.id = "dv1"
        client.dataviews.create.return_value = mock_dv

        mock_kn = MagicMock()
        mock_kn.id = "kn3"
        mock_kn.name = "filtered"
        client.knowledge_networks.create.return_value = mock_kn

        mock_ot = MagicMock()
        mock_ot.id = "ot1"
        mock_ot.name = "users"
        client.object_types.create.return_value = mock_ot

        mock_job = MagicMock()
        mock_status = MagicMock()
        mock_status.state = "completed"
        mock_job.wait.return_value = mock_status
        client.knowledge_networks.build.return_value = mock_job

        mock_make.return_value = client

        result = runner.invoke(cli, [
            "kn", "create", "ds1", "--name", "filtered", "--tables", "users",
        ])
        assert result.exit_code == 0
        # Only one OT created (for "users", not "orders")
        assert client.object_types.create.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli.py::test_kn_create -v`
Expected: FAIL — `create` command not found on `kn` group

- [ ] **Step 3: Add kn create command with PK/display key heuristics**

Add to `src/kweaver/cli/kn.py`:

```python
import json
from typing import Any

# PK/display key heuristics (moved from BuildKnSkill)
_PK_CANDIDATES = {"id", "pk", "key"}
_PK_TYPES = {"integer", "unsigned integer", "string", "varchar", "bigint", "int"}
_DISPLAY_HINTS = {"name", "title", "label", "display_name", "description"}


def _detect_primary_key(table: Any) -> str:
    """Heuristic: find the best primary key column."""
    for col in table.columns:
        if col.name.lower() in _PK_CANDIDATES and col.type.lower() in _PK_TYPES:
            return col.name
    for col in table.columns:
        if col.type.lower() in _PK_TYPES:
            return col.name
    return table.columns[0].name if table.columns else "id"


def _detect_display_key(table: Any, primary_key: str) -> str:
    """Heuristic: find the best display key column."""
    for col in table.columns:
        if any(hint in col.name.lower() for hint in _DISPLAY_HINTS):
            return col.name
    return primary_key


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

    # 1. Get table metadata
    all_tables = client.datasources.list_tables(datasource_id)
    table_map = {t.name: t for t in all_tables}

    if tables:
        target_names = [n.strip() for n in tables.split(",")]
        target_tables = [table_map[n] for n in target_names if n in table_map]
    else:
        target_tables = all_tables

    if not target_tables:
        from kweaver.cli._helpers import error_exit
        error_exit("没有可用的表")

    # 2. Create data views
    view_map: dict[str, str] = {}
    for t in target_tables:
        dv = client.dataviews.create(
            name=t.name, datasource_id=datasource_id, table=t.name,
            columns=t.columns,
        )
        view_map[t.name] = dv.id

    # 3. Create knowledge network
    kn = client.knowledge_networks.create(name=name)

    # 4. Create object types
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
            "name": ot.name,
            "id": ot.id,
            "field_count": len(t.columns),
        })

    # 5. Build
    status_str = "skipped"
    if build:
        click.echo("Building ...", err=True)
        job = client.knowledge_networks.build(kn.id)
        status = job.wait(timeout=timeout)
        status_str = status.state

    pp({
        "kn_id": kn.id,
        "kn_name": kn.name,
        "object_types": ot_results,
        "status": status_str,
    })
```

Also add the missing import at the top of kn.py:

```python
from kweaver.cli._helpers import error_exit, handle_errors, make_client, pp
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_kn_create tests/unit/test_cli.py::test_kn_create_no_build tests/unit/test_cli.py::test_kn_create_with_tables_filter -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/kn.py tests/unit/test_cli.py
git commit -m "feat(cli): add kn create command with PK/display key heuristics"
```

---

## Chunk 2: `query subgraph` + `agent sessions|history`

### Task 6: `query subgraph` Command

**Files:**
- Modify: `src/kweaver/cli/query.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_cli.py`:

```python
def test_query_subgraph(runner):
    with patch("kweaver.cli.query.make_client") as mock_make:
        client = _mock_client()

        # Mock OT list for name→ID resolution
        mock_ot = MagicMock()
        mock_ot.id = "ot1"
        mock_ot.name = "users"
        client.object_types.list.return_value = [mock_ot]

        # Mock RT list for name→ID resolution
        mock_rt1 = MagicMock()
        mock_rt1.id = "rt1"
        mock_rt1.name = "has_order"
        mock_rt1.source_ot_id = "ot1"
        mock_rt1.target_ot_id = "ot2"
        mock_rt2 = MagicMock()
        mock_rt2.id = "rt2"
        mock_rt2.name = "belongs_to"
        mock_rt2.source_ot_id = "ot2"
        mock_rt2.target_ot_id = "ot3"
        client.relation_types.list.return_value = [mock_rt1, mock_rt2]

        # Mock subgraph result
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"entries": [{"id": "n1"}]}
        client.query.subgraph.return_value = mock_result
        mock_make.return_value = client

        result = runner.invoke(cli, [
            "query", "subgraph", "kn1",
            "--start-type", "users",
            "--start-condition", '{"field":"id","operation":"eq","value":"1"}',
            "--path", "has_order,belongs_to",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "entries" in data

        # Verify subgraph was called with resolved IDs
        call_args = client.query.subgraph.call_args
        paths = call_args[0][1]  # second positional arg
        assert paths[0].object_types[0].id == "ot1"
        assert paths[0].relation_types[0].id == "rt1"


def test_query_subgraph_rt_not_found(runner):
    with patch("kweaver.cli.query.make_client") as mock_make:
        client = _mock_client()

        mock_ot = MagicMock()
        mock_ot.id = "ot1"
        mock_ot.name = "users"
        client.object_types.list.return_value = [mock_ot]
        client.relation_types.list.return_value = []  # No RTs
        mock_make.return_value = client

        result = runner.invoke(cli, [
            "query", "subgraph", "kn1",
            "--start-type", "users",
            "--start-condition", '{"field":"id","operation":"eq","value":"1"}',
            "--path", "nonexistent_rt",
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "not found" in (result.stderr or "").lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_cli.py::test_query_subgraph -v`
Expected: FAIL — `subgraph` command not found

- [ ] **Step 3: Add subgraph command to query.py**

Add to `src/kweaver/cli/query.py`:

```python
from kweaver.cli._helpers import error_exit, handle_errors, make_client, pp
from kweaver.types import Condition, PathNode, PathEdge, SubgraphPath


@query_group.command("subgraph")
@click.argument("kn_id")
@click.option("--start-type", required=True, help="Starting object type name.")
@click.option("--start-condition", required=True, help="JSON condition for start nodes.")
@click.option("--path", required=True, help="Comma-separated relation type names.")
@handle_errors
def subgraph(kn_id: str, start_type: str, start_condition: str, path: str) -> None:
    """Query a subgraph by path traversal."""
    client = make_client()

    # Resolve OT name to ID
    ots = client.object_types.list(kn_id)
    ot_map = {ot.name: ot.id for ot in ots}
    start_ot_id = ot_map.get(start_type)
    if not start_ot_id:
        error_exit(f"Object type '{start_type}' not found. Available: {list(ot_map.keys())}")

    cond = Condition(**json.loads(start_condition))
    rt_names = [n.strip() for n in path.split(",")]

    # Resolve RT names to IDs
    rts = client.relation_types.list(kn_id)
    rt_map = {rt.name: rt for rt in rts}

    # Build path: start node + edges + intermediate nodes
    nodes = [PathNode(id=start_ot_id, condition=cond)]
    edges = []
    for rt_name in rt_names:
        rt = rt_map.get(rt_name)
        if not rt:
            error_exit(f"Relation type '{rt_name}' not found. Available: {list(rt_map.keys())}")
        edges.append(PathEdge(id=rt.id, source=rt.source_ot_id, target=rt.target_ot_id))
        # Add target node
        if rt.target_ot_id not in {n.id for n in nodes}:
            nodes.append(PathNode(id=rt.target_ot_id))

    paths = [SubgraphPath(object_types=nodes, relation_types=edges)]
    result = client.query.subgraph(kn_id, paths)
    pp(result.model_dump())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_cli.py::test_query_subgraph -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/query.py tests/unit/test_cli.py
git commit -m "feat(cli): add query subgraph command with name-based resolution"
```

---

### Task 7: `agent sessions` and `agent history` Commands

**Files:**
- Modify: `src/kweaver/cli/agent.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_cli.py`:

```python
def test_agent_sessions(runner):
    with patch("kweaver.cli.agent.make_client") as mock_make:
        client = _mock_client()
        mock_conv = MagicMock()
        mock_conv.model_dump.return_value = {
            "id": "conv1", "agent_id": "a1", "title": "Test session",
        }
        client.conversations.list.return_value = [mock_conv]
        mock_make.return_value = client

        result = runner.invoke(cli, ["agent", "sessions", "a1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["id"] == "conv1"
        client.conversations.list.assert_called_once_with(agent_id="a1")


def test_agent_history(runner):
    with patch("kweaver.cli.agent.make_client") as mock_make:
        client = _mock_client()
        mock_msg = MagicMock()
        mock_msg.model_dump.return_value = {
            "id": "msg1", "role": "user", "content": "hello",
        }
        client.conversations.list_messages.return_value = [mock_msg]
        mock_make.return_value = client

        result = runner.invoke(cli, ["agent", "history", "conv1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["id"] == "msg1"
        client.conversations.list_messages.assert_called_once_with("conv1", limit=None)


def test_agent_history_with_limit(runner):
    with patch("kweaver.cli.agent.make_client") as mock_make:
        client = _mock_client()
        client.conversations.list_messages.return_value = []
        mock_make.return_value = client

        result = runner.invoke(cli, ["agent", "history", "conv1", "--limit", "10"])
        assert result.exit_code == 0
        client.conversations.list_messages.assert_called_once_with("conv1", limit=10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli.py::test_agent_sessions -v`
Expected: FAIL — `sessions` command not found

- [ ] **Step 3: Add sessions and history commands to agent.py**

> **Note:** `conversations.list()` and `conversations.list_messages()` are currently stubs in
> `src/kweaver/resources/conversations.py` that always return empty lists (the backend does not
> expose these endpoints in all deployments). The CLI commands are added now for completeness;
> they will return `[]` until the resource methods are implemented with actual HTTP calls.
> The unit tests use mocks, so they verify the CLI wiring is correct regardless.

Add to `src/kweaver/cli/agent.py`:

```python
from kweaver.cli._helpers import handle_errors, make_client, pp


@agent_group.command("sessions")
@click.argument("agent_id")
@handle_errors
def sessions(agent_id: str) -> None:
    """List all conversations for an agent."""
    client = make_client()
    convs = client.conversations.list(agent_id=agent_id)
    pp([c.model_dump() for c in convs])


@agent_group.command("history")
@click.argument("conversation_id")
@click.option("--limit", default=None, type=int, help="Max messages to return.")
@handle_errors
def history(conversation_id: str, limit: int | None) -> None:
    """Show message history for a conversation."""
    client = make_client()
    messages = client.conversations.list_messages(conversation_id, limit=limit)
    pp([m.model_dump() for m in messages])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_agent_sessions tests/unit/test_cli.py::test_agent_history tests/unit/test_cli.py::test_agent_history_with_limit -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/agent.py tests/unit/test_cli.py
git commit -m "feat(cli): add agent sessions and history commands"
```

---

### Task 8: `action execute --action-name` Option

Per spec: add `--action-name` option to `kweaver action execute` for name-based action type lookup via `query.kn_search`.

**Files:**
- Modify: `src/kweaver/cli/action.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_cli.py`:

```python
def test_action_execute_by_name(runner):
    with patch("kweaver.cli.action.make_client") as mock_make:
        client = _mock_client()

        # Mock kn_search to resolve action name → ID
        mock_search = MagicMock()
        mock_search.action_types = [{"id": "at_resolved", "name": "sync_data"}]
        client.query.kn_search.return_value = mock_search

        mock_exec = MagicMock()
        mock_exec.execution_id = "exec1"
        mock_exec_done = MagicMock()
        mock_exec_done.status = "completed"
        mock_exec_done.result = {"ok": True}
        mock_exec.wait.return_value = mock_exec_done
        client.action_types.execute.return_value = mock_exec
        mock_make.return_value = client

        result = runner.invoke(cli, [
            "action", "execute", "kn1", "--action-name", "sync_data",
        ])
        assert result.exit_code == 0
        assert "completed" in result.output
        # Verify kn_search was called to resolve the name
        client.query.kn_search.assert_called_once()
        # Verify execute was called with the resolved ID
        client.action_types.execute.assert_called_once()
        call_args = client.action_types.execute.call_args
        assert call_args[0][1] == "at_resolved"  # action_type_id


def test_action_execute_by_name_not_found(runner):
    with patch("kweaver.cli.action.make_client") as mock_make:
        client = _mock_client()
        mock_search = MagicMock()
        mock_search.action_types = []
        client.query.kn_search.return_value = mock_search
        mock_make.return_value = client

        result = runner.invoke(cli, [
            "action", "execute", "kn1", "--action-name", "nonexistent",
        ])
        assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_cli.py::test_action_execute_by_name -v`
Expected: FAIL

- [ ] **Step 3: Modify action execute command**

In `src/kweaver/cli/action.py`, modify the `execute_action` command:

```python
from kweaver.cli._helpers import error_exit, handle_errors, make_client, pp


@action_group.command("execute")
@click.argument("kn_id")
@click.argument("action_type_id", required=False, default=None)
@click.option("--action-name", default=None, help="Resolve action type by name (via kn_search).")
@click.option("--params", "params_json", default=None, help="JSON execution parameters.")
@click.option("--wait/--no-wait", default=True)
@click.option("--timeout", default=300, type=int)
@handle_errors
def execute_action(kn_id: str, action_type_id: str | None, action_name: str | None,
                   params_json: str | None, wait: bool, timeout: int) -> None:
    """Execute an action type."""
    client = make_client()

    if not action_type_id and not action_name:
        error_exit("Either ACTION_TYPE_ID or --action-name must be provided")

    if action_name and not action_type_id:
        # Resolve name → ID via kn_search
        search_result = client.query.kn_search(kn_id, action_name)
        actions = search_result.action_types or []
        if not actions:
            error_exit(f"Action type '{action_name}' not found")
        action_type_id = actions[0]["id"]

    params = json.loads(params_json) if params_json else None
    execution = client.action_types.execute(kn_id, action_type_id, params=params)
    click.echo(f"Execution started: {execution.execution_id}")

    if wait:
        click.echo("Waiting for completion ...")
        result = execution.wait(timeout=timeout)
        click.echo(f"Status: {result.status}")
        if result.result:
            pp(result.result)
    else:
        click.echo(f"Status: {execution.status}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_cli.py::test_action_execute_by_name tests/unit/test_cli.py::test_action_execute_by_name_not_found tests/unit/test_cli.py::test_action_execute_wait -v`
Expected: PASS (both new and existing tests)

- [ ] **Step 5: Commit**

```bash
git add src/kweaver/cli/action.py tests/unit/test_cli.py
git commit -m "feat(cli): add --action-name option for name-based action execution"
```

---

### Task 9: Add `handle_errors` to All Existing CLI Commands

Apply the `handle_errors` decorator to all pre-existing CLI commands that call `make_client()` for consistent error handling.

**Files:**
- Modify: `src/kweaver/cli/kn.py`, `src/kweaver/cli/query.py`, `src/kweaver/cli/action.py`, `src/kweaver/cli/agent.py`, `src/kweaver/cli/call.py`

- [ ] **Step 1: Add @handle_errors to all existing commands**

For each file, import `handle_errors` from `_helpers` and add the decorator after `@click.*` decorators but before the function definition. Apply to these commands:

- `kn.py`: `list_kns`, `get_kn`, `export_kn`, `build_kn`, `delete_kn`
- `query.py`: `search`, `instances`, `kn_search`
- `action.py`: `query_action`, `execute_action`, `list_logs`, `get_log`
- `agent.py`: `list_agents`, `chat`
- `call.py`: the `call` command

- [ ] **Step 2: Run full test suite to verify no regressions**

Run: `python -m pytest tests/unit/test_cli.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/kweaver/cli/kn.py src/kweaver/cli/query.py src/kweaver/cli/action.py src/kweaver/cli/agent.py src/kweaver/cli/call.py
git commit -m "refactor(cli): apply handle_errors decorator to all existing commands"
```

---

## Chunk 3: SKILL.md Rewrite + E2E Test Rewrite

### Task 10: Rewrite SKILL.md Files

**Files:**
- Modify: `skills/kweaver-core/SKILL.md`
- Modify: `.claude/skills/kweaver/SKILL.md`

The two files should have identical content (except frontmatter). Content structure per spec:
- Prerequisites (install, auth)
- Command quick reference by domain (ds, kn, query, action, agent, call)
- Operation playbooks for AI agents (build from scratch, explore existing, agent chat, execute action)
- No Python `import kweaver` examples

- [ ] **Step 1: Read existing SKILL.md files**

Read both `skills/kweaver-core/SKILL.md` and `.claude/skills/kweaver/SKILL.md` to understand current frontmatter.

- [ ] **Step 2: Rewrite `skills/kweaver-core/SKILL.md`**

Replace content with CLI-only documentation. Keep existing frontmatter. Remove all Python Skill class references. Document all CLI commands including new `ds`, `kn create`, `query subgraph`, `agent sessions`, `agent history`. Include playbooks using only shell commands.

Key sections:
```markdown
## Prerequisites
pip install kweaver-sdk[cli]
kweaver auth login <platform-url>

## Command Reference
### Datasources (`kweaver ds`)
### Knowledge Networks (`kweaver kn`)
### Querying (`kweaver query`)
### Actions (`kweaver action`)
### Agents (`kweaver agent`)
### Raw API (`kweaver call`)

## Playbooks
### Build a Knowledge Network from Scratch
### Explore an Existing Knowledge Network
### Chat with a Decision Agent
### Execute an Action
```

- [ ] **Step 3: Copy content to `.claude/skills/kweaver/SKILL.md`**

Copy the body content from `skills/kweaver-core/SKILL.md` to `.claude/skills/kweaver/SKILL.md`, keeping the `.claude/` version's frontmatter (especially `allowed-tools`).

- [ ] **Step 4: Commit**

```bash
git add skills/kweaver-core/SKILL.md .claude/skills/kweaver/SKILL.md
git commit -m "docs: rewrite SKILL.md for CLI-first architecture"
```

---

### Task 11: Rewrite `test_full_flow_e2e.py`

Replace Skill class imports with CLI CliRunner invocations.

**Files:**
- Modify: `tests/e2e/test_full_flow_e2e.py`

- [ ] **Step 1: Rewrite test_full_flow_e2e.py using CLI commands**

```python
"""E2E: full flow — connect database -> build knowledge network -> query.

Exercises the complete lifecycle through CLI commands.
Destructive: creates and deletes datasources, knowledge networks, etc.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from kweaver import ADPClient
from kweaver.cli.main import cli

pytestmark = [pytest.mark.e2e, pytest.mark.destructive]


def _invoke(runner: CliRunner, args: list[str]) -> dict[str, Any]:
    """Invoke CLI and parse JSON output."""
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    # Find the last JSON object in output (skip stderr progress messages)
    for line in reversed(result.output.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    return json.loads(result.output)


def test_cli_full_lifecycle(adp_client: ADPClient, db_config: dict[str, Any], cli_runner):
    """End-to-end: ds connect -> kn create -> query search."""
    runner = cli_runner

    kn_name = "e2e_full_flow_kn"
    # Clean up stale KN from previous runs
    for kn in adp_client.knowledge_networks.list(name=kn_name):
        if kn.name == kn_name:
            try:
                adp_client.knowledge_networks.delete(kn.id)
            except Exception:
                pass

    # Step 1: ds connect
    connect_result = runner.invoke(cli, [
        "ds", "connect", db_config["type"],
        db_config["host"], str(db_config["port"]), db_config["database"],
        "--account", db_config["account"],
        "--password", db_config["password"],
    ] + (["--schema", db_config["schema"]] if db_config.get("schema") else []))

    assert connect_result.exit_code == 0, f"ds connect failed: {connect_result.output}"
    connect_data = json.loads(connect_result.output.strip().split("\n")[-1])
    ds_id = connect_data["datasource_id"]
    assert len(connect_data["tables"]) > 0

    first_table = connect_data["tables"][0]["name"]
    kn_id = None

    try:
        # Step 2: kn create
        create_result = runner.invoke(cli, [
            "kn", "create", ds_id,
            "--name", kn_name,
            "--tables", first_table,
        ])
        assert create_result.exit_code == 0, f"kn create failed: {create_result.output}"
        create_data = json.loads(create_result.output.strip().split("\n")[-1])
        kn_id = create_data["kn_id"]
        assert create_data["status"] in ("completed", "failed")
        assert len(create_data["object_types"]) == 1

        # Step 3: kn export (covers LoadKnContextSkill schema mode)
        export_result = runner.invoke(cli, ["kn", "export", kn_id])
        assert export_result.exit_code == 0

        # Step 4: query search (if build succeeded)
        if create_data["status"] == "completed":
            search_result = runner.invoke(cli, [
                "query", "search", kn_id, first_table,
            ])
            assert search_result.exit_code == 0

    finally:
        if kn_id:
            try:
                adp_client.knowledge_networks.delete(kn_id)
            except Exception:
                pass
        try:
            adp_client.datasources.delete(ds_id)
        except Exception:
            pass
```

**Auth setup note:** The E2E conftest's `e2e_env` fixture provides `base_url` and `token` keys. The recommended approach is to add a `cli_runner` fixture to `tests/e2e/conftest.py` that creates a `CliRunner` with these as env vars:

```python
@pytest.fixture
def cli_runner(e2e_env):
    env = {"ADP_BASE_URL": e2e_env["base_url"]}
    if e2e_env.get("token"):
        env["ADP_TOKEN"] = e2e_env["token"]
    if e2e_env.get("business_domain"):
        env["ADP_BUSINESS_DOMAIN"] = e2e_env["business_domain"]
    return CliRunner(env=env)
```

Use `cli_runner` for CLI commands and `adp_client` for setup/teardown (KN cleanup etc). Do NOT access private attributes like `_http._auth_header`.

- [ ] **Step 2: Run test to verify it works**

Run: `python -m pytest tests/e2e/test_full_flow_e2e.py -v -m e2e --run-destructive`
Expected: PASS (against a live ADP instance with database configured)

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_full_flow_e2e.py
git commit -m "test(e2e): rewrite full flow test using CLI commands instead of Skills"
```

---

### Task 12: Rewrite `test_context_loader_e2e.py`

Replace `LoadKnContextSkill` with equivalent CLI commands (`kn list`, `kn export`, `query instances`).

**Files:**
- Modify: `tests/e2e/test_context_loader_e2e.py`

- [ ] **Step 1: Rewrite test_context_loader_e2e.py using CLI commands**

```python
"""E2E: context loader — schema discovery and instance browsing via CLI.

Requires at least one existing knowledge network with built data.
These tests are read-only (non-destructive) by default.
"""

from __future__ import annotations

import json

import pytest

from kweaver import ADPClient
from kweaver.cli.main import cli

pytestmark = pytest.mark.e2e

# Note: cli_runner fixture is defined in tests/e2e/conftest.py (added in Task 11)


def test_kn_list_discovers_knowledge_networks(cli_runner):
    """kn list should return knowledge networks."""
    result = cli_runner.invoke(cli, ["kn", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for kn in data:
        assert "id" in kn
        assert "name" in kn


def test_kn_export_returns_structure(adp_client: ADPClient, cli_runner):
    """kn export should return object types and relation types."""
    kns = adp_client.knowledge_networks.list()
    if not kns:
        pytest.skip("No knowledge networks available")

    result = cli_runner.invoke(cli, ["kn", "export", kns[0].id])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Export returns the full KN definition
    assert isinstance(data, dict)


def test_query_instances_returns_data(adp_client: ADPClient, cli_runner):
    """query instances should return data rows."""
    kns = adp_client.knowledge_networks.list()
    if not kns:
        pytest.skip("No knowledge networks available")

    kn = kns[0]
    ots = adp_client.object_types.list(kn.id)
    if not ots:
        pytest.skip("No object types available")

    ot = ots[0]
    result = cli_runner.invoke(cli, [
        "query", "instances", kn.id, ot.id, "--limit", "5",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
```

The implementer should expand these tests to cover the same scenarios as the original file (schema with samples, relations, name resolution, etc.) using the equivalent CLI commands. The tests above cover the core paths; additional tests can be added for edge cases.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/e2e/test_context_loader_e2e.py -v -m e2e`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_context_loader_e2e.py
git commit -m "test(e2e): rewrite context loader tests using CLI commands"
```

---

## Chunk 4: Deletions + Version Bump

### Task 13: Delete Skills and Integration Tests

**Files:**
- Delete: `src/kweaver/skills/` (entire directory)
- Delete: `tests/integration/` (entire directory)

- [ ] **Step 1: Verify no remaining imports of kweaver.skills**

Run: `grep -r "from kweaver.skills" src/ tests/ --include="*.py" | grep -v "^tests/integration/" | grep -v "^src/kweaver/skills/"`

Expected: No output (no imports remain outside of the directories being deleted). If any remain in test files, they should have been rewritten in Tasks 10-11.

- [ ] **Step 2: Delete the skills directory**

```bash
rm -rf src/kweaver/skills/
```

- [ ] **Step 3: Delete the integration tests directory**

```bash
rm -rf tests/integration/
```

- [ ] **Step 4: Run unit tests to verify no breakage**

Run: `python -m pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor!: remove kweaver.skills module and integration tests

BREAKING: removed kweaver.skills module; use CLI commands instead.
Skills orchestration logic has been moved to CLI commands (ds, kn create, etc.)."
```

---

### Task 14: Update Version and Exports

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/kweaver/__init__.py` (verify — skills were not exported here, but check)

- [ ] **Step 1: Bump version to 0.6.0 in pyproject.toml**

In `pyproject.toml`, change:
```toml
version = "0.5.0"
```
to:
```toml
version = "0.6.0"
```

Also update the description to remove "skills" reference:
```toml
description = "ADP Python SDK — CLI and client library for knowledge network construction and querying"
```

Also update `addopts` in pytest config to remove integration test handling (they no longer exist):
```toml
addopts = "--ignore=tests/e2e"
```
(This is the same — integration tests were run by default before, but now the directory doesn't exist, so no change needed. Keep as-is.)

- [ ] **Step 2: Update version test**

In `tests/unit/test_cli.py`, update:
```python
def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.6.0" in result.output
```

- [ ] **Step 3: Update __init__.py docstring and verify no skill exports**

In `src/kweaver/__init__.py`, update the docstring from:
```python
"""KWeaver SDK — Agent-oriented skills for ADP knowledge networks."""
```
to:
```python
"""KWeaver SDK — CLI and client library for ADP knowledge networks."""
```

Verify no skill exports exist (confirmed: only ADPClient, auth, and error classes are exported).

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/unit/test_cli.py
git commit -m "chore: bump version to 0.6.0, update description"
```

---

### Task 15: Final Verification

- [ ] **Step 1: Run full unit test suite**

Run: `python -m pytest tests/unit/ -v --tb=short`
Expected: All PASS

- [ ] **Step 2: Verify CLI help includes new commands**

Run: `python -m kweaver.cli.main --help`
Expected: Shows `ds` in command list

Run: `python -m kweaver.cli.main ds --help`
Expected: Shows `connect`, `list`, `get`, `delete`, `tables`

Run: `python -m kweaver.cli.main kn --help`
Expected: Shows `create` alongside existing commands

Run: `python -m kweaver.cli.main query --help`
Expected: Shows `subgraph` alongside existing commands

Run: `python -m kweaver.cli.main agent --help`
Expected: Shows `sessions`, `history` alongside existing commands

- [ ] **Step 3: Verify no dangling imports**

Run: `python -c "import kweaver; print(kweaver.__all__)"`
Expected: No import errors, prints the __all__ list without skill references

Run: `python -c "from kweaver.cli.main import cli"`
Expected: No import errors

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```
