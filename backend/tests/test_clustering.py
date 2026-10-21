from datetime import datetime
import numpy as np
import pytest
from backend.app.repository_mining.models import ExtractedChange
from backend.app.feature_extraction.representation import CodeChangeRepresentationPipeline
from backend.app.clustering.service import ClusteringEngine

@pytest.fixture
def synthetic_changes_dataset():
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    changes = [
        # Group A: None-check anti-pattern fixes
        ExtractedChange(
            change_id="ch_none_1",
            commit_hash="h111",
            file_path="src/auth.py",
            timestamp=base_time,
            author="DevA",
            commit_message="Fix NoneType in auth token",
            old_start=10, new_start=10,
            deleted_code="return token.decode()",
            added_code="if token is None:\n    return None\nreturn token.decode()",
            raw_diff="@@ -10,1 +10,3 @@",
            normalized_code="[-] return VAR_1 . decode ( )\n[+] if VAR_1 is None : return None\nreturn VAR_1 . decode ( )",
            added_lines_count=2, deleted_lines_count=0,
        ),
        ExtractedChange(
            change_id="ch_none_2",
            commit_hash="h222",
            file_path="src/user.py",
            timestamp=base_time,
            author="DevB",
            commit_message="Guard against None profile",
            old_start=20, new_start=20,
            deleted_code="return profile.name",
            added_code="if profile is None:\n    return None\nreturn profile.name",
            raw_diff="@@ -20,1 +20,3 @@",
            normalized_code="[-] return VAR_1 . name\n[+] if VAR_1 is None : return None\nreturn VAR_1 . name",
            added_lines_count=2, deleted_lines_count=0,
        ),
        ExtractedChange(
            change_id="ch_none_3",
            commit_hash="h333",
            file_path="src/session.py",
            timestamp=base_time,
            author="DevC",
            commit_message="Handle None session id",
            old_start=30, new_start=30,
            deleted_code="return session.id",
            added_code="if session is None:\n    return None\nreturn session.id",
            raw_diff="@@ -30,1 +30,3 @@",
            normalized_code="[-] return VAR_1 . id\n[+] if VAR_1 is None : return None\nreturn VAR_1 . id",
            added_lines_count=2, deleted_lines_count=0,
        ),

        # Group B: Try/Except exception suppression
        ExtractedChange(
            change_id="ch_except_1",
            commit_hash="h444",
            file_path="src/cache.py",
            timestamp=base_time,
            author="DevA",
            commit_message="Catch KeyError in cache lookup",
            old_start=5, new_start=5,
            deleted_code="return cache[key]",
            added_code="try:\n    return cache[key]\nexcept KeyError:\n    return None",
            raw_diff="@@ -5,1 +5,4 @@",
            normalized_code="[-] return VAR_1 [ VAR_2 ]\n[+] try : return VAR_1 [ VAR_2 ]\nexcept KeyError : return None",
            added_lines_count=3, deleted_lines_count=0,
        ),
        ExtractedChange(
            change_id="ch_except_2",
            commit_hash="h555",
            file_path="src/registry.py",
            timestamp=base_time,
            author="DevB",
            commit_message="Suppress KeyError on missing registry entry",
            old_start=15, new_start=15,
            deleted_code="return registry[name]",
            added_code="try:\n    return registry[name]\nexcept KeyError:\n    return None",
            raw_diff="@@ -15,1 +15,4 @@",
            normalized_code="[-] return VAR_1 [ VAR_2 ]\n[+] try : return VAR_1 [ VAR_2 ]\nexcept KeyError : return None",
            added_lines_count=3, deleted_lines_count=0,
        ),

        # Group C: Unrelated unique change (Noise / Outlier)
        ExtractedChange(
            change_id="ch_noise_1",
            commit_hash="h666",
            file_path="scripts/banner.py",
            timestamp=base_time,
            author="DevD",
            commit_message="Print startup banner",
            old_start=1, new_start=1,
            deleted_code="print('v1')",
            added_code="for char in 'WELCOME':\n    print(char)",
            raw_diff="@@ -1,1 +1,2 @@",
            normalized_code="[-] print ( 'v1' )\n[+] for VAR_1 in 'WELCOME' : print ( VAR_1 )",
            added_lines_count=2, deleted_lines_count=1,
        ),
    ]
    return changes

