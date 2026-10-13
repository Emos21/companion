"""Text embeddings for retrieval.

Uses BAAI/bge-small-en-v1.5 (384-dim, normalized) via fastembed - a light, ONNX
model that runs on a free-tier box and needs no embedding API or key. The embedder
is behind a tiny interface so it can be swapped for a hosted model (Voyage, OpenAI)
by changing one class, without touching the retrieval code.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedEmbedder:
    """bge-small-en-v1.5 via fastembed. Vectors come back L2-normalized."""

    dim = 384

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding  # imported lazily so tests can skip it

        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vec] for vec in self._model.embed(list(texts))]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return FastEmbedEmbedder()
