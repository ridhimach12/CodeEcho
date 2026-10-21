import subprocess
import tempfile
import pytest
from pathlib import Path
from backend.app.repository_mining.cloner import safe_rmtree
from backend.app.repository_mining.extractor import GitExtractor

@pytest.fixture
def temp_git_repo():
    temp_dir = Path(tempfile.mkdtemp(prefix="test_repo_"))
    try:
        # Initialize Git repo
        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=temp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@codeecho.local"], cwd=temp_dir, check=True)

        # Commit 1: Initial file
        file1 = temp_dir / "service.py"
        file1.write_text("def process(data):\n    return data\n")
        subprocess.run(["git", "add", "service.py"], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

        # Commit 2: Bug fix referencing issue
        file1.write_text("def process(data):\n    if not data:\n        raise ValueError('empty')\n    return data\n")
        subprocess.run(["git", "add", "service.py"], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Fix NoneType error in process (#101)"], cwd=temp_dir, check=True)

        # Commit 3: Revert commit
        subprocess.run(["git", "revert", "--no-edit", "HEAD"], cwd=temp_dir, check=True)

        yield temp_dir
    finally:
        safe_rmtree(temp_dir)

def test_git_extractor_commits(temp_git_repo):
    extractor = GitExtractor(temp_git_repo)
    commits = extractor.extract_commits(max_commits=10)

    assert len(commits) == 3
    # Check latest commit (revert)
    revert_commit = commits[0]
    assert revert_commit.is_revert is True
    assert "Revert" in revert_commit.commit_message

    # Check fix commit
    fix_commit = commits[1]
    assert fix_commit.is_revert is False
    assert "#101" in fix_commit.issue_references
    assert "Fix NoneType" in fix_commit.commit_message

def test_git_extractor_changes(temp_git_repo):
    extractor = GitExtractor(temp_git_repo)
    commits, changes = extractor.mine_all_changes(max_commits=10)

    assert len(commits) == 3
    assert len(changes) >= 1

    # Verify the fix change
    fix_changes = [c for c in changes if not c.is_revert and "#101" in c.issue_references]
    assert len(fix_changes) >= 1
    fix_change = fix_changes[0]
    assert fix_change.file_path == "service.py"
    assert "raise ValueError" in fix_change.added_code
    assert fix_change.added_lines_count > 0
    assert len(fix_change.normalized_code) > 0

    # Verify the revert change
    revert_changes = [c for c in changes if c.is_revert]
    assert len(revert_changes) >= 1
    revert_change = revert_changes[0]
    assert revert_change.file_path == "service.py"
    assert "raise ValueError" in revert_change.deleted_code
    assert revert_change.deleted_lines_count > 0
