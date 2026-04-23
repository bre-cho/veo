This patch corrects the earlier misunderstanding.

Goal:
Embed the Custom GPT operating structure as the decision brain of the existing codebase.
It does NOT create a parallel growth system.

Where the brain is inserted:
1. Intake layer
   - script_upload_preview now returns:
     - autopilot_brain runtime memory
     - youtube_seo package
   - new endpoint /api/v1/autopilot/brain/compile supports topic-first workflows

2. Memory layer
   - reuses existing PatternMemory table for winner DNA recall/store
   - reuses existing EpisodeMemory continuity concepts already present in the repo

3. Post-render publish layer
   - PublishScheduler enriches payload before provider.execute()
   - YouTube provider now sends:
     - SEO title
     - SEO description with next-video chain CTA
     - tags
     - pinned comment draft
     - thumbnail brief

SEO payload created automatically:
- thumbnail brief
- title
- long description with bridge to next videos in the chain
- pinned comment
- video hashtags
- channel hashtags
- normalized tags

Important limitation:
This patch prepares SEO and post-publish action payloads.
If you want the system to actually pin the comment or upload a custom thumbnail through the real YouTube API proxy,
your publish proxy must read `seo_package` and `post_publish_actions` and execute those provider-specific operations.
