"""CodeBrain MCP server — ONE FastMCP, all tools via mcp.add_tool()."""

from __future__ import annotations

from typing import Any

from codebrain.config import Settings
from codebrain.core.di import init_container

# --- Bootstrap settings and DI ---
settings = Settings()
container = init_container(settings)

# --- Create FastMCP ---
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise RuntimeError(
        "mcp package required. Install with: pip install mcp"
    ) from exc

mcp = FastMCP(name="codebase-brain")


# --- Health tool ---
@mcp.tool()
def health() -> dict[str, Any]:
    """Return server health and core dependency status."""
    status: dict[str, Any] = {"ok": True, "name": "codebase-brain"}
    try:
        c = container
        status["vector_store"] = c.vector_store is not None
    except Exception as exc:
        status["ok"] = False
        status["vector_store"] = False
        status["vector_store_error"] = str(exc)

    try:
        c = container
        status["embedder"] = c.embedder is not None
        status["embedder_dimension"] = c.embedder.dimension()
        status["embedder_provider"] = c.settings.embedder_provider
    except Exception as exc:
        status["ok"] = False
        status["embedder"] = False
        status["embedder_error"] = str(exc)

    status["vector_store_backend"] = container.settings.vector_store_backend
    status["db_path"] = str(container.settings.resolved_db_path)
    status["resources"] = container.resource_status()
    status["stable_profile"] = "mvp"
    status["embedding_policy"] = "local_only"
    status["git_history_vector_index_enabled"] = container.settings.git_history_index_enabled
    return status


# --- Codebase Brain task-shaped tools (7) ---
from codebrain.domains.brain import tools as brain_tools

mcp.add_tool(brain_tools.brain_context_for_task)
mcp.add_tool(brain_tools.brain_status)
mcp.add_tool(brain_tools.brain_sync_status)
mcp.add_tool(brain_tools.brain_sync_project)
mcp.add_tool(brain_tools.brain_index_job_status)
mcp.add_tool(brain_tools.brain_index_project)
mcp.add_tool(brain_tools.brain_explain_symbol)


# --- Conventions tools (4) ---
from codebrain.domains.conventions import tools as conv_tools

mcp.add_tool(conv_tools.add_convention)
mcp.add_tool(conv_tools.search_conventions)
mcp.add_tool(conv_tools.list_conventions)
mcp.add_tool(conv_tools.index_convention_files)


# --- Session memory tools (6) ---
from codebrain.domains.session_memory import tools as mem_tools

mcp.add_tool(mem_tools.start_session)
mcp.add_tool(mem_tools.record_decision)
mcp.add_tool(mem_tools.record_problem)
mcp.add_tool(mem_tools.record_file_change)
mcp.add_tool(mem_tools.end_session)
mcp.add_tool(mem_tools.recall_context)


# --- Safe Git read-only tools (3) ---
from codebrain.domains.history import tools as hist_tools

mcp.add_tool(hist_tools.get_blame)
mcp.add_tool(hist_tools.get_co_changed_files)
mcp.add_tool(hist_tools.get_recent_changes)

if container.settings.git_history_index_enabled:
    mcp.add_tool(hist_tools.index_git_history)
    mcp.add_tool(hist_tools.search_history)


def main() -> None:
    """Run the MCP server via stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
