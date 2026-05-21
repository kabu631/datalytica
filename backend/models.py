"""
models.py — SQLAlchemy ORM models.

Tables
------
Dataset          Metadata for each uploaded file.
DatasetColumn    Per-column schema info derived at ingest time.
PipelineStep     Audit log of every transform applied to a dataset.
Report           Saved AI narrative reports.
AppConfig        Key-value store for application settings.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# ── Dataset ───────────────────────────────────────────────────────────────────

class Dataset(Base):
    """
    Stores metadata for each uploaded file.
    The actual data rows live in a dynamically created SQLite table
    whose name is stored in `sqlite_table_name`.
    """
    __tablename__ = "datasets"

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String(255),  nullable=False)
    original_filename = Column(String(512),  nullable=False)
    row_count         = Column(Integer,      nullable=False, default=0)
    column_count      = Column(Integer,      nullable=False, default=0)
    file_size_kb      = Column(Float,        nullable=False, default=0.0)
    created_at        = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at        = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    status            = Column(String(50),   nullable=False, default="raw")
    #   valid values: 'raw' | 'cleansed' | 'transformed'
    sqlite_table_name = Column(String(255),  nullable=False, unique=True)

    # Relationships
    columns       = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    pipeline_steps= relationship("PipelineStep",  back_populates="dataset", cascade="all, delete-orphan")
    reports       = relationship("Report",         back_populates="dataset", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name!r} status={self.status!r}>"


# ── DatasetColumn ─────────────────────────────────────────────────────────────

class DatasetColumn(Base):
    """
    Column-level metadata detected at ingest time.
    `sample_values` is a JSON array (stored as a plain string) of up to
    5 representative non-null values from the column.
    """
    __tablename__ = "dataset_columns"

    id            = Column(Integer, primary_key=True, index=True)
    dataset_id    = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    column_name   = Column(String(255), nullable=False)
    detected_type = Column(String(50),  nullable=False)
    #   valid values: 'numeric' | 'categorical' | 'datetime' | 'text' | 'boolean'
    null_count    = Column(Integer, nullable=False, default=0)
    null_pct      = Column(Float,   nullable=False, default=0.0)
    unique_count  = Column(Integer, nullable=False, default=0)
    sample_values = Column(Text,    nullable=True)   # JSON array, e.g. '["a","b","c"]'

    # Relationship
    dataset = relationship("Dataset", back_populates="columns")

    def __repr__(self) -> str:
        return (
            f"<DatasetColumn id={self.id} "
            f"column={self.column_name!r} type={self.detected_type!r}>"
        )


# ── PipelineStep ──────────────────────────────────────────────────────────────

class PipelineStep(Base):
    """
    Immutable audit log — every cleanse / ETL / filter operation is recorded
    here together with the exact pandas code that was executed so the
    transformation can be replayed or inspected later.
    """
    __tablename__ = "pipeline_steps"

    id          = Column(Integer, primary_key=True, index=True)
    dataset_id  = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    step_type   = Column(String(50), nullable=False)
    #   e.g. 'cleanse' | 'etl' | 'filter' | 'rename' | 'cast' | …
    description = Column(String(512), nullable=False)
    python_code = Column(Text, nullable=False)   # actual pandas code that was executed
    applied_at  = Column(DateTime(timezone=True), nullable=False, default=_now)
    rows_before = Column(Integer, nullable=False, default=0)
    rows_after  = Column(Integer, nullable=False, default=0)

    # Relationship
    dataset = relationship("Dataset", back_populates="pipeline_steps")

    def __repr__(self) -> str:
        return (
            f"<PipelineStep id={self.id} "
            f"type={self.step_type!r} "
            f"rows={self.rows_before}→{self.rows_after}>"
        )


# ── Report ────────────────────────────────────────────────────────────────────

class Report(Base):
    """
    Saved AI-generated narrative reports.
    `content_markdown` holds the full report text in Markdown format.
    """
    __tablename__ = "reports"

    id               = Column(Integer, primary_key=True, index=True)
    dataset_id       = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    title            = Column(String(512), nullable=False)
    content_markdown = Column(Text, nullable=False)
    created_at       = Column(DateTime(timezone=True), nullable=False, default=_now)

    # Relationship
    dataset = relationship("Dataset", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} title={self.title!r}>"


# ── AppConfig ─────────────────────────────────────────────────────────────────

class AppConfig(Base):
    """
    Key-value store for application settings.
    Examples: DEEPSEEK_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL, LICENSE_KEY, AI_PROVIDER.
    Values are always stored as strings; the application layer is responsible
    for parsing/casting them to the correct type.
    """
    __tablename__ = "app_config"

    key   = Column(String(255), primary_key=True)   # e.g. 'DEEPSEEK_API_KEY'
    value = Column(Text, nullable=True)              # e.g. 'sk-abc123…'

    def __repr__(self) -> str:
        # Mask secrets in repr
        display = self.value if self.value is None else (
            self.value[:4] + "…" if len(self.value) > 4 else "***"
        )
        return f"<AppConfig key={self.key!r} value={display!r}>"
