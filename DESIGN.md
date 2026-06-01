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
  - Clear local/cloud boundary.
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
  - Keep the safe path local-first while allowing Milvus Standalone/Zilliz Cloud for larger teams.
  - Build on mature open-source projects where practical instead of reimplementing every subsystem.
- Non-goals:
  - Do not rewrite `codebase-memory-mcp`'s graph engine in the first version.
  - Do not build a full Attu replacement in the first version.
  - Do not make cloud embedding or cloud vector storage mandatory.
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
- Principle 3: Local-first by default, cloud-capable by configuration.
  - Private repositories should work without cloud keys.
- Principle 4: Borrow proven systems at boundaries.
  - Use `codebase-memory-mcp` as a graph sidecar before attempting to port its internals.
  - Use Milvus/Zilliz-compatible schemas for vector data.
  - Use Claude Context's indexing, ignore, async, and sync-trigger patterns where they fit.
- Tradeoffs:
  - Sidecar integration is less elegant than a single binary, but reaches useful capability faster.
  - Milvus Lite increases dependency weight, but gives us a real vector path for team knowledge and hybrid retrieval.
  - A unified MCP tool layer hides complexity from users, but requires careful status/error reporting.

## Visual language

- Color:
  - Future UI should use a quiet developer-tool palette with clear status colors.
  - Avoid a decorative marketing look; this is an operational tool.
- Typography:
  - Dense, readable technical UI. Monospace only for paths, commands, and IDs.
- Spacing/layout rhythm:
  - Compact dashboards, table-first where data is inspectable.
- Shape/radius/elevation:
  - Minimal cards, low radius, restrained elevation.
- Motion:
  - Only for indexing progress and status transitions.
- Imagery/iconography:
  - Use concrete diagrams and status icons. Avoid decorative illustrations.

## Components

- Existing components to reuse:
  - Current FastMCP server shell.
  - Current convention/session/Git read-only domain modules where behavior is still valid.
  - Current test harness for stable MCP surface checks.
- New/changed components:
  - `brain` orchestration domain for task-level context packs.
  - `adapters/codebase_memory.py` sidecar adapter.
  - `storage/milvus.py` vector store backend.
  - `indexing/project_indexer.py` orchestration pipeline.
  - `installers/` client config writers.
  - Optional `ui/` dashboard later.
- Variants and states:
  - Local-only mode: codebase-memory sidecar + SQLite/Milvus Lite.
  - Team mode: codebase-memory sidecar + Milvus Standalone/Zilliz Cloud.
  - Degraded mode: graph unavailable, vector/memory still usable with explicit warnings.
  - Privacy mode: disables cloud embedding and raw Git semantic indexing.
- Token/component ownership:
  - MCP contracts are owned by `src/codebrain/server.py` and domain tool modules.
  - Storage contracts are owned by core/infrastructure modules.
  - UI tokens are deferred until dashboard work starts.

## Accessibility

- Target standard:
  - Future UI should target WCAG 2.1 AA.
- Keyboard/focus behavior:
  - Dashboard workflows should be keyboard navigable.
- Contrast/readability:
  - Use high contrast for logs, status badges, and error states.
- Screen-reader semantics:
  - Tables, tabs, dialogs, and status messages must be semantic.
- Reduced motion and sensory considerations:
  - Indexing progress must not rely on motion alone.

## Responsive behavior

- Supported breakpoints/devices:
  - Desktop-first for dashboard and local developer workflows.
  - Mobile is read-only/secondary if added.
- Layout adaptations:
  - Sidebar plus main detail panes on desktop.
  - Single-column stacked layout for narrow screens.
- Touch/hover differences:
  - Do not hide critical actions behind hover-only UI.

## Interaction states

- Loading:
  - Indexing status should show phase, target path, elapsed time, and safe next actions.
- Empty:
  - Empty project state should show exact commands/tools to index.
- Error:
  - Errors must distinguish missing binary, missing database, bad path, cloud auth failure, and privacy-blocked operations.
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
  - Dashboard work later requires browser screenshots.

## Open questions

- [ ] Decide whether v1 keeps Python orchestration only, or introduces a Node sidecar to reuse `@zilliz/claude-context-core`.
- [ ] Decide whether Codebase Brain vendors/forks `codebase-memory-mcp`, downloads it, or requires user installation.
- [ ] Decide the first supported company workflow: Cursor/Qoder first, or Codex/OpenCode first.
- [ ] Decide the privacy policy for indexing Git commit messages and diffs.
- [ ] Decide whether the first vector backend is Milvus Lite only, or Milvus Lite plus remote Milvus.
