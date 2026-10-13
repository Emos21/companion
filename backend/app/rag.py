"""Retrieval over the knowledge base.

A small vector index: embed each document once, embed the query, rank by cosine
similarity. The store is behind an interface so the in-memory index used in dev and
tests can be swapped for Supabase/pgvector in production without changing callers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Hit:
    id: str
    title: str
    text: str
    score: float


def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class MemoryVectorStore:
    """Cosine-similarity search over an in-memory matrix. Fine for a small KB."""

    def __init__(self) -> None:
        self._docs: list[dict] = []
        self._mat: np.ndarray | None = None

    def add(self, docs: list[dict], vectors: list[list[float]]) -> None:
        self._docs = list(docs)
        self._mat = _normalize(np.asarray(vectors, dtype=np.float32))

    def search(self, query_vec: list[float], k: int = 4) -> list[Hit]:
        if self._mat is None or not self._docs:
            return []
        q = np.asarray(query_vec, dtype=np.float32)
        n = np.linalg.norm(q)
        if n:
            q = q / n
        scores = self._mat @ q
        order = np.argsort(-scores)[:k]
        return [
            Hit(self._docs[i]["id"], self._docs[i]["title"], self._docs[i]["text"], float(scores[i]))
            for i in order
        ]


class Retriever:
    """Embeds documents and queries, delegates ranking to a vector store."""

    def __init__(self, embedder, store: MemoryVectorStore | None = None) -> None:
        self.embedder = embedder
        self.store = store or MemoryVectorStore()

    def index(self, docs: list[dict]) -> None:
        texts = [f"{d['title']}. {d['text']}" for d in docs]
        self.store.add(docs, self.embedder.embed(texts))

    def search(self, query: str, k: int = 4) -> list[Hit]:
        qv = self.embedder.embed([query])[0]
        return self.store.search(qv, k=k)
