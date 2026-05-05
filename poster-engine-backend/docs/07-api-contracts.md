# 07 — API Contracts

## Create Brand

```http
POST /api/v1/brands
```

```json
{
  "name": "Luxury Beauty Demo",
  "industry": "beauty",
  "colors": ["black", "gold", "deep red"],
  "fonts": ["serif", "modern sans"],
  "brand_voice": "luxury, premium, trustworthy"
}
```

## Create Project

```http
POST /api/v1/projects
```

```json
{
  "brand_id": "...",
  "product_name": "Luxury Red Lipstick",
  "campaign_type": "luxury_beauty",
  "target_customer": "women 18-35",
  "offer": "Inbox chọn màu theo cá tính"
}
```

## Generate Variants

```http
POST /api/v1/projects/{project_id}/generate
```

Creates 5 default variants.

## Score Variant

```http
POST /api/v1/variants/{variant_id}/score
```

## Export Variant

```http
POST /api/v1/variants/{variant_id}/export
```
