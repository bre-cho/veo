1. Add new files:
   - backend/app/schemas/autopilot_brain.py
   - backend/app/services/autopilot_brain_runtime.py
   - backend/app/services/youtube_seo_orchestrator.py
   - backend/app/api/autopilot_brain.py
2. Replace modified files:
   - backend/app/api/script_upload_preview.py
   - backend/app/services/publish_scheduler.py
   - backend/app/services/publish_providers/youtube_provider.py
   - backend/app/api/channel.py
   - backend/app/api/_registry.py
3. No new DB tables are required for this patch.
4. Existing tables reused for memory:
   - pattern_memories
   - episode_memories
5. Flow after merge:
   topic/script intake -> Autopilot Brain compile -> preview/render context
   render complete -> publish scheduler injects YouTube SEO package -> provider upload
