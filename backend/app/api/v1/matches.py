import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import MatchJob
from app.schemas import (
    ErrorDetail,
    JobStatus,
    MatchJobResponse,
    MatchListResponse,
    MatchSubmitRequest,
    MatchSubmitResponse,
    PaginationMeta,
)
from app.worker import score_job

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post(
    "",
    response_model=MatchSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit jobs for scoring",
)
async def submit_matches(
    payload: MatchSubmitRequest,
    db: AsyncSession = Depends(get_db),
) -> MatchSubmitResponse:
    """
    Submit between 1 and 10 job descriptions in a single batch.
    Each entry can be plain text pasted from a job posting, or a URL
    pointing to one.

    The response comes back immediately with a list of job IDs — the
    actual scoring happens in the background. Use the returned `batch_id`
    to track progress, or poll individual job IDs if you only care about
    one result at a time.

    Duplicate entries within the same batch are rejected. Submitting
    the same description twice in one request is almost certainly a mistake,
    so the API catches it early rather than silently wasting compute.
    """
    candidate_id = uuid.UUID(settings.candidate_id)
    batch_id = uuid.uuid4()

    jobs: list[MatchJob] = []
    for submission in payload.jobs:
        job = MatchJob(
            candidate_id=candidate_id,
            batch_id=batch_id,
            raw_input=submission.content,
            status="pending",
            job_title=submission.title or None,
        )
        db.add(job)
        jobs.append(job)

    await db.flush()
    await db.commit()

    for job in jobs:
        score_job.apply_async(
            args=[str(job.id)],
            task_id=str(job.id),
            countdown=1,
            queue="scoring",
        )

    return MatchSubmitResponse(
        batch_id=batch_id,
        jobs=[{"id": str(j.id), "status": "pending"} for j in jobs],
        total_submitted=len(jobs),
    )


@router.get(
    "/{job_id}",
    response_model=MatchJobResponse,
    summary="Get a single job result",
)
async def get_match(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MatchJobResponse:
    """
    Fetch the current state of one scoring job.

    The response shape is the same regardless of where the job is in its
    lifecycle — fields like `overall_score`, `matched_skills`, and
    `recommendation` will simply be `null` until the worker finishes.
    Your client should handle null values for those fields gracefully.

    Status values mean exactly what they say: `pending` means the job is
    waiting in the queue, `processing` means a worker has picked it up,
    `completed` means results are ready, and `failed` means something went
    wrong (the `error_message` field will tell you what).
    """
    candidate_id = uuid.UUID(settings.candidate_id)

    result = await db.execute(
        select(MatchJob).where(
            MatchJob.id == job_id,
            MatchJob.candidate_id == candidate_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetail(
                code="JOB_NOT_FOUND",
                message=f"Match job {job_id} not found.",
                details={"job_id": str(job_id)},
            ).model_dump(),
        )

    return MatchJobResponse.from_orm_model(job)


@router.get(
    "",
    response_model=MatchListResponse,
    summary="List match results",
)
async def list_matches(
    db: AsyncSession = Depends(get_db),
    job_status: Annotated[
        JobStatus | None,
        Query(alias="status", description="Filter by job status"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=settings.max_page_limit),
    ] = settings.default_page_limit,
    offset: Annotated[int, Query(ge=0)] = 0,
    batch_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter to a specific submission batch"),
    ] = None,
) -> MatchListResponse:
    """
    Returns a paginated list of match jobs for the current candidate.

    You can filter by **status** to see only jobs that are still running,
    or only the ones that finished. Use **batch_id** to narrow results down
    to a single submission if you submitted multiple batches and want to
    track them separately.

    For real-time updates after a submission, poll this endpoint every few
    seconds with your `batch_id`. Once every job in the response has a
    status of `completed` or `failed`, you can stop — nothing will change
    after that point.

    The `pagination` object in the response tells you the total number of
    matching jobs and whether there are more pages to fetch.
    """
    candidate_id = uuid.UUID(settings.candidate_id)

    base = select(MatchJob).where(MatchJob.candidate_id == candidate_id)
    if job_status:
        base = base.where(MatchJob.status == job_status)
    if batch_id:
        base = base.where(MatchJob.batch_id == batch_id)

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    data_result = await db.execute(
        base.order_by(MatchJob.enqueued_at.desc()).limit(limit).offset(offset)
    )
    jobs = data_result.scalars().all()

    return MatchListResponse(
        data=[MatchJobResponse.from_orm_model(j) for j in jobs],
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        ),
    )
