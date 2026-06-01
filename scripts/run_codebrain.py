"""Unified entry point — one MCP server, one database, 14 tools."""

import sys
import types
from pathlib import Path

_packages = Path(__file__).resolve().parent.parent / "packages"
if str(_packages) not in sys.path:
    sys.path.insert(0, str(_packages))

from core.mcp_base import BrainMCP


def _bind_tools(mcp_instance: BrainMCP, tool_class, tool_names: tuple[str, ...]) -> None:
    """Register tools from a server class onto a shared MCP instance.

    Uses __new__ to skip the class's __init__ (which would create duplicate
    FastMCP and MilvusClient instances), then binds each specified method
    to a lightweight wrapper object that shares the parent's services.
    """
    obj = tool_class.__new__(tool_class)
    obj.mcp = mcp_instance.mcp
    obj._milvus = mcp_instance._milvus
    obj._embedder = None  # re-init lazily via parent config
    obj.config = mcp_instance.config
    obj.logger = mcp_instance.logger

    for name in tool_names:
        unbound = getattr(tool_class, name)
        bound = types.MethodType(unbound, obj)
        mcp_instance.tool()(bound)


class CodebrainMCP(BrainMCP):
    """Single MCP server combining conventions + session-memory + history."""

    def __init__(self) -> None:
        super().__init__("codebase-brain")

        from conventions_mcp.server import ConventionsMCP
        _bind_tools(self, ConventionsMCP, (
            "add_convention", "search_conventions",
            "list_conventions", "index_convention_files",
        ))

        from session_memory_mcp.server import SessionMemoryMCP
        _bind_tools(self, SessionMemoryMCP, (
            "start_session", "record_decision", "record_problem",
            "record_file_change", "end_session", "recall_context",
        ))

        from history_mcp.server import HistoryMCP
        _bind_tools(self, HistoryMCP, (
            "search_history", "get_blame", "get_co_changed_files",
            "get_recent_changes", "index_git_history",
        ))


def main() -> None:
    CodebrainMCP().run()


if __name__ == "__main__":
    main()
