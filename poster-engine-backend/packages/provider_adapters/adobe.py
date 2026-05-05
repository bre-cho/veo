import hashlib

import httpx

from apps.api.core.config import settings
from packages.provider_adapters.base import ProviderError

class AdobeMockAdapter:
    def generate_visual(self, prompt: str, campaign_metadata: dict | None = None) -> dict:
        digest = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return {
            "provider": "adobe_mock",
            "adobe_asset_id": f"adobe_mock_{digest}",
            "image_url": f"mock://adobe/{digest}.png",
            "metadata": {"mode": "mock", "prompt_hash": digest},
        }


class AdobeProductionAdapter:
    def __init__(self, access_token: str, client_id: str, base_url: str | None = None):
        self.access_token = access_token
        self.client_id = client_id
        self.base_url = (base_url or settings.adobe_api_base_url).rstrip("/")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.client_id,
            "Content-Type": "application/json",
        }

    def _map_error(self, response: httpx.Response) -> ProviderError:
        status = response.status_code
        if status in (401, 403):
            return ProviderError("adobe", "AUTH", retryable=False, message="Adobe authentication failed")
        if status == 429:
            return ProviderError("adobe", "RATE_LIMIT", retryable=True, message="Adobe rate limit exceeded")
        if 500 <= status <= 599:
            return ProviderError("adobe", "PROVIDER_DOWN", retryable=True, message="Adobe service unavailable")
        return ProviderError("adobe", "INVALID_PROMPT", retryable=False, message=f"Adobe request failed: {status}")

    def generate_visual(self, prompt: str, campaign_metadata: dict | None = None) -> dict:
        campaign_metadata = campaign_metadata or {}
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        payload = {
            "prompt": prompt,
            "numVariations": 1,
            "size": {"width": 1080, "height": 1350},
            "metadata": campaign_metadata,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/v3/images/generate-async",
                headers=self._headers(),
                json=payload,
            )
            if response.status_code >= 400:
                raise self._map_error(response)

            data = response.json()
            job_id = data.get("operationId") or data.get("operation_id") or data.get("job_id")
            if not job_id:
                outputs = data.get("outputs") or data.get("images") or []
                image_url = data.get("image_url") or (outputs[0].get("url") if outputs else None)
                if not image_url:
                    raise ProviderError("adobe", "PROVIDER_DOWN", retryable=True, message="Missing Adobe image URL")
                asset_id = data.get("asset_id") or data.get("assetId") or f"adobe_{prompt_hash}"
                return {
                    "provider": "adobe",
                    "adobe_asset_id": asset_id,
                    "image_url": image_url,
                    "metadata": {
                        "model": data.get("model", "unknown"),
                        "prompt_hash": prompt_hash,
                        "raw_response": data,
                    },
                }

            for _ in range(settings.adobe_poll_max_attempts):
                poll = client.get(
                    f"{self.base_url}/v3/images/operations/{job_id}",
                    headers=self._headers(),
                )
                if poll.status_code >= 400:
                    raise self._map_error(poll)
                poll_data = poll.json()
                status = str(poll_data.get("status", "")).lower()
                if status in {"done", "completed", "success"}:
                    outputs = poll_data.get("outputs") or poll_data.get("images") or []
                    image_url = poll_data.get("image_url") or (outputs[0].get("url") if outputs else None)
                    if not image_url:
                        raise ProviderError("adobe", "PROVIDER_DOWN", retryable=True, message="Adobe job done but no image")
                    asset_id = poll_data.get("asset_id") or poll_data.get("assetId") or f"adobe_{prompt_hash}"
                    return {
                        "provider": "adobe",
                        "adobe_asset_id": asset_id,
                        "image_url": image_url,
                        "metadata": {
                            "model": poll_data.get("model", "unknown"),
                            "prompt_hash": prompt_hash,
                            "raw_response": poll_data,
                        },
                    }
                if status in {"failed", "error"}:
                    raise ProviderError("adobe", "PROVIDER_DOWN", retryable=True, message="Adobe async job failed")
                # Delay between polls to reduce provider pressure.
                import time

                time.sleep(settings.adobe_poll_interval_seconds)

        raise ProviderError("adobe", "PROVIDER_DOWN", retryable=True, message="Adobe async polling timeout")
