# Design

## Source of truth

- Status: Draft
- Last refreshed: 2026-06-02
- Primary product surfaces:
  - MCP server used by Cursor, Qoder, Codex, OpenCode, Claude Code, Cline, Windsurf, Hermes, and other MCP clients.
  - CLI installer and project indexer.
  - Optional local/admin dashboard for index health, memory review, and Milvus inspection.
- Evidence reviewed:
  - `README.md` on `main`: current stable MVP scope.
  - `README.md` on `dev`: original product intent and AI coding pain points.
  - `docs/plan.md` on `dev`: original implementation plan.
  - [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp): local graph index, code search, call tracing, architecture, installer, watcher.
  - [zilliztech/claude-context](https://github.com/zilliztech/claude-context): semantic code search, Milvus/Zilliz storage, async indexing, file inclusion rules, sync trigger, MCP packaging.
  - [milvus-io/milvus](https://github.com/milvus-io/milvus): vector database, Milvus Lite, standalone/cloud deployment, hybrid search.
  - [zilliztech/attu](https://github.com/zilliztech/attu): Milvus workbench, multi-cluster management, vector search UI, AI agent, monitoring.

## Brand

- Personality: practical, technical, local-first, enterprise-safe.
- Trust signals:
  - Clear local-only embedding boundary.
  - Explicit source attribution for borrowed ideas or code.
  - Small number of high-value MCP tools instead of many overlapping tools.
  - Reproducible install, health checks, and testable workflows.
- Avoid:
  - Claiming graph-index, benchmark, installer, or UI capabilities before they exist.
  - Copying proprietary Attu v3 code.
  - Requiring cloud API keys for company/private-code workflows.
  - Returning large unranked context dumps to the AI client.

## Product goals

- Goals:
  - Fuse code structure, semantic retrieval, team conventions, session memory, and Git history into one practical AI coding context layer.
  - Make one MCP entry useful across Cursor, Qoder, Codex, OpenCode, Claude Code, Hermes, and similar clients.
  - Let developers ask for task context and receive a compact, cited edit brief.
  - Keep embeddings local-only while allowing explicitly configured Milvus Standalone/Zilliz Cloud for vector storage when a team approves it.
  - Build on mature open-source projects where practical instead of reimplementing every subsystem.
- Non-goals:
  - Do not rewrite `codebase-memory-mcp`'s graph engine in the first version.
  - Do not build a full Attu replacement in the first version.
  - Do not support cloud embedding providers in Codebase Brain.
  - Do not make cloud vector storage mandatory.
  - Do not expose raw Git history semantic indexing until filtering and privacy controls are implemented.
- Success signals:
  - A developer can install once and use one MCP server in multiple AI coding clients.
  - `brain_context_for_task` returns useful context from graph, conventions, memory, and Git history in one call.
  - Index status is observable and recoverable.
  - Team convention files can be committed, while personal memory and databases remain local by default.

## Personas and jobs

- Primary personas:
  - Company developers using Cursor or Qoder for daily coding.
  - Power users using Codex, OpenCode, Claude Code, or Hermes.
  - Tech leads who want team conventions and historical decisions to guide AI edits.
  - Platform/tooling maintainers who need predictable local setup and safe defaults.
- User jobs:
  - Before editing, gather the relevant code structure, files, conventions, and recent history.
  - Ask why code is shaped a certain way.
  - Continue a multi-day task without losing decisions and gotchas.
  - Keep AI clients aligned with team-specific engineering rules.
  - Inspect index health and storage state when search results look wrong.
- Key contexts of use:
  - Private company repositories.
  - Large projects where file-by-file exploration wastes tokens.
  - Teams with different AI coding clients.
  - Long-running refactors, bug hunts, and feature work.

## Information architecture

- Primary navigation:
  - MCP tools for AI clients.
  - CLI commands for humans and installers.
  - Optional dashboard for operational visibility.
- Core routes/screens:
  - Not required for v1.
  - Future dashboard screens: overview, projects, collections, context preview, memories, conventions, Git/history, settings.
- Content hierarchy:
  - Task context should be ranked by usefulness:
    1. edit-critical warnings and conventions,
    2. relevant code symbols/files,
    3. call paths and dependencies,
    4. recent Git/change signals,
    5. similar past sessions and decisions,
    6. optional raw snippets.

## Design principles

- Principle 1: One product, multiple engines.
  - Codebase Brain should be the orchestration layer over graph, vector, team memory, and Git context.
- Principle 2: Context packs, not raw search.
  - MCP clients should receive compact, cited, task-shaped briefs.
- Principle 3: Local embedding only.
  - Private repositories should work without cloud keys or cloud embedding providers.
- Principle 4: Borrow proven systems at boundaries.
  - Use `codebase-memory-mcp` as a graph sidecar before attempting to port its internals.
  - Use Milvus/Zilliz-compatible schemas for vector data.
  - Use Claude Context's indexing, ignore, async, and sync-trigger patterns where they fit.
- Tradeoffs:
  - Sidecar integration is less elegant than a single binary, but reaches useful capability faster.
  - Milvus Lite increases dependency weight, but gives us a real vector path for team knowledge and hybrid retrieval.
  - A unified MCP tool layer hides complexity from users, but requires careful status/error reporting.

## Components

- Existing components to reuse:
  - Current FastMCP server shell.
  - Current convention/session/Git read-only domain modules where behavior is still valid.
  - Current test harness for stable MCP surface checks.
- New/changed components:
  - `domains/brain/local_context.py`: gathers conventions, session memory, and Git read-only signals without sidecar dependencies.
  - `domains/brain/graph_context.py`: gathers code graph and call-path signals through the optional `codebase-memory-mcp` sidecar.
  - `domains/brain/context_pack.py`: ranks, merges, and formats local plus graph signals into a compact Context Pack.
  - `domains/brain/tools.py`: MCP wrappers only; parameter validation and calls into the context modules.
  - `adapters/codebase_memory.py` sidecar adapter.
  - `domains/brain/indexing.py` file filtering and sync snapshots.
  - `domains/brain/jobs.py` in-process async indexing job registry.
  - `dashboard.py` local read-only status and MCP config UI.
  - `infrastructure/vector_store/milvus.py` optional Milvus vector store backend.
  - `installers/` client config writers.
- Variants and states:
  - Local-only mode: codebase-memory sidecar + SQLite/Milvus Lite.
  - Team mode: codebase-memory sidecar + Milvus Standalone/Zilliz Cloud.
  - Offline mode: local embeddings, SQLite, conventions, memory, and Git read-only tools remain usable after dependencies and models are installed.
  - Degraded mode: graph sidecar unavailable returns empty graph fields plus explicit warnings; conventions, memory, and Git read-only signals still return when available.
  - Privacy mode: enforces local-only embedding and disables raw Git semantic indexing.
- Token/component ownership:
  - MCP contracts are owned by `src/codebrain/server.py` and domain tool modules.
  - Storage contracts are owned by core/infrastructure modules.
  - UI tokens are deferred until dashboard work starts.

## Context Pack Contract

- `brain_context_for_task` is the core orchestration tool.
- Input:
  - `task: str` required, natural-language task description.
  - `files: list[str] | None`, relevant file paths when known.
  - `symbols: list[str] | None`, relevant symbols when known.
  - `repo_path: str = "."`, repository root for Git and graph lookups.
  - `top_k: int = 5`, bounded result count per source.
- Output:
  - `task`: original task string.
  - `status`: per-source status for `local`, `graph`, `history`, and `memory`.
  - `critical_conventions`: top conventions ranked by relevance, max 3.
  - `related_symbols`: graph symbols and call-path hints, empty when sidecar is missing.
  - `recent_changes`: recent Git read-only signals for supplied files, max 5.
  - `similar_sessions`: recalled session memory, max 3.
  - `warnings`: degraded-mode and disabled-feature warnings.
  - `suggested_next_steps`: compact checks or tool calls useful before editing.
- Ranking order:
  1. critical conventions,
  2. directly supplied files and symbols,
  3. graph symbols and call paths,
  4. recent Git read-only changes,
  5. similar past sessions.
- Degraded modes:
  - Sidecar unavailable: `related_symbols=[]`, `status.graph="missing"`, warning explains that local context is still usable.
  - No conventions indexed: `critical_conventions=[]`, warning suggests indexing `.codebrain/conventions`.
  - No session memory: `similar_sessions=[]`, no hard failure.
  - Git history semantic search disabled: semantic history is omitted; Git read-only signals can still be returned.
  - All sources empty: return a valid empty Context Pack with warnings, not an unhandled exception.

## Feature Flags

| Capability | Flag | Default | Tool-surface behavior |
| --- | --- | --- | --- |
| Git history semantic indexing/search | `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED` | `false` | Register `index_git_history` and `search_history` only when true. |
| Vector store backend | `CODEBRAIN_VECTOR_STORE_BACKEND` | `sqlite` | `sqlite` is the stable default; `milvus` is explicit opt-in. |
| Embedding provider | `CODEBRAIN_EMBEDDER_PROVIDER` | `sentence-transformers` | Only `sentence-transformers` and `ollama` are supported; cloud providers are out of scope. |
| Code graph sidecar | `CODEBRAIN_CODEBASE_MEMORY_BINARY` | `codebase-memory-mcp` | Missing binary degrades graph fields; local context remains usable. |

## Dashboard UI

- Dashboard UI design is deferred to v2.
- The current local dashboard should stay desktop-first, high-contrast, and keyboard-navigable where practical; do not add a dashboard framework until MCP/CLI orchestration is working.

## Interaction States

- Loading:
  - Indexing status should show phase, target path, elapsed time, and safe next actions.
- Empty:
  - Empty project state should show exact commands/tools to index.
- Error:
  - Target error taxonomy should distinguish missing binary, missing database, bad path, unsupported provider, and privacy-blocked operations.
  - Code changes that claim this taxonomy must add typed mapping and tests.
- Success:
  - Index success should report files/chunks/nodes/edges where available.
- Disabled:
  - Disabled experimental features should explain the required config and risk.
- Offline/slow network:
  - Local mode should remain usable without network after dependencies are installed.

## Content voice

- Tone:
  - Direct, factual, developer-facing Chinese by default, with English tool names.
- Terminology:
  - Use "结构层" for graph/code structure.
  - Use "语义层" for vector/semantic search.
  - Use "团队知识层" for conventions, decisions, and memory.
  - Use "Context Pack" or "上下文包" for final task-shaped output.
- Microcopy rules:
  - Do not say "AI understands everything".
  - Prefer "indexed", "retrieved", "ranked", "not available", and "disabled by policy".

## Implementation constraints

- Framework/styling system:
  - Current repo is Python/FastMCP.
  - Do not add a dashboard framework until MCP/CLI orchestration is working.
- Design-token constraints:
  - Defer.
- Performance constraints:
  - Indexing must be resumable or observable.
  - Main task-context tool should return compact results and avoid dumping full files.
- Compatibility constraints:
  - Python 3.11+.
  - macOS, Linux, Windows where possible.
  - Client configs for Cursor, Qoder, Codex, OpenCode, Claude Code, Hermes where practical.
- Test/screenshot expectations:
  - MCP tool unit tests and CLI smoke tests before UI work.
  - Dashboard work should keep HTTP payload tests and browser smoke checks.

## Open questions

- [ ] Decide final ranking weights and output budget for `brain_context_for_task` after the v1 Context Pack tests land.
- [ ] Decide whether v1 keeps Python orchestration only, or introduces a Node sidecar to reuse `@zilliz/claude-context-core`.
- [ ] Decide whether Codebase Brain vendors/forks `codebase-memory-mcp`, downloads it, or requires user installation.
- [ ] Decide the first supported company workflow: Cursor/Qoder first, or Codex/OpenCode first.
- [ ] Decide the privacy policy for indexing Git commit messages and diffs.
- [x] Decide whether the first vector backend is Milvus Lite only, or Milvus Lite plus remote Milvus.
  - Decision: support both through `MilvusClient` URI configuration, default to local Milvus Lite path when explicitly enabled.
