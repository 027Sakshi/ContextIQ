from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(DEFAULT_MODEL)


def _lexical_scores(query: str, documents: Sequence[str]) -> np.ndarray:
    if not documents:
        return np.array([], dtype=float)
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=12000, ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(list(documents))
        query_vector = vectorizer.transform([query])
        return cosine_similarity(query_vector, matrix)[0]
    except ValueError:
        return np.zeros(len(documents), dtype=float)


def hybrid_scores(query: str, documents: Sequence[str]) -> tuple[np.ndarray, str]:
    """Return semantic+lexical relevance scores with a zero-cost local fallback."""
    if not documents:
        return np.array([], dtype=float), "none"

    lexical = _lexical_scores(query, documents)
    try:
        model = _load_model()
        vectors = model.encode(
            [query, *documents],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        semantic = np.asarray(vectors[1:]) @ np.asarray(vectors[0])
        # Semantic meaning is primary; TF-IDF helps exact names/amounts/keywords.
        scores = (0.78 * semantic) + (0.22 * lexical)
        return np.asarray(scores, dtype=float), DEFAULT_MODEL
    except Exception:
        return lexical, "tfidf-fallback"
