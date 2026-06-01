"""High-level data access repository for CodeBrain domains."""

from __future__ import annotations

from typing import Any

from codebrain.core.embedder import Embedder
from codebrain.core.vector_store import AbstractVectorStore


class Repository:
    """Repository wraps vector store + embedder for domain-level data access."""

    def __init__(self, vector_store: AbstractVectorStore, embedder: Embedder) -> None:
        self.store = vector_store
        self.embedder = embedder

    # ----------------------------------------------------------------- Conventions

    def add_convention(
        self, module: str, title: str, content: str, *, record_id: str | None = None
    ) -> str:
        text = _convention_search_text(module, title, content, [])
        embedding = self.embedder.embed(text)
        return self.store.insert_convention(
            module=module,
            title=title,
            content=content,
            embedding=embedding,
            record_id=record_id,
        )

    def search_conventions(
        self,
        query: str,
        keywords_text: str = "",
        module_filter: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        search_text = " ".join(part for part in (query, keywords_text) if part)
        embedding = self.embedder.embed(search_text)
        filter_expr = None
        if module_filter:
            escaped = module_filter.replace("\\", "\\\\").replace('"', '\\"')
            filter_expr = f'module == "{escaped}"'
        return self.store.search("conventions", embedding, top_k, filter_expr=filter_expr)

    def list_conventions(
        self, module: str | None = None, limit: int = 1000
    ) -> list[dict[str, Any]]:
        filter_expr = None
        if module:
            escaped = module.replace("\\", "\\\\").replace('"', '\\"')
            filter_expr = f'module == "{escaped}"'
        return self.store.query(
            "conventions",
            filter_expr=filter_expr,
            output_fields=["id", "module", "title", "created_at"],
            limit=limit,
        )

    def upsert_convention(
        self,
        module: str,
        title: str,
        content: str,
        record_id: str,
        tags: list[str] | None = None,
    ) -> str:
        # Delete old then insert
        try:
            self.store.delete("conventions", [record_id])
        except Exception:
            pass
        text = _convention_search_text(module, title, content, tags or [])
        embedding = self.embedder.embed(text)
        return self.store.insert_convention(
            module=module,
            title=title,
            content=content,
            embedding=embedding,
            record_id=record_id,
        )

    # ----------------------------------------------------------------- Session Memory

    def insert_session(
        self,
        task: str,
        files_modified: str,
        decisions: str,
        assumptions: str,
        problems: str,
        record_id: str | None = None,
        created_at: str | None = None,
        summary: str = "",
    ) -> str:
        compiled = _compile_session_summary(
            task, files_modified, decisions, assumptions, problems, summary, created_at or ""
        )
        embedding = self.embedder.embed(compiled)
        return self.store.insert_session(
            task=task,
            files_modified=files_modified,
            decisions=decisions,
            assumptions=assumptions,
            problems=problems,
            embedding=embedding,
            record_id=record_id,
            created_at=created_at,
        )

    def search_sessions(
        self, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        embedding = self.embedder.embed(query)
        return self.store.search("session_memory", embedding, top_k)

    # ----------------------------------------------------------------- Git History

    def insert_git_entry(
        self,
        file_path: str,
        commit_hash: str,
        commit_msg: str,
        author: str,
        date: str,
        code_snippet: str,
        record_id: str | None = None,
    ) -> str:
        text = _git_embedding_text(commit_msg, file_path, author, date, code_snippet)
        embedding = self.embedder.embed(text)
        return self.store.insert_git_entry(
            file_path=file_path,
            commit_hash=commit_hash,
            commit_msg=commit_msg,
            author=author,
            date=date,
            code_snippet=code_snippet,
            embedding=embedding,
            record_id=record_id,
        )

    def search_history(
        self,
        query: str,
        file_filter: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        embedding = self.embedder.embed(query)
        filter_expr = None
        if file_filter:
            escaped = file_filter.replace("\\", "\\\\").replace('"', '\\"')
            filter_expr = f'file_path == "{escaped}"'
        return self.store.search("git_history", embedding, top_k, filter_expr=filter_expr)


# ------------------------------------------------------------------- helpers

def _convention_search_text(
    module: str, title: str, content: str, tags: list[str]
) -> str:
    parts = [f"module: {module}", f"title: {title}"]
    if tags:
        parts.append(f"tags: {', '.join(tags)}")
    parts.append(content)
    return "\n".join(parts)


def _compile_session_summary(
    task: str,
    files_modified: str,
    decisions: str,
    assumptions: str,
    problems: str,
    summary: str,
    created_at: str,
) -> str:
    sections = [
        f"Task: {task}",
        f"Started: {created_at}",
        f"Files changed: {files_modified}",
        f"Decisions: {decisions}",
        f"Problems solved: {problems}",
        f"Assumptions: {assumptions}",
    ]
    if summary:
        sections.append(f"Summary: {summary}")
    return "\n\n".join(sections)


def _git_embedding_text(
    commit_msg: str, file_path: str, author: str, date: str, code_snippet: str
) -> str:
    return "\n".join([commit_msg, file_path, author, date, code_snippet])
