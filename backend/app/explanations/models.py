from pydantic import BaseModel, Field

class GroundedEvidenceItem(BaseModel):
    commit_hash: str
    file_path: str
    lines_summary: str = ""
    evidence_snippet: str = ""

class ClusterExplanation(BaseModel):
    cluster_id: int
    pattern_title: str
    plain_description: str
    supporting_evidence: list[GroundedEvidenceItem] = Field(default_factory=list)
    root_cause_hypothesis: str
    suggested_systemic_fix: str
    limitations_and_uncertainty: str
    explanation_mode: str  # "llm_generated" or "deterministic_fallback"
    model_name: str
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)

class NLQueryRequest(BaseModel):
    query: str
    cluster_id: int | None = None

class NLQueryCitation(BaseModel):
    type: str  # "cluster", "commit", "file"
    identifier: str
    description: str = ""

class NLQueryResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    query_type: str  # "deterministic_db", "grounded_retrieval", "unsupported"
    citations: list[NLQueryCitation] = Field(default_factory=list)
