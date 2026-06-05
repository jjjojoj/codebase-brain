# Codebase Brain 2.0 Rebuild Plan

Last updated: 2026-06-02

## Target

Rebuild Codebase Brain as an AI coding context platform that combines:

- `codebase-memory-mcp` for local code graph, symbol search, call tracing, architecture, and impact analysis.
- `claude-context` ideas for semantic search, AST chunking, hybrid retrieval, async indexing, snapshot status, and sync-trigger.
- Milvus for vector storage, hybrid retrieval, local Lite mode, and larger team deployment.
- Attu as an operational reference and optional Milvus admin companion, not as copied source code.
- Codebase Brain's own layer for team conventions, session memory, decisions, Git history, privacy policy, and unified MCP tools.

The goal is not to make a smaller clone. The goal is to make a company-usable "context control plane" for AI coding tools.

## Source Projects And What To Use

| Project | Use directly | Use as reference | Do not use |
| --- | --- | --- | --- |
| [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | Binary sidecar or vendored fork, tool contracts, graph output | Installer, update flow, watcher, shared graph artifact, security docs | Rewriting the whole C graph engine in v1 |
| [zilliztech/claude-context](https://github.com/zilliztech/claude-context) | MIT concepts and possibly package-level reuse | Async indexing, snapshot, file inclusion rules, sync-trigger, hybrid search UX | Blindly adding cloud OpenAI/Zilliz requirements to private-code default; adopting cloud embedding |
| [milvus-io/milvus](https://github.com/milvus-io/milvus) | Milvus Lite / Standalone / Cloud as vector backend | Hybrid search, multi-tenancy, RBAC, scaling model | Running full Milvus by default for individual users |
| [zilliztech/attu](https://github.com/zilliztech/attu) | Optional external admin tool | Multi-cluster UI, data explorer, search playground, agent ops | Copying current Attu v3 code; it is proprietary from v2.6.0 onward |

License note:

- `codebase-memory-mcp` and `claude-context` are MIT; copying or modifying code requires keeping license/copyright notices.
- Milvus is Apache 2.0.
- Current Attu v3 is proprietary; only older <= 2.5.12 was Apache 2.0. Treat current Attu as a tool/inspiration, not code to copy.

## Pain Points From The Original `dev` README

The original README says Codebase Brain should help AI coding tools stop working from shallow search only. The pain points can be restated as seven product problems:

1. **Code structure is hard for agents to discover**
   Agents waste steps reading files and still miss call paths, entry points, and cross-file dependencies.

2. **Semantic code search is noisy or expensive**
   Loading large directories into context wastes tokens; keyword search misses intent.

3. **Project conventions are implicit**
   Rules live in developers' heads, not in a searchable system the AI can consult.

4. **Tasks lose continuity across sessions**
   Long tasks restart from zero unless decisions, files, and problems are persisted.

5. **Historical decisions are invisible**
   Commit history, blame, co-change patterns, and ADR-like decisions are not surfaced before editing.

6. **Indexing goes stale**
   Generated context becomes untrustworthy when code changes and index status is unclear.

7. **Every AI client needs different setup**
   Cursor, Qoder, Codex, OpenCode, Claude Code, and Hermes should not each require hand-built context plumbing.

## Product Architecture

```text
AI clients
Cursor / Qoder / Codex / OpenCode / Claude Code / Hermes
        |
        v
Codebase Brain MCP facade
        |
        +-- brain_context_for_task
        +-- brain_before_edit
        +-- brain_explain_symbol
        +-- brain_explain_history
        +-- brain_record_decision
        +-- brain_index_project
        +-- brain_status
        |
        v
Context Orchestrator
        |
        +-- Graph Adapter
        |      `codebase-memory-mcp` CLI/MCP sidecar
        |      index_repository / search_graph / trace_call_path / get_architecture
        |
        +-- Semantic Vector Layer
        |      Milvus Lite first, Milvus Standalone/Zilliz optional
        |      code chunks / docs / conventions / memories / decisions
        |
        +-- Team Knowledge Layer
        |      .codebrain/conventions/*.md
        |      sessions, decisions, problems, file changes
        |      filtered Git history and ADRs
        |
        +-- Policy Layer
        |      local-first defaults
        |      secret filtering
        |      ignore rules
        |      local-only embedding policy
        |
        +-- Status Layer
               snapshots, locks, progress, health
```

## Core Decision

Use **one MCP server** for users and AI clients.

Internally, Codebase Brain can call sidecars and storage engines, but users should configure one MCP server called `codebase-brain`. This avoids the old `dev` design problem where users had to wire `codebase-memory`, `conventions`, `session-memory`, and `history` separately.

## Tool Surface V1

Keep the public tool surface small and task-shaped:

| Tool | Purpose |
| --- | --- |
| `brain_status` | Show graph/vector/index/privacy status. |
| `brain_index_project` | Index graph, conventions, docs, and optional memories/history. |
| `brain_context_for_task` | Return a compact context pack for a natural-language task. |
| `brain_before_edit` | Given files or task, return conventions, call graph, recent changes, risks, and suggested checks. |
| `brain_explain_symbol` | Explain a symbol using graph search, code snippets, callers/callees, and conventions. |
| `brain_explain_history` | Explain why code changed using blame, recent commits, co-change files, decisions, and ADRs. |
| `brain_record_decision` | Persist human/AI decisions with files, rationale, and tags. |
| `brain_record_problem` | Persist problems and solutions for future recall. |
| `brain_search_knowledge` | Search conventions, sessions, decisions, docs, and selected Git history. |
| `brain_manage_conventions` | Index/list/add team conventions. |

Keep raw lower-level tools internal at first. The agent should ask for "task context", not manually stitch 20 calls.

## Context Pack Contract

`brain_context_for_task` and `brain_before_edit` should return:

```json
{
  "task": "...",
  "status": {
    "graph": "ready|missing|stale|error",
    "vector": "ready|missing|stale|error",
    "privacy": "local_only"
  },
  "must_follow": [
    {"source": "convention", "title": "...", "reason": "..."}
  ],
  "relevant_code": [
    {"file": "...", "symbol": "...", "why": "...", "source": "graph|semantic"}
  ],
  "call_paths": [
    {"symbol": "...", "direction": "inbound|outbound", "summary": "..."}
  ],
  "history": [
    {"file": "...", "signal": "recent_change|blame|co_change|decision", "summary": "..."}
  ],
  "past_sessions": [
    {"task": "...", "lesson": "...", "files": ["..."]}
  ],
  "risks": [
    {"risk": "...", "check": "..."}
  ],
  "suggested_next_steps": [
    "..."
  ]
}
```

The output must be compact, cited, and ranked. Do not return unbounded snippets.

## Storage Model

### Graph Store

- Owner: `codebase-memory-mcp`.
- Data: symbols, files, call edges, imports, routes, architecture, graph search.
- First implementation: sidecar adapter that shells to `codebase-memory-mcp cli ...` or talks to its MCP endpoint.
- Later implementation: vendored/forked graph engine if packaging requires one binary.

### Vector Store

- Owner: Codebase Brain.
- Backend:
  - v1 local: Milvus Lite through `pymilvus[milvus-lite]`.
  - v1 team: remote Milvus or Zilliz Cloud by explicit config.
- Collections:
  - `brain_conventions`
  - `brain_sessions`
  - `brain_decisions`
  - `brain_problems`
  - `brain_docs`
  - `brain_git_history` only when enabled
  - `brain_code_chunks` optional if we implement Claude Context-style semantic code indexing

### Local State

- `.codebrain/conventions/*.md`: committed team knowledge.
- `.codebrain/codebrain.toml`: project config, safe to commit if no secrets.
- `.codebrain/index-state.json`: optional project index metadata, normally local.
- `.codebrain/*.db`: local and ignored.
- `~/.codebrain/`: user-level config, caches, sidecar binaries, locks.

## Privacy And Safety Defaults

- Default mode is local-only.
- Embeddings are local-only by product policy.
- Remote Milvus/Zilliz vector storage is explicit opt-in.
- Raw Git diff indexing is disabled until secret filtering is implemented.
- `.env`, keys, tokens, lockfiles, build outputs, vendor directories, and ignored files are excluded.
- All indexing accepts explicit include/exclude rules.
- `brain_status` must show when a risky feature is enabled.

## Implementation Roadmap

### Phase 0: Design Lock

Deliverables:

- `docs/rebuild-plan.md`
- Updated README that explains Codebase Brain 2.0 honestly.

Exit criteria:

- Design names the source projects, license constraints, target tools, and v1 tool surface.

### Phase 1: One MCP Facade

Deliverables:

- Keep one `codebrain serve` MCP server.
- Add `brain_status`.
- Add adapter interfaces:
  - `GraphBackend`
  - `VectorBackend`
  - `KnowledgeRepository`
  - `PrivacyPolicy`
- Keep existing convention/session/Git read-only tools as internal logic.

Tests:

- Tool registration test.
- Status output test.
- Privacy defaults test.

### Phase 2: Codebase-Memory Sidecar

Deliverables:

- Detect `codebase-memory-mcp` binary.
- `brain_index_project` can call `index_repository`.
- `brain_explain_symbol` can call `search_graph`, `trace_call_path`, and `get_code_snippet`.
- `brain_status` reports sidecar version and indexed projects.

Tests:

- Adapter unit tests with fake CLI output.
- Smoke test skipped when binary is absent.

### Phase 3: Milvus Vector Knowledge Layer

Status: initial optional backend implemented. Current code has `MilvusVectorStore`, Milvus/Milvus Lite configuration fields, split optional dependency extras (`milvus` for remote client, `milvus-lite` for local engine), and fake-client contract tests. SQLite remains the default backend until Milvus Lite receives broader live smoke coverage and migration documentation.

Deliverables:

- Add Milvus Lite backend. Done for the initial optional backend.
- Add collections for conventions, sessions, decisions, problems, docs.
- Port/keep existing SQLite vector store only as fallback if needed.
- Add hybrid ranking for team knowledge where Milvus supports it.

Tests:

- Local Milvus Lite insert/search tests. Fake-client contract tests are done; live Milvus Lite smoke should run when `pymilvus[milvus-lite]` is installed in CI. Local install was blocked on one macOS environment by `faiss-cpu` requiring `swig`, so remote Milvus/Zilliz and SQLite remain the safer adoption paths.
- Fallback tests.
- Collection schema migration tests.

### Phase 4: Context Pack Orchestrator

Status: initial `brain_context_for_task` implemented with local context, optional graph context, degraded warnings, and contract tests. `brain_before_edit`, token-budget tuning, and golden fixtures remain open.

Deliverables:

- `brain_context_for_task`. Initial version done.
- `brain_before_edit`
- Context ranking and output budget.
- Merge graph, semantic, convention, memory, and Git signals.

Tests:

- Golden context-pack tests.
- Missing backend/degraded mode tests.
- Token budget tests.

### Phase 5: Sync And Freshness

Status: partially implemented. Current code has file filtering snapshots, `.codebrain/index-state.json`, `brain_sync_status`, `brain_sync_project`, and in-process async indexing jobs. Lock files, external sync-trigger files, and stale lock recovery are still pending.

Deliverables:

- File inclusion and ignore rules modeled after Claude Context.
- Index snapshot file.
- Lock file to prevent concurrent indexing corruption.
- Sync-trigger file such as `~/.codebrain/.sync-trigger`.
- Optional background sync.

Tests:

- Ignore rule tests.
- Snapshot migration tests.
- Stale lock recovery tests.

### Phase 6: Installer And Client Config

Deliverables:

- `codebrain install`
- Detect and configure:
  - Cursor
  - Qoder
  - Codex CLI
  - OpenCode
  - Claude Code
  - Hermes if config format is available
- `codebrain uninstall`
- `codebrain doctor`

Tests:

- Fixture-based config writer tests.
- No-op/dry-run mode.
- Backup and restore tests.

### Phase 7: Optional Dashboard

Status: initial local read-only dashboard implemented through `codebrain dashboard`. It shows status, file snapshot, privacy, Milvus configuration state, and MCP JSON. It does not edit client config files and does not replace Attu.

Deliverables:

- Minimal dashboard only after MCP/CLI is stable.
- Project status, collections, memories, conventions, context preview.
- Link out to Attu or document using Attu for Milvus inspection.

Constraint:

- Do not copy Attu v3 source. Current Attu is proprietary from v2.6.0 onward.

## First Build Slice

Start with Phase 1 and Phase 2. This gives real capability quickly:

1. Keep current repo structure.
2. Add `src/codebrain/adapters/codebase_memory.py`.
3. Add `brain_status`.
4. Add `brain_index_project`.
5. Add `brain_explain_symbol`.
6. Hide or de-emphasize raw old tools in README, but keep internal logic.
7. Test with fake sidecar output first, then with installed `codebase-memory-mcp`.

This slice proved the new direction without forcing Milvus, dashboard, or installer complexity immediately.

## Second Build Slice

The next shipped slice adds operational visibility and sync freshness without changing the one-MCP-server contract:

1. Add `brain_sync_status` for filtered file snapshots.
2. Add `brain_sync_project` for sync-trigger indexing.
3. Add `brain_index_job_status` for in-process async job visibility.
4. Persist successful sync snapshots to `.codebrain/index-state.json`.
5. Add `codebrain dashboard` as a local read-only UI for status and MCP config generation.
6. Add Milvus Lite config fields and optional dependency metadata, but keep SQLite as the active default until Milvus has broader rollout coverage.
7. Add `MilvusVectorStore` behind `CODEBRAIN_VECTOR_STORE_BACKEND=milvus`.

## Risks

- Sidecar dependency may make setup harder until installer exists.
- `codebase-memory-mcp` tool output may change across versions; adapter needs version checks.
- Milvus Lite increases dependency weight compared with SQLite.
- Attu cannot be copied directly if using current v3 code.
- Combining graph and vector signals can return noisy results unless ranking is strict.

## Recommendation

Proceed with a composition-first rebuild:

1. Use `codebase-memory-mcp` for graph.
2. Use Codebase Brain for team knowledge and context packs.
3. Add Milvus for vector knowledge once the facade is stable.
4. Add installer after the main tools work.
5. Add dashboard last.

This makes Codebase Brain stronger than the original MVP while avoiding the cost of rewriting mature graph and vector systems from scratch.
