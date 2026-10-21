from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.session import Base
from backend.app.database.models import (
    RepositoryDB,
    AnalysisRunDB,
    CommitDB,
    CodeChangeDB,
    PatternClusterDB,
    ClusterMembershipDB,
)

@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_database_crud_and_relationships(in_memory_db):
    session = in_memory_db

    # 1. Create Repository
    repo = RepositoryDB(
        url="https://github.com/pallets/flask.git",
        owner="pallets",
        repo="flask",
    )
    session.add(repo)
    session.commit()
    assert repo.id is not None

    # 2. Create Analysis Run
    analysis = AnalysisRunDB(
        id="test-run-12345",
        repository_id=repo.id,
        status="COMPLETED",
        commit_limit=50,
        commits_mined=45,
        changes_extracted=120,
        clusters_discovered=3,
        noise_points=12,
        execution_time_seconds=4.25,
    )
    session.add(analysis)
    session.commit()

    # 3. Create Commit & Change
    commit = CommitDB(
        analysis_id=analysis.id,
        commit_hash="a1b2c3d4e5",
        author="Armin",
        commit_message="Fix context tear down (#55)",
        timestamp=datetime.utcnow(),
        is_revert=False,
        issue_references_json='["#55"]',
    )
    session.add(commit)

    change = CodeChangeDB(
        id="change_test_1",
        analysis_id=analysis.id,
        commit_hash="a1b2c3d4e5",
        file_path="src/flask/app.py",
        deleted_code="pass",
        added_code="if ctx is not None:\n    ctx.pop()",
        raw_diff="@@",
        normalized_code="[+] if ctx is not None: ctx.pop()",
        added_lines_count=2,
        deleted_lines_count=0,
        detected_shifts_json='["added_none_guard"]',
        timestamp=datetime.utcnow(),
    )
    session.add(change)
    session.commit()

    # 4. Create Cluster & Membership
    cluster = PatternClusterDB(
        analysis_id=analysis.id,
        cluster_number=0,
        label_name="Candidate Pattern #1: added_none_guard",
        is_noise=False,
        member_count=1,
        avg_similarity=1.0,
        dominant_shifts_json='["added_none_guard"]',
        affected_files_json='["src/flask/app.py"]',
        exemplar_change_id="change_test_1",
        exemplar_file="src/flask/app.py",
    )
    session.add(cluster)
    session.flush()

    membership = ClusterMembershipDB(
        cluster_id=cluster.id,
        change_id=change.id,
    )
    session.add(membership)
    session.commit()

    # 5. Verify roundtrip queries & relationships
    fetched_run = session.query(AnalysisRunDB).filter(AnalysisRunDB.id == "test-run-12345").first()
    assert fetched_run is not None
    assert fetched_run.repository.repo == "flask"
    assert len(fetched_run.commits) == 1
    assert fetched_run.commits[0].issue_references == ["#55"]
    assert len(fetched_run.changes) == 1
    assert fetched_run.changes[0].detected_shifts == ["added_none_guard"]
    assert len(fetched_run.clusters) == 1
    assert fetched_run.clusters[0].dominant_shifts == ["added_none_guard"]
    assert len(fetched_run.clusters[0].memberships) == 1
    assert fetched_run.clusters[0].memberships[0].change_id == "change_test_1"
