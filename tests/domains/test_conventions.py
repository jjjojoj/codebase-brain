"""Tests for conventions domain logic layer (no MCP needed)."""

import pytest

from codebrain.core.repository import Repository
from codebrain.domains.conventions import logic


def _write_convention(path, *, module: str, title: str, content: str) -> None:
    path.write_text(
        f"---\nmodule: {module}\ntitle: {title}\ntags: []\n---\n\n{content}\n",
        encoding="utf-8",
    )


def test_add_convention(repository: Repository) -> None:
    """Adding a convention should return ok with an ID."""
    result = logic.add_convention(
        module="test-module",
        title="Test Title",
        content="This is test content.",
        repo=repository,
    )
    assert result["ok"] is True
    assert result["module"] == "test-module"
    assert result["title"] == "Test Title"
    assert "id" in result
    assert len(result["id"]) > 0


def test_list_conventions_empty(repository: Repository) -> None:
    """Listing conventions on empty store should return empty list."""
    results = logic.list_conventions(repository)
    assert results == []


def test_list_conventions_after_add(repository: Repository) -> None:
    """After adding, listing should show the convention."""
    logic.add_convention(
        module="test-module",
        title="Test Title",
        content="Test content.",
        repo=repository,
    )
    results = logic.list_conventions(repository)
    assert len(results) == 1
    assert results[0]["module"] == "test-module"
    assert results[0]["title"] == "Test Title"


def test_search_conventions(repository: Repository) -> None:
    """Searching should find relevant conventions."""
    logic.add_convention(
        module="python", title="Code Style", content="Use snake_case",
        repo=repository,
    )
    logic.add_convention(
        module="python", title="Testing", content="Use pytest for all tests",
        repo=repository,
    )
    results = logic.search_conventions("snake_case naming", repository, top_k=2)
    assert len(results) >= 1
    # First result should be about code style
    assert "snake_case" in results[0].get("content", "")


def test_add_convention_empty_module(repository: Repository) -> None:
    """Empty module should raise ValueError."""
    with pytest.raises(ValueError, match="module is required"):
        logic.add_convention(module=" ", title="T", content="C", repo=repository)


def test_add_convention_empty_title(repository: Repository) -> None:
    """Empty title should raise ValueError."""
    with pytest.raises(ValueError, match="title is required"):
        logic.add_convention(module="M", title="", content="C", repo=repository)


def test_list_conventions_filtered(repository: Repository) -> None:
    """Filtering by module should work."""
    logic.add_convention(module="foo", title="A", content="c", repo=repository)
    logic.add_convention(module="bar", title="B", content="c", repo=repository)
    foo_results = logic.list_conventions(repository, module="foo")
    assert len(foo_results) == 1
    assert foo_results[0]["module"] == "foo"


def test_search_top_k_validation(repository: Repository) -> None:
    """top_k < 1 should raise ValueError."""
    with pytest.raises(ValueError, match="top_k"):
        logic.search_conventions("query", repository, top_k=0)


def test_index_convention_files_warns_about_low_signal_content(
    tmp_path,
    repository: Repository,
) -> None:
    """Quality warnings should not prevent convention indexing."""
    conventions_dir = tmp_path / "conventions"
    conventions_dir.mkdir()
    _write_convention(
        conventions_dir / "long.md",
        module="docs",
        title="Verbose rule",
        content=" ".join(["keep rule actionable"] * 180),
    )
    _write_convention(
        conventions_dir / "django.md",
        module="django",
        title="Django internals",
        content="Avoid turning creation_counter or contribute_to_class internals into rules.",
    )
    _write_convention(
        conventions_dir / "fastapi.md",
        module="fastapi",
        title="FastAPI internals",
        content="Do not write solve_dependencies or get_flat_dependant as app conventions.",
    )

    result = logic.index_convention_files(repository, str(conventions_dir))

    assert result["indexed"] == 3
    assert result["skipped"] == 0
    assert result["errors"] == []
    warnings = result["warnings"]
    assert any(warning["code"] == "long_content" for warning in warnings)
    assert any(warning.get("keyword") == "creation_counter" for warning in warnings)
    assert any(warning.get("keyword") == "solve_dependencies" for warning in warnings)


def test_index_convention_files_uses_env_quality_keywords(
    monkeypatch,
    tmp_path,
    repository: Repository,
) -> None:
    monkeypatch.setenv("CODEBRAIN_CONVENTION_QUALITY_KEYWORDS", "fixture_magic, MetaHook")
    conventions_dir = tmp_path / "conventions"
    conventions_dir.mkdir()
    _write_convention(
        conventions_dir / "pytest.md",
        module="pytest",
        title="Pytest internals",
        content="Do not turn fixture_magic into a team convention.",
    )

    result = logic.index_convention_files(repository, str(conventions_dir))

    assert result["indexed"] == 1
    assert any(warning.get("keyword") == "fixture_magic" for warning in result["warnings"])


def test_index_convention_files_does_not_warn_for_lowercase_options(
    tmp_path,
    repository: Repository,
) -> None:
    conventions_dir = tmp_path / "conventions"
    conventions_dir.mkdir()
    _write_convention(
        conventions_dir / "params.md",
        module="api",
        title="Query options",
        content="Expose only documented query options in public handlers.",
    )

    result = logic.index_convention_files(repository, str(conventions_dir))

    assert result["indexed"] == 1
    assert result["warnings"] == []
