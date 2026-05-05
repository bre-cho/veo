# 04 — Adobe Provider Patch

Current file:

```txt
packages/provider_adapters/adobe.py
```

Current class:

```python
AdobeMockAdapter
```

## Production Responsibilities

The real adapter should:

1. Accept prompt + campaign metadata.
2. Call Adobe image generation / Firefly service.
3. Poll job status if async.
4. Download or store generated assets.
5. Return normalized output.

## Normalized Output Contract

```json
{
  "provider": "adobe",
  "adobe_asset_id": "...",
  "image_url": "...",
  "metadata": {
    "model": "...",
    "prompt_hash": "...",
    "raw_response": {}
  }
}
```

## Failure Contract

Raise a typed exception with:

```json
{
  "provider": "adobe",
  "error_code": "RATE_LIMIT | AUTH | PROVIDER_DOWN | INVALID_PROMPT",
  "retryable": true,
  "message": "..."
}
```
