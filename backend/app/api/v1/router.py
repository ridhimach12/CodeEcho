import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.database.models import (
    AnalysisRunDB,
    PatternClusterDB,
    CodeChangeDB,
    ClusterMembershipDB,
)
from backend.app.schemas.repository import (
    ValidateRepoRequest,
    ValidateRepoResponse,
    HealthResponse,
    FeatureExtractRequest,
    FeatureExtractResponse,
)
from backend.app.schemas.analysis import (
    StartAnalysisRequest,
    StartAnalysisResponse,
    AnalysisSummaryResponse,
    ClusterDetailResponse,
    CodeChangeDetailResponse,
)
from backend.app.repository_mining.validator import validate_github_url, RepoValidationError
from backend.app.repository_mining.normalizer import normalize_code_diff
from backend.app.feature_extraction.ast_parser import PythonASTParser
from backend.app.embeddings.tfidf_embedder import TFIDFEmbedder
from backend.app.services.analysis_service import AnalysisService

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

# --- Analysis & Pattern Clustering Endpoints ---

@api_router.post("/analyses", response_model=StartAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
def start_analysis(
    payload: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Initiates an asynchronous repository mining, feature extraction, and pattern clustering run.
    """
    try:
        analysis = AnalysisService.create_analysis_record(
            db=db,
            repo_url=payload.repo_url,
            commit_limit=payload.commit_limit,
            algorithm=payload.clustering_algorithm,
        )

        # Dispatch background worker
        background_tasks.add_task(
            AnalysisService.execute_analysis,
            analysis_id=analysis.id,
            repo_url=payload.repo_url,
            commit_limit=payload.commit_limit,
            algorithm=payload.clustering_algorithm,
        )

        return StartAnalysisResponse(
            analysis_id=analysis.id,
            status=analysis.status,
            message="Analysis scheduled in background worker.",
        )
    except RepoValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to schedule analysis: {str(e)}")

@api_router.get("/analyses", response_model=list[AnalysisSummaryResponse])
def list_analyses(db: Session = Depends(get_db)):
    """Lists recent repository analysis runs."""
    analyses = db.query(AnalysisRunDB).order_by(AnalysisRunDB.started_at.desc()).limit(50).all()
    results = []
    for a in analyses:
        results.append(
            AnalysisSummaryResponse(
                analysis_id=a.id,
                repo_url=a.repository.url,
                owner=a.repository.owner,
                repo=a.repository.repo,
                status=a.status,
                commit_limit=a.commit_limit,
                commits_mined=a.commits_mined,
                changes_extracted=a.changes_extracted,
                clusters_discovered=a.clusters_discovered,
                noise_points=a.noise_points,
                clustering_algorithm=a.clustering_algorithm,
                execution_time_seconds=a.execution_time_seconds,
                error_message=a.error_message,
                started_at=a.started_at,
                completed_at=a.completed_at,
            )
        )
    return results

@api_router.get("/analyses/{analysis_id}", response_model=AnalysisSummaryResponse)
def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieves status and summary metrics for an analysis run."""
    a = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")

    return AnalysisSummaryResponse(
        analysis_id=a.id,
        repo_url=a.repository.url,
        owner=a.repository.owner,
        repo=a.repository.repo,
        status=a.status,
        commit_limit=a.commit_limit,
        commits_mined=a.commits_mined,
        changes_extracted=a.changes_extracted,
        clusters_discovered=a.clusters_discovered,
        noise_points=a.noise_points,
        clustering_algorithm=a.clustering_algorithm,
        execution_time_seconds=a.execution_time_seconds,
        error_message=a.error_message,
        started_at=a.started_at,
        completed_at=a.completed_at,
    )

@api_router.get("/analyses/{analysis_id}/clusters", response_model=list[ClusterDetailResponse])
def get_analysis_clusters(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieves candidate recurring pattern clusters discovered during an analysis."""
    a = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found.")

    clusters = db.query(PatternClusterDB).filter(PatternClusterDB.analysis_id == analysis_id).order_by(PatternClusterDB.cluster_number).all()
    results = []
    for c in clusters:
        results.append(
            ClusterDetailResponse(
                id=c.id,
                cluster_number=c.cluster_number,
                label_name=c.label_name,
                is_noise=c.is_noise,
                member_count=c.member_count,
                avg_similarity=c.avg_similarity,
                dominant_shifts=c.dominant_shifts,
                affected_files=c.affected_files,
                exemplar_change_id=c.exemplar_change_id,
                exemplar_file=c.exemplar_file,
                exemplar_diff=c.exemplar_diff,
            )
        )
    return results

@api_router.get("/analyses/{analysis_id}/clusters/{cluster_id}/changes", response_model=list[CodeChangeDetailResponse])
def get_cluster_changes(analysis_id: str, cluster_id: int, db: Session = Depends(get_db)):
    """Retrieves all code changes belonging to a specific cluster."""
    cluster = db.query(PatternClusterDB).filter(
        PatternClusterDB.id == cluster_id,
        PatternClusterDB.analysis_id == analysis_id,
    ).first()
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found.")

    memberships = db.query(ClusterMembershipDB).filter(ClusterMembershipDB.cluster_id == cluster_id).all()
    change_ids = [m.change_id for m in memberships]

    changes = db.query(CodeChangeDB).filter(CodeChangeDB.id.in_(change_ids)).order_by(CodeChangeDB.timestamp.asc()).all()
    results = []
    for ch in changes:
        results.append(
            CodeChangeDetailResponse(
                change_id=ch.id,
                commit_hash=ch.commit_hash,
                file_path=ch.file_path,
                old_start=ch.old_start,
                new_start=ch.new_start,
                deleted_code=ch.deleted_code,
                added_code=ch.added_code,
                raw_diff=ch.raw_diff,
                added_lines_count=ch.added_lines_count,
                deleted_lines_count=ch.deleted_lines_count,
                detected_shifts=ch.detected_shifts,
                enclosing_scope=ch.enclosing_scope,
                timestamp=ch.timestamp,
            )
        )
    return results
