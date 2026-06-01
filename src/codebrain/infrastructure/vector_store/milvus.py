"""Milvus-backed vector store implementation.

This backend is optional. It imports pymilvus only when selected so the default
SQLite/local setup remains lightweight.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from codebrain.core.vector_store import AbstractVectorStore


class MilvusVectorStore(AbstractVectorStore):
    """Vector store using pymilvus MilvusClient.

    Collection names are prefixed to avoid collisions with existing Milvus data.
    Dynamic fields hold Codebase Brain metadata so repository code can use the
    same metadata shape as the SQLite backend.
    """

    def __init__(
        self,
        uri: str,
        dimension: int = 384,
        *,
        token: str | None = None,
        collection_prefix: str = "codebrain",
        client: Any | None = None,
    ) -> None:
        self.uri = _resolve_local_uri(uri)
        self.dimension = dimension
        self.collection_prefix = _sanitize_collection_name(collection_prefix)
        self.client = client or _build_client(self.uri, token)
        self._ensured: set[str] = set()

    def insert(
        self,
        collection: str,
        vectors: list[list[float]],
        ids: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        if not vectors:
            return
        if len(vectors) != len(ids):
            raise ValueError("vectors and ids must have the same length")
        metadata = metadata or [{} for _ in ids]
        if len(metadata) != len(ids):
            raise ValueError("metadata and ids must have the same length")

        name = self._ensure_collection(collection)
        rows = [
            {"id": rid, "vector": vector, **meta}
            for rid, vector, meta in zip(ids, vectors, metadata, strict=True)
        ]
        self.client.insert(collection_name=name, data=rows)

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        name = self._ensure_collection(collection)
        raw = self.client.search(
            collection_name=name,
            data=[query_vector],
            limit=top_k,
            filter=filter_expr or "",
            output_fields=["*"],
        )
        hits = raw[0] if isinstance(raw, list) and raw else []
        return [_normalize_search_hit(hit) for hit in hits]

    def delete(self, collection: str, ids: list[str]) -> None:
        if not ids:
            return
        name = self._ensure_collection(collection)
        self.client.delete(collection_name=name, ids=ids)

    def count(self, collection: str) -> int:
        name = self._ensure_collection(collection)
        if hasattr(self.client, "get_collection_stats"):
            stats = self.client.get_collection_stats(collection_name=name)
            row_count = stats.get("row_count", 0)
            return int(row_count)
        rows = self.client.query(
            collection_name=name,
            filter="",
            output_fields=["count(*)"],
        )
        if rows:
            return int(rows[0].get("count(*)", 0))
        return 0

    def query(
        self,
        collection: str,
        filter_expr: str | None = None,
        output_fields: list[str] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        name = self._ensure_collection(collection)
        fields = output_fields or ["*"]
        rows = self.client.query(
            collection_name=name,
            filter=filter_expr or "",
            output_fields=fields,
            limit=limit,
        )
        return [_normalize_query_row(row) for row in rows]

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            close()

    def insert_convention(
        self,
        module: str,
        title: str,
        content: str,
        embedding: list[float],
        *,
        record_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        rid = record_id or self._new_id()
        self.insert(
            "conventions",
            [embedding],
            [rid],
            [{
                "module": module,
                "title": title,
                "content": content,
                "created_at": created_at or self._now(),
            }],
        )
        return rid

    def insert_session(
        self,
        task: str,
        files_modified: str,
        decisions: str,
        assumptions: str,
        problems: str,
        embedding: list[float],
        *,
        record_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        rid = record_id or self._new_id()
        self.insert(
            "session_memory",
            [embedding],
            [rid],
            [{
                "task": task,
                "files_modified": files_modified,
                "decisions": decisions,
                "assumptions": assumptions,
                "problems": problems,
                "created_at": created_at or self._now(),
            }],
        )
        return rid

    def insert_git_entry(
        self,
        file_path: str,
        commit_hash: str,
        commit_msg: str,
        author: str,
        date: str,
        code_snippet: str,
        embedding: list[float],
        *,
        record_id: str | None = None,
    ) -> str:
        rid = record_id or self._new_id()
        self.insert(
            "git_history",
            [embedding],
            [rid],
            [{
                "file_path": file_path,
                "commit_hash": commit_hash,
                "commit_msg": commit_msg,
                "author": author,
                "date": date,
                "code_snippet": code_snippet,
            }],
        )
        return rid

    def _ensure_collection(self, collection: str) -> str:
        name = self._collection_name(collection)
        if name in self._ensured:
            return name
        if not _collection_exists(self.client, name):
            self.client.create_collection(
                collection_name=name,
                dimension=self.dimension,
                primary_field_name="id",
                id_type="string",
                max_length=512,
                vector_field_name="vector",
                metric_type="COSINE",
                auto_id=False,
                enable_dynamic_field=True,
            )
        self._ensured.add(name)
        return name

    def _collection_name(self, collection: str) -> str:
        return f"{self.collection_prefix}_{_sanitize_collection_name(collection)}"

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _new_id(self) -> str:
        return uuid4().hex


def _build_client(uri: str, token: str | None) -> Any:
    try:
        from pymilvus import MilvusClient
    except ImportError as exc:
        raise RuntimeError(
            "Milvus backend requires pymilvus. Install with: "
            "pip install -e '.[milvus]' for remote Milvus/Zilliz or "
            "pip install -e '.[milvus-lite]' for local Milvus Lite."
        ) from exc
    kwargs: dict[str, Any] = {"uri": uri}
    if token:
        kwargs["token"] = token
    return MilvusClient(**kwargs)


def _resolve_local_uri(uri: str) -> str:
    if "://" in uri:
        return uri
    path = Path(uri).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path.resolve())


def _collection_exists(client: Any, name: str) -> bool:
    has_collection = getattr(client, "has_collection", None)
    if callable(has_collection):
        return bool(has_collection(collection_name=name))
    list_collections = getattr(client, "list_collections", None)
    if callable(list_collections):
        return name in list_collections()
    return False


def _sanitize_collection_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", value.strip())
    if not sanitized:
        return "codebrain"
    if not re.match(r"[A-Za-z_]", sanitized):
        sanitized = f"c_{sanitized}"
    return sanitized


def _normalize_search_hit(hit: dict[str, Any]) -> dict[str, Any]:
    entity = hit.get("entity") if isinstance(hit.get("entity"), dict) else {}
    rid = hit.get("id") or hit.get("pk") or entity.get("id")
    score = hit.get("distance", hit.get("score", 0.0))
    return {
        "id": rid,
        "similarity": score,
        **_metadata_from_row(entity),
    }


def _normalize_query_row(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": row.get("id"), **_metadata_from_row(row)}


def _metadata_from_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(row)
    metadata.pop("id", None)
    metadata.pop("vector", None)
    metadata.pop("distance", None)
    metadata.pop("score", None)
    metadata.pop("pk", None)
    meta_json = metadata.pop("meta_json", None)
    if isinstance(meta_json, str):
        try:
            parsed = json.loads(meta_json)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            metadata.update(parsed)
    return metadata
