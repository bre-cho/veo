from typing import Protocol


class ProviderError(Exception):
    def __init__(self, provider: str, error_code: str, retryable: bool, message: str):
        self.provider = provider
        self.error_code = error_code
        self.retryable = retryable
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "error_code": self.error_code,
            "retryable": self.retryable,
            "message": self.message,
        }


class VisualProvider(Protocol):
    def generate_visual(self, prompt: str, campaign_metadata: dict | None = None) -> dict: ...


class LayoutProvider(Protocol):
    def create_layout(self, payload: dict) -> dict: ...
