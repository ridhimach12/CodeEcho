import json
import logging
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    RepositoryDB,
    AnalysisRunDB,
    CommitDB,
    CodeChangeDB,
    PatternClusterDB,
    ClusterMembershipDB,
)
from backend.app.repository_mining.validator import validate_github_url
from backend.app.repository_mining.cloner import RepoCloner
from backend.app.repository_mining.extractor import GitExtractor
from backend.app.feature_extraction.representation import CodeChangeRepresentationPipeline
from backend.app.clustering.service import ClusteringEngine

logger = logging.getLogger(__name__)

class AnalysisService:
    @staticmethod
    def cleanup_stale_analyses(db: Session, max_age_seconds: int = 300) -> int:
        """
        Identifies analyses stuck in non-terminal states (CLONING, EXTRACTING, CLUSTERING)
        longer than max_age_seconds (e.g., due to server reboot or killed worker) and marks them FAILED.
        """
        now = datetime.now(timezone.utc)
        stale_runs = db.query(AnalysisRunDB).filter(
            AnalysisRunDB.status.in_(["PENDING", "CLONING", "EXTRACTING", "CLUSTERING"])
        ).all()
        cleaned = 0
        for run in stale_runs:
            if run.started_at:
                run_started = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=timezone.utc)
                age = (now - run_started).total_seconds()
            else:
                age = max_age_seconds + 1

            if age > max_age_seconds:
                run.status = "FAILED"
                run.error_message = "Analysis timed out or worker process was terminated unexpectedly."
                run.completed_at = now
                cleaned += 1
        if cleaned > 0:
            db.commit()
        return cleaned

    @staticmethod
    def create_analysis_record(db: Session, repo_url: str, commit_limit: int, algorithm: str = "dbscan") -> AnalysisRunDB:
        """
        Validates URL, creates or retrieves RepositoryDB, and initializes AnalysisRunDB.
        Safe against concurrent duplicate repository creation race conditions.
        """
        validated = validate_github_url(repo_url)

        # Get or create repository record
        repo_record = db.query(RepositoryDB).filter(RepositoryDB.url == validated["normalized_url"]).first()
        if not repo_record:
            try:
                repo_record = RepositoryDB(
                    url=validated["normalized_url"],
                    owner=validated["owner"],
                    repo=validated["repo"],
                )
                db.add(repo_record)
                db.commit()
                db.refresh(repo_record)
            except Exception:
                db.rollback()
                repo_record = db.query(RepositoryDB).filter(RepositoryDB.url == validated["normalized_url"]).first()

        analysis_id = str(uuid.uuid4())
        analysis = AnalysisRunDB(
            id=analysis_id,
            repository_id=repo_record.id,
            status="PENDING",
            commit_limit=commit_limit,
            clustering_algorithm=algorithm,
            started_at=datetime.now(timezone.utc),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    @classmethod
    def execute_analysis(cls, analysis_id: str, repo_url: str, commit_limit: int, algorithm: str = "dbscan"):
        """
        Executes end-to-end repository mining, feature extraction, clustering,
        and persistence. Designed to run as an asynchronous background worker.
        """
        db = SessionLocal()
        cloner = RepoCloner()
        clone_path = None
        start_time = time.time()

        try:
            # Clean up any stale analyses from previous crashes
            cls.cleanup_stale_analyses(db)

            analysis = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == analysis_id).first()
            if not analysis:
                return

            # Stage 1: Safe Shallow Clone
            analysis.status = "CLONING"
            db.commit()
            clone_path, _ = cloner.clone(repo_url, depth=commit_limit)

            # Stage 2: Git Extraction
            analysis.status = "EXTRACTING"
            db.commit()
            extractor = GitExtractor(clone_path)
            commits, changes = extractor.mine_all_changes(max_commits=commit_limit)

            # Ensure change IDs are scoped to this analysis run to guarantee
            # uniqueness across repeated analyses of the same repository
            for ch in changes:
                ch.change_id = f"{analysis_id[:8]}_{ch.change_id}"

            # Stage 3: Feature Representation & Clustering
            analysis.status = "CLUSTERING"
            db.commit()

            pipeline = CodeChangeRepresentationPipeline()
            fused_vectors, ast_profiles = pipeline.process_changes_batch(changes)

            clusterer = ClusteringEngine(algorithm=algorithm)
            cluster_results = clusterer.cluster(changes, fused_vectors, ast_profiles)

            # Stage 4: Database Persistence
            # 4a. Persist Commits
            for c in commits:
                db_commit = CommitDB(
                    analysis_id=analysis_id,
                    commit_hash=c.commit_hash,
                    author=c.author,
                    author_email=c.author_email,
                    commit_message=c.commit_message,
                    timestamp=c.timestamp,
                    is_revert=c.is_revert,
                    issue_references_json=json.dumps(c.issue_references),
                )
                db.add(db_commit)

            # 4b. Persist Code Changes
            change_id_to_profile = {c.change_id: p for c, p in zip(changes, ast_profiles)}
            for ch in changes:
                profile = change_id_to_profile.get(ch.change_id)
                shifts = profile.detected_shifts if profile else []
                db_change = CodeChangeDB(
                    id=ch.change_id,
                    analysis_id=analysis_id,
                    commit_hash=ch.commit_hash,
                    file_path=ch.file_path,
                    old_start=ch.old_start,
                    new_start=ch.new_start,
                    deleted_code=ch.deleted_code,
                    added_code=ch.added_code,
                    raw_diff=ch.raw_diff,
                    normalized_code=ch.normalized_code,
                    added_lines_count=ch.added_lines_count,
                    deleted_lines_count=ch.deleted_lines_count,
                    detected_shifts_json=json.dumps(shifts),
                    enclosing_scope=ch.enclosing_scope,
                    timestamp=ch.timestamp,
                )
                db.add(db_change)
            db.commit()

            # 4c. Persist Clusters & Memberships
            discovered_clusters_count = 0
            noise_points_count = 0

            for res in cluster_results:
                if res.is_noise:
                    noise_points_count += res.size
                else:
                    discovered_clusters_count += 1

                db_cluster = PatternClusterDB(
                    analysis_id=analysis_id,
                    cluster_number=res.cluster_id,
                    label_name=res.label_name,
                    is_noise=res.is_noise,
                    member_count=res.size,
                    avg_similarity=res.avg_intra_cluster_similarity,
                    dominant_shifts_json=json.dumps(res.dominant_shifts),
                    affected_files_json=json.dumps(res.affected_files),
                    exemplar_change_id=res.exemplar_change_id,
                    exemplar_file=res.exemplar_file,
                    exemplar_diff=res.exemplar_diff,
                )
                db.add(db_cluster)
                db.flush()  # Populates db_cluster.id

                for change_id in res.member_change_ids:
                    membership = ClusterMembershipDB(
                        cluster_id=db_cluster.id,
                        change_id=change_id,
                    )
                    db.add(membership)

            # Update final analysis metrics
            duration = round(time.time() - start_time, 2)
            analysis.commits_mined = len(commits)
            analysis.changes_extracted = len(changes)
            analysis.clusters_discovered = discovered_clusters_count
            analysis.noise_points = noise_points_count
            analysis.execution_time_seconds = duration
            analysis.status = "COMPLETED"
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as e:
            logger.exception(f"Analysis failed for {analysis_id}: {str(e)}")
            try:
                analysis = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == analysis_id).first()
                if analysis:
                    analysis.status = "FAILED"
                    analysis.error_message = str(e)
                    analysis.completed_at = datetime.now(timezone.utc)
                    analysis.execution_time_seconds = round(time.time() - start_time, 2)
                    db.commit()
            except Exception:
                pass
        finally:
            if clone_path:
                cloner.cleanup(clone_path)
            db.close()
