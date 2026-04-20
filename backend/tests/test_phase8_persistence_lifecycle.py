from __future__ import annotations


def test_optimization_persisted_history(api_client) -> None:
    response = api_client.post(
        "/api/v1/optimization/analyze",
        json={
            "project_id": "proj-1",
            "metrics": {"hook_strength": 0.2, "cta_quality": 0.3, "clarity": 0.4, "trust": 0.5},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("run_id")
    assert payload.get("winner_candidate_id")
    assert payload.get("candidates")

    run_id = payload["run_id"]
    history = api_client.get(f"/api/v1/optimization/history/{run_id}")
    assert history.status_code == 200
    assert history.json()["status"] == "completed"


def test_channel_plan_and_publish_job_lifecycle(api_client) -> None:
    plan_resp = api_client.post(
        "/api/v1/channel/generate-plan",
        json={"channel_name": "Creator", "niche": "fitness", "days": 2, "posts_per_day": 1},
    )
    assert plan_resp.status_code == 200
    plan_payload = plan_resp.json()
    assert plan_payload.get("plan_id")
    assert plan_payload.get("winner_candidate_id")
    assert plan_payload.get("candidates")

    queue_resp = api_client.post("/api/v1/channel/build-publish-queue", json=plan_payload)
    assert queue_resp.status_code == 200
    jobs = queue_resp.json()["publish_jobs"]
    assert jobs
    first_job_id = jobs[0]["id"]
    assert jobs[0]["status"] == "queued"

    run_job_resp = api_client.post(f"/api/v1/channel/publish-jobs/{first_job_id}/run")
    assert run_job_resp.status_code == 200
    assert run_job_resp.json()["status"] == "published"

    plan_id = plan_payload["plan_id"]
    history_resp = api_client.get(f"/api/v1/channel/history/{plan_id}")
    assert history_resp.status_code == 200
    assert history_resp.json()["status"] == "completed"
