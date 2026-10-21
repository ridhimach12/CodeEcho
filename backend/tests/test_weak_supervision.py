from datetime import datetime, timedelta
import pytest
from backend.app.repository_mining.models import ExtractedChange, CommitMetadata
from backend.app.feature_extraction.weak_supervision import WeakSupervisionGenerator

@pytest.fixture
def sample_dataset():
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    commits = [
        CommitMetadata(
            commit_hash="c1111111",
            author="Alice",
            timestamp=base_time,
            commit_message="Fix buffer overflow (#101)",
            issue_references=["#101"],
            is_revert=False,
        ),
        CommitMetadata(
            commit_hash="c2222222",
            author="Bob",
            timestamp=base_time + timedelta(hours=2),
            commit_message="Refactor parser for #101",
            issue_references=["#101"],
            is_revert=False,
        ),
        CommitMetadata(
            commit_hash="c3333333",
            author="Charlie",
            timestamp=base_time + timedelta(hours=6),
            commit_message="Revert 'Fix buffer overflow (#101)'",
            issue_references=["#101"],
            is_revert=True,
        ),
        CommitMetadata(
            commit_hash="c4444444",
            author="David",
            timestamp=base_time + timedelta(days=60),
            commit_message="Update docs and license",
            issue_references=[],
            is_revert=False,
        ),
    ]

    changes = [
        # Change 1: in parser.py with #101
        ExtractedChange(
            change_id="ch_1",
            commit_hash="c1111111",
            file_path="src/parser.py",
            timestamp=base_time,
            author="Alice",
            commit_message="Fix buffer overflow (#101)",
            old_start=10,
            new_start=10,
            deleted_code="return buf[i]",
            added_code="if i >= len(buf): raise IndexError()\nreturn buf[i]",
            raw_diff="@@ -10,1 +10,2 @@",
            normalized_code="[-] return buf [ i ]\n[+] if i >= len ( buf ) : raise IndexError ( )\nreturn buf [ i ]",
            added_lines_count=2,
            deleted_lines_count=1,
            issue_references=["#101"],
            is_revert=False,
        ),
        # Change 2: also in parser.py with #101 (same issue, same file)
        ExtractedChange(
            change_id="ch_2",
            commit_hash="c2222222",
            file_path="src/parser.py",
            timestamp=base_time + timedelta(hours=2),
            author="Bob",
            commit_message="Refactor parser for #101",
            old_start=25,
            new_start=25,
            deleted_code="val = buf[pos]",
            added_code="if pos >= len(buf): return None\nval = buf[pos]",
            raw_diff="@@ -25,1 +25,2 @@",
            normalized_code="[-] val = buf [ pos ]\n[+] if pos >= len ( buf ) : return None\nval = buf [ pos ]",
            added_lines_count=2,
            deleted_lines_count=1,
            issue_references=["#101"],
            is_revert=False,
        ),
        # Change 3: Revert commit reverting in parser.py
        ExtractedChange(
            change_id="ch_3",
            commit_hash="c3333333",
            file_path="src/parser.py",
            timestamp=base_time + timedelta(hours=6),
            author="Charlie",
            commit_message="Revert 'Fix buffer overflow (#101)'",
            old_start=10,
            new_start=10,
            deleted_code="if i >= len(buf): raise IndexError()\nreturn buf[i]",
            added_code="return buf[i]",
            raw_diff="@@ -10,2 +10,1 @@",
            normalized_code="[-] if i >= len ( buf ) : raise IndexError ( )\nreturn buf [ i ]\n[+] return buf [ i ]",
            added_lines_count=1,
            deleted_lines_count=2,
            issue_references=["#101"],
            is_revert=True,
        ),
        # Change 4: Unrelated change 60 days later in different file
        ExtractedChange(
            change_id="ch_4",
            commit_hash="c4444444",
            file_path="docs/conf.py",
            timestamp=base_time + timedelta(days=60),
            author="David",
            commit_message="Update docs and license",
            old_start=1,
            new_start=1,
            deleted_code="year = '2025'",
            added_code="year = '2026'",
            raw_diff="@@ -1,1 +1,1 @@",
            normalized_code="[-] year = '2025'\n[+] year = '2026'",
            added_lines_count=1,
            deleted_lines_count=1,
            issue_references=[],
            is_revert=False,
        ),
    ]

    return commits, changes

def test_weak_supervision_shared_issue(sample_dataset):
    commits, changes = sample_dataset
    generator = WeakSupervisionGenerator(random_seed=42)
    pairs = generator.generate_pairs(changes, commits)

    # Check for shared issue same file pair (ch_1 and ch_2)
    shared_issue_pairs = [p for p in pairs if p.relationship_type == "shared_issue_same_file"]
    assert len(shared_issue_pairs) >= 1
    p = shared_issue_pairs[0]
    assert p.label == 1
    assert p.confidence >= 0.8
    assert "parser.py" in p.file_1 and "parser.py" in p.file_2

def test_weak_supervision_revert(sample_dataset):
    commits, changes = sample_dataset
    generator = WeakSupervisionGenerator(random_seed=42)
    pairs = generator.generate_pairs(changes, commits)

    revert_pairs = [p for p in pairs if p.relationship_type == "revert_retraction"]
    assert len(revert_pairs) >= 1
    rp = revert_pairs[0]
    assert rp.label == -1
    assert rp.confidence >= 0.85
    assert "revert" in rp.relationship_type.lower()

def test_weak_supervision_negative_sampling(sample_dataset):
    commits, changes = sample_dataset
    generator = WeakSupervisionGenerator(random_seed=42)
    pairs = generator.generate_pairs(changes, commits)

    neg_pairs = [p for p in pairs if p.relationship_type == "distant_unrelated_sample"]
    assert len(neg_pairs) >= 1
    np_item = neg_pairs[0]
    assert np_item.label == -1
    assert np_item.file_1 != np_item.file_2

def test_weak_supervision_summary(sample_dataset):
    commits, changes = sample_dataset
    generator = WeakSupervisionGenerator(random_seed=42)
    pairs = generator.generate_pairs(changes, commits)
    summary = generator.summarize(pairs)

    assert summary.total_pairs == len(pairs)
    assert summary.positive_pairs > 0
    assert summary.negative_pairs > 0
    assert 0.0 < summary.avg_confidence <= 1.0
