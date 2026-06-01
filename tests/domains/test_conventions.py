"""Tests for conventions domain logic layer (no MCP needed)."""

import pytest

from codebrain.core.repository import Repository
from codebrain.domains.conventions import logic


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
