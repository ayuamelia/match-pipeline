import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from app.config import settings

log = logging.getLogger(__name__)

# ── Celery factory ──────────────────────────────────────────────────────────
def create_celery() -> Celery:
    app = Celery(
        "pelgo",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.worker"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        result_expires=settings.celery_result_expires,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_default_queue="scoring",
        task_soft_time_limit=settings.worker_task_timeout,
        task_time_limit=settings.worker_task_timeout + 30,
        timezone="UTC",
        enable_utc=True,
    )
    return app


celery_app = create_celery()


# ── Sync DB session (worker only) ───────────────────────────────────────────
def _make_sync_session() -> Session:
    engine = create_engine(
        settings.sync_database_url,
        pool_size=2,
        max_overflow=5,
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine)()


# ── Scoring logic ───────────────────────────────────────────────────────────
SENIORITY_RANK: dict[str, int] = {
    "intern": 0, "junior": 1, "mid": 2, "senior": 3,
    "lead": 4, "principal": 5, "staff": 5, "director": 6,
}

SKILL_ALIASES: dict[str, list[str]] = {
    "Python": ["python", "python3"],
    "JavaScript": ["javascript", "js", "es6"],
    "TypeScript": ["typescript", "ts"],
    "Go": ["golang", " go "],
    "Java": ["java"],
    "Rust": ["rust"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "NestJS": ["nestjs", "nest.js"],
    "Express": ["express", "express.js"],
    "Spring Boot": ["spring boot", "springboot"],
    "React": ["react", "react.js"],
    "Next.js": ["next.js", "nextjs"],
    "Vue": ["vue", "vue.js"],
    "Angular": ["angular"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "opensearch"],
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud"],
    "Azure": ["azure", "microsoft azure"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Terraform": ["terraform"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration"],
    "Git": ["git", "github", "gitlab"],
    "REST API": ["rest api", "restful", "rest"],
    "GraphQL": ["graphql"],
    "Microservices": ["microservices", "micro services"],
    "System Design": ["system design", "distributed systems"],
    "Celery": ["celery"],
    "SQLAlchemy": ["sqlalchemy"],
    "Kafka": ["kafka"],
    "Agile": ["agile", "scrum"],
    "Machine Learning": ["machine learning", "ml"],
    "TypeScript": ["typescript", "ts"],
}


def _extract_skills(text: str) -> list[str]:
    import re
    text_lower = text.lower()
    found: set[str] = set()
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text_lower):
                found.add(canonical)
                break
    return sorted(found)


def _extract_seniority(text: str) -> str | None:
    text_lower = text.lower()
    checks = [
        ("director", ["director", "head of engineering"]),
        ("principal", ["principal", "staff engineer"]),
        ("lead", ["tech lead", "team lead", " lead "]),
        ("senior", ["senior", "sr."]),
        ("mid", ["mid-level", " mid ", "intermediate"]),
        ("junior", ["junior", "jr.", "entry level", "entry-level", "graduate"]),
        ("intern", ["intern", "internship"]),
    ]
    for level, keywords in checks:
        if any(kw in text_lower for kw in keywords):
            return level
    return None


