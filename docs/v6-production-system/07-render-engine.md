# 07 — Render Engine

Current render options:

1. OpenAI image API
2. External image model
3. Manual prompt export
4. Future: queue-based render

Recommended production:

- Save prompt result
- Render image
- Upload to Supabase Storage
- Save generated asset URL
- Show in editor

Important:

- Never block UI for long render jobs.
- Use job status if render time grows.
