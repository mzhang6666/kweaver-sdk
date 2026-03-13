# CLI-First Architecture Refactor

**Date:** 2026-03-13
**Status:** Approved

## Problem

Skills (`src/kweaver/skills/`) and CLI (`src/kweaver/cli/`) are two parallel consumers of ADPClient, each duplicating orchestration logic. SKILL.md instructs AI agents to write Python code calling Skill classes, while CLI provides the same capabilities via shell commands. This creates maintenance burden, inconsistent behavior, and a confusing layering.

## Decision

**Approach A — Pure CLI.** Delete all Skill classes. CLI becomes the sole orchestration layer. SKILL.md documents CLI commands only. AI agents invoke `kweaver` shell commands instead of writing Python.

```
Before:
  SKILL.md → Python Skill classes → ADPClient → HTTP API
  CLI      → Click commands       → ADPClient → HTTP API

After:
  SKILL.md → kweaver CLI commands (shell)
                    ↓
  CLI (Click) = sole orchestration layer → ADPClient → HTTP API
```

## New CLI Command Group: `kweaver ds`

The `ds` command group is **entirely new**. It wraps datasource resource methods.

### `kweaver ds connect`

```
kweaver ds connect <type> <host> <port> <database> \
    --account <user> --password <pass> \
    [--schema <schema>] [--name <datasource-name>]
```

Behavior:
1. `datasources.test()` — verify connectivity
2. `datasources.create()` — register datasource (name defaults to database)
3. `datasources.list_tables()` — discover tables
4. Output JSON: `{datasource_id, tables: [{name, columns: [{name, type}]}]}`

### `kweaver ds list`

```
kweaver ds list [--keyword <filter>] [--type <db-type>]
```

### `kweaver ds get <datasource-id>`

### `kweaver ds delete <datasource-id>`

### `kweaver ds tables <datasource-id>`

```
kweaver ds tables <datasource-id> [--keyword <filter>]
```

Lists tables with columns for a datasource.

## New CLI Commands

### `kweaver kn create`

```
kweaver kn create <datasource-id> \
    --name <kn-name> \
    [--tables <t1,t2,...>] \
    [--build/--no-build] \
    [--timeout <seconds>]
```

Behavior:
1. `datasources.list_tables()` — get table metadata
2. For each table: `dataviews.create()` — create view
3. `knowledge_networks.create()` — create KN
4. For each table: `object_types.create()` — create OT (auto-detect PK/display key)
5. If `--build` (default): `knowledge_networks.build()` and poll to completion (default timeout 300s)
6. Output JSON: `{kn_id, kn_name, object_types: [...], status}`

PK/display key detection heuristics move from `BuildKnSkill` into this command.

Note: Relation type creation is not included. Relations require explicit foreign key mapping that cannot be reliably auto-detected. Users create relations via `kweaver call` or the Python SDK directly.

### `kweaver query subgraph`

```
kweaver query subgraph <kn-id> \
    --start-type <ot-name> \
    --start-condition <json> \
    --path <rt1,rt2,...>
```

Behavior:
1. Resolve OT name to ID via `object_types.list(kn_id)` and match by name
2. Call `query.subgraph()`
3. Output result JSON

### `kweaver agent sessions`

```
kweaver agent sessions <agent-id>
```

Lists all conversations for an agent. Enables AI agents to find previous conversation IDs for multi-turn chat.

### `kweaver agent history`

```
kweaver agent history <conversation-id> [--limit <int>]
```

Shows message history for a conversation.

## Modifications to Existing Commands

- **`kweaver action execute`** — add `--action-name` option for name-based lookup via `query.kn_search`

## CLI Error Handling

Add a shared error handler decorator in `cli/_helpers.py` to replace `BaseSkill.run()`'s error wrapping. All commands use it:

```python
def handle_errors(fn):
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

## Deletions

| Path | Reason |
|------|--------|
| `src/kweaver/skills/` (entire directory, 8 files) | Orchestration logic moves to CLI |
| `tests/integration/` (entire directory, 6 test files) | All import Skill classes |
| `tests/e2e/test_full_flow_e2e.py` | Imports Skill classes; rewrite as CLI test |
| `tests/e2e/test_context_loader_e2e.py` | Imports `LoadKnContextSkill`; rewrite as CLI test |

## What Stays

| Path | Reason |
|------|--------|
| `src/kweaver/resources/` | Pure CRUD, CLI depends on it |
| `src/kweaver/_client.py`, `_http.py`, `_auth.py`, `_errors.py` | Infrastructure |
| `src/kweaver/cli/` | Extended with new commands |
| `tests/unit/` | Test resource layer, no Skill imports |
| `tests/e2e/test_datasource_e2e.py` | Tests resource layer directly |
| `tests/e2e/test_build_e2e.py` | Tests resource layer directly |
| `tests/e2e/test_query_e2e.py` | Tests resource layer directly |
| `tests/e2e/test_agents_e2e.py` | Tests resource layer directly |

## SKILL.md Rewrite

Two files merge. `skills/kweaver-core/SKILL.md` is the source of truth. `.claude/skills/kweaver/SKILL.md` becomes a **copy** (not symlink, for Git and cross-platform compatibility) maintained manually — content is identical, frontmatter may differ (e.g., `.claude/` version has `allowed-tools`).

Content structure:
- Prerequisites (install, auth)
- Command quick reference by domain (ds, kn, query, action, agent, call)
- Operation playbooks for AI agents (build from scratch, explore existing, agent chat, execute action)
- No Python `import kweaver` examples

`kweaver kn export` covers the schema discovery use case (`LoadKnContextSkill` overview/schema modes). The export endpoint returns full KN structure including object types, relation types, and properties. No new `kn schema` command needed. The `instances` mode is covered by the existing `kweaver query instances` command.

## Version and Deprecation

This is a pre-1.0 SDK (currently 0.5.0). The `kweaver.skills` module is deleted without deprecation period — bump to **0.6.0**. The `CHANGELOG` or commit message notes: "BREAKING: removed `kweaver.skills` module; use CLI commands instead."

## Testing Strategy

- **Unit tests**: Existing tests in `tests/unit/` continue unchanged (no Skill imports).
- **CLI unit tests**: New commands (`ds connect`, `ds list/get/delete/tables`, `kn create`, `query subgraph`, `agent sessions`, `agent history`) get `click.testing.CliRunner` tests with mocked HTTP in `tests/unit/test_cli.py`.
- **E2E tests**: `test_full_flow_e2e.py` and `test_context_loader_e2e.py` are rewritten to invoke CLI commands via `CliRunner` or subprocess.

## Implementation Order

1. Create `ds` command group with all subcommands (`connect`, `list`, `get`, `delete`, `tables`)
2. Add `kn create` command
3. Add `query subgraph` command
4. Add `agent sessions` and `agent history` commands
5. Add CLI error handling decorator
6. Add CLI unit tests for all new commands
7. Rewrite SKILL.md files
8. Rewrite `test_full_flow_e2e.py` and `test_context_loader_e2e.py`
9. Delete `src/kweaver/skills/` and `tests/integration/`
10. Update `pyproject.toml` version and `__init__.py` exports
