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
    status = {"ok": True, "name": "codebase-brain"}
    try:
        c = container
        status["vector_store"] = c.vector_store is not None
        status["embedder"] = c.embedder is not None
        status["embedder_dimension"] = c.embedder.dimension()
        status["embedder_provider"] = c.settings.embedder_provider
        status["vector_store_backend"] = c.settings.vector_store_backend
        status["db_path"] = str(c.settings.resolved_db_path)
    except Exception as exc:
        status["error"] = str(exc)
    return status


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


# --- History tools (5) ---
from codebrain.domains.history import tools as hist_tools

mcp.add_tool(hist_tools.search_history)
mcp.add_tool(hist_tools.get_blame)
mcp.add_tool(hist_tools.get_co_changed_files)
mcp.add_tool(hist_tools.get_recent_changes)
mcp.add_tool(hist_tools.index_git_history)


def main() -> None:
    """Run the MCP server via stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
