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


@lru_cache(maxsize=8)
def _encode_document_corpus(documents: tuple[str, ...]) -> np.ndarray:
    if not documents:
        return np.empty((0, 384), dtype=np.float32)

    model = _load_model()
    vectors = model.encode(
        list(documents),
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def warm_embedding_model() -> str:
    model = _load_model()
    model.encode(
        ["ContextIQ semantic retrieval warm-up"],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return DEFAULT_MODEL


def _lexical_scores(query: str, documents: Sequence[str]) -> np.ndarray:
    if not documents:
        return np.array([], dtype=float)

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=12000,
            ngram_range=(1, 2),
        )
        matrix = vectorizer.fit_transform(list(documents))
        query_vector = vectorizer.transform([query])
        return cosine_similarity(query_vector, matrix)[0]
    except ValueError:
        return np.zeros(len(documents), dtype=float)


def hybrid_scores(
    query: str,
    documents: Sequence[str],
) -> tuple[np.ndarray, str]:
    if not documents:
        return np.array([], dtype=float), "none"

    document_tuple = tuple(str(item or "") for item in documents)
    lexical = _lexical_scores(query, document_tuple)

    try:
        model = _load_model()
        document_vectors = _encode_document_corpus(document_tuple)
        query_vector = model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )[0]
        semantic = document_vectors @ np.asarray(
            query_vector,
            dtype=np.float32,
        )
        scores = (0.78 * semantic) + (0.22 * lexical)
        return np.asarray(scores, dtype=float), DEFAULT_MODEL
    except Exception:
        return lexical, "tfidf-fallback"
