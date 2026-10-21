import re
import subprocess
from datetime import datetime
from pathlib import Path
from backend.app.core.config import settings
from backend.app.repository_mining.models import CommitMetadata, DiffHunk, FileDiff, ExtractedChange
from backend.app.repository_mining.normalizer import normalize_code_diff

ISSUE_REF_REGEX = re.compile(r"(?:#|gh-|GH-)(\d+)|(?:(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#(\d+))", re.IGNORECASE)
REVERT_REGEX = re.compile(r"\b(?:revert|reverting|reverted)\b", re.IGNORECASE)
HUNK_HEADER_REGEX = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@\s*(.*)$")

class GitExtractor:
    def __init__(self, repo_path: str | Path, supported_extensions: list[str] | None = None):
        self.repo_path = Path(repo_path)
        self.supported_extensions = supported_extensions or settings.SUPPORTED_EXTENSIONS

    def _run_git(self, args: list[str]) -> str:
        cmd = ["git", "-C", str(self.repo_path)] + args
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            return ""
        return res.stdout

    def extract_commits(self, max_commits: int | None = None) -> list[CommitMetadata]:
        """
        Extracts structured commit history using git log with delimiter format.
        %H = hash, %an = author, %ae = email, %aI = ISO 8601 date, %P = parent hashes, %s = subject
        """
        limit = max_commits or settings.MAX_COMMITS_DEFAULT
        # Using %x1f as field separator and %x1e as record separator
        log_format = "%H%x1f%an%x1f%ae%x1f%aI%x1f%P%x1f%s%x1e"
        output = self._run_git(["log", f"-n{limit}", f"--pretty=format:{log_format}"])

        commits: list[CommitMetadata] = []
        records = output.split("\x1e")

        for record in records:
            parts = record.strip().split("\x1f")
            if len(parts) < 6:
                continue

            commit_hash, author, email, date_str, parents_str, subject = parts[:6]
            parent_hashes = parents_str.strip().split() if parents_str.strip() else []
            is_merge = len(parent_hashes) > 1
            is_revert = bool(REVERT_REGEX.search(subject))

            issue_refs = []
            for match in ISSUE_REF_REGEX.finditer(subject):
                ref = match.group(1) or match.group(2)
                if ref and ref not in issue_refs:
                    issue_refs.append(f"#{ref}")

            try:
                timestamp = datetime.fromisoformat(date_str)
            except Exception:
                timestamp = datetime.utcnow()

            commits.append(
                CommitMetadata(
                    commit_hash=commit_hash,
                    author=author,
                    author_email=email,
                    timestamp=timestamp,
                    commit_message=subject,
                    parent_hashes=parent_hashes,
                    is_merge=is_merge,
                    is_revert=is_revert,
                    issue_references=issue_refs,
                )
            )

        return commits

    def extract_changes_for_commit(self, commit: CommitMetadata) -> list[ExtractedChange]:
        """
        Extracts code diffs and normalized changes for all supported files in a commit.
        """
        if commit.is_merge:
            # Skip merge commits for change pattern mining to avoid duplicate diff signals
            return []

        # Determine git diff command
        if commit.parent_hashes:
            parent = commit.parent_hashes[0]
            diff_output = self._run_git(["diff", "-U3", parent, commit.commit_hash])
        else:
            # Initial / orphan commit
            diff_output = self._run_git(["show", "--pretty=format:", "-U3", commit.commit_hash])

        return self._parse_unified_diff(diff_output, commit)

    def _parse_unified_diff(self, diff_text: str, commit: CommitMetadata) -> list[ExtractedChange]:
        """
        Parses raw unified diff output into ExtractedChange instances for supported files.
        """
        changes: list[ExtractedChange] = []
        if not diff_text:
            return changes

        # Split diff into per-file chunks
        file_chunks = re.split(r"^diff --git ", diff_text, flags=re.MULTILINE)

        for chunk in file_chunks:
            if not chunk.strip():
                continue

            lines = chunk.splitlines()
            header_line = lines[0] if lines else ""

            # Extract target file path (e.g. b/app/main.py)
            path_match = re.search(r"b/(.+)$", header_line)
            if not path_match:
                continue

            file_path = path_match.group(1).strip()
            # Verify file extension is supported
            if not any(file_path.endswith(ext) for ext in self.supported_extensions):
                continue

            # Parse hunks in this file
            current_hunk_header = None
            hunk_meta = None
            added_lines: list[str] = []
            deleted_lines: list[str] = []
            raw_hunk_lines: list[str] = []
            hunk_counter = 0

            def finalize_hunk():
                nonlocal added_lines, deleted_lines, raw_hunk_lines, hunk_meta, hunk_counter
                if not (added_lines or deleted_lines) or not hunk_meta:
                    return

                added_str = "\n".join(added_lines)
                deleted_str = "\n".join(deleted_lines)
                raw_diff = "\n".join(raw_hunk_lines)
                normalized = normalize_code_diff(added_str, deleted_str)

                # Skip changes that normalized to empty (e.g., pure comments or whitespace)
                if not normalized.strip():
                    return

                change_id = f"{commit.commit_hash[:8]}_{file_path.replace('/', '_')}_{hunk_counter}"
                hunk_counter += 1

                changes.append(
                    ExtractedChange(
                        change_id=change_id,
                        commit_hash=commit.commit_hash,
                        file_path=file_path,
                        timestamp=commit.timestamp,
                        author=commit.author,
                        commit_message=commit.commit_message,
                        old_start=hunk_meta["old_start"],
                        new_start=hunk_meta["new_start"],
                        deleted_code=deleted_str,
                        added_code=added_str,
                        raw_diff=raw_diff,
                        normalized_code=normalized,
                        added_lines_count=len(added_lines),
                        deleted_lines_count=len(deleted_lines),
                        enclosing_scope=hunk_meta["scope"] or None,
                        is_revert=commit.is_revert,
                        issue_references=commit.issue_references,
                    )
                )
                added_lines = []
                deleted_lines = []
                raw_hunk_lines = []

            for line in lines[1:]:
                hunk_match = HUNK_HEADER_REGEX.match(line)
                if hunk_match:
                    finalize_hunk()
                    old_start = int(hunk_match.group(1))
                    old_lines = int(hunk_match.group(2) or 1)
                    new_start = int(hunk_match.group(3))
                    new_lines = int(hunk_match.group(4) or 1)
                    scope = hunk_match.group(5).strip()

                    hunk_meta = {
                        "old_start": old_start,
                        "old_lines": old_lines,
                        "new_start": new_start,
                        "new_lines": new_lines,
                        "scope": scope,
                    }
                    raw_hunk_lines = [line]
                elif hunk_meta:
                    raw_hunk_lines.append(line)
                    if line.startswith("+") and not line.startswith("+++"):
                        added_lines.append(line[1:])
                    elif line.startswith("-") and not line.startswith("---"):
                        deleted_lines.append(line[1:])

            finalize_hunk()

        return changes

    def mine_all_changes(self, max_commits: int | None = None) -> tuple[list[CommitMetadata], list[ExtractedChange]]:
        """
        Coordinates full extraction across the repository up to max_commits.
        """
        commits = self.extract_commits(max_commits=max_commits)
        all_changes: list[ExtractedChange] = []
        for commit in commits:
            changes = self.extract_changes_for_commit(commit)
            all_changes.extend(changes)
        return commits, all_changes
