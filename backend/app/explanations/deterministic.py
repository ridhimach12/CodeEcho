from backend.app.explanations.models import (
    ClusterExplanation,
    GroundedEvidenceItem,
)
from backend.app.database.models import CodeChangeDB

class DeterministicExplainer:
    """
    Rule-based, deterministic explanation engine.
    Derives grounded explanations directly from AST structural shifts,
    diff metrics, and commit citations without calling external LLMs.
    Guarantees zero hallucination and clear academic hypothesis framing.
    """

    @classmethod
    def generate_explanation(
        cls,
        cluster_id: int,
        label_name: str,
        is_noise: bool,
        dominant_shifts: list[str],
        affected_files: list[str],
        member_changes: list[CodeChangeDB],
        exemplar_file: str | None = None,
        exemplar_diff: str | None = None,
        avg_similarity: float = 0.0,
    ) -> ClusterExplanation:
        # Build exact grounded evidence items from actual member changes
        evidence_items: list[GroundedEvidenceItem] = []
        for ch in member_changes[:5]:
            snippet_lines = ch.raw_diff.splitlines()[:3]
            snippet = "\n".join(snippet_lines)
            evidence_items.append(
                GroundedEvidenceItem(
                    commit_hash=ch.commit_hash,
                    file_path=ch.file_path,
                    lines_summary=f"Hunk @@ -{ch.old_start} +{ch.new_start} (Added {ch.added_lines_count}, Deleted {ch.deleted_lines_count})",
                    evidence_snippet=snippet,
                )
            )

        if is_noise:
            return ClusterExplanation(
                cluster_id=cluster_id,
                pattern_title="Unclustered Outlier Modifications",
                plain_description=f"Isolated changes across {len(affected_files)} files that did not meet the density threshold required to form a recurring pattern.",
                supporting_evidence=evidence_items,
                root_cause_hypothesis="HYPOTHESIS: These changes represent one-off bug fixes, isolated feature additions, or repository configuration maintenance rather than systemic repeating anti-patterns.",
                suggested_systemic_fix="No systemic remediation required; these edits do not exhibit repeated structural recurrence.",
                limitations_and_uncertainty="Classified as noise points by density-based clustering based on precomputed cosine distance thresholds.",
                explanation_mode="deterministic_fallback",
                model_name="codeecho-rule-engine-v1",
                confidence_score=0.95,
            )

        # Check for specific structural shifts
        shifts_set = set(dominant_shifts)

        if "added_none_guard" in shifts_set or "removed_none_guard" in shifts_set:
            title = "Recurrent Null / None Defensive Guard Pattern"
            description = (
                f"Modifications across {len(affected_files)} files repeatedly introduce None guards "
                f"or null-checks (e.g. 'if var is None' or 'if not var') to safeguard against unhandled NoneType values."
            )
            hypothesis = (
                "HYPOTHESIS: Upstream functions or external data sources may return None or missing attributes "
                "without explicit contract enforcement, necessitating defensive guards at downstream call sites."
            )
            fix = (
                "Introduce static type annotations ('Optional[T]' or 'T | None') enforced with mypy/pyright. "
                "Validate data boundaries at ingestion points rather than dispersing defensive checks across consumers."
            )
            conf = 0.85

        elif "added_exception_handling" in shifts_set or "added_explicit_raise" in shifts_set:
            title = "Recurrent Exception Interception & Error Handling Pattern"
            description = (
                f"Changes across {len(affected_files)} files insert try-except blocks or explicit error raises "
                f"to capture runtime exceptions across execution paths."
            )
            hypothesis = (
                "HYPOTHESIS: Defensive error interception applied to prevent unhandled runtime exceptions "
                "encountered during component execution or testing."
            )
            fix = (
                "Implement structured pre-condition checks (e.g. dict.get() with fallback defaults) and define "
                "domain-specific exception hierarchies rather than generic exception catching."
            )
            conf = 0.80

        elif "modified_function_definition" in shifts_set or "added_function_calls" in shifts_set:
            title = "Recurrent Interface Refactoring & Call Adaptation Pattern"
            description = (
                f"Changes across {len(affected_files)} files repeatedly modify function definitions, argument lists, "
                f"or invocation structures."
            )
            hypothesis = (
                "HYPOTHESIS: Internal API evolution or signature modifications where interface changes necessitated "
                "coordinated adaptations across calling modules."
            )
            fix = (
                "Adhere to strict API versioning with keyword-only arguments and deprecation cycles to avoid "
                "cascading signature refactoring across the repository."
            )
            conf = 0.75

        elif "added_conditional_branching" in shifts_set or "simplified_conditional_branching" in shifts_set:
            title = "Recurrent Conditional Logic Modification Pattern"
            description = (
                f"Changes across {len(affected_files)} files alter branching logic, conditional statements, "
                f"or validation gates."
            )
            hypothesis = (
                "HYPOTHESIS: Refinement of business logic conditions, edge-case filtering, or state validation rules."
            )
            fix = (
                "Encapsulate complex conditional branching into domain policy functions or lookup tables to reduce "
                "branching complexity."
            )
            conf = 0.75

        else:
            title = f"Candidate Recurring Pattern: {label_name}"
            description = (
                f"Syntactically similar changes recurring across {len(affected_files)} files with an average "
                f"intra-cluster similarity of ~{round(avg_similarity * 100)}%."
            )
            hypothesis = (
                "HYPOTHESIS: Repetitive structural logic or boilerplate code replicated across multiple repository locations."
            )
            fix = (
                "Extract duplicated code fragments into a shared utility function to eliminate structural repetition."
            )
            conf = 0.70

        limitations = (
            "Rule-based synthesis generated deterministically from observed AST syntax mutations and diff metrics. "
            "Semantic intent is hypothesized from syntax patterns and must be verified by a software engineer."
        )

        return ClusterExplanation(
            cluster_id=cluster_id,
            pattern_title=title,
            plain_description=description,
            supporting_evidence=evidence_items,
            root_cause_hypothesis=hypothesis,
            suggested_systemic_fix=fix,
            limitations_and_uncertainty=limitations,
            explanation_mode="deterministic_fallback",
            model_name="codeecho-rule-engine-v1",
            confidence_score=conf,
        )
