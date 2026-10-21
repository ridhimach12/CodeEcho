import random
from datetime import timedelta
from pydantic import BaseModel, Field
from backend.app.repository_mining.models import ExtractedChange, CommitMetadata

class WeakSupervisionPair(BaseModel):
    pair_id: str
    change_id_1: str
    change_id_2: str
    commit_1: str
    commit_2: str
    file_1: str
    file_2: str
    label: int  # +1 = candidate positive, -1 = candidate negative
    confidence: float = Field(ge=0.0, le=1.0)
    relationship_type: str
    evidence: str
    assumptions: str

class WeakSupervisionSummary(BaseModel):
    total_pairs: int = 0
    positive_pairs: int = 0
    negative_pairs: int = 0
    avg_confidence: float = 0.0
    by_relationship: dict[str, int] = Field(default_factory=dict)

class WeakSupervisionGenerator:
    """
    Derives candidate positive and negative training/evaluation pairs
    from observed Git relationships (reverts, issue references, temporal proximity).
    Assigns calibrated confidence scores and explicitly documents assumptions.
    """

    def __init__(self, random_seed: int = 42):
        self.random = random.Random(random_seed)

    def generate_pairs(
        self,
        changes: list[ExtractedChange],
        commits: list[CommitMetadata],
        max_negative_ratio: float = 1.0,
    ) -> list[WeakSupervisionPair]:
        """
        Generates weak supervision pairs from extracted changes and commit metadata.
        """
        if len(changes) < 2:
            return []

        pairs: list[WeakSupervisionPair] = []
        commit_map = {c.commit_hash: c for c in commits}
        pair_keys_seen: set[tuple[str, str]] = set()

        def add_pair(
            c1: ExtractedChange,
            c2: ExtractedChange,
            label: int,
            confidence: float,
            rel_type: str,
            evidence: str,
            assumptions: str,
        ):
            # Sort IDs to prevent duplicate pair entries (A, B) and (B, A)
            k1, k2 = min(c1.change_id, c2.change_id), max(c1.change_id, c2.change_id)
            if (k1, k2) in pair_keys_seen or k1 == k2:
                return
            pair_keys_seen.add((k1, k2))

            pairs.append(
                WeakSupervisionPair(
                    pair_id=f"wp_{len(pairs) + 1}",
                    change_id_1=c1.change_id,
                    change_id_2=c2.change_id,
                    commit_1=c1.commit_hash,
                    commit_2=c2.commit_hash,
                    file_1=c1.file_path,
                    file_2=c2.file_path,
                    label=label,
                    confidence=confidence,
                    relationship_type=rel_type,
                    evidence=evidence,
                    assumptions=assumptions,
                )
            )

        # 1. Mine Shared Issue References
        issue_to_changes: dict[str, list[ExtractedChange]] = {}
        for ch in changes:
            for issue in ch.issue_references:
                issue_to_changes.setdefault(issue, []).append(ch)

        for issue, issue_changes in issue_to_changes.items():
            if len(issue_changes) > 1:
                for i in range(len(issue_changes)):
                    for j in range(i + 1, min(i + 5, len(issue_changes))):
                        c1, c2 = issue_changes[i], issue_changes[j]
                        if c1.commit_hash == c2.commit_hash and c1.file_path == c2.file_path:
                            continue
                        # Revert commits must not be paired as positive fixes
                        if c1.is_revert or c2.is_revert:
                            continue

                        if c1.file_path == c2.file_path:
                            add_pair(
                                c1, c2,
                                label=1,
                                confidence=0.85,
                                rel_type="shared_issue_same_file",
                                evidence=f"Both changes reference {issue} and target '{c1.file_path}'.",
                                assumptions="Changes addressing the same issue in the same file are assumed to modify related defect logic.",
                            )
                        else:
                            add_pair(
                                c1, c2,
                                label=1,
                                confidence=0.55,
                                rel_type="shared_issue_cross_file",
                                evidence=f"Both changes reference {issue} across different files ('{c1.file_path}' and '{c2.file_path}').",
                                assumptions="Changes referencing the same issue across files may represent coordinated adjustments or sub-tasks.",
                            )

        # 2. Mine Revert Relationships
        # Reverts explicitly undo a previous commit
        for ch in changes:
            if ch.is_revert:
                # Find candidate changes in the same file from prior commits
                for other in changes:
                    if (
                        other.file_path == ch.file_path
                        and other.commit_hash != ch.commit_hash
                        and other.timestamp < ch.timestamp
                        and (ch.timestamp - other.timestamp) < timedelta(days=14)
                    ):
                        add_pair(
                            ch, other,
                            label=-1,
                            confidence=0.90,
                            rel_type="revert_retraction",
                            evidence=f"Change in revert commit {ch.commit_hash[:7]} undoes or retracts changes in {other.commit_hash[:7]}.",
                            assumptions="Reverting a commit indicates that the earlier code change was problematic, buggy, or unwanted.",
                        )
                        break

        # 3. Mine Temporal Follow-up Commits in the Same File and Scope
        file_to_changes: dict[str, list[ExtractedChange]] = {}
        for ch in changes:
            file_to_changes.setdefault(ch.file_path, []).append(ch)

        for file_path, file_changes in file_to_changes.items():
            # Sort chronologically
            sorted_changes = sorted(file_changes, key=lambda x: x.timestamp)
            for i in range(len(sorted_changes) - 1):
                c1 = sorted_changes[i]
                c2 = sorted_changes[i + 1]
                time_delta = c2.timestamp - c1.timestamp

                # If within 72 hours and non-revert
                if timedelta(seconds=0) < time_delta <= timedelta(days=3) and not (c1.is_revert or c2.is_revert):
                    same_scope = bool(c1.enclosing_scope and c1.enclosing_scope == c2.enclosing_scope)
                    conf = 0.65 if same_scope else 0.45
                    rel_type = "temporal_followup_same_scope" if same_scope else "temporal_followup_same_file"
                    add_pair(
                        c1, c2,
                        label=1,
                        confidence=conf,
                        rel_type=rel_type,
                        evidence=f"Changes in '{file_path}' occurred within {time_delta.total_seconds() / 3600:.1f} hours ({c1.commit_hash[:7]} -> {c2.commit_hash[:7]}).",
                        assumptions="Rapid successive modifications in the same file or function frequently represent iterative bug-fixes.",
                    )

        # 4. Sample Negative Pairs (distant, unrelated commits across different files)
        positive_count = sum(1 for p in pairs if p.label == 1)
        target_negative_count = max(5, int(positive_count * max_negative_ratio))

        candidates_for_negatives = []
        for i in range(len(changes)):
            for j in range(i + 1, len(changes)):
                c1, c2 = changes[i], changes[j]
                if (
                    c1.file_path != c2.file_path
                    and c1.commit_hash != c2.commit_hash
                    and not set(c1.issue_references).intersection(set(c2.issue_references))
                    and not (c1.is_revert or c2.is_revert)
                ):
                    time_diff = abs((c1.timestamp - c2.timestamp).total_seconds())
                    # Prefer pairs separated in time
                    candidates_for_negatives.append((time_diff, c1, c2))

        # Sort by largest time difference to pick the most demonstrably unrelated changes
        candidates_for_negatives.sort(key=lambda x: x[0], reverse=True)
        sampled_negatives = candidates_for_negatives[:target_negative_count]

        for _, c1, c2 in sampled_negatives:
            add_pair(
                c1, c2,
                label=-1,
                confidence=0.88,
                rel_type="distant_unrelated_sample",
                evidence=f"Changes target distinct files ('{c1.file_path}' vs '{c2.file_path}') across separate commits with no shared issues.",
                assumptions="Distant commits touching completely different files without shared issue metadata are assumed semantically unrelated.",
            )

        return pairs

    @staticmethod
    def summarize(pairs: list[WeakSupervisionPair]) -> WeakSupervisionSummary:
        if not pairs:
            return WeakSupervisionSummary()

        pos = sum(1 for p in pairs if p.label == 1)
        neg = sum(1 for p in pairs if p.label == -1)
        avg_conf = sum(p.confidence for p in pairs) / len(pairs)
        by_rel: dict[str, int] = {}
        for p in pairs:
            by_rel[p.relationship_type] = by_rel.get(p.relationship_type, 0) + 1

        return WeakSupervisionSummary(
            total_pairs=len(pairs),
            positive_pairs=pos,
            negative_pairs=neg,
            avg_confidence=round(avg_conf, 3),
            by_relationship=by_rel,
        )
