"""Vector store abstraction (ABC) and SQLite implementation."""

from __future__ import annotations

import json
import sqlite3
import struct
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


SQLITE_COLLECTIONS = frozenset({"conventions", "session_memory", "git_history"})


def _validate_collection(collection: str) -> str:
    if collection not in SQLITE_COLLECTIONS:
        raise ValueError(f"Unknown vector collection: {collection}")
    return collection


class AbstractVectorStore(ABC):
    """Pluggable vector store backend."""

    @abstractmethod
    def insert(
        self,
        collection: str,
        vectors: list[list[float]],
        ids: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        """Insert vectors with IDs and optional metadata."""

    @abstractmethod
    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search by vector similarity, returns list of metadata dicts with 'similarity'."""

    @abstractmethod
    def delete(self, collection: str, ids: list[str]) -> None:
        """Delete entries by ID."""

    @abstractmethod
    def count(self, collection: str) -> int:
        """Return total entries in a collection."""

    @abstractmethod
    def query(
        self,
        collection: str,
        filter_expr: str | None = None,
        output_fields: list[str] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query entries with optional filter."""

    @abstractmethod
    def close(self) -> None:
        """Release resources."""


def _serialize_vector(vector: list[float]) -> bytes:
    """Serialize a float vector to bytes."""
    return struct.pack(f"{len(vector)}f", *vector)


def _deserialize_vector(data: bytes) -> list[float]:
    """Deserialize bytes back to a float vector."""
    count = len(data) // 4
    return list(struct.unpack(f"{count}f", data))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math

    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SqliteVectorStore(AbstractVectorStore):
    """SQLite-backed vector store using numpy-free brute-force cosine search.

    Each collection is a table with columns: id TEXT PRIMARY KEY, vector BLOB, meta TEXT (JSON).
    No external dependencies beyond the Python stdlib.
    Suitable for moderate data sizes (< 100K vectors).
    """

    def __init__(self, db_path: str | Path, dimension: int = 384) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30,
        )
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._enable_wal()
        self._init_collections()

    def _enable_wal(self) -> None:
        for attempt in range(5):
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
                return
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _init_collections(self) -> None:
        """Create the three domain collections if they don't exist."""
        for coll in SQLITE_COLLECTIONS:
            self._conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {coll} (
                    id TEXT PRIMARY KEY,
                    vector BLOB NOT NULL,
                    meta TEXT NOT NULL DEFAULT '{{}}'
                )"""
            )
        self._conn.commit()

    # ------------------------------------------------------------------ ABC impl

    def insert(
        self,
        collection: str,
        vectors: list[list[float]],
        ids: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        collection = _validate_collection(collection)
        metadata = metadata or [{}] * len(ids)
        rows = [
            (rid, _serialize_vector(vec), json.dumps(meta))
            for rid, vec, meta in zip(ids, vectors, metadata, strict=True)
        ]
        with self._conn:
            self._conn.executemany(
                f"INSERT OR REPLACE INTO {collection} (id, vector, meta) VALUES (?, ?, ?)",
                rows,
            )

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        collection = _validate_collection(collection)
        rows = self._conn.execute(
            f"SELECT id, vector, meta FROM {collection}"
        ).fetchall()

        scored: list[tuple[float, dict[str, Any]]] = []
        for rid, vec_blob, meta_json in rows:
            vector = _deserialize_vector(vec_blob)
            meta = json.loads(meta_json)
            if filter_expr and not self._match_filter(meta, filter_expr):
                continue
            sim = _cosine_similarity(query_vector, vector)
            scored.append((sim, {"id": rid, "similarity": sim, **meta}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def delete(self, collection: str, ids: list[str]) -> None:
        collection = _validate_collection(collection)
        placeholders = ",".join("?" * len(ids))
        with self._conn:
            self._conn.execute(
                f"DELETE FROM {collection} WHERE id IN ({placeholders})", ids
            )

    def count(self, collection: str) -> int:
        collection = _validate_collection(collection)
        row = self._conn.execute(f"SELECT COUNT(*) FROM {collection}").fetchone()
        return row[0] if row else 0

    def query(
        self,
        collection: str,
        filter_expr: str | None = None,
        output_fields: list[str] | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        collection = _validate_collection(collection)
        rows = self._conn.execute(
            f"SELECT id, meta FROM {collection} LIMIT ?", (limit,)
        ).fetchall()

        results: list[dict[str, Any]] = []
        for rid, meta_json in rows:
            meta = json.loads(meta_json)
            if filter_expr and not self._match_filter(meta, filter_expr):
                continue
            entry = {"id": rid, **meta}
            if output_fields:
                entry = {k: entry.get(k) for k in output_fields if k in entry}
            results.append(entry)
        return results

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _match_filter(meta: dict[str, Any], filter_expr: str) -> bool:
        """Simple equality filter: field == "value"."""
        import re

        m = re.match(r'(\w+)\s*==\s*"(.+)"', filter_expr)
        if not m:
            return True  # can't parse, include
        field, value = m.group(1), m.group(2)
        return str(meta.get(field, "")) == value

    # ------------------------------------------------------------------ domain helpers

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _new_id(self) -> str:
        return uuid4().hex

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
        meta = {
            "module": module,
            "title": title,
            "content": content,
            "created_at": created_at or self._now(),
        }
        self.insert("conventions", [embedding], [rid], [meta])
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
        meta = {
            "task": task,
            "files_modified": files_modified,
            "decisions": decisions,
            "assumptions": assumptions,
            "problems": problems,
            "created_at": created_at or self._now(),
        }
        self.insert("session_memory", [embedding], [rid], [meta])
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
        meta = {
            "file_path": file_path,
            "commit_hash": commit_hash,
            "commit_msg": commit_msg,
            "author": author,
            "date": date,
            "code_snippet": code_snippet,
        }
        self.insert("git_history", [embedding], [rid], [meta])
        return rid
