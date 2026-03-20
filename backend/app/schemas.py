import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

if TYPE_CHECKING:
    from app.models import MatchJob

JobStatus = Literal["pending", "processing", "completed", "failed"]


# ── Request schemas ─────────────────────────────────────────────────────────
class JobSubmission(BaseModel):
    content: Annotated[
        str,
        Field(min_length=10, max_length=50_000, description="Job description text or URL."),
    ]
    is_url: bool = False
    title: str | None = Field(
        default=None,
        max_length=120,
        description="Optional display label set by the user.",
    )

    @field_validator("content", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def auto_detect_url(self) -> "JobSubmission":
        if self.content.startswith(("http://", "https://")):
            self.is_url = True
        return self


class MatchSubmitRequest(BaseModel):
    jobs: Annotated[
        list[JobSubmission],
        Field(min_length=1, max_length=10, description="1–10 job descriptions per batch."),
    ]

    @model_validator(mode="after")
    def reject_duplicates(self) -> "MatchSubmitRequest":
        contents = [j.content for j in self.jobs]
        if len(contents) != len(set(contents)):
            raise ValueError(
                "Batch contains duplicate job descriptions. Each entry must be unique."
            )
        return self


# ── Response schemas ────────────────────────────────────────────────────────
class DimensionScores(BaseModel):
    skills: int | None = Field(None, ge=0, le=100)
    experience: int | None = Field(None, ge=0, le=100)
    location: int | None = Field(None, ge=0, le=100)


class ScoreExplanation(BaseModel):
    skills: str | None = None
    experience: str | None = None
    location: str | None = None


class MatchJobResponse(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    status: JobStatus
    raw_input: str

    job_title: str | None
    required_seniority: str | None
    required_skills: list[str]

    overall_score: int | None
    dimension_scores: DimensionScores
    matched_skills: list[str]
    missing_skills: list[str]
    recommendation: str | None
    score_explanation: ScoreExplanation | None

    error_message: str | None
    retry_count: int

    enqueued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, job: "MatchJob") -> "MatchJobResponse":
        return cls(
            id=job.id,
            batch_id=job.batch_id,
            status=job.status,
            raw_input=job.raw_input,
            job_title=job.job_title,
            required_seniority=job.required_seniority,
            required_skills=job.required_skills or [],
            overall_score=job.overall_score,
            dimension_scores=DimensionScores(
                skills=job.skills_score,
                experience=job.experience_score,
                location=job.location_score,
            ),
            matched_skills=job.matched_skills or [],
            missing_skills=job.missing_skills or [],
            recommendation=job.recommendation,
            score_explanation=(
                ScoreExplanation(**job.score_explanation)
                if job.score_explanation
                else None
            ),
            error_message=job.error_message,
            retry_count=job.retry_count,
            enqueued_at=job.enqueued_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            duration_seconds=job.duration_seconds,
        )


class MatchSubmitResponse(BaseModel):
    batch_id: uuid.UUID
    jobs: list[dict]
    total_submitted: int
    message: str = "Jobs enqueued. Poll GET /api/v1/matches or GET /api/v1/matches/{id} for results."


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class MatchListResponse(BaseModel):
    data: list[MatchJobResponse]
    pagination: PaginationMeta


# ── Error schemas ───────────────────────────────────────────────────────────
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
