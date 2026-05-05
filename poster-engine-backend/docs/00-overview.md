# 00 — Overview

This package is a production-oriented MVP backend scaffold for an AI Poster Engine focused on luxury ads and beauty campaigns.

## Goal

Build a backend that can:

1. Store Brand DNA.
2. Create poster campaigns.
3. Generate 5 visual/layout variants.
4. Route visual generation to Adobe adapter.
5. Route layout/template creation to Canva adapter.
6. Score variants by CTR, attention, luxury, trust, product focus, and conversion.
7. Export final asset packs.

## Current State

The package ships with mock adapters so devs can run everything locally without paid provider API calls.

## Production Integration Points

- Replace `AdobeMockAdapter` with real Adobe Firefly / Express implementation.
- Replace `CanvaMockAdapter` with real Canva Connect / Autofill implementation.
- Replace local storage export with S3/MinIO.
- Move synchronous generation into Celery task queue.
