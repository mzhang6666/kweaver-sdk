# Vega TypeScript CLI — Phase 1 Design

## Goal

Add `kweaver vega` CLI commands to the TypeScript package, covering read-only operations against `/api/vega-backend/v1/` endpoints: catalogs, resources, connector-types, health/stats/inspect.

Excludes `mdl-data-model` and `mdl-uniquery` paths (pending deprecation).

## Scope

### In Scope

| Command Group | Subcommands |
|---------------|-------------|
| `vega` (top-level) | `health`, `stats`, `inspect` |
| `vega catalog` | `list`, `get`, `health`, `test-connection`, `discover`, `resources` |
| `vega resource` | `list`, `get`, `data`, `preview` |
| `vega connector-type` | `list`, `get` |

### Out of Scope

- Model resources (6 types via `mdl-data-model`) — deprecated
- Query engines (DSL/PromQL via `mdl-uniquery`) — deprecated
- Task management (metric-tasks via `mdl-data-model`) — deprecated
- Trace diagnostics — depends on deprecated paths
- SDK resource layer (`src/resources/vega.ts`) — defer until API stabilizes

## Architecture

Two new files + one modification:

```
src/api/vega.ts          — raw fetch functions returning JSON strings
src/commands/vega.ts     — CLI arg parsing + subcommand routing
src/cli.ts               — add "vega" case to command router
```

No resource layer. No new types. No changes to `KWeaverClient`.

### Design Principle

Follow the existing `ds` command pattern exactly:
- `ensureValidToken()` for auth
- `buildHeaders()` for request headers
- `formatCallOutput()` for JSON output
- `formatHttpError()` for error display
- Hand-rolled arg parsing via index-based loop
- Return exit code (`0` success, `1` error)

### Base URL

Reuse existing KWeaver `base_url` — Vega endpoints are served from the same gateway. No separate `vega_url` needed.

## API Layer (`src/api/vega.ts`)

All functions follow the same signature pattern:

```typescript
interface VegaBaseOptions {
  baseUrl: string;
  accessToken: string;
  businessDomain?: string;  // defaults to "bd_public"
}
```

Note: `buildHeaders()` is duplicated per API file in the current codebase (not shared). Follow the same pattern — define a local `buildHeaders()` in `src/api/vega.ts`.

Note: TypeScript option names use camelCase (e.g., `catalogId`), but HTTP query parameters must use snake_case (e.g., `catalog_id`) to match the server API.

### Endpoints

| Function | Method | Path | Extra Options |
|----------|--------|------|---------------|
| `vegaHealth` | GET | `/health` | — |
| `listVegaCatalogs` | GET | `/api/vega-backend/v1/catalogs` | `status?`, `limit?`, `offset?` |
| `getVegaCatalog` | GET | `/api/vega-backend/v1/catalogs/{id}` | — |
| `vegaCatalogHealthStatus` | GET | `/api/vega-backend/v1/catalogs/health-status` | `ids` (comma-separated) |
| `testVegaCatalogConnection` | POST | `/api/vega-backend/v1/catalogs/{id}/test-connection` | — |
| `discoverVegaCatalog` | POST | `/api/vega-backend/v1/catalogs/{id}/discover` | `wait?` (query param) |
| `listVegaCatalogResources` | GET | `/api/vega-backend/v1/catalogs/{id}/resources` | `category?`, `limit?`, `offset?` |
| `listVegaResources` | GET | `/api/vega-backend/v1/resources` | `catalogId?`, `category?`, `status?`, `limit?`, `offset?` |
| `getVegaResource` | GET | `/api/vega-backend/v1/resources/{id}` | — |
| `queryVegaResourceData` | POST | `/api/vega-backend/v1/resources/{id}/data` | `body` (JSON string) |
| `previewVegaResource` | GET | `/api/vega-backend/v1/resources/{id}/preview` | `limit?` |
| `listVegaDiscoverTasks` | GET | `/api/vega-backend/v1/discover-tasks` | `status?`, `limit?`, `offset?` |
| `listVegaConnectorTypes` | GET | `/api/vega-backend/v1/connector-types` | — |
| `getVegaConnectorType` | GET | `/api/vega-backend/v1/connector-types/{type}` | — |

