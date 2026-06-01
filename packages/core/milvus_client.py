"""Milvus Lite client wrapper for Codebase Brain collections."""

from __future__ import annotations

from datetime import UTC, datetime
from math import log
import re
from typing import Any, Iterable
from uuid import uuid4

from .config import Config
from .embedder import Embedder


class MilvusClient:
    """Manage Codebase Brain collections in embedded Milvus Lite."""

    VECTOR_FIELD = "embedding"
    DIMENSION = Embedder.DIMENSION

    CONVENTIONS = "conventions"
    SESSION_MEMORY = "session_memory"
    GIT_HISTORY = "git_history"

    def __init__(self, config: Config | None = None) -> None:
        """Connect to Milvus Lite using the configured database path."""
        self.config = config or Config()
        self.config.ensure_data_dirs()
        self._client: Any | None = None
        self._data_type: Any | None = None
        self._connect()

    def _connect(self) -> None:
        """Create the underlying pymilvus client with retries for Windows."""
        try:
            from pymilvus import DataType
            from pymilvus import MilvusClient as PyMilvusClient
        except ImportError as exc:
            raise RuntimeError(
                "pymilvus is required for vector storage. "
                "Install project dependencies before using MilvusClient."
            ) from exc

        import time
        last_exc = None
        for attempt in range(3):
            try:
                self._client = PyMilvusClient(uri=self.config.milvus_uri)
                self._data_type = DataType
                return  # success
            except NotImplementedError:
                # Milvus Lite 3.0 on Windows: non-fatal gRPC noise, retry
                time.sleep(1 + attempt)
            except Exception as exc:
                last_exc = exc
                if "lock" in str(exc).lower() or "permission" in str(exc).lower():
                    # Another process is using the DB, wait and retry
                    time.sleep(2)
                else:
                    raise RuntimeError(
                        f"Failed to connect to Milvus Lite at {self.config.milvus_uri!r}."
                    ) from exc

        if last_exc:
            raise RuntimeError(
                f"Failed to connect to Milvus Lite after 3 attempts at {self.config.milvus_uri!r}."
            ) from last_exc

    @property
    def client(self) -> Any:
        """Return the underlying pymilvus client."""
        if self._client is None:
            raise RuntimeError("Milvus client is not connected.")
        return self._client

    @property
    def data_type(self) -> Any:
        """Return pymilvus DataType after connection."""
        if self._data_type is None:
            raise RuntimeError("Milvus data types are not available.")
        return self._data_type

    def init_collections(self) -> None:
        """Create and load all Codebase Brain collections if needed."""
        self._ensure_collection(
            self.CONVENTIONS,
            [
                ("id", self.data_type.VARCHAR, {"is_primary": True, "max_length": 128}),
                ("module", self.data_type.VARCHAR, {"max_length": 512}),
                ("title", self.data_type.VARCHAR, {"max_length": 1024}),
                ("content", self.data_type.VARCHAR, {"max_length": 65535}),
                ("embedding", self.data_type.FLOAT_VECTOR, {"dim": self.DIMENSION}),
                ("created_at", self.data_type.VARCHAR, {"max_length": 64}),
            ],
        )
        self._ensure_collection(
            self.SESSION_MEMORY,
            [
                ("id", self.data_type.VARCHAR, {"is_primary": True, "max_length": 128}),
                ("task", self.data_type.VARCHAR, {"max_length": 8192}),
                ("files_modified", self.data_type.VARCHAR, {"max_length": 65535}),
                ("decisions", self.data_type.VARCHAR, {"max_length": 65535}),
                ("assumptions", self.data_type.VARCHAR, {"max_length": 65535}),
                ("problems", self.data_type.VARCHAR, {"max_length": 65535}),
                ("embedding", self.data_type.FLOAT_VECTOR, {"dim": self.DIMENSION}),
                ("created_at", self.data_type.VARCHAR, {"max_length": 64}),
            ],
        )
        self._ensure_collection(
            self.GIT_HISTORY,
            [
                ("id", self.data_type.VARCHAR, {"is_primary": True, "max_length": 128}),
                ("file_path", self.data_type.VARCHAR, {"max_length": 4096}),
                ("commit_hash", self.data_type.VARCHAR, {"max_length": 128}),
                ("commit_msg", self.data_type.VARCHAR, {"max_length": 8192}),
                ("author", self.data_type.VARCHAR, {"max_length": 1024}),
                ("date", self.data_type.VARCHAR, {"max_length": 128}),
                ("code_snippet", self.data_type.VARCHAR, {"max_length": 65535}),
                ("embedding", self.data_type.FLOAT_VECTOR, {"dim": self.DIMENSION}),
            ],
        )

    def _ensure_collection(self, name: str, fields: list[tuple[str, Any, dict[str, Any]]]) -> None:
        """Create a collection with an embedding index when it does not exist."""
        try:
            if self.client.has_collection(name):
                self.client.load_collection(name)
                return

            schema = self.client.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            for field_name, data_type, kwargs in fields:
                schema.add_field(
                    field_name=field_name,
                    datatype=data_type,
                    **kwargs,
                )

            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name=self.VECTOR_FIELD,
                metric_type="COSINE",
                index_type="AUTOINDEX",
            )
            self.client.create_collection(
                collection_name=name,
                schema=schema,
                index_params=index_params,
            )
            self.client.load_collection(name)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Milvus collection {name!r}.") from exc

    def insert_convention(
        self,
        module: str,
        title: str,
        content: str,
        embedding: list[float],
        *,
        id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        """Insert one convention record and return its ID."""
        record_id = id or self._new_id()
        self._insert(
            self.CONVENTIONS,
            {
                "id": record_id,
                "module": module,
                "title": title,
                "content": content,
                "embedding": self._validate_embedding(embedding),
                "created_at": created_at or self._now(),
            },
        )
        return record_id

    def insert_session(
        self,
        task: str,
        files_modified: str | list[str],
        decisions: str,
        assumptions: str,
        problems: str,
        embedding: list[float],
        *,
        id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        """Insert one session memory record and return its ID."""
        record_id = id or self._new_id()
        self._insert(
            self.SESSION_MEMORY,
            {
                "id": record_id,
                "task": task,
                "files_modified": self._join(files_modified),
                "decisions": decisions,
                "assumptions": assumptions,
                "problems": problems,
                "embedding": self._validate_embedding(embedding),
                "created_at": created_at or self._now(),
            },
        )
        return record_id

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
        id: str | None = None,
    ) -> str:
        """Insert one git history record and return its ID."""
        record_id = id or self._new_id()
        self._insert(
            self.GIT_HISTORY,
            {
                "id": record_id,
                "file_path": file_path,
                "commit_hash": commit_hash,
                "commit_msg": commit_msg,
                "author": author,
                "date": date,
                "code_snippet": code_snippet,
                "embedding": self._validate_embedding(embedding),
            },
        )
        return record_id

    def search_conventions(
        self,
        embedding: list[float],
        top_k: int = 5,
        *,
        module_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search conventions by embedding similarity."""
        filter_expr = self._eq_filter("module", module_filter) if module_filter else None
        return self._search(
            self.CONVENTIONS,
            embedding,
            top_k,
            ["id", "module", "title", "content", "created_at"],
            filter_expr=filter_expr,
        )

    def search_sessions(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Search session memories by embedding similarity."""
        return self._search(
            self.SESSION_MEMORY,
            embedding,
            top_k,
            ["id", "task", "files_modified", "decisions", "assumptions", "problems", "created_at"],
        )

    def search_history(self, embedding: list[float], top_k: int = 10) -> list[dict[str, Any]]:
        """Search git history by embedding similarity."""
        return self._search(
            self.GIT_HISTORY,
            embedding,
            top_k,
            ["id", "file_path", "commit_hash", "commit_msg", "author", "date", "code_snippet"],
        )

    def hybrid_search(
        self,
        collection: str,
        query_text: str,
        embedding: list[float],
        top_k: int,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search with dense vectors plus keyword re-ranking fallback.

        Milvus Lite deployments may not expose BM25 sparse hybrid search. This
        method first attempts native hybrid search when available, then falls
        back to dense vector retrieval plus Python-side keyword ranking and RRF.
        """
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")
        fields = self._collection_output_fields(collection)
        native = self._try_native_hybrid_search(
            collection,
            query_text,
            embedding,
            top_k,
            fields,
            filter_expr,
        )
        if native is not None:
            return native

        dense_results = self._search(
            collection,
            embedding,
            top_k * 2,
            fields,
            filter_expr=filter_expr,
        )
        keyword_results = self._keyword_rank(
            collection,
            query_text,
            fields,
            limit=max(top_k * 10, 50),
            filter_expr=filter_expr,
        )
        return self._rrf_merge(dense_results, keyword_results, top_k)

    def list_conventions(self, module: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        """List convention metadata, optionally filtered by module."""
        filter_expr = self._eq_filter("module", module) if module else ""
        try:
            return self.client.query(
                collection_name=self.CONVENTIONS,
                filter=filter_expr,
                output_fields=["id", "module", "title", "created_at"],
                limit=limit,
            )
        except Exception as exc:
            raise RuntimeError("Failed to list conventions.") from exc

    def _try_native_hybrid_search(
        self,
        collection: str,
        query_text: str,
        embedding: list[float],
        top_k: int,
        output_fields: list[str],
        filter_expr: str | None,
    ) -> list[dict[str, Any]] | None:
        """Attempt native Milvus hybrid search when sparse BM25 support exists."""
        if not hasattr(self.client, "hybrid_search"):
            return None
        try:
            from pymilvus import AnnSearchRequest, RRFRanker

            dense_request = AnnSearchRequest(
                data=[self._validate_embedding(embedding)],
                anns_field=self.VECTOR_FIELD,
                param={"metric_type": "COSINE"},
                limit=top_k,
                expr=filter_expr,
            )
            sparse_request = AnnSearchRequest(
                data=[query_text],
                anns_field="sparse",
                param={"metric_type": "BM25"},
                limit=top_k,
                expr=filter_expr,
            )
            results = self.client.hybrid_search(
                collection_name=collection,
                reqs=[dense_request, sparse_request],
                ranker=RRFRanker(),
                limit=top_k,
                output_fields=output_fields,
            )
        except Exception:
            return None
        return [self._normalize_hit(hit) for hit in results[0]] if results else []

    def _insert(self, collection_name: str, record: dict[str, Any]) -> None:
        """Insert a single record into a collection."""
        try:
            self.client.insert(collection_name=collection_name, data=[record])
        except Exception as exc:
            raise RuntimeError(f"Failed to insert into {collection_name!r}.") from exc

    def _search(
        self,
        collection_name: str,
        embedding: list[float],
        top_k: int,
        output_fields: list[str],
        *,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run a vector search and normalize pymilvus result rows."""
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")
        vector = self._validate_embedding(embedding)
        try:
            results = self.client.search(
                collection_name=collection_name,
                data=[vector],
                anns_field=self.VECTOR_FIELD,
                search_params={"metric_type": "COSINE"},
                limit=top_k,
                output_fields=output_fields,
                filter=filter_expr,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to search {collection_name!r}.") from exc

        return [self._normalize_hit(hit) for hit in results[0]] if results else []

    def _keyword_rank(
        self,
        collection: str,
        query_text: str,
        output_fields: list[str],
        *,
        limit: int,
        filter_expr: str | None,
    ) -> list[dict[str, Any]]:
        """Rank rows by simple BM25-style token overlap."""
        tokens = self._tokens(query_text)
        if not tokens:
            return []
        try:
            rows = self.client.query(
                collection_name=collection,
                filter=filter_expr or "",
                output_fields=output_fields,
                limit=limit,
            )
        except Exception:
            return []

        documents = [self._document_text(row) for row in rows]
        doc_count = max(len(documents), 1)
        doc_freq: dict[str, int] = {}
        for document in documents:
            unique_tokens = set(self._tokens(document))
            for token in tokens:
                if token in unique_tokens:
                    doc_freq[token] = doc_freq.get(token, 0) + 1

        scored: list[tuple[float, dict[str, Any]]] = []
        for row, document in zip(rows, documents, strict=True):
            doc_tokens = self._tokens(document)
            if not doc_tokens:
                continue
            score = 0.0
            for token in tokens:
                term_frequency = doc_tokens.count(token)
                if term_frequency == 0:
                    continue
                inverse_doc_frequency = log(
                    1 + (doc_count - doc_freq.get(token, 0) + 0.5)
                    / (doc_freq.get(token, 0) + 0.5)
                )
                score += term_frequency * inverse_doc_frequency
            if score > 0:
                scored.append((score, {**row, "similarity": score}))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored]

    def _rrf_merge(
        self,
        dense_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Merge dense and keyword rankings with Reciprocal Rank Fusion."""
        rrf_k = 60
        merged: dict[str, dict[str, Any]] = {}
        scores: dict[str, float] = {}

        for result_set in (dense_results, keyword_results):
            for rank, result in enumerate(result_set, start=1):
                result_id = str(result.get("id", ""))
                if not result_id:
                    continue
                merged.setdefault(result_id, result)
                scores[result_id] = scores.get(result_id, 0.0) + 1.0 / (rrf_k + rank)

        ranked_ids = sorted(scores, key=scores.__getitem__, reverse=True)
        return [
            {**merged[result_id], "similarity": scores[result_id]}
            for result_id in ranked_ids[:top_k]
        ]

    def _normalize_hit(self, hit: Any) -> dict[str, Any]:
        """Convert a pymilvus search hit into a plain dictionary."""
        if isinstance(hit, dict):
            entity = hit.get("entity", {})
            score = hit.get("distance", hit.get("score"))
            return {**entity, "similarity": score}

        entity = getattr(hit, "entity", {}) or {}
        if hasattr(entity, "to_dict"):
            entity = entity.to_dict()
        score = getattr(hit, "distance", getattr(hit, "score", None))
        return {**dict(entity), "similarity": score}

    def _validate_embedding(self, embedding: list[float]) -> list[float]:
        """Validate and coerce an embedding vector."""
        if len(embedding) != self.DIMENSION:
            raise ValueError(f"embedding must have {self.DIMENSION} dimensions")
        return [float(value) for value in embedding]

    def _eq_filter(self, field: str, value: str) -> str:
        """Build a simple equality filter with escaped string content."""
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'{field} == "{escaped}"'

    def _collection_output_fields(self, collection: str) -> list[str]:
        """Return output fields for a known collection."""
        fields = {
            self.CONVENTIONS: ["id", "module", "title", "content", "created_at"],
            self.SESSION_MEMORY: [
                "id",
                "task",
                "files_modified",
                "decisions",
                "assumptions",
                "problems",
                "created_at",
            ],
            self.GIT_HISTORY: [
                "id",
                "file_path",
                "commit_hash",
                "commit_msg",
                "author",
                "date",
                "code_snippet",
            ],
        }
        if collection not in fields:
            raise ValueError(f"Unknown collection {collection!r}")
        return fields[collection]

    def _document_text(self, row: dict[str, Any]) -> str:
        """Join searchable string fields from a row."""
        return "\n".join(
            str(value)
            for key, value in row.items()
            if key != "id" and isinstance(value, str)
        )

    def _tokens(self, text: str) -> list[str]:
        """Tokenize text for keyword fallback ranking."""
        return re.findall(r"[A-Za-z0-9_]+", text.lower())

    def _join(self, values: str | Iterable[str]) -> str:
        """Serialize string lists using newline separation."""
        if isinstance(values, str):
            return values
        return "\n".join(values)

    def _new_id(self) -> str:
        """Return a unique record ID."""
        return uuid4().hex

    def _now(self) -> str:
        """Return the current UTC timestamp."""
        return datetime.now(UTC).isoformat()
