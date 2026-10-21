import json
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class RepositoryDB(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255), unique=True, index=True, nullable=False)
    owner = Column(String(100), nullable=False)
    repo = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    analyses = relationship("AnalysisRunDB", back_populates="repository", cascade="all, delete-orphan")


class AnalysisRunDB(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(36), primary_key=True, index=True)  # UUID string
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True, nullable=False)
    commit_limit = Column(Integer, default=50)
    commits_mined = Column(Integer, default=0)
    changes_extracted = Column(Integer, default=0)
    clusters_discovered = Column(Integer, default=0)
    noise_points = Column(Integer, default=0)
    clustering_algorithm = Column(String(50), default="dbscan")
    execution_time_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    repository = relationship("RepositoryDB", back_populates="analyses")
    commits = relationship("CommitDB", back_populates="analysis", cascade="all, delete-orphan")
    changes = relationship("CodeChangeDB", back_populates="analysis", cascade="all, delete-orphan")
    clusters = relationship("PatternClusterDB", back_populates="analysis", cascade="all, delete-orphan")


class CommitDB(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    commit_hash = Column(String(40), index=True, nullable=False)
    author = Column(String(200), nullable=False)
    author_email = Column(String(200), default="")
    commit_message = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    is_revert = Column(Boolean, default=False)
    issue_references_json = Column(Text, default="[]")

    analysis = relationship("AnalysisRunDB", back_populates="commits")

    @property
    def issue_references(self) -> list[str]:
        try:
            return json.loads(self.issue_references_json or "[]")
        except Exception:
            return []


class CodeChangeDB(Base):
    __tablename__ = "code_changes"

    id = Column(String(100), primary_key=True, index=True)  # change_id
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    commit_hash = Column(String(40), index=True, nullable=False)
    file_path = Column(String(500), index=True, nullable=False)
    old_start = Column(Integer, default=0)
    new_start = Column(Integer, default=0)
    deleted_code = Column(Text, default="")
    added_code = Column(Text, default="")
    raw_diff = Column(Text, default="")
    normalized_code = Column(Text, default="")
    added_lines_count = Column(Integer, default=0)
    deleted_lines_count = Column(Integer, default=0)
    detected_shifts_json = Column(Text, default="[]")
    enclosing_scope = Column(String(200), nullable=True)
    timestamp = Column(DateTime, nullable=False)

    analysis = relationship("AnalysisRunDB", back_populates="changes")
    memberships = relationship("ClusterMembershipDB", back_populates="change", cascade="all, delete-orphan")

    @property
    def detected_shifts(self) -> list[str]:
        try:
            return json.loads(self.detected_shifts_json or "[]")
        except Exception:
            return []


class PatternClusterDB(Base):
    __tablename__ = "pattern_clusters"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    cluster_number = Column(Integer, nullable=False)
    label_name = Column(String(255), nullable=False)
    is_noise = Column(Boolean, default=False)
    member_count = Column(Integer, default=0)
    avg_similarity = Column(Float, default=0.0)
    dominant_shifts_json = Column(Text, default="[]")
    affected_files_json = Column(Text, default="[]")
    exemplar_change_id = Column(String(100), nullable=True)
    exemplar_file = Column(String(500), nullable=True)
    exemplar_diff = Column(Text, nullable=True)

    analysis = relationship("AnalysisRunDB", back_populates="clusters")
    memberships = relationship("ClusterMembershipDB", back_populates="cluster", cascade="all, delete-orphan")

    @property
    def dominant_shifts(self) -> list[str]:
        try:
            return json.loads(self.dominant_shifts_json or "[]")
        except Exception:
            return []

    @property
    def affected_files(self) -> list[str]:
        try:
            return json.loads(self.affected_files_json or "[]")
        except Exception:
            return []


class ClusterMembershipDB(Base):
    __tablename__ = "cluster_memberships"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("pattern_clusters.id"), nullable=False, index=True)
    change_id = Column(String(100), ForeignKey("code_changes.id"), nullable=False, index=True)

    cluster = relationship("PatternClusterDB", back_populates="memberships")
    change = relationship("CodeChangeDB", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("cluster_id", "change_id", name="uq_cluster_change"),
    )
