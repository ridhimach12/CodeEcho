import numpy as np
from backend.app.repository_mining.models import ExtractedChange
from backend.app.feature_extraction.ast_parser import PythonASTParser
from backend.app.feature_extraction.models import ASTDiffProfile
from backend.app.embeddings.base import BaseEmbedder
from backend.app.embeddings.tfidf_embedder import TFIDFEmbedder

class CodeChangeRepresentationPipeline:
    """
    Modular representation pipeline combining semantic text embeddings with
    AST structural syntax mutations into unified, normalized numerical vectors.
    """

    def __init__(
        self,
        embedder: BaseEmbedder | None = None,
        semantic_weight: float = 0.7,
        structural_weight: float = 0.3,
    ):
        self.embedder = embedder or TFIDFEmbedder(max_features=128)
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        # Normalize weights so they sum to 1.0
        total_w = self.semantic_weight + self.structural_weight
        if total_w > 0:
            self.w_sem = np.sqrt(self.semantic_weight / total_w)
            self.w_struct = np.sqrt(self.structural_weight / total_w)
        else:
            self.w_sem = 1.0
            self.w_struct = 0.0

    @property
    def total_dimension(self) -> int:
        # 12 is the dimension of the AST delta vector
        return self.embedder.dimension + 12

    def process_change(self, change: ExtractedChange) -> tuple[np.ndarray, ASTDiffProfile]:
        """
        Extracts structural AST profile and computes fused representation vector for a single change.
        """
        ast_profile = PythonASTParser.analyze_change(change.deleted_code, change.added_code)
        fused_vec = self._build_fused_vector(change.normalized_code, ast_profile)
        return fused_vec, ast_profile

    def process_changes_batch(
        self, changes: list[ExtractedChange]
    ) -> tuple[np.ndarray, list[ASTDiffProfile]]:
        """
        Processes a batch of changes, fitting embedder vocabulary if applicable
        and returning [N, total_dimension] numpy array and AST profiles.
        """
        if not changes:
            return np.empty((0, self.total_dimension), dtype=np.float32), []

        # Fit embedder on batch if needed
        normalized_texts = [c.normalized_code for c in changes]
        self.embedder.fit(normalized_texts)
        semantic_vectors = self.embedder.embed(normalized_texts)

        profiles: list[ASTDiffProfile] = []
        fused_vectors = np.zeros((len(changes), self.total_dimension), dtype=np.float32)

        for i, change in enumerate(changes):
            profile = PythonASTParser.analyze_change(change.deleted_code, change.added_code)
            profiles.append(profile)

            sem_vec = semantic_vectors[i]
            ast_delta = np.array(profile.delta_vector, dtype=np.float32)
            ast_norm = np.linalg.norm(ast_delta)
            if ast_norm > 0:
                ast_normalized = ast_delta / ast_norm
            else:
                ast_normalized = ast_delta

            # Weighted concatenation
            combined = np.concatenate([self.w_sem * sem_vec, self.w_struct * ast_normalized])
            c_norm = np.linalg.norm(combined)
            if c_norm > 0:
                fused_vectors[i] = combined / c_norm
            else:
                fused_vectors[i] = combined

        return fused_vectors, profiles

    def _build_fused_vector(self, normalized_code: str, ast_profile: ASTDiffProfile) -> np.ndarray:
        sem_vec = self.embedder.embed_single(normalized_code)
        ast_delta = np.array(ast_profile.delta_vector, dtype=np.float32)
        ast_norm = np.linalg.norm(ast_delta)
        if ast_norm > 0:
            ast_normalized = ast_delta / ast_norm
        else:
            ast_normalized = ast_delta

        combined = np.concatenate([self.w_sem * sem_vec, self.w_struct * ast_normalized])
        c_norm = np.linalg.norm(combined)
        return (combined / c_norm).astype(np.float32) if c_norm > 0 else combined.astype(np.float32)
