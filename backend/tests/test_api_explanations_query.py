from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import get_db, SessionLocal, Base, engine
from backend.app.database.models import (
    RepositoryDB,
    AnalysisRunDB,
    PatternClusterDB,
    CodeChangeDB,
    ClusterMembershipDB,
)

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_api_data():
    db = SessionLocal()
    # Check or insert test repo
    repo = db.query(RepositoryDB).filter(RepositoryDB.url == "https://github.com/pallets/click-test-m5").first()
    if not repo:
        repo = RepositoryDB(
            url="https://github.com/pallets/click-test-m5",
            owner="pallets",
            repo="click-test-m5",
        )
        db.add(repo)
        db.commit()

    analysis = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == "test-m5-analysis-run").first()
    if not analysis:
        analysis = AnalysisRunDB(
            id="test-m5-analysis-run",
            repository_id=repo.id,
            status="COMPLETED",
            commit_limit=10,
            commits_mined=10,
            changes_extracted=15,
            clusters_discovered=1,
            noise_points=1,
            execution_time_seconds=1.2,
        )
        db.add(analysis)
        db.commit()

    cluster = db.query(PatternClusterDB).filter(PatternClusterDB.id == 9999).first()
    if not cluster:
        cluster = PatternClusterDB(
            id=9999,
            analysis_id=analysis.id,
            cluster_number=0,
            label_name="Candidate Pattern #1: added_none_guard",
            is_noise=False,
            member_count=1,
            avg_similarity=0.91,
            dominant_shifts_json='["added_none_guard"]',
            affected_files_json='["src/click/core.py"]',
            exemplar_file="src/click/core.py",
            exemplar_diff="@@ -5,1 +5,3 @@\n+ if ctx is None: return None",
        )
        db.add(cluster)
        db.commit()

    change = db.query(CodeChangeDB).filter(CodeChangeDB.id == "ch_m5_1").first()
    if not change:
        change = CodeChangeDB(
            id="ch_m5_1",
            analysis_id=analysis.id,
            commit_hash="c0ffee123456",
            file_path="src/click/core.py",
            old_start=5, new_start=5,
            deleted_code="",
            added_code="if ctx is None:\n    return None",
            raw_diff="@@ -5,1 +5,3 @@",
            added_lines_count=2, deleted_lines_count=0,
            detected_shifts_json='["added_none_guard"]',
            timestamp=datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        )
        db.add(change)
        db.commit()

    membership = db.query(ClusterMembershipDB).filter(
        ClusterMembershipDB.cluster_id == cluster.id,
        ClusterMembershipDB.change_id == change.id,
    ).first()
    if not membership:
        membership = ClusterMembershipDB(cluster_id=cluster.id, change_id=change.id)
        db.add(membership)
        db.commit()

    db.close()
    yield
    # We leave records in place or could clean up if needed

def test_get_cluster_explanation_endpoint(setup_api_data):
    response = client.get("/api/v1/analyses/test-m5-analysis-run/clusters/9999/explanation")
    assert response.status_code == 200
    data = response.json()
    assert data["cluster_id"] == 0
    assert "Null / None" in data["pattern_title"] or "None" in data["pattern_title"]
    assert "HYPOTHESIS:" in data["root_cause_hypothesis"]
    assert "suggested_systemic_fix" in data
    assert data["explanation_mode"] in ["deterministic_fallback", "llm_generated"]
    assert len(data["supporting_evidence"]) >= 1
    assert data["supporting_evidence"][0]["commit_hash"] == "c0ffee123456"

def test_get_cluster_explanation_not_found():
    response = client.get("/api/v1/analyses/test-m5-analysis-run/clusters/999999/explanation")
    assert response.status_code == 404

def test_post_nl_query_endpoint(setup_api_data):
    response = client.post(
        "/api/v1/analyses/test-m5-analysis-run/query",
        json={"query": "Which candidate pattern recurred most frequently?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Pattern #1" in data["answer"]
    assert data["confidence"] > 0.8
    assert data["query_type"] == "deterministic_db"
    assert len(data["citations"]) >= 1

def test_post_nl_query_out_of_scope(setup_api_data):
    response = client.post(
        "/api/v1/analyses/test-m5-analysis-run/query",
        json={"query": "Who is the president of France?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query_type"] == "unsupported"
    assert data["confidence"] == 0.0
    assert "outside the scope" in data["answer"]
