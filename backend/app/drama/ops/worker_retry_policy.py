from __future__ import annotations

from dataclasses import dataclass
from typing import Type


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    max_retries: int
    backoff_seconds: int
    send_to_dead_letter: bool = False
    reason: str = ""


class WorkerRetryPolicy:
    TRANSIENT_ERRORS = {"OperationalError", "TimeoutError", "ConnectionError"}
    NON_RETRYABLE_ERRORS = {"ValidationError", "IntegrityError", "ContractError"}

    def classify(self, exc: Exception, retry_count: int) -> RetryDecision:
        error_name = exc.__class__.__name__

        if error_name in self.NON_RETRYABLE_ERRORS:
            return RetryDecision(
                should_retry=False,
                max_retries=retry_count,
                backoff_seconds=0,
                send_to_dead_letter=True,
                reason="non_retryable_error",
            )

        if error_name in self.TRANSIENT_ERRORS:
            max_retries = 5
            if retry_count >= max_retries:
                return RetryDecision(
                    should_retry=False,
                    max_retries=max_retries,
                    backoff_seconds=0,
                    send_to_dead_letter=True,
                    reason="transient_error_retry_exhausted",
                )
            return RetryDecision(
                should_retry=True,
                max_retries=max_retries,
                backoff_seconds=min(300, 2 ** max(retry_count, 1)),
                send_to_dead_letter=False,
                reason="transient_error",
            )

        if retry_count >= 3:
            return RetryDecision(
                should_retry=False,
                max_retries=3,
                backoff_seconds=0,
                send_to_dead_letter=True,
                reason="unknown_error_retry_exhausted",
            )

        return RetryDecision(
            should_retry=True,
            max_retries=3,
            backoff_seconds=15 * max(retry_count, 1),
            send_to_dead_letter=False,
            reason="unknown_error",
        )
