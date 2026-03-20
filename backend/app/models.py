import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    years_of_experience: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    seniority_level: Mapped[str] = mapped_column(String(50), nullable=False, default="mid")
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    jobs: Mapped[list["MatchJob"]] = relationship(back_populates="candidate", lazy="noload")

    def __repr__(self) -> str:
        return f"<Candidate {self.name!r}>"


class MatchJob(Base):
    __tablename__ = "match_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    job_description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    job_title: Mapped[str | None] = mapped_column(String(255))
    required_seniority: Mapped[str | None] = mapped_column(String(50))
    required_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    overall_score: Mapped[int | None] = mapped_column(SmallInteger)
    skills_score: Mapped[int | None] = mapped_column(SmallInteger)
    experience_score: Mapped[int | None] = mapped_column(SmallInteger)
    location_score: Mapped[int | None] = mapped_column(SmallInteger)

    matched_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recommendation: Mapped[str | None] = mapped_column(Text)
    score_explanation: Mapped[dict | None] = mapped_column(JSONB)

    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_match_jobs_candidate_status", "candidate_id", "status", "enqueued_at"),
        Index("idx_match_jobs_batch_id", "batch_id"),
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="jobs", lazy="noload")

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"<MatchJob {self.id} status={self.status!r}>"
