# Stable MVP Plan

## Decision

`main` carries a conservative internal-use MCP server. The previous
all-capability prototype is preserved on the `dev` branch.

## Drivers

- Company users need a setup that works across Cursor, Qoder, Codex, OpenCode,
  and similar MCP clients.
- The stable profile must avoid accidental source-code or secret exfiltration.
- Documentation must match the shipped code path.

## Included

- One `codebrain serve` MCP server.
- Project convention indexing and retrieval.
- Lightweight manual session memory.
- Git read-only context tools: blame, recent changes, and co-change lookup.

## Excluded For Now

- Git history vector indexing.
- Semantic search over indexed Git history.
- OpenAI/cloud embedding by default.
- Legacy multi-server `packages/*` entry points.
- Automatic file watchers.

## Acceptance Criteria

- README documents one stable setup path.
- MCP tool surface excludes `index_git_history` and `search_history`.
- OpenAI embedding fails closed unless cloud embeddings are explicitly enabled.
- Tests cover the stable tool surface and default safety flags.
