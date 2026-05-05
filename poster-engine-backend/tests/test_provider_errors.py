from packages.provider_adapters.base import ProviderError


def test_provider_error_contract():
    err = ProviderError("adobe", "RATE_LIMIT", retryable=True, message="Too many requests")
    payload = err.to_dict()
    assert payload == {
        "provider": "adobe",
        "error_code": "RATE_LIMIT",
        "retryable": True,
        "message": "Too many requests",
    }
