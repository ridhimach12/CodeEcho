from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from backend.app.core.config import settings
from backend.app.schemas.repository import (
    ValidateRepoRequest,
    ValidateRepoResponse,
    HealthResponse,
)
from backend.app.repository_mining.validator import validate_github_url, RepoValidationError

api_router = APIRouter()

@api_router.get("/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint to verify backend operational readiness."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )

@api_router.post("/validate-repo", response_model=ValidateRepoResponse)
def validate_repo(payload: ValidateRepoRequest):
    """
    Validates a repository URL before kicking off an analysis.
    Ensures safe protocols, GitHub domain, and extracts repository components.
    """
    try:
        res = validate_github_url(payload.repo_url)
        return ValidateRepoResponse(
            valid=True,
            owner=res["owner"],
            repo=res["repo"],
            normalized_url=res["normalized_url"],
            message="Repository URL passed syntax and safety validation.",
        )
    except RepoValidationError as e:
        return ValidateRepoResponse(
            valid=False,
            message=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(e)}",
        )