All functions return `Promise<string>` (raw JSON response text).

### `inspect` and `stats`

`inspect` and `stats` are composite operations implemented in the command layer, not the API layer. They call multiple API functions and aggregate results — same as Python SDK's `VegaNamespace.inspect()` / `stats()`, but simplified for CLI output.

## Command Layer (`src/commands/vega.ts`)

### Routing

```
runVegaCommand(args)
  ├── (no args / --help)  → printVegaHelp()
  ├── "health"            → runVegaHealthCommand()
  ├── "stats"             → runVegaStatsCommand()
  ├── "inspect"           → runVegaInspectCommand(rest)
  ├── "catalog"           → runVegaCatalogCommand(rest)
  │     ├── "list"        → listVegaCatalogs(...)
  │     ├── "get"         → getVegaCatalog(...)
  │     ├── "health"      → vegaCatalogHealthStatus(...)
  │     ├── "test-connection" → testVegaCatalogConnection(...)
  │     ├── "discover"    → discoverVegaCatalog(...)
  │     └── "resources"   → listVegaCatalogResources(...)
  ├── "resource"          → runVegaResourceCommand(rest)
  │     ├── "list"        → listVegaResources(...)
  │     ├── "get"         → getVegaResource(...)
  │     ├── "data"        → queryVegaResourceData(...)
  │     └── "preview"     → previewVegaResource(...)
  └── "connector-type"    → runVegaConnectorTypeCommand(rest)
        ├── "list"        → listVegaConnectorTypes(...)
        └── "get"         → getVegaConnectorType(...)
```

### CLI Flags

Common flags on all subcommands:
- `--pretty` (default: true)
- `-bd, --biz-domain <value>` (default: "bd_public")
- `-v, --verbose`
- `--help, -h`

Subcommand-specific:
- `catalog list`: `--status <value>`, `--limit <n>`, `--offset <n>`
- `catalog health`: `<ids...>` positional or `--all`
- `catalog resources`: `<id>` positional, `--category <value>`, `--limit <n>`
- `resource list`: `--catalog-id <value>`, `--category <value>`, `--status <value>`, `--limit <n>`, `--offset <n>`
- `resource data`: `<id>` positional, `-d <body>` (JSON string)
- `resource preview`: `<id>` positional, `--limit <n>` (default: 10)
- `catalog discover`: `<id>` positional, `--wait` (poll until completion)
- `inspect`: `--full` (currently no-op, reserved for future)

### `inspect` Implementation

Calls `vegaHealth()`, `listVegaCatalogs()`, `listVegaDiscoverTasks(status="running")`, and prints a combined report:
- Server info (name, version)
- Catalog summary (total, healthy/degraded/unhealthy counts)
- Active discover tasks (if any)

Best-effort: individual failures are logged to stderr, partial results still displayed.

### `stats` Implementation

Calls `listVegaCatalogs(limit=100)` and prints a count. (Phase 1 only counts catalogs since model resources are excluded.)

## CLI Router Change (`src/cli.ts`)

Add to `run()`:

```typescript
if (command === "vega") {
  return runVegaCommand(rest);
}
```

Add to `printHelp()`:
```
kweaver vega [health|stats|inspect|catalog|resource|connector-type]
```

And in the Commands section:
```
vega           Vega observability platform (catalogs, resources, connector-types, health)
```

## Testing Strategy

E2E tests against a live Vega backend (consistent with project testing philosophy — no mocks for SDK).

File: `packages/typescript/tests/e2e/vega.test.ts`

Core scenarios:
1. `vega health` — returns server info
2. `vega catalog list` — returns array
3. `vega connector-type list` — returns array
4. `vega inspect` — returns composite report

Gated by environment: skip if no valid token or Vega backend unavailable.

## Skill Update

After implementation, update `.claude/skills/kweaver/SKILL.md`:
- Add `vega` to the command group table
- Remove Vega-related trigger words if they reference unimplemented features (models, query, trace)

Update `.claude/skills/kweaver/references/vega.md`:
- Remove `mdl-*` commands (model, query dsl/promql, trace)
- Keep only `/api/vega-backend/v1/` commands
