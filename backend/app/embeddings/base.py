from abc import ABC, abstractmethod
import numpy as np

class BaseEmbedder(ABC):
    """
    Abstract interface for code change embedders.
    Supports consistent vectorization, dimensionality guarantees,
    empty input handling, and cosine similarity computation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name and version identifier of the embedding model."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the generated embedding vectors."""
        pass

    @abstractmethod
    def fit(self, texts: list[str]) -> "BaseEmbedder":
        """Fits vocabulary/weights on a code corpus if applicable."""
        pass

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """
        Converts a list of code diff texts into a 2D float32 numpy array [N, dimension].
        Guaranteed to handle empty strings, out-of-vocabulary terms, and return L2-normalized vectors.
        """
        pass

    def embed_single(self, text: str) -> np.ndarray:
        """
        Converts a single code diff text into a 1D float32 numpy array [dimension].
        """
        return self.embed([text])[0]

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Computes cosine similarity between two 1D vectors with zero-norm safety.
        Returns a float in range [-1.0, 1.0], or 0.0 for zero vectors.
        """
        v1 = np.asarray(vec1, dtype=np.float32).flatten()
        v2 = np.asarray(vec2, dtype=np.float32).flatten()

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0.0 or norm2 == 0.0 or np.isnan(norm1) or np.isnan(norm2):
            return 0.0

        similarity = float(np.dot(v1, v2) / (norm1 * norm2))
        return float(np.clip(similarity, -1.0, 1.0))

    @staticmethod
    def pairwise_cosine_similarity(vecs: np.ndarray) -> np.ndarray:
        """
        Computes pairwise cosine similarity matrix for a 2D array [N, dimension].
        Returns [N, N] symmetric similarity matrix.
        """
        if len(vecs) == 0:
            return np.empty((0, 0), dtype=np.float32)

        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1.0, norms)
        normalized = vecs / norms
        sim_matrix = np.dot(normalized, normalized.T)
        return np.clip(sim_matrix, -1.0, 1.0)
