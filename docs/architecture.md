# Architecture: KOL Render Factory with AICLIP Tree Integration

## 1. System Overview

The **KOL Render Factory** is a full-stack video production pipeline that executes scene-level
video rendering via AI providers (Veo 3, Runway Gen4, Kling). The **AICLIP Tree** integration
extends this core with a pre-render intelligence layer consisting of avatar DNA profiling,
market-aware template selection, and a creator economy (marketplace + earnings).

### Core Philosophy

> Avatar → Template Fit → Render → Performance → Earnings

The avatar layer sits **before** the render pipeline. It is pre-render intelligence that determines
*who* presents the content, *how* it should be styled, and *which* template achieves the target
conversion goal for the target market.

---

## 2. Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: PRE-RENDER INTELLIGENCE                           │
│  ──────────────────────────────────────────────────────     │
│  Avatar DNA Builder   → Identity, Visual, Voice, Motion     │
│  Market Profile       → country, language, RTL, currency    │
│  Template Fit Engine  → AvatarTemplateFit + fit_score       │
│  Content Goal         → classify_content_goal / recommend   │
└───────────────────────────┬─────────────────────────────────┘
                            │ avatar_id + template_family_id
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: RENDER CORE (existing, unchanged)                 │
│  ──────────────────────────────────────────────────────     │
│  Script Upload  → Script Preview → Render Plan              │
│  Provider Dispatch (Veo / Runway / Kling)                   │
│  Scene Tasks    → Health Monitor → Incident Engine          │
│  Final Preview  → Timeline Assembly                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ render_job_id + output_urls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: POST-RENDER (marketplace + creator economy)       │
│  ──────────────────────────────────────────────────────     │
│  Avatar Usage Events  → PerformanceSnapshot                 │
│  Marketplace Listings → Rankings (trending + recommended)   │
│  Creator Store        → Earnings Ledger → Payout Requests   │
│  Analytics Dashboard  → Conversion Metrics                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Backend Module Map

| Module | Path | Responsibility |
|--------|------|---------------|
| `avatar` | `app/api/avatar/` | Avatar DNA (identity, visual, voice, motion), publish |
| `marketplace` | `app/api/marketplace/` | Listings, rankings, trending, recommended |
| `creator` | `app/api/creator/` | Creator store, earnings ledger, payout requests |
| `meta` | `app/api/meta/` | Localization profiles, roles, countries |
| `commerce` | `app/api/commerce/` | recommendAvatar, recommendTemplate, recommendCTA, classifyContentGoal |
| `render` | `app/api/render/` | RenderJob, SceneTask, health, events, dashboard |
| `audio` | `app/api/audio/` | VoiceProfiles, NarrationJob, MusicAsset, AudioMixJob |
| `template` | `app/api/template/` | TemplateFamily, TemplateDetail, generate, publish |
| `project` | `app/api/project/` | Project CRUD, render trigger, render status |
| `autopilot` | `app/api/autopilot/` | KillSwitch, notifications, observability |
| `strategy` | `app/api/strategy/` | StrategyState, directives, portfolio, SLA risk |

---

## 4. Frontend Page Map

| Route | File | Purpose |
|-------|------|---------|
| `/` | `app/page.tsx` | Dashboard |
| `/avatar-builder` | `app/avatar-builder/page.tsx` | Avatar DNA builder |
| `/marketplace` | `app/marketplace/page.tsx` | Browse + search avatars |
| `/marketplace/[id]` | `app/marketplace/[id]/page.tsx` | Avatar detail + pricing |
| `/creator/[id]` | `app/creator/[id]/page.tsx` | Creator profile + payouts |
| `/wallet` | `app/wallet/page.tsx` | Earnings viewer + payout request |
| `/analytics` | `app/analytics/page.tsx` | Marketplace + creator analytics |
| `/production-studio` | `app/production-studio/page.tsx` | Render studio with avatar context |
| `/render-jobs` | `app/render-jobs/page.tsx` | Render job list + health |
| `/render-jobs/[jobId]` | `app/render-jobs/[jobId]/page.tsx` | Job detail |
| `/script-upload` | `app/script-upload/page.tsx` | Script upload + preview |
| `/settings` | `app/settings/page.tsx` | Account config |
| `/settings/language` | `app/settings/language/page.tsx` | Market + language lock |
| `/templates` | `app/templates/page.tsx` | Template library |
| `/audio` | `app/audio/page.tsx` | Audio studio |
| `/autopilot` | `app/autopilot/page.tsx` | Autopilot control |
| `/strategy` | `app/strategy/page.tsx` | Strategy orchestration |

---

## 5. Data Flow Diagram

```
User
 │
 ├── [1] Build Avatar DNA
 │        ├── POST /avatar-builder/identity
 │        ├── POST /avatar-builder/dna  (visual / voice / motion)
 │        └── POST /avatars/{id}/publish
 │
 ├── [2] Market Selection
 │        └── POST /meta/switch-country  →  LocaleStore.SET_MARKET
 │
 ├── [3] Template Fit
 │        └── POST /commerce/recommend-template
 │                 └── returns [ { template_family_id, fit_score } ]
 │
 ├── [4] Script Upload
 │        ├── POST /script/upload-file
 │        ├── POST /script/preview
 │        └── POST /projects (creates project_id)
 │
 ├── [5] Render
 │        ├── POST /render/jobs  (create render job)
 │        ├── GET  /render/jobs/{id}/health
 │        └── GET  /render/jobs/{id}/events
 │
 └── [6] Post-Render
          ├── Avatar usage event recorded  →  PerformanceSnapshot
          ├── Rankings recomputed          →  AvatarRanking
          ├── Creator earnings credited    →  CreatorEarning
          └── Payout flow                 →  POST /creator/{id}/payout
```

