"""Ollama embedder request-boundary tests."""

from __future__ import annotations

import httpx
import pytest

from codebrain.config import Settings
from codebrain.infrastructure.embedder.ollama import OllamaEmbedder


class FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_embed_batch_chunks_large_requests(monkeypatch) -> None:
    requests: list[list[str]] = []

    def post(url, *, json, timeout):
        batch = json["input"]
        requests.append(batch)
        return FakeResponse({"embeddings": [[float(len(text))] for text in batch]})

    monkeypatch.setattr(httpx, "post", post)
    embedder = OllamaEmbedder(Settings(ollama_batch_size=2))

    result = embedder.embed_batch(["one", "two", "three", "four", "five"])

    assert [len(batch) for batch in requests] == [2, 2, 1]
    assert result == [[3.0], [3.0], [5.0], [4.0], [4.0]]


def test_embed_batch_rejects_mismatched_response_count(monkeypatch) -> None:
    monkeypatch.setattr(
        httpx, "post", lambda *args, **kwargs: FakeResponse({"embeddings": []})
    )
    embedder = OllamaEmbedder(Settings(ollama_batch_size=2))

    with pytest.raises(RuntimeError, match="count did not match"):
        embedder.embed_batch(["one"])


def test_embed_batch_rejects_non_object_response(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse([]))
    embedder = OllamaEmbedder(Settings())

    with pytest.raises(RuntimeError, match="not a JSON object"):
        embedder.embed_batch(["one"])
