import asyncio
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.session import Base
from backend.app.database.models import (
    RepositoryDB,
    AnalysisRunDB,
    PatternClusterDB,
    CodeChangeDB,
    ClusterMembershipDB,
)
from backend.app.services.query_service import NLQueryService

@pytest.fixture
def query_test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    repo = RepositoryDB(
        url="https://github.com/pallets/click",
        owner="pallets",
        repo="click",
    )
    session.add(repo)
    session.commit()

    analysis = AnalysisRunDB(
        id="analysis-query-test",
        repository_id=repo.id,
        status="COMPLETED",
        commit_limit=20,
        commits_mined=15,
        changes_extracted=25,
        clusters_discovered=2,
        noise_points=3,
        execution_time_seconds=1.85,
    )
    session.add(analysis)
    session.commit()

    c1 = PatternClusterDB(
        id=101,
        analysis_id=analysis.id,
        cluster_number=0,
        label_name="Candidate Pattern #1: added_none_guard",
        is_noise=False,
        member_count=3,
        avg_similarity=0.92,
        dominant_shifts_json='["added_none_guard"]',
        affected_files_json='["src/click/core.py", "src/click/utils.py"]',
        exemplar_file="src/click/core.py",
        exemplar_diff="@@ -10,2 +10,4 @@\n+ if value is None: return None",
    )
    c2 = PatternClusterDB(
        id=102,
        analysis_id=analysis.id,
        cluster_number=1,
        label_name="Candidate Pattern #2: added_exception_handling",
        is_noise=False,
        member_count=2,
        avg_similarity=0.85,
        dominant_shifts_json='["added_exception_handling"]',
        affected_files_json='["src/click/parser.py"]',
        exemplar_file="src/click/parser.py",
        exemplar_diff="@@ -40,2 +40,5 @@\n+ try:\n+     run()\n+ except Exception: pass",
    )
    c_noise = PatternClusterDB(
        id=103,
        analysis_id=analysis.id,
        cluster_number=-1,
        label_name="Unclustered Changes (Noise)",
        is_noise=True,
        member_count=3,
        avg_similarity=0.0,
        dominant_shifts_json='[]',
        affected_files_json='["setup.py"]',
    )
    session.add_all([c1, c2, c_noise])
    session.commit()

    # Code changes for cluster 1
    t1 = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    ch1 = CodeChangeDB(
        id="ch_q1",
        analysis_id=analysis.id,
        commit_hash="aaaaaaa1111111",
        file_path="src/click/core.py",
        old_start=10, new_start=10,
        deleted_code="",
        added_code="if value is None:\n    return None",
        raw_diff="@@",
        added_lines_count=2, deleted_lines_count=0,
        detected_shifts_json='["added_none_guard"]',
        timestamp=t1,
    )
    ch2 = CodeChangeDB(
        id="ch_q2",
        analysis_id=analysis.id,
        commit_hash="bbbbbbb2222222",
        file_path="src/click/utils.py",
        old_start=25, new_start=25,
        deleted_code="",
        added_code="if param is None:\n    return",
        raw_diff="@@",
        added_lines_count=2, deleted_lines_count=0,
        detected_shifts_json='["added_none_guard"]',
        timestamp=t2,
    )
    session.add_all([ch1, ch2])
    session.commit()

    m1 = ClusterMembershipDB(cluster_id=c1.id, change_id=ch1.id)
    m2 = ClusterMembershipDB(cluster_id=c1.id, change_id=ch2.id)
    session.add_all([m1, m2])
    session.commit()

    try:
        yield session
    finally:
        session.close()

def test_query_unknown_analysis(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="non-existent-id",
        question="Which pattern is largest?",
        db=query_test_db,
    ))
    assert res.query_type == "unsupported"
    assert "not found" in res.answer.lower()

def test_query_out_of_scope(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="What is the weather today and who won the football match?",
        db=query_test_db,
    ))
    assert res.query_type == "unsupported"
    assert "outside the scope" in res.answer
    assert res.confidence == 0.0

def test_query_ranking_most_frequent(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="Which candidate anti-pattern recurred most frequently in this repository?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "Pattern #1" in res.answer
    assert "3 code changes" in res.answer
    assert len(res.citations) >= 1
    assert any(c.type == "cluster" for c in res.citations)

def test_query_affected_files_target_cluster(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="What files are affected by pattern 1?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "src/click/core.py" in res.answer
    assert "src/click/utils.py" in res.answer
    assert len(res.citations) == 2

def test_query_affected_files_all_patterns(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="Which files are impacted overall?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "unique files were impacted" in res.answer

def test_query_commits_belonging_to_cluster(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="Which commits belong to pattern 1?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "aaaaaaa" in res.answer
    assert "bbbbbbb" in res.answer
    assert len(res.citations) == 2

def test_query_chronology(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="When was pattern 1 first introduced and when did it last appear?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "2025-01-10" in res.answer
    assert "2025-02-15" in res.answer
    assert any("Earliest Occurrence" in (c.description or "") for c in res.citations)

def test_query_systemic_fix(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="How can we prevent or fix pattern 1?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "Suggested systemic fix" in res.answer
    assert "type" in res.answer.lower() or "guard" in res.answer.lower()

def test_query_overview_count(query_test_db):
    res = asyncio.run(NLQueryService.answer_question(
        analysis_id="analysis-query-test",
        question="Can you give me a summary of how many patterns were discovered?",
        db=query_test_db,
    ))
    assert res.query_type == "deterministic_db"
    assert "2 candidate recurring pattern clusters" in res.answer
    assert "3 unclustered noise changes" in res.answer