---

## 6. Key API Endpoints

### Avatar Layer

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/avatar-builder/identity` | Set avatar name, role, niche, market |
| POST | `/avatar-builder/dna` | Save visual / voice / motion DNA |
| POST | `/avatars/{id}/publish` | Publish avatar to marketplace |
| GET  | `/avatars` | List avatars (filterable) |
| GET  | `/avatars/{id}` | Get avatar detail |
| GET  | `/avatars/recommended` | Recommended avatars |
| GET  | `/avatars/trending` | Trending avatars |

### Commerce Layer

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/commerce/recommend-avatar` | Find avatar by content goal |
| POST | `/commerce/recommend-template` | Find template by avatar + goal |
| POST | `/commerce/recommend-cta` | Get CTA text by goal |
| POST | `/commerce/classify-content-goal` | Classify brief into content goal |

### Creator Economy

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/creators` | List all creators |
| GET  | `/creators/{id}` | Creator profile |
| GET  | `/creators/{id}/store` | Creator store (avatars + earnings) |
| GET  | `/creators/{id}/earnings` | Earnings ledger |
| POST | `/creators/{id}/payout` | Request payout |

### Meta / Localization

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/meta/switch-country` | Switch active market |
| GET  | `/meta/market-profiles` | All localization profiles |
| GET  | `/meta/roles` | Available avatar roles |
| GET  | `/meta/countries` | Supported countries |

---

## 7. Database Tables

### Avatar Domain

| Table | Key Columns |
|-------|------------|
| `avatars` | id, name, role_id, niche_code, market_code, owner_user_id, creator_id, is_published, is_featured |
| `avatar_visual_dna` | id, avatar_id, skin_tone, hair_style, outfit_code, background_code, age_range, gender_expression |
| `avatar_voice_dna` | id, avatar_id, language_code, accent_code, tone, pitch, speed |
| `avatar_motion_dna` | id, avatar_id, motion_style, gesture_set, idle_animation, lipsync_mode |
| `avatar_rankings` | id, avatar_id, rank_score, trending_score, usage_count_7d, usage_count_30d |

### Marketplace Domain

| Table | Key Columns |
|-------|------------|
| `marketplace_items` | id, avatar_id, creator_id, price_usd, is_free, is_active, download_count, rating_avg |
| `avatar_template_fits` | id, avatar_id, template_family_id, fit_score |
| `performance_snapshots` | id, avatar_id, snapshot_date, views_count, uses_count, earnings_usd |

### Creator Economy

| Table | Key Columns |
|-------|------------|
| `creator_earnings` | id, creator_id, avatar_id, amount_usd, earning_type, payout_status, period_start, period_end |
| `creator_rankings` | id, creator_id, rank_score, total_earnings_usd, avatar_count |

### Meta / Localization

| Table | Key Columns |
|-------|------------|
| `localization_profiles` | id, market_code, country_name, language_code, currency_code, timezone, rtl |
| `avatar_roles` | id, name, description, niche_tags |
| `template_families` | id, name, content_goal, niche_tags, market_codes, is_active |

---

## 8. Frontend Store Architecture

All state management uses React Context + useReducer (no external state libs).

| Store | File | State Shape |
|-------|------|------------|
| `LocaleStore` | `store/locale-store.tsx` | marketCode, languageCode, rtl |
| `BuilderStore` | `store/builder-store.tsx` | avatarId, name, roleId, nicheCode, step, isDirty |
| `MarketplaceStore` | `store/marketplace-store.tsx` | marketCode, roleFilter, search, items, loading |
| `RenderStudioStore` | `store/render-studio-store.tsx` | avatarId, contentGoal, marketCode, conversionMode |

---

## 9. Component Hierarchy

```
app/avatar-builder/page.tsx
  └── AvatarBuilderPanel
        ├── IdentityPanel         → /avatar-builder/identity
        ├── VisualPanel           → saveAvatarDna (visual)
        ├── VoicePanel            → saveAvatarDna (voice)
        ├── MotionPanel           → saveAvatarDna (motion)
        ├── PresenterStylePanel   → saveAvatarDna (preset)
        ├── AvatarPreviewStage    → getAvatar
        └── SavePublishBar        → publishAvatar

app/marketplace/page.tsx
  ├── MarketplaceSearchBar
  ├── MarketplaceFilterSidebar
  ├── TrendingAvatarRail         → trendingAvatars
  ├── RecommendedAvatarRail      → recommendedAvatars
  └── AvatarCardGrid             → listAvatars

app/creator/[id]/page.tsx
  ├── CreatorStoreHeader
  ├── CreatorStats
  ├── CreatorAvatarGrid
  └── PayoutRequestForm          → requestPayout
```
