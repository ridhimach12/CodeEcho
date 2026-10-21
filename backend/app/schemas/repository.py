from datetime import datetime
from pydantic import BaseModel, Field
from backend.app.feature_extraction.models import ASTDiffProfile

class ValidateRepoRequest(BaseModel):
    repo_url: str

class ValidateRepoResponse(BaseModel):
    valid: bool
    owner: str = ""
    repo: str = ""
    normalized_url: str = ""
    message: str = "Repository URL is valid."

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime

class FeatureExtractRequest(BaseModel):
    deleted_code: str = ""
    added_code: str = ""

class FeatureExtractResponse(BaseModel):
    normalized_code: str
    ast_profile: ASTDiffProfile
    detected_shifts: list[str]
    embedder_name: str
    embedding_dimension: int
    vector_preview: list[float]
