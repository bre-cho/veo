# 05 — Canva Provider Patch

Current file:

```txt
packages/provider_adapters/canva.py
```

Current class:

```python
CanvaMockAdapter
```

## Production Responsibilities

The real adapter should:

1. Create or select a brand template.
2. Use campaign fields to autofill text/image slots.
3. Return Canva design ID.
4. Export selected formats.
5. Save export URLs or store files into S3/MinIO.

## Normalized Output Contract

```json
{
  "provider": "canva",
  "canva_design_id": "...",
  "export_url": "...",
  "metadata": {
    "template_id": "...",
    "brand_id": "...",
    "raw_response": {}
  }
}
```

## Layout Rules

- Main product must dominate composition.
- Text area should remain secondary.
- CTA must be visible but not overpower hero product.
- Export sizes: 4:5, 1:1, 9:16.