def _extract_title(text: str) -> str | None:
    import re
    m = re.search(r"(?:job title|position|role|title)\s*:?\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
        if len(t) <= 100:
            return t
    lines = text.strip().split("\n")
    if lines and len(lines[0].strip()) <= 100:
        return lines[0].strip()
    return None


def _score_skills(required: list[str], candidate_skills: list[str]) -> tuple[int, list[str], list[str]]:
    if not required:
        return 70, [], []
    cand_lower = {s.lower() for s in candidate_skills}
    req_lower = {s.lower(): s for s in required}
    matched = [name for k, name in req_lower.items() if k in cand_lower]
    missing = [name for k, name in req_lower.items() if k not in cand_lower]
    base = round(len(matched) / len(required) * 100)
    bonus = min(15, ((len(candidate_skills) - len(matched)) // 3) * 5)
    return min(100, base + bonus), matched, missing


def _score_experience(req_seniority: str | None, cand_seniority: str, cand_years: int) -> tuple[int, str]:
    if not req_seniority:
        return 75, "No seniority requirement specified."
    req_rank = SENIORITY_RANK.get(req_seniority, 2)
    cand_rank = SENIORITY_RANK.get(cand_seniority, 2)
    diff = cand_rank - req_rank
    if diff == 0:
        score, note = 100, f"Exact seniority match: {cand_seniority}."
    elif diff >= 2:
        score, note = 75, f"Over-qualified ({cand_seniority}) for {req_seniority} role."
    elif diff == 1:
        score, note = 85, f"Slightly over-qualified ({cand_seniority}) for {req_seniority}."
    elif diff == -1:
        score, note = 60, f"Slightly under required ({req_seniority}), you are {cand_seniority}."
    elif diff == -2:
        score, note = 30, f"Significant seniority gap: required {req_seniority}, you are {cand_seniority}."
    else:
        score, note = 0, f"Seniority mismatch too large: required {req_seniority}, you are {cand_seniority}."
    if cand_years >= 7 and diff < 0:
        score = min(100, score + 10)
        note += f" Your {cand_years} years of experience is a positive signal."
    return score, note


def _score_location(job_title: str | None, cand_location: str | None, willing: bool) -> tuple[int, str]:
    if not cand_location:
        return 70, "Candidate location not specified."
    return 80, "Location scoring uses job description text; remote-friendly roles score higher."


def _build_recommendation(score: int, missing: list[str], title: str | None) -> str:
    role = f'"{title}"' if title else "this role"
    if score >= 80:
        return f"Strong match for {role}. Apply with confidence."
    elif score >= 60:
        gap = f" Consider building: {', '.join(missing[:3])}." if missing else ""
        return f"Good match for {role} with some gaps.{gap} Worth applying."
    elif score >= 40:
        gap = f" Key skills to develop: {', '.join(missing[:3])}." if missing else ""
        return f"Partial match for {role}.{gap} Skill-building recommended before applying."
    else:
        return f"Significant gaps for {role}. Focus on skill development first."


# ── Celery task ─────────────────────────────────────────────────────────────
@celery_app.task(
    bind=True,
    name="app.worker.score_job",
    max_retries=settings.worker_max_retries,
    queue="scoring",
)
def score_job(self: Task, job_id: str) -> dict[str, Any]:
    logger = logging.LoggerAdapter(log, {"job_id": job_id, "attempt": self.request.retries + 1})
    logger.info("task_received")

    session = _make_sync_session()

    try:
        from app.models import Candidate, MatchJob

        job = session.execute(
            select(MatchJob).where(MatchJob.id == uuid.UUID(job_id))
        ).scalar_one_or_none()

        if not job:
            logger.error("job_not_found")
            return {"status": "error", "reason": "not_found"}

        if job.status in ("completed", "failed"):
            logger.warning(f"task_skipped_terminal_status status={job.status!r}")
            return {"status": "skipped"}

        candidate = session.execute(
            select(Candidate).where(Candidate.id == job.candidate_id)
        ).scalar_one_or_none()

        if not candidate:
            logger.error("candidate_not_found")
            job.status = "failed"
            job.error_message = "Candidate profile not found."
            session.commit()
            return {"status": "failed"}

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.retry_count = self.request.retries
        session.commit()
        logger.info("task_processing")

        # Resolve job text
        job_text = job.raw_input
        job.job_description = job_text

        # Parse JD
        title = _extract_title(job_text)
        seniority = _extract_seniority(job_text)
        skills = _extract_skills(job_text)

        job.job_title = title
        job.required_seniority = seniority
        job.required_skills = skills

        logger.info(f"jd_parsed title={title!r} seniority={seniority!r} skills_found={len(skills)}")

        # Score
        cand = {
            "skills": candidate.skills or [],
            "years_of_experience": candidate.years_of_experience,
            "seniority_level": candidate.seniority_level,
            "location": candidate.location,
            "willing_to_relocate": candidate.willing_to_relocate,
        }

        skills_score, matched, missing = _score_skills(skills, cand["skills"])
        exp_score, exp_note = _score_experience(seniority, cand["seniority_level"], cand["years_of_experience"])
        loc_score, loc_note = _score_location(title, cand["location"], cand["willing_to_relocate"])

        overall = round(skills_score * 0.5 + exp_score * 0.3 + loc_score * 0.2)
        overall = max(0, min(100, overall))

        now = datetime.now(timezone.utc)
        job.status = "completed"
        job.completed_at = now
        job.overall_score = overall
        job.skills_score = skills_score
        job.experience_score = exp_score
        job.location_score = loc_score
        job.matched_skills = matched
        job.missing_skills = missing
        job.recommendation = _build_recommendation(overall, missing, title)
        job.score_explanation = {"skills": _build_skills_note(skills_score, matched, missing), "experience": exp_note, "location": loc_note}
        job.error_message = None

        session.commit()

        duration = (now - job.started_at).total_seconds()
        logger.info(f"task_completed overall_score={overall} duration={round(duration, 2)}")
        return {"status": "completed", "job_id": job_id, "score": overall}

    except SoftTimeLimitExceeded:
        logger.warning("task_soft_timeout")
        try:
            job.status = "failed"
            job.error_message = f"Task timed out after {settings.worker_task_timeout}s."
            session.commit()
        except Exception:
            pass
        return {"status": "timeout"}

    except Exception as exc:
        logger.error(f"task_error error={str(exc)!r} error_type={type(exc).__name__}")
        try:
            backoff = settings.worker_retry_backoff_base * (2 ** self.request.retries)
            job.status = "failed"
            job.error_message = f"Attempt {self.request.retries + 1} failed: {exc}"
            job.retry_count = self.request.retries + 1
            session.commit()
            raise self.retry(exc=exc, countdown=backoff)
        except self.MaxRetriesExceededError:
            logger.error(f"task_max_retries_exceeded final_error={str(exc)!r}")
            job.status = "failed"
            job.error_message = f"Failed after {settings.worker_max_retries} attempts: {exc}"
            session.commit()
            return {"status": "permanently_failed"}

    finally:
        session.close()


def _build_skills_note(score: int, matched: list[str], missing: list[str]) -> str:
    parts = []
    if matched:
        parts.append(f"Matched {len(matched)} skill(s): {', '.join(matched[:5])}{'...' if len(matched) > 5 else ''}.")
    if missing:
        parts.append(f"Missing {len(missing)} skill(s): {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}.")
    return " ".join(parts) if parts else "No specific skills listed in job description."
