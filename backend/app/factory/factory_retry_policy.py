from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryDecision:
    action: str  # retry | downgrade | human_review | block
    max_retries: int
    reason: str


class FactoryRetryPolicy:
    def decide(self, error_code: str | None, stage_name: str, attempt: int) -> RetryDecision:
        del stage_name
        del attempt
        code = (error_code or "unknown_error").lower()

        if any(x in code for x in ["timeout", "connection", "temporary", "rate_limit"]):
            return RetryDecision("retry", 2, "transient_error")

        if any(x in code for x in ["db", "redis", "celery", "storage", "infra"]):
            return RetryDecision("retry", 1, "infra_error")

        if any(x in code for x in ["qa", "validation", "artifact", "manifest"]):
            return RetryDecision("human_review", 0, "validation_fail")

        if any(x in code for x in ["policy", "blocked", "forbidden", "fatal"]):
            return RetryDecision("block", 0, "fatal_error")

        return RetryDecision("retry", 1, "unknown_retryable")
