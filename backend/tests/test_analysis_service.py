import subprocess
import tempfile
import pytest
from pathlib import Path
from backend.app.repository_mining.cloner import safe_rmtree
from backend.app.database.session import SessionLocal, init_db
from backend.app.database.models import AnalysisRunDB, RepositoryDB
from backend.app.services.analysis_service import AnalysisService

@pytest.fixture
def mock_git_repo():
    temp_dir = Path(tempfile.mkdtemp(prefix="mock_repo_"))
    try:
        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "CI Runner"], cwd=temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "ci@codeecho.local"], cwd=temp_dir, check=True)

        # Commit 1
        f1 = temp_dir / "calc.py"
        f1.write_text("def div(a, b):\n    return a / b\n")
        subprocess.run(["git", "add", "calc.py"], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial calculator"], cwd=temp_dir, check=True)

        # Commit 2 (Fix 1: ZeroDivisionError guard)
        f1.write_text("def div(a, b):\n    if b == 0:\n        raise ZeroDivisionError('zero denom')\n    return a / b\n")
        subprocess.run(["git", "add", "calc.py"], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Guard against zero division (#10)"], cwd=temp_dir, check=True)

        # Commit 3 (Fix 2: Another ZeroDivisionError guard in helper)
        f2 = temp_dir / "helper.py"
        f2.write_text("def mod(a, b):\n    if b == 0:\n        raise ZeroDivisionError('zero denom')\n    return a % b\n")
        subprocess.run(["git", "add", "helper.py"], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Guard against zero modulo (#10)"], cwd=temp_dir, check=True)

        yield temp_dir
    finally:
        safe_rmtree(temp_dir)

def test_analysis_service_local_execution(mock_git_repo, monkeypatch):
    init_db()
    db = SessionLocal()
    try:
        # We monkeypatch RepoCloner.clone to return our local mock_git_repo directly
        # so this end-to-end integration test runs offline deterministically
        def mock_clone(self, repo_url, depth=None, timeout=None):
            return mock_git_repo, {
                "owner": "mock",
                "repo": "repo",
                "url": repo_url,
                "local_path": str(mock_git_repo),
                "default_branch": "master",
                "depth": depth or 10,
            }
        monkeypatch.setattr("backend.app.repository_mining.cloner.RepoCloner.clone", mock_clone)
        # Avoid deleting the fixture dir during cleanup
        monkeypatch.setattr("backend.app.repository_mining.cloner.RepoCloner.cleanup", lambda self, p: None)

        # Initialize analysis record
        analysis = AnalysisService.create_analysis_record(
            db=db,
            repo_url="https://github.com/mock/repo",
            commit_limit=10,
            algorithm="dbscan",
        )
        assert analysis.status == "PENDING"
        analysis_id = analysis.id

        # Execute end-to-end pipeline
        AnalysisService.execute_analysis(
            analysis_id=analysis_id,
            repo_url="https://github.com/mock/repo",
            commit_limit=10,
            algorithm="dbscan",
        )

        # Check DB state (expire cache to reload committed values from other session)
        db.expire_all()
        updated = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == analysis_id).first()
        assert updated.status == "COMPLETED"
        assert updated.commits_mined >= 2
        assert updated.changes_extracted >= 2
        assert updated.execution_time_seconds > 0.0

        # Verify persisted clusters
        assert len(updated.clusters) >= 1
        first_cluster = updated.clusters[0]
        assert first_cluster.member_count >= 1

    finally:
        db.close()