def test_dbscan_clustering_groups_and_exemplars(synthetic_changes_dataset):
    changes = synthetic_changes_dataset
    pipeline = CodeChangeRepresentationPipeline()
    vectors, profiles = pipeline.process_changes_batch(changes)

    clusterer = ClusteringEngine(algorithm="dbscan", eps=0.45, min_samples=2)
    clusters = clusterer.cluster(changes, vectors, profiles)

    # Filter out noise cluster (-1)
    non_noise = [c for c in clusters if not c.is_noise]
    noise = [c for c in clusters if c.is_noise]

    # Should discover at least 2 distinct candidate patterns (None guards and Try/Except handlers)
    assert len(non_noise) >= 2

    # Check that None-guard changes are grouped together
    none_cluster = [c for c in non_noise if "ch_none_1" in c.member_change_ids][0]
    assert "ch_none_2" in none_cluster.member_change_ids
    assert "ch_none_3" in none_cluster.member_change_ids
    assert none_cluster.exemplar_change_id in none_cluster.member_change_ids
    assert none_cluster.avg_intra_cluster_similarity > 0.6
    assert "added_none_guard" in none_cluster.dominant_shifts

    # Check that Except changes are grouped together
    except_cluster = [c for c in non_noise if "ch_except_1" in c.member_change_ids][0]
    assert "ch_except_2" in except_cluster.member_change_ids
    assert "added_exception_handling" in except_cluster.dominant_shifts

    # The noise point should be in the noise cluster or unclustered
    if noise:
        noise_ids = noise[0].member_change_ids
        assert "ch_noise_1" in noise_ids

def test_hdbscan_clustering_runs(synthetic_changes_dataset):
    changes = synthetic_changes_dataset
    pipeline = CodeChangeRepresentationPipeline()
    vectors, profiles = pipeline.process_changes_batch(changes)

    clusterer = ClusteringEngine(algorithm="hdbscan", min_samples=2)
    clusters = clusterer.cluster(changes, vectors, profiles)
    assert isinstance(clusters, list)
    assert len(clusters) > 0

def test_clustering_empty_and_singleton():
    clusterer = ClusteringEngine()
    # Empty
    assert clusterer.cluster([], np.empty((0, 10)), []) == []

    # Singleton
    single_change = ExtractedChange(
        change_id="single_1", commit_hash="h1", file_path="a.py",
        timestamp=datetime.utcnow(), author="A", commit_message="msg",
        old_start=1, new_start=1, deleted_code="a=1", added_code="a=2",
        raw_diff="@@", normalized_code="[-] a=1\n[+] a=2",
        added_lines_count=1, deleted_lines_count=1,
    )
    pipeline = CodeChangeRepresentationPipeline()
    vecs, profiles = pipeline.process_changes_batch([single_change])
    res = clusterer.cluster([single_change], vecs, profiles)
    assert len(res) == 1
    assert res[0].is_noise is True
    assert res[0].cluster_id == -1

def test_duplicate_vectors_clustering():
    # Exactly identical changes should group into a cluster with intra-similarity ~ 1.0
    change1 = ExtractedChange(
        change_id="dup_1", commit_hash="h1", file_path="a.py",
        timestamp=datetime.utcnow(), author="A", commit_message="fix",
        old_start=1, new_start=1, deleted_code="x = 1", added_code="if x is None: return",
        raw_diff="@@", normalized_code="[-] x=1\n[+] if x is None: return",
        added_lines_count=1, deleted_lines_count=1,
    )
    change2 = ExtractedChange(
        change_id="dup_2", commit_hash="h2", file_path="b.py",
        timestamp=datetime.utcnow(), author="B", commit_message="fix",
        old_start=1, new_start=1, deleted_code="x = 1", added_code="if x is None: return",
        raw_diff="@@", normalized_code="[-] x=1\n[+] if x is None: return",
        added_lines_count=1, deleted_lines_count=1,
    )
    pipeline = CodeChangeRepresentationPipeline()
    vecs, profiles = pipeline.process_changes_batch([change1, change2])
    clusterer = ClusteringEngine(eps=0.35, min_samples=2)
    clusters = clusterer.cluster([change1, change2], vecs, profiles)

    non_noise = [c for c in clusters if not c.is_noise]
    assert len(non_noise) == 1
    assert np.isclose(non_noise[0].avg_intra_cluster_similarity, 1.0, atol=1e-3)
