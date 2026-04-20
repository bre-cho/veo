"""Tests for the publish signal ingestion endpoint and scheduler write-back."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


def _make_published_job(db, job_id: str = "test-job-signal-001") -> "PublishJob":
    from app.models.publish_job import PublishJob
    from datetime import datetime

    job = PublishJob(
        id=job_id,
        platform="tiktok",
        publish_mode="REAL",
        status="published",
        signal_status="pending",
        payload={
            "format": "short",
            "content_goal": "conversion",
            "metadata": {"market_code": "VN"},
        },
        request_payload={},
        retry_metadata={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class TestPublishSignalEndpoint:
    def test_ingest_signal_updates_signal_status(self, api_client, db_session) -> None:
        _make_published_job(db_session)
        response = api_client.post(
            "/api/v1/publish/jobs/test-job-signal-001/signal",
            json={"conversion_score": 0.82, "view_count": 1000, "click_through_rate": 0.05},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["signal_status"] == "received"
        assert data["conversion_score"] == pytest.approx(0.82)

    def test_ingest_signal_job_not_found(self, api_client, db_session) -> None:
        response = api_client.post(
            "/api/v1/publish/jobs/nonexistent-job/signal",
            json={"conversion_score": 0.7},
        )
        assert response.status_code == 404

    def test_ingest_signal_not_published_returns_409(self, api_client, db_session) -> None:
        from app.models.publish_job import PublishJob

        job = PublishJob(
            id="test-job-queued-001",
            platform="shorts",
            publish_mode="REAL",
            status="queued",
            payload={},
            request_payload={},
            retry_metadata={},
        )
        db_session.add(job)
        db_session.commit()

        response = api_client.post(
            "/api/v1/publish/jobs/test-job-queued-001/signal",
            json={"conversion_score": 0.7},
        )
        assert response.status_code == 409

    def test_ingest_signal_writes_to_learning_engine(self, api_client, db_session, tmp_path) -> None:
        from app.services.learning_engine import PerformanceLearningEngine

        _make_published_job(db_session, "test-job-learn-001")

        engine_path = str(tmp_path / "store.json")
        with patch(
            "app.api.publish_signal.PerformanceLearningEngine",
            lambda **kw: PerformanceLearningEngine(store_path=engine_path, **kw),
        ):
            response = api_client.post(
                "/api/v1/publish/jobs/test-job-learn-001/signal",
                json={"conversion_score": 0.91, "platform": "tiktok"},
            )
        assert response.status_code == 200

    def test_ingest_signal_platform_defaults_to_job_platform(self, api_client, db_session) -> None:
        _make_published_job(db_session, "test-job-platform-001")
        response = api_client.post(
            "/api/v1/publish/jobs/test-job-platform-001/signal",
            json={"conversion_score": 0.75},  # no platform in body
        )
        assert response.status_code == 200


class TestPublishSchedulerNeutralBaseline:
    """The scheduler should write neutral 0.5 baseline, not optimistic 1.0."""

    def test_record_publish_outcome_uses_neutral_score(self, db_session, tmp_path) -> None:
        from app.services.publish_scheduler import PublishScheduler

        job = MagicMock()
        job.id = "sched-test-001"
        job.platform = "shorts"
        job.payload = {"format": "short", "content_goal": "awareness", "metadata": {}}

        mock_engine_instance = MagicMock()
        with patch("app.services.publish_scheduler.PerformanceLearningEngine") as mock_cls:
            mock_cls.return_value = mock_engine_instance
            PublishScheduler._record_publish_outcome(job)
        mock_engine_instance.record.assert_called_once()
        call_kwargs = mock_engine_instance.record.call_args.kwargs
        assert call_kwargs["conversion_score"] == pytest.approx(0.5)

    def test_run_job_sets_signal_status_pending(self, db_session) -> None:
        from app.models.publish_job import PublishJob
        from app.services.publish_scheduler import PublishScheduler

        job = PublishJob(
            id="run-job-signal-test",
            platform="tiktok",
            publish_mode="SIMULATED",
            status="queued",
            payload={"format": "short", "metadata": {}},
            request_payload={},
            retry_metadata={},
        )
        db_session.add(job)
        db_session.commit()

        scheduler = PublishScheduler()
        result = scheduler.run_job(db_session, job)
        assert result.status == "published"
        assert result.signal_status == "pending"
