"""MCP server for storing and searching project conventions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from core.mcp_base import BrainMCP
from core.milvus_client import MilvusClient


DEFAULT_CONVENTIONS_PATH = Path("~/.codebrain/conventions")
DEFAULT_SYNC_TRIGGER = Path("~/.codebrain/.sync-trigger")


@dataclass(frozen=True)
class ConventionFile:
    """Parsed convention markdown file."""

    module: str
    title: str
    tags: list[str]
    content: str
    path: Path


class ConventionsMCP(BrainMCP):
    """FastMCP server exposing convention memory tools."""

    def __init__(self) -> None:
        super().__init__("conventions-mcp")
        self._register_tools()
        self.watch_sync_trigger(
            lambda: self.index_convention_files(),
            trigger_path=DEFAULT_SYNC_TRIGGER,
            debounce_seconds=2.0,
        )

    def _register_tools(self) -> None:
        """Register convention MCP tools."""
        self.tool()(self.add_convention)
        self.tool()(self.search_conventions)
        self.tool()(self.list_conventions)
        self.tool()(self.index_convention_files)

    def add_convention(self, module: str, title: str, content: str) -> dict[str, Any]:
        """Add one convention directly to the conventions collection."""
        module = _require_text(module, "module")
        title = _require_text(title, "title")
        content = _require_text(content, "content")
        embedding = self.get_embedder().embed(_searchable_text(module, title, content, []))
        record_id = self.get_milvus().insert_convention(
            module=module,
            title=title,
            content=content,
            embedding=embedding,
        )
        return {"ok": True, "id": record_id, "module": module, "title": title}

    def search_conventions(
        self,
        query: str,
        keywords: str | list[str] | None = None,
        module_filter: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search conventions with dense retrieval plus BM25/RRF hybrid ranking."""
        query = _require_text(query, "query")
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")

        keyword_text = _keywords_to_text(keywords)
        hybrid_query = " ".join(part for part in (query, keyword_text) if part)
        embedding = self.get_embedder().embed(query)
        filter_expr = _module_filter(module_filter)
        return self.get_milvus().hybrid_search(
            MilvusClient.CONVENTIONS,
            hybrid_query,
            embedding,
            top_k,
            filter_expr=filter_expr,
        )

    def list_conventions(self, module: str | None = None) -> list[dict[str, Any]]:
        """List convention metadata, optionally filtered by module."""
        return self.get_milvus().list_conventions(module=module)

    def index_convention_files(self, path: str | None = None) -> dict[str, Any]:
        """Index markdown convention files with YAML frontmatter."""
        root = Path(path).expanduser() if path else DEFAULT_CONVENTIONS_PATH.expanduser()
        if not root.exists():
            return {
                "ok": True,
                "path": str(root),
                "indexed": 0,
                "skipped": 0,
                "errors": [],
            }
        if not root.is_dir():
            raise ValueError(f"path must be a directory: {root}")

        indexed = 0
        skipped = 0
        errors: list[dict[str, str]] = []
        for file_path in sorted(root.rglob("*.md")):
            try:
                convention = _parse_convention_file(file_path)
                self._upsert_convention_file(convention)
                indexed += 1
            except ValueError as exc:
                skipped += 1
                errors.append({"path": str(file_path), "error": str(exc)})

        return {
            "ok": True,
            "path": str(root),
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors,
        }

    def _upsert_convention_file(self, convention: ConventionFile) -> None:
        """Store one convention file using a stable path-derived ID."""
        milvus = self.get_milvus()
        record_id = _file_record_id(convention.path)
        embedding = self.get_embedder().embed(
            _searchable_text(
                convention.module,
                convention.title,
                convention.content,
                convention.tags,
            )
        )
        try:
            milvus.client.delete(
                collection_name=MilvusClient.CONVENTIONS,
                filter=f'id == "{record_id}"',
            )
        except Exception:
            self.logger.debug("No existing convention row to delete for %s", record_id)
        milvus.insert_convention(
            module=convention.module,
            title=convention.title,
            content=convention.content,
            embedding=embedding,
            id=record_id,
        )


def create_server() -> ConventionsMCP:
    """Create a conventions MCP server instance."""
    return ConventionsMCP()


def _parse_convention_file(path: Path) -> ConventionFile:
    """Parse a markdown convention file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    try:
        _, frontmatter, content = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("invalid YAML frontmatter") from exc

    metadata = yaml.safe_load(frontmatter) or {}
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a YAML mapping")

    module = _metadata_text(metadata, "module")
    title = _metadata_text(metadata, "title")
    tags = _metadata_tags(metadata.get("tags"))
    content = content.strip()
    if not content:
        raise ValueError("content is required")

    return ConventionFile(
        module=module,
        title=title,
        tags=tags,
        content=content,
        path=path,
    )


def _metadata_text(metadata: dict[Any, Any], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"frontmatter field {key!r} is required")
    return value.strip()


def _metadata_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("frontmatter field 'tags' must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _require_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _keywords_to_text(keywords: str | list[str] | None) -> str:
    if keywords is None:
        return ""
    if isinstance(keywords, str):
        return keywords.strip()
    if isinstance(keywords, list) and all(isinstance(item, str) for item in keywords):
        return " ".join(item.strip() for item in keywords if item.strip())
    raise TypeError("keywords must be a string, a list of strings, or None")


def _module_filter(module_filter: str | None) -> str | None:
    if module_filter is None or not module_filter.strip():
        return None
    escaped = module_filter.strip().replace("\\", "\\\\").replace('"', '\\"')
    return f'module == "{escaped}"'


def _searchable_text(module: str, title: str, content: str, tags: list[str]) -> str:
    parts = [f"module: {module}", f"title: {title}"]
    if tags:
        parts.append(f"tags: {', '.join(tags)}")
    parts.append(content)
    return "\n".join(parts)


def _file_record_id(path: Path) -> str:
    digest = sha256(str(path.expanduser().resolve()).encode("utf-8")).hexdigest()
    return f"convention-file-{digest[:48]}"


server = create_server()
mcp = server.mcp


if __name__ == "__main__":
    server.run()
