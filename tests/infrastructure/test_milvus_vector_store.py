"""Tests for the optional Milvus vector store backend."""

from __future__ import annotations

from typing import Any

from codebrain.infrastructure.vector_store.milvus import MilvusVectorStore


class FakeMilvusClient:
    def __init__(self) -> None:
        self.collections: dict[str, list[dict[str, Any]]] = {}
        self.created: list[dict[str, Any]] = []
        self.closed = False

    def has_collection(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, **kwargs: Any) -> None:
        self.created.append(kwargs)
        self.collections[kwargs["collection_name"]] = []

    def insert(self, collection_name: str, data: list[dict[str, Any]]) -> None:
        current = self.collections[collection_name]
        by_id = {row["id"]: row for row in current}
        for row in data:
            by_id[row["id"]] = row
        self.collections[collection_name] = list(by_id.values())

    def search(
        self,
        collection_name: str,
        data: list[list[float]],
        limit: int,
        filter: str,
        output_fields: list[str],
    ) -> list[list[dict[str, Any]]]:
        hits = [
            {"id": row["id"], "distance": 0.9, "entity": row}
            for row in self.collections[collection_name][:limit]
        ]
        return [hits]

    def query(
        self,
        collection_name: str,
        filter: str,
        output_fields: list[str],
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        rows = self.collections[collection_name][:limit]
        if output_fields == ["count(*)"]:
            return [{"count(*)": len(rows)}]
        if output_fields == ["*"]:
            return rows
        return [
            {field: row[field] for field in output_fields if field in row}
            for row in rows
        ]

    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        return {"row_count": str(len(self.collections[collection_name]))}

    def delete(self, collection_name: str, ids: list[str]) -> None:
        self.collections[collection_name] = [
            row for row in self.collections[collection_name] if row["id"] not in ids
        ]

    def close(self) -> None:
        self.closed = True


def test_milvus_store_insert_search_query_delete_count() -> None:
    fake = FakeMilvusClient()
    store = MilvusVectorStore(
        uri="/tmp/codebrain-milvus-test.db",
        dimension=4,
        collection_prefix="team-a",
        client=fake,
    )

    store.insert("conventions", [[1.0, 0.0, 0.0, 0.0]], ["id1"], [{"module": "auth"}])
    results = store.search("conventions", [1.0, 0.0, 0.0, 0.0], top_k=1)
    rows = store.query("conventions", output_fields=["*"])

    assert fake.created[0]["collection_name"] == "team_a_conventions"
    assert fake.created[0]["id_type"] == "string"
    assert fake.created[0]["max_length"] == 512
    assert fake.created[0]["enable_dynamic_field"] is True
    assert store.count("conventions") == 1
    assert results[0]["id"] == "id1"
    assert results[0]["module"] == "auth"
    assert rows[0]["module"] == "auth"

    store.delete("conventions", ["id1"])

    assert store.count("conventions") == 0


def test_milvus_store_domain_helpers_and_close() -> None:
    fake = FakeMilvusClient()
    store = MilvusVectorStore(
        uri="/tmp/codebrain-milvus-test.db",
        dimension=4,
        collection_prefix="codebrain",
        client=fake,
    )

    convention_id = store.insert_convention(
        "auth",
        "Errors",
        "Use AuthError",
        [1.0, 0.0, 0.0, 0.0],
    )
    session_id = store.insert_session(
        "task",
        "[]",
        "[]",
        "",
        "[]",
        [1.0, 0.0, 0.0, 0.0],
    )
    git_id = store.insert_git_entry(
        "f.py",
        "abc",
        "msg",
        "author",
        "date",
        "code",
        [1.0, 0.0, 0.0, 0.0],
    )
    assert convention_id
    assert session_id
    assert git_id
    assert store.count("conventions") == 1
    assert store.count("session_memory") == 1
    assert store.count("git_history") == 1

    store.close()

    assert fake.closed is True
