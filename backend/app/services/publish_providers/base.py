from __future__ import annotations

from typing import Any

from app.models.publish_job import PublishJob


class PublishProviderBase:
    """Abstraction layer for publish providers.

    Subclasses must implement ``execute(job)`` and return a dict with at
    minimum ``{"ok": bool, ...}``.

    ``refresh_token()`` and ``check_quota()`` are optional extension points for
    providers that support token rotation and quota inspection.  The default
    implementations are no-ops so existing providers remain unaffected.
    """

    def execute(self, job: PublishJob) -> dict[str, Any]:
        raise NotImplementedError

    def refresh_token(self) -> None:
        """Refresh the provider's access token.

        Called by the scheduler before a publish batch when the token is close
        to expiry.  Default implementation is a no-op; override in platform
        providers that support token rotation.
        """

    def check_quota(self) -> dict[str, Any]:
        """Return quota / rate-limit status for the provider.

        Returns a dict with at minimum ``{"ok": bool}``.  When ``ok`` is
        ``False`` the scheduler will skip the batch and log a warning.
        Default implementation always returns ``{"ok": True}``.
        """
        return {"ok": True}

