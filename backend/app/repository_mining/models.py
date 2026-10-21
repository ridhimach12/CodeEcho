from datetime import datetime
from pydantic import BaseModel, Field

class CommitMetadata(BaseModel):
    commit_hash: str
    author: str
    author_email: str = ""
    timestamp: datetime
    commit_message: str
    parent_hashes: list[str] = Field(default_factory=list)
    is_merge: bool = False
    is_revert: bool = False
    issue_references: list[str] = Field(default_factory=list)

class DiffHunk(BaseModel):
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str = ""
    deleted_code: str = ""
    added_code: str = ""
    normalized_diff: str = ""
    enclosing_scope: str | None = None

class FileDiff(BaseModel):
    file_path: str
    old_path: str | None = None
    change_type: str = "M"  # M=Modified, A=Added, D=Deleted, R=Renamed
    hunks: list[DiffHunk] = Field(default_factory=list)
    added_lines_count: int = 0
    deleted_lines_count: int = 0

class ExtractedChange(BaseModel):
    change_id: str
    commit_hash: str
    file_path: str
    timestamp: datetime
    author: str
    commit_message: str
    old_start: int
    new_start: int
    deleted_code: str
    added_code: str
    raw_diff: str
    normalized_code: str
    added_lines_count: int
    deleted_lines_count: int
    enclosing_scope: str | None = None
    is_revert: bool = False
    issue_references: list[str] = Field(default_factory=list)
