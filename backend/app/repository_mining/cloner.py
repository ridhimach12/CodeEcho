import os
import shutil
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path
from backend.app.core.config import settings
from backend.app.repository_mining.validator import validate_github_url

class GitCloneError(Exception):
    """Raised when git clone fails."""
    pass

def _remove_readonly(func, path, excinfo):
    """Clear readonly bit and reattempt deletion for Windows filesystem."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def safe_rmtree(dir_path: str | Path):
    """Safely removes a directory tree, handling Windows read-only git files."""
    path = Path(dir_path)
    if path.exists():
        shutil.rmtree(path, onerror=_remove_readonly)

class RepoCloner:
    def __init__(self, temp_root: str | None = None):
        self.temp_root = Path(temp_root or settings.TEMP_DIR_ROOT)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def clone(self, repo_url: str, depth: int | None = None, timeout: int | None = None) -> tuple[Path, dict]:
        """
        Safely clones a GitHub repository into an isolated temporary folder.
        Uses depth-limited shallow clone to minimize download time and storage.
        """
        validated = validate_github_url(repo_url)
        depth = depth or settings.MAX_COMMITS_DEFAULT
        timeout = timeout or settings.CLONE_TIMEOUT_SECONDS

        # Unique destination to avoid collisions
        unique_id = f"{validated['owner']}_{validated['repo']}_{uuid.uuid4().hex[:8]}"
        destination = self.temp_root / unique_id

        # Git clone command without shell=True to prevent injection
        cmd = [
            "git", "clone",
            "--depth", str(depth),
            "--single-branch",
            validated["normalized_url"],
            str(destination),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            if result.returncode != 0:
                # Cleanup if clone partially created folder
                safe_rmtree(destination)
                err_msg = result.stderr.strip() or "Unknown Git error"
                raise GitCloneError(f"Failed to clone repository: {err_msg}")

            # Get default branch name
            branch_cmd = ["git", "-C", str(destination), "rev-parse", "--abbrev-ref", "HEAD"]
            branch_res = subprocess.run(branch_cmd, capture_output=True, text=True, check=False)
            default_branch = branch_res.stdout.strip() or "master"

            metadata = {
                "owner": validated["owner"],
                "repo": validated["repo"],
                "url": validated["normalized_url"],
                "local_path": str(destination),
                "default_branch": default_branch,
                "depth": depth,
            }
            return destination, metadata

        except subprocess.TimeoutExpired:
            safe_rmtree(destination)
            raise GitCloneError(f"Git clone operation timed out after {timeout} seconds.")
        except Exception as e:
            safe_rmtree(destination)
            if isinstance(e, GitCloneError):
                raise
            raise GitCloneError(f"Unexpected error while cloning: {str(e)}")

    def cleanup(self, path: str | Path):
        """Cleans up the cloned repository directory."""
        safe_rmtree(path)
