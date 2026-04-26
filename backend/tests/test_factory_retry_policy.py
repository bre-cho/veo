from __future__ import annotations

from app.factory.factory_retry_policy import FactoryRetryPolicy


def test_retry_policy_transient_error_is_retry() -> None:
    decision = FactoryRetryPolicy().decide("connection_timeout", "EXECUTE_RENDER", 0)
    assert decision.action == "retry"
    assert decision.reason == "transient_error"


def test_retry_policy_validation_error_is_human_review() -> None:
    decision = FactoryRetryPolicy().decide("artifact_validation_failed", "QA_VALIDATE", 1)
    assert decision.action == "human_review"
    assert decision.reason == "validation_fail"
