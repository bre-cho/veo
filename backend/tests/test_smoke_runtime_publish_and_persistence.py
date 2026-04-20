from __future__ import annotations


def test_smoke_runtime_publish_and_persistence_flow(api_client) -> None:
    plan_resp = api_client.post(
        "/api/v1/channel/generate-plan",
        json={"channel_name": "Creator", "niche": "fitness", "days": 2, "posts_per_day": 1},
    )
    assert plan_resp.status_code == 200
    plan_payload = plan_resp.json()
    plan_id = plan_payload["plan_id"]

    queue_resp = api_client.post("/api/v1/channel/build-publish-queue", json=plan_payload)
    assert queue_resp.status_code == 200
    jobs = queue_resp.json()["publish_jobs"]
    assert jobs
    first_job = jobs[0]
    first_job_id = first_job["id"]
    assert first_job["publish_mode"] == "SIMULATED"

    run_job_resp = api_client.post(f"/api/v1/channel/publish-jobs/{first_job_id}/run")
    assert run_job_resp.status_code == 200
    run_job_payload = run_job_resp.json()
    assert run_job_payload["status"] == "published"
    assert run_job_payload["publish_mode"] == "SIMULATED"
    assert run_job_payload["provider_response"]["mode"] == "SIMULATED"
    assert run_job_payload["provider_response"]["raw"]["mode"] == "SIMULATED"
    assert "SIMULATED publish" in run_job_payload["provider_response"]["raw"]["note"]

    job_history_resp = api_client.get(f"/api/v1/channel/publish-jobs/{first_job_id}")
    assert job_history_resp.status_code == 200
    assert job_history_resp.json()["status"] == "published"

    channel_history_resp = api_client.get(f"/api/v1/channel/history/{plan_id}")
    assert channel_history_resp.status_code == 200
    assert channel_history_resp.json()["status"] == "completed"

    trend_resp = api_client.post(
        "/api/v1/trend-images/generate",
        json={"topic": "protein shake", "niche": "fitness", "market_code": "VN"},
    )
    assert trend_resp.status_code == 200
    trend_payload = trend_resp.json()
    run_id = trend_payload["run_id"]
    assert run_id

    creative_history_resp = api_client.get("/api/v1/creative-runs?engine_type=trend_image")
    assert creative_history_resp.status_code == 200
    run_ids = [item["id"] for item in creative_history_resp.json()["items"]]
    assert run_id in run_ids

    creative_run_resp = api_client.get(f"/api/v1/creative-runs/{run_id}")
    assert creative_run_resp.status_code == 200
    creative_run_payload = creative_run_resp.json()
    assert creative_run_payload["status"] == "completed"
    assert creative_run_payload["engine_type"] == "trend_image"
    assert creative_run_payload["input_payload"]["topic"] == "protein shake"
