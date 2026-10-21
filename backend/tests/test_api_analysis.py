from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import RepositoryDB, AnalysisRunDB, PatternClusterDB, CodeChangeDB, ClusterMembershipDB
from datetime import datetime

client = TestClient(app)

def test_analysis_api_workflow():
    db = SessionLocal()
    try:
        # Pre-seed or retrieve test repository in DB
        repo = db.query(RepositoryDB).filter(RepositoryDB.url == "https://github.com/pallets/click.git").first()
        if not repo:
            repo = RepositoryDB(
                url="https://github.com/pallets/click.git",
                owner="pallets",
                repo="click",
            )
            db.add(repo)
            db.commit()

        analysis = db.query(AnalysisRunDB).filter(AnalysisRunDB.id == "api-test-run-101").first()
        if not analysis:
            analysis = AnalysisRunDB(
                id="api-test-run-101",
                repository_id=repo.id,
                status="COMPLETED",
                commit_limit=25,
                commits_mined=20,
                changes_extracted=15,
                clusters_discovered=1,
                noise_points=2,
                execution_time_seconds=2.5,
            )
            db.add(analysis)
            db.commit()

            change = CodeChangeDB(
                id="ch_api_1",
                analysis_id=analysis.id,
                commit_hash="abc1234",
                file_path="src/click/core.py",
                deleted_code="pass",
                added_code="if x is None: return",
                raw_diff="@@",
                normalized_code="[+] if x is None: return",
                added_lines_count=1,
                deleted_lines_count=0,
                detected_shifts_json='["added_none_guard"]',
                timestamp=datetime.utcnow(),
            )
            db.add(change)
            db.commit()

            cluster = PatternClusterDB(
                analysis_id=analysis.id,
                cluster_number=0,
                label_name="Candidate Pattern #1: added_none_guard",
                is_noise=False,
                member_count=1,
                avg_similarity=1.0,
                dominant_shifts_json='["added_none_guard"]',
                affected_files_json='["src/click/core.py"]',
                exemplar_change_id="ch_api_1",
                exemplar_file="src/click/core.py",
                exemplar_diff="@@",
            )
            db.add(cluster)
            db.flush()

            membership = ClusterMembershipDB(cluster_id=cluster.id, change_id=change.id)
            db.add(membership)
            db.commit()
    finally:
        db.close()

    # 1. Test List Analyses
    res_list = client.get("/api/v1/analyses")
    assert res_list.status_code == 200
    runs = res_list.json()
    assert any(r["analysis_id"] == "api-test-run-101" for r in runs)

    # 2. Test Get Specific Analysis Status
    res_single = client.get("/api/v1/analyses/api-test-run-101")
    assert res_single.status_code == 200
    data = res_single.json()
    assert data["status"] == "COMPLETED"
    assert data["clusters_discovered"] == 1
    assert data["commits_mined"] == 20

    # 3. Test Get Analysis Clusters
    res_clusters = client.get("/api/v1/analyses/api-test-run-101/clusters")
    assert res_clusters.status_code == 200
    clusters_data = res_clusters.json()
    assert len(clusters_data) == 1
    assert clusters_data[0]["label_name"] == "Candidate Pattern #1: added_none_guard"
    assert clusters_data[0]["exemplar_change_id"] == "ch_api_1"

    # 4. Test Get Cluster Changes
    cluster_db_id = clusters_data[0]["id"]
    res_changes = client.get(f"/api/v1/analyses/api-test-run-101/clusters/{cluster_db_id}/changes")
    assert res_changes.status_code == 200
    changes_data = res_changes.json()
    assert len(changes_data) == 1
    assert changes_data[0]["change_id"] == "ch_api_1"
    assert changes_data[0]["file_path"] == "src/click/core.py"

    # 5. Test Trigger Analysis (Accepted 202)
    res_trigger = client.post(
        "/api/v1/analyses",
        json={"repo_url": "https://github.com/psf/requests", "commit_limit": 10}
    )
    assert res_trigger.status_code == 202
    assert "analysis_id" in res_trigger.json()

    # 6. Test 404 for Unknown Analysis
    res_404 = client.get("/api/v1/analyses/non-existent-id")
    assert res_404.status_code == 404
