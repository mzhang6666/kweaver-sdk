# BKN Examples

Shared BKN (Business Knowledge Network) example files for tests and documentation.

Source: `adp/docs/design/bkn/features/bkn_docs/examples/`

## Structure

- **k8s-topology/** — Single-file example (`k8s-topology.bkn`)
- **k8s-network/** — Multi-file layout (index, entities, relations, actions)
- **k8s-modular/** — Modular layout (entities/, relations/, actions/ subdirs)

## Usage

- **TypeScript** (`packages/typescript`): `resolve(process.cwd(), "..", "..", "examples", "bkn")`
- **Python** (`packages/python`): `Path(__file__).resolve().parents[2] / "examples" / "bkn"` or equivalent
