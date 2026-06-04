"""Tests for the vector store."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from codebrain.core.vector_store import SqliteVectorStore, _cosine_similarity


class TestSqliteVectorStore:
    """Contract tests for SqliteVectorStore."""

    @pytest.fixture
    def store(self, temp_db_path: str) -> SqliteVectorStore:
        s = SqliteVectorStore(db_path=temp_db_path, dimension=4)
        yield s
        s.close()

    def test_insert_and_count(self, store: SqliteVectorStore) -> None:
        assert store.count("conventions") == 0
        store.insert("conventions", [[1.0, 0.0, 0.0, 0.0]], ["id1"], [{"title": "T"}])
        assert store.count("conventions") == 1

    def test_search_returns_results(self, store: SqliteVectorStore) -> None:
        store.insert("conventions", [[1.0, 0.0, 0.0, 0.0]], ["id1"], [{"title": "T"}])
        results = store.search("conventions", [1.0, 0.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0]["id"] == "id1"
        assert "similarity" in results[0]

    def test_delete_removes_entry(self, store: SqliteVectorStore) -> None:
        store.insert("conventions", [[1.0, 0.0, 0.0, 0.0]], ["id1"])
        store.delete("conventions", ["id1"])
        assert store.count("conventions") == 0

    def test_query_with_filter(self, store: SqliteVectorStore) -> None:
        store.insert(
            "conventions",
            [[1.0, 0.0, 0.0, 0.0]],
            ["id1"],
            [{"module": "foo", "title": "T"}],
        )
        results = store.query("conventions", filter_expr='module == "foo"')
        assert len(results) == 1
        assert results[0]["module"] == "foo"

    def test_insert_convention_domain_helper(self, store: SqliteVectorStore) -> None:
        rid = store.insert_convention("mod", "Title", "Content", [1.0, 0.0, 0.0, 0.0])
        assert len(rid) > 0
        assert store.count("conventions") == 1

    def test_insert_session_domain_helper(self, store: SqliteVectorStore) -> None:
        rid = store.insert_session("task", "[]", "[]", "", "[]", [1.0, 0.0, 0.0, 0.0])
        assert len(rid) > 0
        assert store.count("session_memory") == 1

    def test_insert_git_entry_domain_helper(self, store: SqliteVectorStore) -> None:
        rid = store.insert_git_entry("f.py", "abc", "msg", "author", "date", "code", [1.0, 0.0, 0.0, 0.0])
        assert len(rid) > 0
        assert store.count("git_history") == 1


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_concurrent_store_initialization_avoids_database_locked(temp_db_path: str) -> None:
    def create_and_close(_: int) -> None:
        store = SqliteVectorStore(temp_db_path, dimension=4)
        store.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(create_and_close, range(2)))
