"""Text embedders. Every embedder returns L2-normalised rows, so a dot product is cosine similarity."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> np.ndarray: ...


def _normalise(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norms == 0, 1, norms)


class SentenceEmbedder:
    """MiniLM sentence embeddings: small (80 MB), CPU-friendly, good at short-text similarity."""

    def __init__(self, model: str = DEFAULT_MODEL):
        from sentence_transformers import SentenceTransformer

        self.name = model.split("/")[-1]
        self._model = SentenceTransformer(model)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=64)


class TfidfEmbedder:
    """Dependency-light fallback: TF-IDF + truncated SVD (LSA), fitted on the texts it is given.

    Useful for tests and machines without PyTorch. Vectors are only comparable
    within one fit, so call `fit` with the whole document before `encode`.
    """

    name = "tfidf-lsa"

    def __init__(self, dims: int = 128):
        self.dims = dims
        self._vec = None
        self._svd = None

    def fit(self, texts: list[str]) -> "TfidfEmbedder":
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, min_df=1)
        x = self._vec.fit_transform(texts)
        k = max(2, min(self.dims, x.shape[0] - 1, x.shape[1] - 1))
        self._svd = TruncatedSVD(n_components=k, random_state=0).fit(x)
        return self

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._vec is None:
            self.fit(texts)
        return _normalise(self._svd.transform(self._vec.transform(texts)))


@lru_cache(maxsize=1)
def _sentence_embedder() -> SentenceEmbedder:
    return SentenceEmbedder()


def get_embedder(kind: str = "auto") -> Embedder:
    """'minilm', 'tfidf', or 'auto' (MiniLM when sentence-transformers is installed)."""
    if kind in ("auto", "minilm"):
        try:
            return _sentence_embedder()
        except ImportError:
            if kind == "minilm":
                raise
    return TfidfEmbedder()  # fresh per document: it is fitted on that document
