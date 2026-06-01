"""Conventions domain — pure business logic, no MCP dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from codebrain.core.repository import Repository


# ----------------------------------------------------------------- Data types

@dataclass(frozen=True)
class ConventionFile:
    """Parsed convention markdown file."""
    module: str
    title: str
    tags: list[str]
    content: str
    path: Path


# ----------------------------------------------------------------- Operations

def add_convention(
    module: str, title: str, content: str, repo: Repository
) -> dict[str, Any]:
    module = _require_text(module, "module")
    title = _require_text(title, "title")
    content = _require_text(content, "content")
    record_id = repo.add_convention(module=module, title=title, content=content)
    return {"ok": True, "id": record_id, "module": module, "title": title}


def search_conventions(
    query: str,
    repo: Repository,
    keywords: str | list[str] | None = None,
    module_filter: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    query = _require_text(query, "query")
    if top_k < 1:
        raise ValueError("top_k must be greater than zero")
    keyword_text = _keywords_to_text(keywords)
    results = repo.search_conventions(
        query=query,
        keywords_text=keyword_text,
        module_filter=module_filter,
        top_k=top_k,
    )
    return results


def list_conventions(
    repo: Repository, module: str | None = None
) -> list[dict[str, Any]]:
    return repo.list_conventions(module=module)


def index_convention_files(
    repo: Repository, path: str | None = None
) -> dict[str, Any]:
    root = Path(path).expanduser() if path else _default_conventions_path()
    if not root.exists():
        return {"ok": True, "path": str(root), "indexed": 0, "skipped": 0, "errors": []}
    if not root.is_dir():
        raise ValueError(f"path must be a directory: {root}")

    indexed = 0
    skipped = 0
    errors: list[dict[str, str]] = []
    for file_path in sorted(root.rglob("*.md")):
        try:
            convention = _parse_convention_file(file_path)
            record_id = _file_record_id(convention.path)
            repo.upsert_convention(
                module=convention.module,
                title=convention.title,
                content=convention.content,
                record_id=record_id,
                tags=convention.tags,
            )
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


# ----------------------------------------------------------------- Helpers

def _default_conventions_path() -> Path:
    return Path(".codebrain/conventions")


def _parse_convention_file(path: Path) -> ConventionFile:
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

    return ConventionFile(module=module, title=title, tags=tags, content=content, path=path)


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


def _file_record_id(path: Path) -> str:
    digest = sha256(str(path.expanduser().resolve()).encode("utf-8")).hexdigest()
    return f"convention-file-{digest[:48]}"
