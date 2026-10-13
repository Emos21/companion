"""Text embeddings for retrieval.

Two interchangeable embedders behind one interface:

- FastEmbedEmbedder: BAAI/bge-small-en-v1.5 (384-dim) via fastembed. Real semantic
  embeddings. The default for local development and the repo.
- HashEmbedder: a dependency-light, deterministic feature-hashing embedder (word +
  character-trigram), 384-dim, no model download and almost no memory. Used on small
  free-tier hosts where loading an ONNX model is too heavy.

get_embedder() picks one from the EMBEDDER env var: "fastembed", "hash", or "auto"
(default) which uses fastembed when it is installed and falls back to hashing. Both
return L2-normalized 384-dim vectors, so the retrieval code never changes.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from functools import lru_cache
from typing import Protocol

import numpy as np

log = logging.getLogger("embeddings")

DIM = 384


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedEmbedder:
    """bge-small-en-v1.5 via fastembed. Vectors come back L2-normalized."""

    dim = DIM

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding  # imported lazily; optional dependency

        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vec] for vec in self._model.embed(list(texts))]


class HashEmbedder:
    """Signed feature hashing over word tokens and character trigrams.

    Deterministic across restarts (hashlib, not Python's salted hash), tiny memory,
    no downloads. Good enough to retrieve over a small curated knowledge base.
    """

    dim = DIM
    _word = re.compile(r"[a-z0-9]+")

    def _features(self, text: str) -> list[str]:
        words = self._word.findall((text or "").lower())
        feats: list[str] = list(words)
        for w in words:
            padded = f"#{w}#"
            for i in range(len(padded) - 2):
                feats.append(padded[i : i + 3])
        return feats

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            for feat in self._features(text):
                digest = hashlib.md5(feat.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dim
                vec[idx] += 1.0 if digest[4] & 1 else -1.0
            norm = float(np.linalg.norm(vec))
            out.append((vec / norm).tolist() if norm else vec.tolist())
        return out


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    pref = os.environ.get("EMBEDDER", "auto").lower()
    if pref == "hash":
        return HashEmbedder()
    try:
        return FastEmbedEmbedder()
    except Exception as exc:  # fastembed not installed or model unavailable
        if pref == "fastembed":
            raise
        log.warning("fastembed unavailable (%s); falling back to HashEmbedder", exc)
        return HashEmbedder()
