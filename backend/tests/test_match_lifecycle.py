import pytest

@pytest.mark.asyncio
async def test_full_job_lifecycle(client):
    job_description = """
    Senior Python Engineer — Remote

    We are looking for a Senior Python Engineer to join our backend team.
    You will build scalable APIs using FastAPI and PostgreSQL.

    Requirements:
    - 5+ years of Python experience
    - Strong knowledge of FastAPI, PostgreSQL, and Docker
    - Experience with AWS and Kubernetes
    - Familiarity with CI/CD pipelines and Git

    Location: Remote (Singapore preferred)
    """

    # Step 1: Submit the job
    submit_response = await client.post(
        "/api/v1/matches",
        json={"jobs": [{"content": job_description}]},
    )
    assert submit_response.status_code == 202, submit_response.text

    body = submit_response.json()
    assert body["total_submitted"] == 1
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["status"] == "pending"

    job_id = body["jobs"][0]["id"]
    batch_id = body["batch_id"]

    # Step 2: Fetch the single job result
    get_response = await client.get(f"/api/v1/matches/{job_id}")
    assert get_response.status_code == 200

    result = get_response.json()
    assert result["id"] == job_id
    assert result["status"] == "completed"
    assert result["overall_score"] is not None
    assert 0 <= result["overall_score"] <= 100

    dim = result["dimension_scores"]
    assert dim["skills"] is not None
    assert dim["experience"] is not None
    assert dim["location"] is not None
    for score in [dim["skills"], dim["experience"], dim["location"]]:
        assert 0 <= score <= 100

    assert isinstance(result["matched_skills"], list)
    assert isinstance(result["missing_skills"], list)

    assert result["recommendation"]
    assert len(result["recommendation"]) > 0

    assert result["started_at"] is not None
    assert result["completed_at"] is not None

    # Step 3: Verify the job appears in the list endpoint
    list_response = await client.get(
        "/api/v1/matches",
        params={"batch_id": batch_id, "status": "completed"},
    )
    assert list_response.status_code == 200

    list_body = list_response.json()
    assert list_body["pagination"]["total"] == 1
    assert list_body["data"][0]["id"] == job_id


@pytest.mark.asyncio
async def test_batch_submission(client):
    jobs = [
        {"content": "Python backend engineer with Django and PostgreSQL experience required."},
        {"content": "Frontend developer: React, TypeScript, Next.js. Three years minimum."},
        {"content": "DevOps engineer: Kubernetes, Terraform, AWS, CI/CD pipelines."},
    ]

    response = await client.post("/api/v1/matches", json={"jobs": jobs})
    assert response.status_code == 202

    body = response.json()
    assert body["total_submitted"] == 3
    assert len(body["jobs"]) == 3

    for job_entry in body["jobs"]:
        r = await client.get(f"/api/v1/matches/{job_entry['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_validation_rejects_empty_batch(client):
    response = await client.post("/api/v1/matches", json={"jobs": []})
    assert response.status_code == 422

    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["field"] is not None


@pytest.mark.asyncio
async def test_validation_rejects_oversized_batch(client):
    jobs = [{"content": f"Job description number {i} with enough text to pass min_length validation check."}
            for i in range(11)]
    response = await client.post("/api/v1/matches", json={"jobs": jobs})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_validation_rejects_duplicates(client):
    same = "Python senior engineer with FastAPI experience needed for backend role."
    response = await client.post(
        "/api/v1/matches",
        json={"jobs": [{"content": same}, {"content": same}]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_nonexistent_job_returns_404(client):
    import uuid
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/matches/{fake_id}")
    assert response.status_code == 404

    error = response.json()["error"]
    assert error["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_pagination(client):
    jobs = [
        {"content": "Senior Python engineer with FastAPI and PostgreSQL knowledge required."},
        {"content": "Backend developer with Go and Kubernetes expertise for cloud platform."},
    ]
    await client.post("/api/v1/matches", json={"jobs": jobs})

    r1 = await client.get("/api/v1/matches", params={"limit": 1, "offset": 0})
    assert r1.status_code == 200
    body1 = r1.json()
    assert len(body1["data"]) == 1
    assert body1["pagination"]["has_more"] is True

    r2 = await client.get("/api/v1/matches", params={"limit": 1, "offset": 1})
    body2 = r2.json()
    assert len(body2["data"]) == 1
    assert body1["data"][0]["id"] != body2["data"][0]["id"]


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
