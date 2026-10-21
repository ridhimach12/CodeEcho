import re
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.database.models import (
    AnalysisRunDB,
    PatternClusterDB,
    CodeChangeDB,
    CommitDB,
    ClusterMembershipDB,
)
from backend.app.explanations.models import NLQueryResponse, NLQueryCitation
from backend.app.explanations.deterministic import DeterministicExplainer
from backend.app.explanations.service import ExplanationService

OUT_OF_SCOPE_WORDS = {
    "weather", "rain", "temperature", "president", "election", "recipe", "cook",
    "movie", "capital", "sport", "football", "cricket", "who won", "joke", "poem"
}

class NLQueryService:
    @classmethod
    async def answer_question(
        cls,
        analysis_id: str,
        question: str,
        db: Session,
        cluster_id_hint: int | None = None,
    ) -> NLQueryResponse:
        """
        Answers natural language questions strictly grounded in persisted repository evidence.
        Prefers deterministic database queries for counting, ranking, file listing,
        and temporal chronology; falls back to LLM or explicit out-of-scope messaging.

        Confidence Score Semantics:
          - 0.0: Unsupported query, zero repository evidence, or out-of-scope question.
          - 0.5 - 0.7: Partial repository evidence or heuristic match.
          - 0.8 - 0.95: Grounded deterministic database records, exact commit SHAs, and AST mutations.
        """
        analysis = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == analysis_id).first()
        if not analysis:
            return NLQueryResponse(
                question=question,
                answer="Analysis run not found in database.",
                confidence=0.0,
                query_type="unsupported",
            )

        q_lower = question.lower()

        # Check for obvious out-of-scope questions
        if any(w in q_lower for w in OUT_OF_SCOPE_WORDS):
            return NLQueryResponse(
                question=question,
                answer=(
                    "I cannot answer this question because it is outside the scope of the analyzed repository evidence. "
                    "CodeEcho only answers questions grounded in mined Git commits, candidate anti-patterns, "
                    "affected files, and structural code changes."
                ),
                confidence=0.0,
                query_type="unsupported",
            )

        # Detect referenced cluster number in question (e.g., "pattern 1", "cluster #2", "pattern 5")
        cluster_ref = cluster_id_hint
        cluster_match = re.search(r"(?:pattern|cluster)\s*#?\s*(\d+)", q_lower)
        if cluster_match and cluster_ref is None:
            # 1-indexed in human text -> convert to 0-indexed cluster_number
            cluster_ref = int(cluster_match.group(1)) - 1

        clusters = db.query(PatternClusterDB).filter(PatternClusterDB.analysis_id == analysis_id).all()
        non_noise = [c for c in clusters if not c.is_noise]

        # Target cluster if referenced
        target_cluster = None
        if cluster_ref is not None:
            target_cluster = next((c for c in clusters if c.cluster_number == cluster_ref), None)

        # ----------------------------------------------------
        # Intent 1: Ranking / Most Frequent / Largest Cluster
        # ----------------------------------------------------
        if any(k in q_lower for k in ["most frequent", "most members", "largest", "highest", "top pattern", "recur most", "recurred most"]):
            if not non_noise:
                return NLQueryResponse(
                    question=question,
                    answer="No candidate recurring pattern clusters were discovered in this analysis.",
                    confidence=1.0,
                    query_type="deterministic_db",
                )
            sorted_clusters = sorted(non_noise, key=lambda c: c.member_count, reverse=True)
            top = sorted_clusters[0]
            answer = (
                f"Candidate Pattern #{top.cluster_number + 1} ('{top.label_name}') recurred most frequently, "
                f"encompassing {top.member_count} code changes across {len(top.affected_files)} files. "
                f"The average intra-cluster similarity is ~{round(top.avg_similarity * 100)}%."
            )
            citations = [
                NLQueryCitation(type="cluster", identifier=f"Pattern #{top.cluster_number + 1}", description=top.label_name)
            ]
            if top.exemplar_file:
                citations.append(NLQueryCitation(type="file", identifier=top.exemplar_file, description="Medoid Exemplar File"))
            return NLQueryResponse(
                question=question,
                answer=answer,
                confidence=0.95,
                query_type="deterministic_db",
                citations=citations,
            )

        # ----------------------------------------------------
        # Intent 2: Affected Files
        # ----------------------------------------------------
        if any(k in q_lower for k in ["what files", "which files", "affected files", "files affected", "impacted files"]):
            if target_cluster:
                files = target_cluster.affected_files
                answer = (
                    f"Candidate Pattern #{target_cluster.cluster_number + 1} impacts {len(files)} files: "
                    f"{', '.join(files)}."
                )
                citations = [NLQueryCitation(type="file", identifier=f) for f in files]
                return NLQueryResponse(
                    question=question,
                    answer=answer,
                    confidence=0.95,
                    query_type="deterministic_db",
                    citations=citations,
                )
            else:
                all_files = set()
                for c in non_noise:
                    all_files.update(c.affected_files)
                answer = f"Across all candidate patterns in this analysis, {len(all_files)} unique files were impacted: {', '.join(sorted(list(all_files))[:8])}."
                return NLQueryResponse(
                    question=question,
                    answer=answer,
                    confidence=0.90,
                    query_type="deterministic_db",
                    citations=[NLQueryCitation(type="file", identifier=f) for f in sorted(list(all_files))[:8]],
                )

        # ----------------------------------------------------
        # Intent 3: Commits Belonging to Cluster
        # ----------------------------------------------------
        if any(k in q_lower for k in ["which commits", "commits belong", "who committed", "commit list", "commit hashes"]):
            if target_cluster:
                memberships = db.query(ClusterMembershipDB).filter(ClusterMembershipDB.cluster_id == target_cluster.id).all()
                change_ids = [m.change_id for m in memberships]
                changes = db.query(CodeChangeDB).filter(CodeChangeDB.id.in_(change_ids)).all()
                commits = sorted(list(set(c.commit_hash for c in changes)))
                short_commits = [h[:7] for h in commits]

                answer = (
                    f"Candidate Pattern #{target_cluster.cluster_number + 1} is present in {len(commits)} commits: "
                    f"{', '.join(short_commits)}."
                )
                citations = [NLQueryCitation(type="commit", identifier=h) for h in commits]
                return NLQueryResponse(
                    question=question,
                    answer=answer,
                    confidence=0.95,
                    query_type="deterministic_db",
                    citations=citations,
                )

        # ----------------------------------------------------
        # Intent 4: Chronology / When Introduced / First Appeared
        # ----------------------------------------------------
        if any(k in q_lower for k in ["when", "first appear", "chronology", "earliest", "date"]):
            if target_cluster:
                memberships = db.query(ClusterMembershipDB).filter(ClusterMembershipDB.cluster_id == target_cluster.id).all()
                change_ids = [m.change_id for m in memberships]
                changes = db.query(CodeChangeDB).filter(CodeChangeDB.id.in_(change_ids)).order_by(CodeChangeDB.timestamp.asc()).all()

                if changes:
                    first = changes[0]
                    last = changes[-1]
                    answer = (
                        f"Candidate Pattern #{target_cluster.cluster_number + 1} first appeared on {first.timestamp.strftime('%Y-%m-%d %H:%M UTC')} "
                        f"in commit {first.commit_hash[:7]} ('{first.file_path}'). "
                        f"Its most recent recurrence occurred on {last.timestamp.strftime('%Y-%m-%d %H:%M UTC')} in commit {last.commit_hash[:7]}."
                    )
                    citations = [
                        NLQueryCitation(type="commit", identifier=first.commit_hash, description="Earliest Occurrence"),
                        NLQueryCitation(type="commit", identifier=last.commit_hash, description="Latest Recurrence"),
                    ]
                    return NLQueryResponse(
                        question=question,
                        answer=answer,
                        confidence=0.95,
                        query_type="deterministic_db",
                        citations=citations,
                    )

        # ----------------------------------------------------
        # Intent 5: Evidence & Structural Changes
        # ----------------------------------------------------
        if any(k in q_lower for k in ["evidence", "support", "structural changes", "shifts"]):
            c = target_cluster or (non_noise[0] if non_noise else None)
            if c:
                shifts_desc = ", ".join(c.dominant_shifts) if c.dominant_shifts else "general syntax adjustments"
                answer = (
                    f"Candidate Pattern #{c.cluster_number + 1} is supported by {c.member_count} code changes "
                    f"with ~{round(c.avg_similarity * 100)}% intra-cluster similarity. "
                    f"Common structural mutations: {shifts_desc}. "
                    f"The medoid exemplar diff is in '{c.exemplar_file}'."
                )
                citations = [
                    NLQueryCitation(type="cluster", identifier=f"Pattern #{c.cluster_number + 1}"),
                    NLQueryCitation(type="file", identifier=c.exemplar_file or ""),
                ]
                return NLQueryResponse(
                    question=question,
                    answer=answer,
                    confidence=0.90,
                    query_type="deterministic_db",
                    citations=citations,
                )

        # ----------------------------------------------------
        # Intent 6: Systemic Fix / Prevention
        # ----------------------------------------------------
        if any(k in q_lower for k in ["fix", "prevent", "systemic", "remedy", "solution"]):
            c = target_cluster or (non_noise[0] if non_noise else None)
            if c:
                explanation = DeterministicExplainer.generate_explanation(
                    cluster_id=c.cluster_number,
                    label_name=c.label_name,
                    is_noise=c.is_noise,
                    dominant_shifts=c.dominant_shifts,
                    affected_files=c.affected_files,
                    member_changes=[],
                    exemplar_file=c.exemplar_file,
                )
                answer = f"Suggested systemic fix for Pattern #{c.cluster_number + 1}: {explanation.suggested_systemic_fix}"
                return NLQueryResponse(
                    question=question,
                    answer=answer,
                    confidence=0.85,
                    query_type="deterministic_db",
                    citations=[NLQueryCitation(type="cluster", identifier=f"Pattern #{c.cluster_number + 1}")],
                )

        # ----------------------------------------------------
        # Intent 7: Total Patterns & Overview
        # ----------------------------------------------------
        if any(k in q_lower for k in ["how many patterns", "pattern count", "summary", "overview"]):
            answer = (
                f"Analysis of {analysis.repository.owner}/{analysis.repository.repo} uncovered "
                f"{analysis.clusters_discovered} candidate recurring pattern clusters and {analysis.noise_points} "
                f"unclustered noise changes from {analysis.commits_mined} mined commits."
            )
            return NLQueryResponse(
                question=question,
                answer=answer,
                confidence=0.95,
                query_type="deterministic_db",
            )

        # ----------------------------------------------------
        # Fallback: Attempt LLM Provider with Retrieved Evidence Context
        # ----------------------------------------------------
        provider = ExplanationService.get_provider()
        if provider:
            context = {
                "repository": f"{analysis.repository.owner}/{analysis.repository.repo}",
                "commits_mined": analysis.commits_mined,
                "clusters_discovered": analysis.clusters_discovered,
                "candidate_patterns": [
                    {
                        "pattern_number": c.cluster_number + 1,
                        "label": c.label_name,
                        "members": c.member_count,
                        "shifts": c.dominant_shifts,
                        "files": c.affected_files[:5],
                    }
                    for c in non_noise[:5]
                ],
            }
            llm_ans = await provider.answer_query(question, context)
            if llm_ans:
                return NLQueryResponse(
                    question=question,
                    answer=llm_ans,
                    confidence=0.85,
                    query_type="grounded_retrieval",
                )

        # Insufficient evidence fallback
        return NLQueryResponse(
            question=question,
            answer=(
                "I cannot determine an answer to this question from the available repository evidence. "
                "You can query about pattern rankings, affected files, commits, chronology, or systemic fixes."
            ),
            confidence=0.0,
            query_type="unsupported",
        )
