"""SentenceTransformer embedder compatibility tests."""

from __future__ import annotations

from codebrain.config import Settings
from codebrain.infrastructure.embedder.sentence_transformer import SentenceTransformerEmbedder


def test_constructor_and_dimension_do_not_load_model(monkeypatch) -> None:
    def fail_load_model(self: SentenceTransformerEmbedder) -> None:
        raise AssertionError("model should not load before embedding text")

    monkeypatch.setattr(SentenceTransformerEmbedder, "_load_model", fail_load_model)

    embedder = SentenceTransformerEmbedder(Settings())

    assert embedder.dimension() == SentenceTransformerEmbedder.DEFAULT_DIMENSION


def test_empty_batch_does_not_load_model(monkeypatch) -> None:
    def fail_load_model(self: SentenceTransformerEmbedder) -> None:
        raise AssertionError("empty input should not load the model")

    monkeypatch.setattr(SentenceTransformerEmbedder, "_load_model", fail_load_model)
    embedder = SentenceTransformerEmbedder(Settings())

    assert embedder.embed_batch([]) == []


def test_embed_loads_model_on_first_use(monkeypatch) -> None:
    class Encoded:
        def tolist(self) -> list[list[float]]:
            return [[0.1, 0.2, 0.3]]

    class Model:
        def encode(
            self,
            texts: list[str],
            *,
            normalize_embeddings: bool,
            convert_to_numpy: bool,
        ) -> Encoded:
            assert texts == ["hello"]
            assert normalize_embeddings is True
            assert convert_to_numpy is True
            return Encoded()

    def load_model(self: SentenceTransformerEmbedder) -> None:
        self._model = Model()

    monkeypatch.setattr(SentenceTransformerEmbedder, "_load_model", load_model)
    embedder = SentenceTransformerEmbedder(Settings())

    assert embedder.embed("hello") == [0.1, 0.2, 0.3]


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
