from backend.app.core.config import settings
from backend.app.database.models import PatternClusterDB, CodeChangeDB
from backend.app.explanations.models import ClusterExplanation
from backend.app.explanations.deterministic import DeterministicExplainer
from backend.app.explanations.providers import GeminiProvider, OpenAIProvider

class ExplanationService:
    @classmethod
    def get_provider(cls):
        prov = (settings.EXPLANATION_PROVIDER or "").lower()
        if prov == "gemini" and settings.GEMINI_API_KEY:
            return GeminiProvider(api_key=settings.GEMINI_API_KEY)
        elif prov == "openai" and settings.OPENAI_API_KEY:
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY)
        return None

    @classmethod
    async def explain_cluster(
        cls,
        cluster: PatternClusterDB,
        changes: list[CodeChangeDB],
    ) -> ClusterExplanation:
        """
        Generates an evidence-grounded explanation for a candidate pattern cluster.
        Attempts LLM provider if configured; seamlessly falls back to the deterministic
        rule-based explainer if keys are missing or provider fails.
        """
        provider = cls.get_provider()
        if provider:
            cluster_info = {
                "cluster_id": cluster.cluster_number,
                "label_name": cluster.label_name,
                "size": cluster.member_count,
                "dominant_shifts": cluster.dominant_shifts,
                "affected_files": cluster.affected_files,
                "exemplar_file": cluster.exemplar_file,
                "exemplar_diff": cluster.exemplar_diff,
                "exemplar_change_id": cluster.exemplar_change_id,
            }
            llm_result = await provider.generate_explanation(cluster_info)
            if llm_result:
                # Merge full grounded evidence items
                fallback_res = DeterministicExplainer.generate_explanation(
                    cluster_id=cluster.cluster_number,
                    label_name=cluster.label_name,
                    is_noise=cluster.is_noise,
                    dominant_shifts=cluster.dominant_shifts,
                    affected_files=cluster.affected_files,
                    member_changes=changes,
                    exemplar_file=cluster.exemplar_file,
                    exemplar_diff=cluster.exemplar_diff,
                    avg_similarity=cluster.avg_similarity,
                )
                llm_result.supporting_evidence = fallback_res.supporting_evidence
                return llm_result

        # Fallback to deterministic rule-based explainer
        return DeterministicExplainer.generate_explanation(
            cluster_id=cluster.cluster_number,
            label_name=cluster.label_name,
            is_noise=cluster.is_noise,
            dominant_shifts=cluster.dominant_shifts,
            affected_files=cluster.affected_files,
            member_changes=changes,
            exemplar_file=cluster.exemplar_file,
            exemplar_diff=cluster.exemplar_diff,
            avg_similarity=cluster.avg_similarity,
        )
