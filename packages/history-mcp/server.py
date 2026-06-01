"""MCP server exposing git history search and analysis tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.mcp_base import BrainMCP
from core.milvus_client import MilvusClient

try:
    from .git_indexer import (
        get_blame_info,
        get_co_changed,
        get_file_snippet_at_commit,
        get_recent_changes as read_recent_changes,
        parse_git_log,
    )
except ImportError:
    from git_indexer import (
        get_blame_info,
        get_co_changed,
        get_file_snippet_at_commit,
        get_recent_changes as read_recent_changes,
        parse_git_log,
    )


class HistoryMCP(BrainMCP):
    """MCP server for git history indexing, search, blame, and change patterns."""

    def __init__(self) -> None:
        """Create the history MCP server and register tools."""
        super().__init__("history-mcp")
        self.tool()(self.search_history)
        self.tool()(self.get_blame)
        self.tool()(self.get_co_changed_files)
        self.tool()(self.get_recent_changes)
        self.tool()(self.index_git_history)

    def search_history(
        self,
        query: str,
        file_filter: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search indexed git history by semantic similarity."""
        if not query.strip():
            return []
        embedding = self.get_embedder().embed(query)
        filter_expr = _file_filter_expr(file_filter)
        if filter_expr:
            results = self.get_milvus().hybrid_search(
                MilvusClient.GIT_HISTORY,
                query,
                embedding,
                top_k,
                filter_expr=filter_expr,
            )
        else:
            results = self.get_milvus().search_history(embedding, top_k=top_k)
        return [_history_result(row) for row in results]

    def get_blame(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        repo_path: str = ".",
    ) -> list[dict[str, Any]]:
        """Return blame metadata for a file line range."""
        return get_blame_info(repo_path, file_path, start_line, end_line)

    def get_co_changed_files(
        self,
        file_path: str,
        limit: int = 10,
        repo_path: str = ".",
    ) -> list[dict[str, Any]]:
        """Return files commonly changed with file_path."""
        return get_co_changed(repo_path, file_path, limit)

    def get_recent_changes(
        self,
        file_path: str,
        limit: int = 10,
        repo_path: str = ".",
    ) -> list[dict[str, str]]:
        """Return recent commits that touched file_path."""
        return read_recent_changes(repo_path, file_path, limit)

    def index_git_history(self, repo_path: str = ".", max_commits: int = 500) -> dict[str, int]:
        """Index recent git commit/file history into the git_history collection."""
        repo = Path(repo_path).expanduser().resolve()
        commits = parse_git_log(repo, max_commits)
        if not commits:
            return {"indexed_commits": 0, "indexed_entries": 0}

        embedder = self.get_embedder()
        milvus = self.get_milvus()
        indexed_entries = 0
        for commit in commits:
            changed_files = commit.get("changed_files", [])
            if not isinstance(changed_files, list):
                continue
            for file_path in changed_files:
                if not isinstance(file_path, str) or not file_path:
                    continue
                code_snippet = get_file_snippet_at_commit(
                    repo,
                    str(commit["commit_hash"]),
                    file_path,
                )
                text = _embedding_text(commit, file_path, code_snippet)
                embedding = embedder.embed(text)
                milvus.insert_git_entry(
                    file_path=file_path,
                    commit_hash=str(commit["commit_hash"]),
                    commit_msg=str(commit["commit_msg"]),
                    author=str(commit["author"]),
                    date=str(commit["date"]),
                    code_snippet=code_snippet,
                    embedding=embedding,
                )
                indexed_entries += 1

        return {"indexed_commits": len(commits), "indexed_entries": indexed_entries}


def _file_filter_expr(file_filter: str | None) -> str | None:
    """Build a Milvus equality filter for file paths."""
    if not file_filter:
        return None
    escaped = file_filter.replace("\\", "\\\\").replace('"', '\\"')
    return f'file_path == "{escaped}"'


def _history_result(row: dict[str, Any]) -> dict[str, Any]:
    """Return the public search_history result shape."""
    return {
        "commit_hash": row.get("commit_hash", ""),
        "commit_msg": row.get("commit_msg", ""),
        "author": row.get("author", ""),
        "date": row.get("date", ""),
        "file_path": row.get("file_path", ""),
        "code_snippet": row.get("code_snippet", ""),
        "similarity": row.get("similarity"),
    }


def _embedding_text(commit: dict[str, Any], file_path: str, code_snippet: str) -> str:
    """Build text used to embed one commit/file history entry."""
    return "\n".join(
        [
            str(commit.get("commit_msg", "")),
            file_path,
            str(commit.get("author", "")),
            str(commit.get("date", "")),
            code_snippet,
        ]
    )


def main() -> None:
    """Run the history MCP server."""
    HistoryMCP().run()


if __name__ == "__main__":
    main()
