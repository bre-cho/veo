from collections import defaultdict

import pytest

import packages.provider_adapters.adobe as adobe_module
import packages.provider_adapters.canva as canva_module
from packages.provider_adapters.adobe import AdobeProductionAdapter
from packages.provider_adapters.base import ProviderError
from packages.provider_adapters.canva import CanvaProductionAdapter


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    def __init__(self, routes: dict, calls: list):
        self.routes = routes
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, headers: dict | None = None, json: dict | None = None):
        self.calls.append({"method": "POST", "url": url, "headers": headers or {}, "json": json or {}})
        key = ("POST", url)
        if key not in self.routes or not self.routes[key]:
            raise AssertionError(f"Unexpected POST request: {url}")
        return self.routes[key].pop(0)

    def get(self, url: str, headers: dict | None = None):
        self.calls.append({"method": "GET", "url": url, "headers": headers or {}})
        key = ("GET", url)
        if key not in self.routes or not self.routes[key]:
            raise AssertionError(f"Unexpected GET request: {url}")
        return self.routes[key].pop(0)


class _ClientFactory:
    def __init__(self, routes: dict):
        self.routes = defaultdict(list)
        for key, responses in routes.items():
            self.routes[key].extend(responses)
        self.calls: list[dict] = []

    def __call__(self, *args, **kwargs):
        return _FakeHttpClient(self.routes, self.calls)


def test_adobe_production_submit_and_poll_success(monkeypatch):
    base_url = "https://adobe.test"
    routes = {
        ("POST", f"{base_url}/v3/images/generate-async"): [
            _FakeResponse(200, {"operationId": "op_1"}),
        ],
        ("GET", f"{base_url}/v3/images/operations/op_1"): [
            _FakeResponse(
                200,
                {
                    "status": "completed",
                    "outputs": [{"url": "https://img.test/generated.png"}],
                    "assetId": "asset_1",
                    "model": "firefly-v3",
                },
            )
        ],
    }
    factory = _ClientFactory(routes)
    monkeypatch.setattr(adobe_module.httpx, "Client", factory)

    adapter = AdobeProductionAdapter(access_token="token", client_id="client_id", base_url=base_url)
    result = adapter.generate_visual("Product hero with CTA", {"brand": "Demo"})

    assert result["provider"] == "adobe"
    assert result["adobe_asset_id"] == "asset_1"
    assert result["image_url"] == "https://img.test/generated.png"
    assert result["metadata"]["model"] == "firefly-v3"
    submit_call = next(call for call in factory.calls if call["method"] == "POST")
    assert submit_call["headers"]["x-api-key"] == "client_id"


def test_adobe_production_error_mapping_on_submit(monkeypatch):
    base_url = "https://adobe.test"
    routes = {
        ("POST", f"{base_url}/v3/images/generate-async"): [
            _FakeResponse(429, {"error": "rate_limit"}),
        ],
    }
    factory = _ClientFactory(routes)
    monkeypatch.setattr(adobe_module.httpx, "Client", factory)

    adapter = AdobeProductionAdapter(access_token="token", client_id="client_id", base_url=base_url)
    with pytest.raises(ProviderError) as err:
        adapter.generate_visual("Product hero with CTA", {"brand": "Demo"})

    assert err.value.provider == "adobe"
    assert err.value.error_code == "RATE_LIMIT"
    assert err.value.retryable is True


def test_canva_production_submit_and_poll_success(monkeypatch):
    base_url = "https://canva.test"
    routes = {
        ("POST", f"{base_url}/rest/v1/autofills"): [
            _FakeResponse(200, {"job_id": "job_1"}),
        ],
        ("GET", f"{base_url}/rest/v1/autofills/job_1"): [
            _FakeResponse(
                200,
                {
                    "design_id": "design_1",
                    "exports": [{"url": "https://cdn.canva.test/export.png"}],
                    "template_id": "tpl_1",
                    "brand_id": "brand_1",
                },
            )
        ],
    }
    factory = _ClientFactory(routes)
    monkeypatch.setattr(canva_module.httpx, "Client", factory)

    adapter = CanvaProductionAdapter(access_token="canva_token", base_url=base_url)
    result = adapter.create_layout(
        {
            "prompt": "Main product dominates and CTA is visible",
            "offer": "Special offer",
            "brand": "Demo",
            "brand_id": "brand_1",
            "template_id": "tpl_1",
        }
    )

    assert result["provider"] == "canva"
    assert result["canva_design_id"] == "design_1"
    assert result["export_url"] == "https://cdn.canva.test/export.png"


def test_canva_production_error_mapping_on_poll(monkeypatch):
    base_url = "https://canva.test"
    routes = {
        ("POST", f"{base_url}/rest/v1/autofills"): [
            _FakeResponse(200, {"job_id": "job_2"}),
        ],
        ("GET", f"{base_url}/rest/v1/autofills/job_2"): [
            _FakeResponse(503, {"error": "unavailable"}),
        ],
    }
    factory = _ClientFactory(routes)
    monkeypatch.setattr(canva_module.httpx, "Client", factory)

    adapter = CanvaProductionAdapter(access_token="canva_token", base_url=base_url)
    with pytest.raises(ProviderError) as err:
        adapter.create_layout(
            {
                "prompt": "Product closeup with CTA button",
                "offer": "Promo",
                "brand": "Demo",
                "brand_id": "brand_1",
                "template_id": "tpl_1",
            }
        )

    assert err.value.provider == "canva"
    assert err.value.error_code == "PROVIDER_DOWN"
    assert err.value.retryable is True
