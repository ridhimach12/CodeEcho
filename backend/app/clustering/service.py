from collections import Counter
import numpy as np
from pydantic import BaseModel, Field
from sklearn.cluster import DBSCAN, HDBSCAN
from backend.app.repository_mining.models import ExtractedChange
from backend.app.feature_extraction.models import ASTDiffProfile

class ClusterResult(BaseModel):
    cluster_id: int  # -1 for noise, 0, 1, 2... for candidate patterns
    label_name: str
    is_noise: bool
    size: int
    member_change_ids: list[str]
    exemplar_change_id: str | None = None
    exemplar_file: str | None = None
    exemplar_diff: str | None = None
    avg_intra_cluster_similarity: float = 0.0
    dominant_shifts: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)

class ClusteringEngine:
    """
    Modular density-based clustering engine for code change representations.
    Groups semantically and structurally similar modifications into candidate recurring patterns.
    Computes medoid exemplars and tracks noise points.
    """

    def __init__(
        self,
        algorithm: str = "dbscan",
        eps: float = 0.35,
        min_samples: int = 2,
    ):
        self.algorithm = algorithm.lower()
        self.eps = eps
        self.min_samples = min_samples

    def compute_distance_matrix(self, vectors: np.ndarray) -> np.ndarray:
        """
        Computes pairwise cosine distance matrix D[i, j] = 1.0 - cos_sim(v_i, v_j).
        Clamps distances into [0.0, 2.0] and enforces zero diagonal.
        """
        n = len(vectors)
        if n == 0:
            return np.empty((0, 0), dtype=np.float32)

        # Dot product of L2-normalized vectors equals cosine similarity
        sim_matrix = np.dot(vectors, vectors.T)
        dist_matrix = 1.0 - sim_matrix
        dist_matrix = np.clip(dist_matrix, 0.0, 2.0)
        np.fill_diagonal(dist_matrix, 0.0)
        return dist_matrix.astype(np.float64)

    def cluster(
        self,
        changes: list[ExtractedChange],
        vectors: np.ndarray,
        profiles: list[ASTDiffProfile],
    ) -> list[ClusterResult]:
        """
        Executes clustering and returns a list of ClusterResult instances.
        Handles empty, singleton, and edge-case inputs gracefully.
        """
        n = len(changes)
        if n == 0:
            return []

        if n < self.min_samples:
            # Not enough changes to form any recurring pattern
            return [
                ClusterResult(
                    cluster_id=-1,
                    label_name="Unclustered (Insufficient Samples)",
                    is_noise=True,
                    size=n,
                    member_change_ids=[c.change_id for c in changes],
                    affected_files=list(set(c.file_path for c in changes)),
                )
            ]

        # Compute precomputed cosine distance matrix
        dist_matrix = self.compute_distance_matrix(vectors)

        # Run density-based clustering
        if self.algorithm == "hdbscan":
            clusterer = HDBSCAN(
                min_cluster_size=self.min_samples,
                metric="precomputed",
                copy=True,
            )
            labels = clusterer.fit_predict(dist_matrix)
        else:
            clusterer = DBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
                metric="precomputed",
            )
            labels = clusterer.fit_predict(dist_matrix)

        # Group indices by cluster label
        cluster_groups: dict[int, list[int]] = {}
        for idx, lbl in enumerate(labels):
            cluster_groups.setdefault(int(lbl), []).append(idx)

        results: list[ClusterResult] = []

        # Process valid non-noise clusters first, then noise (-1)
        sorted_labels = sorted(cluster_groups.keys(), key=lambda l: (l == -1, l))

        for lbl in sorted_labels:
            indices = cluster_groups[lbl]
            member_changes = [changes[i] for i in indices]
            member_profiles = [profiles[i] for i in indices]
            member_ids = [c.change_id for c in member_changes]
            affected_files = sorted(list(set(c.file_path for c in member_changes)))

            # Collect dominant AST shifts
            all_shifts: list[str] = []
            for p in member_profiles:
                all_shifts.extend(p.detected_shifts)
            shift_counts = Counter(all_shifts)
            dominant_shifts = [shift for shift, _ in shift_counts.most_common(3)]

            is_noise = (lbl == -1)

            if is_noise:
                results.append(
                    ClusterResult(
                        cluster_id=-1,
                        label_name="Unclustered Changes (Noise)",
                        is_noise=True,
                        size=len(indices),
                        member_change_ids=member_ids,
                        dominant_shifts=dominant_shifts,
                        affected_files=affected_files,
                    )
                )
            else:
                # Calculate medoid exemplar and intra-cluster similarity
                sub_sim = np.dot(vectors[indices], vectors[indices].T)
                mean_sims = sub_sim.mean(axis=1)
                best_sub_idx = int(np.argmax(mean_sims))
                exemplar_change = member_changes[best_sub_idx]
                avg_similarity = float(mean_sims.mean())

                label_desc = ", ".join(dominant_shifts) if dominant_shifts else "Syntactic Pattern"
                pattern_name = f"Candidate Pattern #{lbl + 1}: {label_desc}"

                results.append(
                    ClusterResult(
                        cluster_id=lbl,
                        label_name=pattern_name,
                        is_noise=False,
                        size=len(indices),
                        member_change_ids=member_ids,
                        exemplar_change_id=exemplar_change.change_id,
                        exemplar_file=exemplar_change.file_path,
                        exemplar_diff=exemplar_change.raw_diff,
                        avg_intra_cluster_similarity=round(avg_similarity, 4),
                        dominant_shifts=dominant_shifts,
                        affected_files=affected_files,
                    )
                )

        return results
