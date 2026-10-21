from datetime import datetime
from pydantic import BaseModel, Field

class StartAnalysisRequest(BaseModel):
    repo_url: str
    commit_limit: int = Field(default=50, ge=5, le=500)
    clustering_algorithm: str = Field(default="dbscan", pattern="^(dbscan|hdbscan)$")

class StartAnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    message: str

class AnalysisSummaryResponse(BaseModel):
    analysis_id: str
    repo_url: str
    owner: str
    repo: str
    status: str
    commit_limit: int
    commits_mined: int
    changes_extracted: int
    clusters_discovered: int
    noise_points: int
    clustering_algorithm: str
    execution_time_seconds: float
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None

class ClusterDetailResponse(BaseModel):
    id: int
    cluster_number: int
    label_name: str
    is_noise: bool
    member_count: int
    avg_similarity: float
    dominant_shifts: list[str]
    affected_files: list[str]
    exemplar_change_id: str | None = None
    exemplar_file: str | None = None
    exemplar_diff: str | None = None

class CodeChangeDetailResponse(BaseModel):
    change_id: str
    commit_hash: str
    file_path: str
    old_start: int
    new_start: int
    deleted_code: str
    added_code: str
    raw_diff: str
    added_lines_count: int
    deleted_lines_count: int
    detected_shifts: list[str]
    enclosing_scope: str | None = None
    timestamp: datetime
