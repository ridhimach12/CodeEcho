from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from backend.app.core.config import settings
from backend.app.schemas.repository import (
    ValidateRepoRequest,
    ValidateRepoResponse,
    HealthResponse,
    FeatureExtractRequest,
    FeatureExtractResponse,
)
from backend.app.repository_mining.validator import validate_github_url, RepoValidationError
from backend.app.repository_mining.normalizer import normalize_code_diff
from backend.app.feature_extraction.ast_parser import PythonASTParser
from backend.app.embeddings.tfidf_embedder import TFIDFEmbedder

# Singleton instance of baseline embedder
default_embedder = TFIDFEmbedder(max_features=128)

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

@api_router.post("/extract-features", response_model=FeatureExtractResponse)
def extract_features_endpoint(payload: FeatureExtractRequest):
    """
    Extracts structural AST profile, detected behavioral shifts, and numerical embedding
    for a given pair of deleted and added code fragments.
    """
    normalized = normalize_code_diff(payload.added_code, payload.deleted_code)
    ast_profile = PythonASTParser.analyze_change(payload.deleted_code, payload.added_code)
    vector = default_embedder.embed_single(normalized)

    return FeatureExtractResponse(
        normalized_code=normalized,
        ast_profile=ast_profile,
        detected_shifts=ast_profile.detected_shifts,
        embedder_name=default_embedder.name,
        embedding_dimension=default_embedder.dimension,
        vector_preview=[round(float(v), 4) for v in vector[:5]],
    )
