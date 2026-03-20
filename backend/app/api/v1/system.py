import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import check_db_connection

router = APIRouter(tags=["system"])
_start_time = time.time()


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


@router.get("/ready", include_in_schema=False)
async def readiness() -> JSONResponse:
    from redis.asyncio import Redis
    from sqlalchemy import text

    from app.database import AsyncSessionLocal

    checks: dict[str, bool] = {}

    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False

    try:
        r = Redis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    all_ok = all(checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )


@router.get("/metrics", summary="System stats")
async def metrics() -> dict:
    """
    A quick snapshot of how the system is doing — how many jobs are in
    each status, average scores for completed jobs, and which scoring
    mode is active (rule-based or LLM-backed).

    This is not a Prometheus-compatible endpoint. It is meant for a quick
    sanity check during development or after a deployment, not for
    production monitoring dashboards.
    """
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import MatchJob

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(MatchJob.status, func.count(MatchJob.id).label("n"), func.avg(MatchJob.overall_score).label("avg"))
            .group_by(MatchJob.status)
        )).all()

    return {
        "environment": settings.environment,
        "scoring_mode": "llm" if settings.use_llm_scoring else "rule_based",
        "uptime_seconds": round(time.time() - _start_time, 2),
        "by_status": {
            r.status: {"count": r.n, "avg_score": round(float(r.avg), 1) if r.avg else None}
            for r in rows
        },
    }
    
@router.get("/me", summary="Current candidate profile")
async def get_candidate() -> dict:
    """
    Returns the candidate profile that all job descriptions are scored against.
    Useful for understanding what skills and experience level the system is comparing with.
    """
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models import Candidate

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Candidate).where(
                Candidate.id == uuid.UUID(settings.candidate_id)
            )
        )
        candidate = result.scalar_one_or_none()

    if not candidate:
        return {"error": "Candidate profile not found"}

    return {
        "name": candidate.name,
        "location": candidate.location,
        "seniority_level": candidate.seniority_level,
        "years_of_experience": candidate.years_of_experience,
        "willing_to_relocate": candidate.willing_to_relocate,
        "skills": candidate.skills,
        "summary": candidate.summary,
    }
