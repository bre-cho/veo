POST /api/v1/autopilot/brain/compile
{
  "topic": "People are using AI to print money while others are still prompting wrong",
  "platform": "youtube",
  "store_if_winner": true
}

Response includes:
- scorecard
- memory_matches
- series_map
- seo_bridge
- runtime_memory_payload

POST /api/v1/script-upload/preview
form-data:
- file=@episode-01.docx
- target_platform=youtube
- use_autopilot_brain=true

Run publish job as usual:
POST /api/v1/channel/publish-jobs/{job_id}/run

Result:
job.payload.youtube_seo is injected automatically before provider upload.
