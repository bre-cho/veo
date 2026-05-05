import hashlib

import httpx

from apps.api.core.config import settings
from packages.provider_adapters.base import ProviderError

class CanvaMockAdapter:
    def create_layout(self, payload: dict) -> dict:
        raw = str(payload).encode()
        digest = hashlib.sha256(raw).hexdigest()[:16]
        return {
            "provider": "canva_mock",
            "canva_design_id": f"canva_mock_{digest}",
            "export_url": f"mock://canva/{digest}.pdf",
            "metadata": {"mode": "mock", "layout_hash": digest},
        }


class CanvaProductionAdapter:
    def __init__(self, access_token: str, base_url: str | None = None):
        self.access_token = access_token
        self.base_url = (base_url or settings.canva_api_base_url).rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _validate_layout_rules(self, payload: dict) -> None:
        prompt = str(payload.get("prompt", "")).lower()
        if "product" not in prompt:
            raise ProviderError("canva", "INVALID_PROMPT", retryable=False, message="Prompt must include product focus")
        if "cta" not in prompt and "offer" not in prompt:
            raise ProviderError("canva", "INVALID_PROMPT", retryable=False, message="Prompt must include CTA or offer")

    def _map_error(self, response: httpx.Response) -> ProviderError:
        status = response.status_code
        if status in (401, 403):
            return ProviderError("canva", "AUTH", retryable=False, message="Canva authentication failed")
        if status == 429:
            return ProviderError("canva", "RATE_LIMIT", retryable=True, message="Canva rate limit exceeded")
        if 500 <= status <= 599:
            return ProviderError("canva", "PROVIDER_DOWN", retryable=True, message="Canva service unavailable")
        return ProviderError("canva", "INVALID_PROMPT", retryable=False, message=f"Canva request failed: {status}")

    def create_layout(self, payload: dict) -> dict:
        self._validate_layout_rules(payload)
        request_payload = {
            "template_id": payload.get("template_id"),
            "brand_template_id": payload.get("template_id"),
            "data": {
                "prompt": payload.get("prompt"),
                "offer": payload.get("offer"),
                "brand": payload.get("brand"),
            },
            "export": {
                "formats": ["png"],
                "sizes": ["4:5", "1:1", "9:16"],
            },
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/rest/v1/autofills",
                headers=self._headers(),
                json=request_payload,
            )
            if response.status_code >= 400:
                raise self._map_error(response)
            data = response.json()

        job_id = data.get("job_id") or data.get("id")
        if not job_id:
            raise ProviderError("canva", "PROVIDER_DOWN", retryable=True, message="Canva response missing job id")

        with httpx.Client(timeout=30.0) as client:
            poll_response = client.get(f"{self.base_url}/rest/v1/autofills/{job_id}", headers=self._headers())
            if poll_response.status_code >= 400:
                raise self._map_error(poll_response)
            poll_data = poll_response.json()

        design_id = poll_data.get("design_id") or poll_data.get("design", {}).get("id")
        exports = poll_data.get("exports") or []
        export_url = poll_data.get("export_url") or (exports[0].get("url") if exports else None)
        if not design_id or not export_url:
            raise ProviderError("canva", "PROVIDER_DOWN", retryable=True, message="Canva response missing design/export")

        return {
            "provider": "canva",
            "canva_design_id": design_id,
            "export_url": export_url,
            "metadata": {
                "template_id": poll_data.get("template_id") or payload.get("template_id"),
                "brand_id": poll_data.get("brand_id") or payload.get("brand_id"),
                "raw_response": poll_data,
            },
        }
