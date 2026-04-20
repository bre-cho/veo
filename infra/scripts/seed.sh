#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000/api/v1}"

echo "Seeding avatar roles..."
curl -sf -X POST "${API_BASE}/meta/roles/seed" \
  -H "Content-Type: application/json" \
  -d '[
    {"name": "host", "description": "Video host and presenter", "niche_tags": ["entertainment", "news"]},
    {"name": "presenter", "description": "Product presenter and demonstrator", "niche_tags": ["ecommerce", "tech"]},
    {"name": "educator", "description": "Educational content instructor", "niche_tags": ["education", "training"]},
    {"name": "influencer", "description": "Social media influencer style", "niche_tags": ["beauty", "lifestyle"]},
    {"name": "spokesperson", "description": "Brand spokesperson", "niche_tags": ["brand", "corporate"]}
  ]' || echo "Warning: roles seed endpoint not available, skipping"

echo ""
echo "Seeding template families..."
curl -sf -X POST "${API_BASE}/meta/template-families/seed" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "name": "Product Demo Short",
      "content_goal": "product_demo",
      "niche_tags": ["ecommerce", "tech"],
      "market_codes": ["US", "UK", "AU"],
      "description": "Short-form product demonstration template",
      "is_active": true
    },
    {
      "name": "Brand Story",
      "content_goal": "brand_awareness",
      "niche_tags": ["brand", "corporate"],
      "market_codes": ["US", "UK", "SG"],
      "description": "Brand awareness storytelling template",
      "is_active": true
    },
    {
      "name": "Lead Gen CTA",
      "content_goal": "lead_generation",
      "niche_tags": ["saas", "finance"],
      "market_codes": ["US", "CA"],
      "description": "Lead generation with strong CTA",
      "is_active": true
    },
    {
      "name": "Educational Explainer",
      "content_goal": "education",
      "niche_tags": ["education", "training"],
      "market_codes": ["US", "UK", "IN"],
      "description": "Step-by-step educational explainer",
      "is_active": true
    },
    {
      "name": "Entertainment Hook",
      "content_goal": "entertainment",
      "niche_tags": ["entertainment", "lifestyle"],
      "market_codes": ["US", "UK", "AU", "SG"],
      "description": "Hook-based entertainment content",
      "is_active": true
    }
  ]' || echo "Warning: template-families seed endpoint not available, skipping"

echo ""
echo "Seeding localization profiles..."
curl -sf -X POST "${API_BASE}/meta/market-profiles/seed" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "market_code": "US",
      "country_name": "United States",
      "language_code": "en",
      "currency_code": "USD",
      "timezone": "America/New_York",
      "rtl": false,
      "preferred_niches": ["ecommerce", "tech", "finance"],
      "preferred_roles": ["presenter", "spokesperson"]
    },
    {
      "market_code": "UK",
      "country_name": "United Kingdom",
      "language_code": "en-GB",
      "currency_code": "GBP",
      "timezone": "Europe/London",
      "rtl": false,
      "preferred_niches": ["fashion", "finance"],
      "preferred_roles": ["host", "presenter"]
    },
    {
      "market_code": "SG",
      "country_name": "Singapore",
      "language_code": "en-SG",
      "currency_code": "SGD",
      "timezone": "Asia/Singapore",
      "rtl": false,
      "preferred_niches": ["fintech", "lifestyle"],
      "preferred_roles": ["influencer", "presenter"]
    },
    {
      "market_code": "IN",
      "country_name": "India",
      "language_code": "hi",
      "currency_code": "INR",
      "timezone": "Asia/Kolkata",
      "rtl": false,
      "preferred_niches": ["education", "ecommerce"],
      "preferred_roles": ["educator", "host"]
    },
    {
      "market_code": "AE",
      "country_name": "United Arab Emirates",
      "language_code": "ar",
      "currency_code": "AED",
      "timezone": "Asia/Dubai",
      "rtl": true,
      "preferred_niches": ["luxury", "finance"],
      "preferred_roles": ["spokesperson", "host"]
    }
  ]' || echo "Warning: market-profiles seed endpoint not available, skipping"

echo ""
echo "Seed complete."
