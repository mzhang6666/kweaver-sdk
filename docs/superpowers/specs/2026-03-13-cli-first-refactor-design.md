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

## New CLI Commands

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

### `kweaver kn create`

```
kweaver kn create <datasource-id> \
    --name <kn-name> \
    [--tables <t1,t2,...>] \
    [--build/--no-build]
```

Behavior:
1. `datasources.list_tables()` — get table metadata
2. For each table: `dataviews.create()` — create view
3. `knowledge_networks.create()` — create KN
4. For each table: `object_types.create()` — create OT (auto-detect PK/display key)
5. If `--build` (default): `knowledge_networks.build()` and poll to completion
6. Output JSON: `{kn_id, kn_name, object_types: [...], status}`

PK/display key detection heuristics move from `BuildKnSkill` into this command.

### `kweaver query subgraph`

```
kweaver query subgraph <kn-id> \
    --start-type <ot-name> \
    --start-condition <json> \
    --path <rt1,rt2,...>
```

Behavior:
1. Resolve OT name to ID
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
- **`kweaver ds`** command group — organize existing datasource commands as `ds list`, `ds get`, `ds delete`, `ds tables`

## Deletions

| Path | Reason |
|------|--------|
| `src/kweaver/skills/` (entire directory) | Orchestration logic moves to CLI |
| `tests/e2e/test_full_flow_e2e.py` | Tests Skill classes; rewrite as CLI test |

## What Stays

| Path | Reason |
|------|--------|
| `src/kweaver/resources/` | Pure CRUD, CLI depends on it |
| `src/kweaver/_client.py`, `_http.py`, `_auth.py`, `_errors.py` | Infrastructure |
| All other e2e/unit tests | Test resource layer, not Skills |

## SKILL.md Rewrite

Two files (`.claude/skills/kweaver/SKILL.md` and `skills/kweaver-core/SKILL.md`) merge into one content source at `skills/kweaver-core/SKILL.md`. The `.claude/` version syncs or symlinks.

Content structure:
- Prerequisites (install, auth)
- Command quick reference by domain (ds, kn, query, action, agent, call)
- Operation playbooks for AI agents (build from scratch, explore existing, agent chat, execute action)
- No Python `import kweaver` examples

## Testing Strategy

- **Unit tests**: Existing 86 tests continue. No Skill-specific unit tests exist to remove.
- **CLI integration tests**: New commands (`ds connect`, `kn create`, `query subgraph`, `agent sessions`, `agent history`) get `click.testing.CliRunner` tests with mocked HTTP.
- **E2E tests**: `test_full_flow_e2e.py` rewrites to invoke CLI commands instead of Skill classes.
