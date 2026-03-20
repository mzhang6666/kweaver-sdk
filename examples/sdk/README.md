# SDK Usage Examples

End-to-end TypeScript scripts demonstrating the full KWeaver SDK, running against a real instance.

## Prerequisites

1. **Node.js 22+**
2. **Install dependencies** from the repo root:
   ```bash
   cd packages/typescript && npm install
   ```
3. **Authenticate** — log in to your KWeaver platform:
   ```bash
   npx tsx packages/typescript/src/cli.ts auth login <your-platform-url>
   ```
4. A KWeaver instance with at least one BKN containing data (for examples 01–05)

## Running

```bash
npx tsx examples/sdk/01-quick-start.ts
```

## Learning Path

| # | File | What you'll learn | API Layer |
|---|------|-------------------|-----------|
| 01 | [01-quick-start.ts](01-quick-start.ts) | Configure, discover BKNs, semantic search | Simple API |
| 02 | [02-explore-schema.ts](02-explore-schema.ts) | Object types, relations, actions, statistics | Client API |
| 03 | [03-query-and-traverse.ts](03-query-and-traverse.ts) | Instance queries, subgraph traversal, Context Loader (MCP) | Client API |
| 04 | [04-actions.ts](04-actions.ts) | Action discovery, execution logs, polling | Client API |
| 05 | [05-agent-conversation.ts](05-agent-conversation.ts) | Agent chat (single + streaming), conversation history | Client API |
| 06 | [06-full-pipeline.ts](06-full-pipeline.ts) | Full datasource → BKN → build → search pipeline | Mixed |

**Start with 01** and work your way up. Each example builds on concepts from the previous ones.

## Notes

- **Examples 01–05 are read-only** — safe to run anytime
- **Example 06 is destructive** — creates and deletes resources; requires `RUN_DESTRUCTIVE=1` and database env vars (see file header for details)
- All examples auto-discover available BKNs and agents at runtime
- Search queries use Chinese ("数据") because the demo BKN data is in Chinese — adjust to match your data

## Troubleshooting

**401 Unauthorized** — If you see `oauth info is not active`:
- Token expired (1-hour TTL). Re-run `auth login`.
- If `KWEAVER_TOKEN` / `KWEAVER_BASE_URL` env vars are set (e.g. in `~/.env.secrets`), example 01 (Simple API) ignores them, but they may shadow `~/.kweaver/` credentials for other tooling. Either `unset KWEAVER_TOKEN KWEAVER_BASE_URL` or update them.

## Imports

Examples use monorepo-relative imports. Published SDK users would use:

```typescript
import kweaver from "@kweaver-ai/kweaver-sdk/kweaver";           // Simple API
import { KWeaverClient } from "@kweaver-ai/kweaver-sdk";          // Client API
import type { ProgressItem } from "@kweaver-ai/kweaver-sdk";      // Types
```
