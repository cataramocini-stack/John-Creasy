"""Modelos ORM do SQLAlchemy."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from vgb.domain.enums import AnalysisModel, EditionStatus, OccurrenceType


class Base(DeclarativeBase):
    pass


class EditionORM(Base):
    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=EditionStatus.PENDING.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    analyses: Mapped[list["AnalysisORM"]] = relationship(back_populates="edition", cascade="all, delete-orphan")


class AnalysisORM(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    edition_id: Mapped[int] = mapped_column(ForeignKey("editions.id"), nullable=False, index=True)
    model_used: Mapped[str] = mapped_column(String(50), default=AnalysisModel.OCR_LOCAL.value)
    raw_response: Mapped[str] = mapped_column(Text, default="")
    structured_result: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    edition: Mapped["EditionORM"] = relationship(back_populates="analyses")
    occurrences: Mapped[list["OccurrenceORM"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class OccurrenceORM(Base):
    __tablename__ = "occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(10), default=OccurrenceType.NOME.value)
    context_snippet: Mapped[str] = mapped_column(Text, default="")
    page_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    analysis: Mapped["AnalysisORM"] = relationship(back_populates="occurrences")


class NotificationORM(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurrence_id: Mapped[int] = mapped_column(ForeignKey("occurrences.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
