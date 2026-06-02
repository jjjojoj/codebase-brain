"""Conventions domain — pure business logic, no MCP dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
from typing import Any

import yaml

from codebrain.core.repository import Repository


_QUALITY_KEYWORDS_ENV = "CODEBRAIN_CONVENTION_QUALITY_KEYWORDS"
_MAX_CONVENTION_WORDS = 500
_BUILTIN_QUALITY_KEYWORDS = {
    "django": [
        "creation_counter",
        "contribute_to_class",
        "from_queryset",
        "_meta",
        "Options",
    ],
    "fastapi": [
        "solve_dependencies",
        "get_flat_dependant",
        "ModelField",
        "lenient_issubclass",
    ],
}


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
        return {
            "ok": True,
            "path": str(root),
            "indexed": 0,
            "skipped": 0,
            "errors": [],
            "warnings": [],
        }
    if not root.is_dir():
        raise ValueError(f"path must be a directory: {root}")

    indexed = 0
    skipped = 0
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, Any]] = []
    for file_path in sorted(root.rglob("*.md")):
        try:
            convention = _parse_convention_file(file_path)
            warnings.extend(_quality_warnings(convention))
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
        "warnings": warnings,
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


def _quality_warnings(convention: ConventionFile) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    content_units = _content_units(convention.content)
    if content_units > _MAX_CONVENTION_WORDS:
        warnings.append({
            "path": str(convention.path),
            "code": "long_content",
            "message": (
                f"Convention content is {content_units} words/chars; keep rules "
                f"under {_MAX_CONVENTION_WORDS} and focused on developer behavior."
            ),
            "limit": _MAX_CONVENTION_WORDS,
            "actual": content_units,
        })

    searchable = f"{convention.module}\n{convention.title}\n{convention.content}"
    for source, keyword in _quality_keywords():
        if _contains_quality_keyword(searchable, keyword):
            warnings.append({
                "path": str(convention.path),
                "code": "internal_keyword",
                "message": (
                    f"Convention mentions internal implementation keyword {keyword!r}; "
                    "make sure this is a developer-facing rule, not framework internals."
                ),
                "keyword": keyword,
                "source": source,
            })
    return warnings


def _content_units(content: str) -> int:
    words = content.split()
    if len(words) > 1:
        return len(words)
    return len("".join(content.split()))


def _quality_keywords() -> list[tuple[str, str]]:
    keywords: list[tuple[str, str]] = []
    for source, values in _BUILTIN_QUALITY_KEYWORDS.items():
        keywords.extend((source, value) for value in values)
    custom_values = os.getenv(_QUALITY_KEYWORDS_ENV, "")
    for value in custom_values.split(","):
        keyword = value.strip()
        if keyword:
            keywords.append(("custom", keyword))
    return keywords


def _contains_quality_keyword(text: str, keyword: str) -> bool:
    flags = 0 if any(char.isupper() for char in keyword) else re.IGNORECASE
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(keyword)}(?![A-Za-z0-9_])"
    return re.search(pattern, text, flags=flags) is not None
