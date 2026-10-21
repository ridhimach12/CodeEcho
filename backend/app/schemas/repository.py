from datetime import datetime
from pydantic import BaseModel, HttpUrl

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
