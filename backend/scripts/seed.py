import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.dialects.postgresql import insert
from app.config import settings
from app.models import Candidate

CANDIDATE_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

CANDIDATE = {
    "id": CANDIDATE_ID,
    "name": "Ayu Amelia",
    "email": "ayu@pelgo-demo.com",
    "location": "Bintaro, South Tangerang, Indonesia",
    "willing_to_relocate": True,
    "years_of_experience": 12,
    "seniority_level": "senior",
    "skills": [
        "Python", "PHP", "TypeScript", "Java", "Go",
        "FastAPI", "NestJS", "Spring", "React Native",
        "PostgreSQL", "Oracle", "MySQL",
        "REST API", "Microservices", "System Design",
        "Docker", "Git", "CI/CD", "Agile",
        "SQLAlchemy", "Celery", "Redis",
    ],
    "summary": (
        "Senior Backend Engineer and Project Manager with 12+ years of experience "
        "across financial sector, IT services, banking, and state-owned enterprises. "
        "Specialised in system integration, microservices architecture, and database management. "
        "Currently holding a dual role as PM and Developer at PT PELNI, "
        "with hands-on expertise across Python, PHP, TypeScript, and Java ecosystems. "
        "Actively pursuing international opportunities with strong German (B2) "
        "and English (C1) language skills."
    ),
}


async def seed(session: AsyncSession) -> bool:
    stmt = (
        insert(Candidate)
        .values(**CANDIDATE)
        .on_conflict_do_nothing(index_elements=["email"])
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def main() -> None:
    print("=" * 56)
    print("Pelgo — Database Seeder")
    print("=" * 56)

    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session:
            inserted = await seed(session)
            await session.commit()

        status = "Inserted new candidate." if inserted else "Candidate already exists — skipped."
        print(f"\n{status}")
        print(f"\nName   : {CANDIDATE['name']}")
        print(f"Email  : {CANDIDATE['email']}")
        print(f"Skills : {len(CANDIDATE['skills'])} skills")
        print(f"\nAdd this to your .env file:")
        print(f"\n  CANDIDATE_ID={CANDIDATE_ID}\n")
    except Exception as e:
        print(f"\nSeed failed: {e}")
        print("Make sure migrations have run first: alembic upgrade head")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())