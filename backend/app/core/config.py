from __future__ import annotations

import os
from pydantic import BaseModel


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Settings(BaseModel):
    voice_consent_min_chars: int = int(os.getenv("VOICE_CONSENT_MIN_CHARS", "20"))
    require_voice_consent: bool = _get_bool("REQUIRE_VOICE_CONSENT", True)
    default_music_gain_db: int = int(os.getenv("DEFAULT_MUSIC_GAIN_DB", "-18"))
    default_narration_gain_db: int = int(os.getenv("DEFAULT_NARRATION_GAIN_DB", "0"))
    default_music_ducking_db: int = int(os.getenv("DEFAULT_MUSIC_DUCKING_DB", "10"))
    default_breath_preset: str = os.getenv("DEFAULT_BREATH_PRESET", "natural")
    elevenlabs_enable_music: bool = _get_bool("ELEVENLABS_ENABLE_MUSIC", False)
    elevenlabs_default_similarity_boost: float = float(os.getenv("ELEVENLABS_DEFAULT_SIMILARITY_BOOST", "0.8"))
    elevenlabs_default_stability: float = float(os.getenv("ELEVENLABS_DEFAULT_STABILITY", "0.45"))
    elevenlabs_tts_output_format: str = os.getenv("ELEVENLABS_TTS_OUTPUT_FORMAT", "mp3_44100_128")
    elevenlabs_base_url: str = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
    ffprobe_binary: str = os.getenv("FFPROBE_BINARY", "ffprobe")
    observability_enabled: bool = _get_bool("OBSERVABILITY_ENABLED", True)
    notification_plane_enabled: bool = _get_bool("NOTIFICATION_PLANE_ENABLED", True)
    decision_engine_enabled: bool = _get_bool("DECISION_ENGINE_ENABLED", True)
    decision_engine_policy_path: str | None = os.getenv("DECISION_ENGINE_POLICY_PATH")
    control_plane_enabled: bool = _get_bool("CONTROL_PLANE_ENABLED", True)
    default_dispatch_batch_limit: int = int(os.getenv("DEFAULT_DISPATCH_BATCH_LIMIT", "10"))
    default_poll_countdown_seconds: int = int(os.getenv("DEFAULT_POLL_COUNTDOWN_SECONDS", "60"))
    autopilot_control_fabric_enabled: bool = _get_bool("AUTOPILOT_CONTROL_FABRIC_ENABLED", True)

    audio_upload_dir: str = os.getenv("AUDIO_UPLOAD_DIR", "/app/storage/audio_uploads")
    audio_output_dir: str = os.getenv("AUDIO_OUTPUT_DIR", "/app/artifacts/audio")
    video_output_dir: str = os.getenv("VIDEO_OUTPUT_DIR", "/app/artifacts/video")
    audio_output_format: str = os.getenv("AUDIO_OUTPUT_FORMAT", "mp3_44100_128")
    audio_upload_to_object_storage: bool = _get_bool("AUDIO_UPLOAD_TO_OBJECT_STORAGE", True)
    ffmpeg_binary: str = os.getenv("FFMPEG_BINARY", "ffmpeg")
    elevenlabs_api_key: str | None = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_tts_model_id: str = os.getenv("ELEVENLABS_TTS_MODEL_ID", "eleven_multilingual_v2")
    default_music_duration_seconds: int = _get_int("DEFAULT_MUSIC_DURATION_SECONDS", 30)
    app_env: str = os.getenv("APP_ENV", "production")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/render_factory")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    storage_root: str = os.getenv("STORAGE_ROOT", "/app/storage")
    storage_public_base_url: str = os.getenv("STORAGE_PUBLIC_BASE_URL", "/storage")
    render_cache_dir: str = os.getenv("RENDER_CACHE_DIR", "/app/storage/render_cache")
    render_output_dir: str = os.getenv("RENDER_OUTPUT_DIR", "/app/storage/render_outputs")
    object_storage_provider: str = os.getenv("OBJECT_STORAGE_PROVIDER", "minio")
    s3_endpoint_url: str | None = os.getenv("S3_ENDPOINT_URL")
    s3_access_key_id: str | None = os.getenv("S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = os.getenv("S3_SECRET_ACCESS_KEY")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "render-assets")
    s3_region: str = os.getenv("S3_REGION", "us-east-1")
    s3_public_base_url: str | None = os.getenv("S3_PUBLIC_BASE_URL")
    signed_url_expires_seconds: int = _get_int("SIGNED_URL_EXPIRES_SECONDS", 3600)
    google_cloud_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    google_genai_use_vertex: bool = _get_bool("GOOGLE_GENAI_USE_VERTEX", True)
    google_application_credentials: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    veo_default_model: str = os.getenv("VEO_DEFAULT_MODEL", "veo-3.1-generate-001")
    veo_fast_model: str = os.getenv("VEO_FAST_MODEL", "veo-3.1-fast-generate-001")
    veo_output_gcs_uri: str | None = os.getenv("VEO_OUTPUT_GCS_URI")
    veo_batch_max_scripts: int = _get_int("VEO_BATCH_MAX_SCRIPTS", 100)
    veo_enable_sound_generation: bool = _get_bool("VEO_ENABLE_SOUND_GENERATION", False)
    veo_enable_reference_preview: bool = _get_bool("VEO_ENABLE_REFERENCE_PREVIEW", False)
    veo_reference_preview_model: str = os.getenv("VEO_REFERENCE_PREVIEW_MODEL", "veo-3.1-generate-preview")

    provider_callback_use_relay: bool = _get_bool("PROVIDER_CALLBACK_USE_RELAY", False)
    provider_callback_public_base_url: str | None = os.getenv("PROVIDER_CALLBACK_PUBLIC_BASE_URL")
    provider_callback_relay_path_template: str = os.getenv("PROVIDER_CALLBACK_RELAY_PATH_TEMPLATE", "/hooks/{provider}")
    provider_max_retries: int = _get_int("PROVIDER_MAX_RETRIES", 2)
    provider_retry_base_seconds: int = _get_int("PROVIDER_RETRY_BASE_SECONDS", 2)
    provider_allow_mock_fallback: bool = _get_bool("PROVIDER_ALLOW_MOCK_FALLBACK", False)
    provider_callback_shared_secret: str | None = os.getenv("PROVIDER_CALLBACK_SHARED_SECRET")
    provider_relay_shared_secret: str | None = os.getenv("PROVIDER_RELAY_SHARED_SECRET")
    veo_relay_shared_secret: str | None = os.getenv("VEO_RELAY_SHARED_SECRET")
    provider_ingress_signature_ttl_seconds: int = _get_int("PROVIDER_INGRESS_SIGNATURE_TTL_SECONDS", 300)
    provider_http_timeout_seconds: int = _get_int("PROVIDER_HTTP_TIMEOUT_SECONDS", 120)
    celery_task_time_limit: int = _get_int("CELERY_TASK_TIME_LIMIT", 1800)
    celery_task_soft_time_limit: int = _get_int("CELERY_TASK_SOFT_TIME_LIMIT", 1500)
    celery_worker_prefetch_multiplier: int = _get_int("CELERY_WORKER_PREFETCH_MULTIPLIER", 1)
    celery_task_acks_late: bool = _get_bool("CELERY_TASK_ACKS_LATE", True)

    # RAG / Embedding settings
    rag_enabled: bool = _get_bool("RAG_ENABLED", True)
    rag_chunk_size: int = _get_int("RAG_CHUNK_SIZE", 400)
    rag_chunk_overlap: int = _get_int("RAG_CHUNK_OVERLAP", 80)
    rag_top_k: int = _get_int("RAG_TOP_K", 5)
    rag_embedding_backend: str = os.getenv("RAG_EMBEDDING_BACKEND", "tfidf")  # "tfidf" | "openrouter"
    rag_embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "openai/text-embedding-ada-002")
    rag_vector_store_path: str = os.getenv("RAG_VECTOR_STORE_PATH", "/app/storage/rag_index.json")
    rag_docs_root: str = os.getenv("RAG_DOCS_ROOT", "docs")
    rag_llm_system_prompt: str = os.getenv(
        "RAG_LLM_SYSTEM_PROMPT",
        "You are an operations assistant for the Render Factory platform. "
        "Answer questions ONLY using the provided context passages. "
        "If the answer is not found in the context, say 'I don't have enough context to answer that.' "
        "Do not speculate or fabricate information.",
    )

    # ML / prediction settings
    ml_enabled: bool = _get_bool("ML_ENABLED", True)
    ml_model_path: str = os.getenv("ML_MODEL_PATH", "/app/storage/ml_render_predictor.json")
    ml_min_training_samples: int = _get_int("ML_MIN_TRAINING_SAMPLES", 10)
    ml_feature_lookback_days: int = _get_int("ML_FEATURE_LOOKBACK_DAYS", 30)

    # LLM function calling
    llm_function_calling_enabled: bool = _get_bool("LLM_FUNCTION_CALLING_ENABLED", True)
    llm_max_tool_calls_per_request: int = _get_int("LLM_MAX_TOOL_CALLS_PER_REQUEST", 5)


settings = Settings()
if settings.app_env.strip().lower() == "production" and settings.provider_allow_mock_fallback:
    raise ValueError("PROVIDER_ALLOW_MOCK_FALLBACK must be false when APP_ENV=production")
