# Codebase Brain

Codebase Brain is a conservative MCP server for sharing project conventions,
lightweight coding-session memory, and safe Git context with AI coding tools.

The `main` branch is the stable internal-use profile. Experimental history
vector indexing and legacy multi-server code are kept on the `dev` branch.

## Stable Scope

The stable profile solves three practical problems first:

- Project conventions: store team rules as Markdown and retrieve them before code changes.
- Lightweight session memory: manually record decisions, problems, and touched files.
- Safe Git context: read blame, recent changes, and co-change patterns directly from Git.

The stable profile intentionally does not expose:

- Git history vector indexing.
- Semantic search over indexed Git history.
- OpenAI/cloud embedding by default.
- Legacy `packages/*` multi-server entry points.
- Automatic file watchers.

## Tools Exposed

| Tool | Purpose |
| --- | --- |
| `health` | Report server, storage, and embedding status. |
| `add_convention` | Add one project convention manually. |
| `search_conventions` | Search indexed conventions with local vector search. |
| `list_conventions` | List convention metadata. |
| `index_convention_files` | Index Markdown files from `.codebrain/conventions`. |
| `start_session` | Start one lightweight session and recall related sessions. |
| `record_decision` | Record a key implementation or architecture decision. |
| `record_problem` | Record a solved problem and its solution. |
| `record_file_change` | Record a file changed during the current session. |
| `end_session` | Save the session memory. |
| `recall_context` | Recall similar saved sessions. |
| `get_blame` | Read Git blame metadata for a line range. |
| `get_recent_changes` | Read recent commits touching a file. |
| `get_co_changed_files` | Find files historically changed together. |

## Install

Use Python 3.11+.

```bash
git clone https://github.com/jjjojoj/codebase-brain.git
cd codebase-brain
python3.12 -m venv .venv
.venv/bin/pip install -e ".[local]"
```

Windows PowerShell:

```powershell
git clone https://github.com/jjjojoj/codebase-brain.git C:\codebase-brain
cd C:\codebase-brain
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -e ".[local]"
```

The `local` extra installs `sentence-transformers` for local CPU embeddings.
Do not use cloud embeddings for company code unless your organization has
explicitly approved that data flow.

## Project Conventions

Create convention files in each repository:

```text
your-project/
  .codebrain/
    conventions/
      testing.md
      error-handling.md
      module-boundaries.md
```

Each file uses YAML frontmatter:

```markdown
---
module: auth
title: Auth error handling
tags: [auth, errors]
---

Authentication code returns typed AuthError values. Do not raise generic
exceptions across the module boundary.
```

Then ask your AI coding tool to call:

```text
index_convention_files
```

or pass an explicit absolute path when the client does not launch the MCP
server from the project root.

## MCP Configuration

Use one MCP server named `codebase-brain`. Prefer absolute paths; not every
MCP client expands `~` consistently.

macOS / Linux:

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "/ABS/PATH/codebase-brain/.venv/bin/codebrain",
      "args": ["serve"],
      "env": {
        "CODEBRAIN_DB_PATH": "/ABS/PATH/your-project/.codebrain/codebrain.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "/ABS/PATH/your-project/.codebrain/conventions"
      }
    }
  }
}
```

Windows:

```json
{
  "mcpServers": {
    "codebase-brain": {
      "command": "C:\\codebase-brain\\.venv\\Scripts\\codebrain.exe",
      "args": ["serve"],
      "env": {
        "CODEBRAIN_DB_PATH": "C:\\path\\to\\your-project\\.codebrain\\codebrain.db",
        "CODEBRAIN_DEFAULT_CONVENTIONS_PATH": "C:\\path\\to\\your-project\\.codebrain\\conventions"
      }
    }
  }
}
```

This shape works for MCP-capable tools such as Cursor, Qoder, Codex CLI,
OpenCode, Claude Code, Windsurf, and Cline. The exact settings file location
depends on the client.

## Recommended Team Workflow

1. Add 5-20 high-value conventions for testing, error handling, naming,
   module boundaries, and review expectations.
2. Run `index_convention_files`.
3. At the start of a task, call `start_session`.
4. During the task, call `record_decision`, `record_problem`, and
   `record_file_change` only for durable facts.
5. Before changing unfamiliar files, call `get_recent_changes`,
   `get_blame`, or `get_co_changed_files`.
6. End the task with `end_session`.

Keep memories short and factual. Do not store secrets, credentials, customer
data, or private production logs.

## Configuration

Environment variables use the `CODEBRAIN_` prefix.

| Variable | Default | Notes |
| --- | --- | --- |
| `CODEBRAIN_EMBEDDER_PROVIDER` | `sentence-transformers` | Stable local default. |
| `CODEBRAIN_EMBEDDER_MODEL` | `all-MiniLM-L6-v2` | Small local model for fast startup. |
| `CODEBRAIN_DB_PATH` | `.codebrain/codebrain.db` | Set this to an absolute per-project path. |
| `CODEBRAIN_DEFAULT_CONVENTIONS_PATH` | `.codebrain/conventions` | Set this to an absolute per-project path. |
| `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS` | `false` | Keep false for stable internal use. |
| `CODEBRAIN_GIT_HISTORY_INDEX_ENABLED` | `false` | Keep false for stable internal use. |

## Disabled Experimental Capabilities

`index_git_history` and `search_history` are not registered in the stable MCP
surface. Their implementation remains behind a disabled setting for future
work, but stable users should rely on the safe Git read-only tools instead.

OpenAI embeddings are blocked unless `CODEBRAIN_ALLOW_CLOUD_EMBEDDINGS=true`
is explicitly set. Enabling it means indexed text can leave your machine.

## Development

Install dev dependencies and run tests:

```bash
uv run --python 3.12 --extra dev pytest -q
```

The stable branch is `main`. The pre-stabilization experimental version is
available on `dev`.
