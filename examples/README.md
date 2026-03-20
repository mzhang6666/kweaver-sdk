# KWeaver Examples

## [`sdk/`](sdk/) — SDK Usage Examples

End-to-end TypeScript scripts demonstrating the full SDK capabilities, running against a real KWeaver instance.

| # | File | What you'll learn | API Layer |
|---|------|-------------------|-----------|
| 01 | [01-quick-start.ts](sdk/01-quick-start.ts) | Configure, discover BKNs, semantic search | Simple API |
| 02 | [02-explore-schema.ts](sdk/02-explore-schema.ts) | Object types, relations, actions, statistics | Client API |
| 03 | [03-query-and-traverse.ts](sdk/03-query-and-traverse.ts) | Instance queries, subgraph traversal, Context Loader | Client API |
| 04 | [04-actions.ts](sdk/04-actions.ts) | Action discovery, execution logs, polling | Client API |
| 05 | [05-agent-conversation.ts](sdk/05-agent-conversation.ts) | Agent chat (single + streaming), conversation history | Client API |
| 06 | [06-full-pipeline.ts](sdk/06-full-pipeline.ts) | Full datasource → BKN → build → search pipeline | Mixed |

### Prerequisites

- Node.js 22+
- `cd packages/typescript && npm install`
- `npx tsx packages/typescript/src/cli.ts auth login <your-platform-url>`
- A KWeaver instance with at least one BKN containing data (for examples 01-05)

### Running

```bash
npx tsx examples/sdk/01-quick-start.ts
```

### Notes

- **Examples 01-05 are read-only** — safe to run anytime
- **Example 06 is destructive** — requires `RUN_DESTRUCTIVE=1` and database env vars
- All examples dynamically discover available BKNs/agents at runtime

## [`bkn/`](bkn/) — BKN Format Examples

Sample `.bkn` files demonstrating different knowledge network definition layouts. See [`bkn/README.md`](bkn/README.md) for details.

- **k8s-topology/** — Single-file example
- **k8s-network/** — Multi-file layout
- **k8s-modular/** — Modular layout with subdirectories
