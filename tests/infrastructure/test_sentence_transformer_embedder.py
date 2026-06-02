"""SentenceTransformer embedder compatibility tests."""

from __future__ import annotations

from codebrain.infrastructure.embedder.sentence_transformer import SentenceTransformerEmbedder


def test_dimension_uses_sentence_transformers_5_api() -> None:
    class Model:
        def get_embedding_dimension(self) -> int:
            return 768

    embedder = SentenceTransformerEmbedder.__new__(SentenceTransformerEmbedder)
    embedder._model = Model()

    assert embedder.dimension() == 768


def test_dimension_falls_back_to_deprecated_sentence_transformers_api() -> None:
    class Model:
        def get_embedding_dimension(self) -> int:
            raise AttributeError("old sentence-transformers")

        def get_sentence_embedding_dimension(self) -> int:
            return 384

    embedder = SentenceTransformerEmbedder.__new__(SentenceTransformerEmbedder)
    embedder._model = Model()

    assert embedder.dimension() == 384
