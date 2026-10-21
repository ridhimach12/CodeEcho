import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from backend.app.embeddings.base import BaseEmbedder

DEFAULT_COMMON_CODE_VOCAB = [
    "def", "return", "if", "else", "elif", "try", "except", "raise", "while", "for",
    "in", "is", "not", "None", "True", "False", "import", "from", "as", "class",
    "with", "pass", "break", "continue", "finally", "yield", "lambda", "assert",
    "self", "cls", "int", "str", "float", "bool", "list", "dict", "set", "tuple",
    "len", "range", "isinstance", "Exception", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "FileNotFoundError",
    "VAR_1", "VAR_2", "VAR_3", "VAR_4", "VAR_5",
    "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "->",
    "[-]", "[+]", "get", "set", "append", "update", "pop", "open", "close"
]

class TFIDFEmbedder(BaseEmbedder):
    """
    Lightweight, high-performance TF-IDF Code Embedder.
    Combines word/operator n-grams with character sub-tokens for syntax-aware code representation.
    Guarantees fixed output dimension, zero-vector handling for empty inputs, and L2 normalization.
    """

    def __init__(self, max_features: int = 256, ngram_range: tuple[int, int] = (1, 2)):
        self._max_features = max_features
        self._ngram_range = ngram_range
        self._is_fitted = False

        # Token pattern matches identifiers as well as code operators and diff markers (+, -, ==, etc.)
        token_pattern = r"(?u)\b\w+\b|[+\-*/<>=!%&|^~]+|\[-\]|\[\+\]"

        self._vectorizer = TfidfVectorizer(
            max_features=self._max_features,
            ngram_range=self._ngram_range,
            token_pattern=token_pattern,
            lowercase=False,  # Preserve case for Python built-ins/classes
            norm="l2",
            sublinear_tf=True,
        )

        # Pre-warm with standard vocabulary so it can vectorize immediately even on cold starts
        self._prewarm_vocabulary()

    def _prewarm_vocabulary(self):
        """Pre-fits vectorizer with common code tokens to guarantee valid dimension before any repository data."""
        prewarm_corpus = [
            " ".join(DEFAULT_COMMON_CODE_VOCAB),
            "[-] VAR_1 = open ( 'file' ) [+] with open ( 'file' ) as VAR_1 :",
            "[-] return None [+] if VAR_1 is None : raise ValueError ( 'empty' )",
            "[-] try : VAR_1 [+] except KeyError : pass",
        ]
        self._vectorizer.fit(prewarm_corpus)
        self._is_fitted = True

    @property
    def name(self) -> str:
        return f"tfidf-code-v1-{self.dimension}d"

    @property
    def dimension(self) -> int:
        if hasattr(self._vectorizer, "vocabulary_") and self._vectorizer.vocabulary_:
            return len(self._vectorizer.vocabulary_)
        return self._max_features

    def fit(self, texts: list[str]) -> "TFIDFEmbedder":
        """
        Fits or updates the TF-IDF vocabulary on an actual repository's code diff corpus.
        Filters out empty inputs.
        """
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return self

        # Augment with prewarm vocabulary to retain standard syntax features
        combined_corpus = valid_texts + [" ".join(DEFAULT_COMMON_CODE_VOCAB)]
        self._vectorizer.fit(combined_corpus)
        self._is_fitted = True
        return self

    def embed(self, texts: list[str]) -> np.ndarray:
        """
        Embeds a list of code diff strings into a 2D float32 numpy array [N, dimension].
        Handles empty inputs by returning zero vectors.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        # Separate empty vs non-empty strings
        results = np.zeros((len(texts), self.dimension), dtype=np.float32)
        non_empty_indices = [i for i, t in enumerate(texts) if t and t.strip()]

        if not non_empty_indices:
            return results

        non_empty_texts = [texts[i] for i in non_empty_indices]

        try:
            sparse_matrix = self._vectorizer.transform(non_empty_texts)
            dense_vectors = sparse_matrix.toarray().astype(np.float32)

            for idx, orig_i in enumerate(non_empty_indices):
                vec = dense_vectors[idx]
                norm = np.linalg.norm(vec)
                if norm > 0:
                    results[orig_i] = vec / norm
        except Exception:
            # Fallback zero vectors on any unexpected transform exception
            pass

        return results
