# Module Wiring: AICLIP Tree Integration

## 1. AvatarBuilderPanel → Render Pipeline

The `AvatarBuilderPanel` collects avatar DNA in 4 steps and connects to the render pipeline
via `avatar_id`:

```
AvatarBuilderPanel (step controller)
  │
  ├── Step 0: IdentityPanel
  │     └── POST /avatar-builder/identity
  │           └── { avatar_id, name, role_id, niche_code, market_code }
  │
  ├── Step 1: VisualPanel
  │     └── saveAvatarDna({ avatar_id, visual: { skin_tone, hair_style, ... } })
  │           └── POST /avatar-builder/dna
  │
  ├── Step 2: VoicePanel
  │     └── saveAvatarDna({ avatar_id, voice: { language_code, accent_code, ... } })
  │
  ├── Step 3: MotionPanel
  │     └── saveAvatarDna({ avatar_id, motion: { motion_style, gesture_set, ... } })
  │
  └── Step 4: Preview + Publish
        ├── AvatarPreviewStage  → GET /avatars/{id}
        └── SavePublishBar      → POST /avatars/{id}/publish
```

After publish, the `avatar_id` is available for use in the **Production Studio** via
`RenderStudioStore.SET_AVATAR`, which carries the avatar context into the render job.

---

## 2. Template Fit: AvatarTemplateFit → TemplateFamily → Render

Template fit determines which template best matches the avatar's profile and content goal.

```
useTemplateFit hook
  │
  └── recommend({ avatar_id, content_goal })
        └── POST /commerce/recommend-template
              └── Response: { templates: [ { template_family_id, fit_score, ... } ] }

AvatarTemplateFit table (DB)
  ├── avatar_id          → FK to avatars.id
  ├── template_family_id → FK to template_families.id
  └── fit_score          → 0.0 – 1.0 (higher = better fit)

TemplateFamily table (DB)
  ├── content_goal   → "product_demo" | "education" | "sales" | ...
  ├── niche_tags     → ["beauty", "tech", ...]
  └── market_codes   → ["US", "UK", "SG", ...]

Render pipeline consumption:
  generateFromTemplate(template_family_id, { avatar_id, market_code, content_goal })
    └── POST /templates/{id}/generate
```

The fit score is displayed via `TemplateFitBadge`:
- ≥ 0.8 → green (high fit)
- ≥ 0.5 → yellow (medium fit)
- < 0.5 → red (low fit)

---

## 3. Avatar Usage Event Recording

When an avatar is used in production, a usage event is recorded:

```
Production Studio
  │
  ├── User selects avatar_id from RenderStudioStore
  ├── createRenderJob({ ..., avatar_id, market_code, content_goal })
  │
  └── Backend (render job creation hook):
        └── POST /avatar-usage-events
              └── { avatar_id, render_job_id, market_code, content_goal }
                    └── triggers PerformanceSnapshot update (nightly or real-time)
```

PerformanceSnapshot columns updated:
- `uses_count` +1
- `views_count` updated via analytics
- `conversion_rate` recalculated when render completes

---

## 4. Marketplace Rankings Update

Rankings are computed from usage events and performance snapshots:

```
Background job / cron:
  1. Aggregate uses_count_7d, uses_count_30d from PerformanceSnapshot
  2. Compute rank_score = f(uses, downloads, ratings, earnings)
  3. Compute trending_score = f(uses_7d / uses_30d, recency)
  4. Write to avatar_rankings table

Frontend consumption:
  trendingAvatars(limit)    → GET /avatars/trending?limit=N
  recommendedAvatars(limit) → GET /avatars/recommended?limit=N
  getMarketplaceTrending()  → GET /marketplace/trending

Displayed via:
  TrendingAvatarRail   → rank badge (#1, #2, ...)
  RecommendedAvatarRail → personalized list
  AvatarCardGrid        → browseable grid
```

---

## 5. Creator Earnings Flow

```
Avatar Usage → Earnings Ledger → Payout

Step 1: Avatar used in render job
  └── avatar_id + creator_id recorded in usage event

Step 2: Earnings credited (nightly batch or on-complete trigger)
  └── INSERT creator_earnings {
        creator_id, avatar_id, amount_usd,
        earning_type: "usage_fee" | "download" | "subscription_share",
        payout_status: "pending",
        period_start, period_end
      }

Step 3: Creator requests payout
  └── PayoutRequestForm.handleSubmit
        └── requestPayout(creatorId, amount)
              └── POST /creators/{id}/payout
                    └── { amount_usd }
                          └── Updates payout_status to "requested"

Step 4: Admin approves (external)
  └── payout_status transitions: pending → requested → paid
```

---

## 6. Component → Hook → Store → API Wiring Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE LAYER                                                  │
│                                                              │
│  avatar-builder/page.tsx                                     │
│    └── uses BuilderStore via useBuilder()                    │
│    └── renders AvatarBuilderPanel { avatarId }               │
│                                                              │
│  marketplace/page.tsx                                        │
│    └── uses MarketplaceStore via useMarketplace()            │
│    └── renders AvatarCardGrid, FilterSidebar, Rails          │
│                                                              │
│  production-studio/page.tsx                                  │
│    └── uses RenderStudioStore via useRenderStudio()          │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  HOOK LAYER                                                  │
│                                                              │
│  useBuilderHook()     → startAvatarBuilder, saveAvatarDna,   │
│                          publishAvatar                       │
│                                                              │
│  useMarketplaceHook() → listAvatars(params)                  │
│                                                              │
│  useAvatarPreview(id) → getAvatar(id)                        │
│                                                              │
│  useTemplateFit()     → recommendTemplate(payload)           │
│                                                              │
│  useCountrySwitch()   → switchCountry(marketCode)            │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  STORE LAYER (React Context + useReducer)                    │
│                                                              │
│  BuilderStore   { avatarId, name, roleId, step, isDirty }   │
│  LocaleStore    { marketCode, languageCode, rtl }            │
│  MarketplaceStore { items, marketCode, roleFilter, loading } │
│  RenderStudioStore { avatarId, contentGoal, conversionMode } │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  API LAYER  (lib/api.ts – monolithic, never modified)        │
│                                                              │
│  Domain re-exports via lib/api/                              │
│    avatars.ts    creators.ts    marketplace.ts               │
│    analytics.ts  system.ts      commerce.ts                  │
│    renders.ts    audio.ts       templates.ts    projects.ts  │
│                                                              │
│  All API calls: fetch(BASE_URL + path, options)              │
│  Base URL: NEXT_PUBLIC_API_BASE_URL or http://localhost:8000  │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Shared Component Contracts

| Component | Input Props | API / Store |
|-----------|------------|-------------|
| `AvatarBuilderPanel` | `avatarId, onComplete` | uses sub-panels |
| `IdentityPanel` | `avatarId, onSaved` | POST /avatar-builder/identity |
| `VisualPanel` | `avatarId, onSaved` | saveAvatarDna (visual) |
| `VoicePanel` | `avatarId, onSaved` | saveAvatarDna (voice) |
| `MotionPanel` | `avatarId, onSaved` | saveAvatarDna (motion) |
| `PresenterStylePanel` | `avatarId, onSaved` | saveAvatarDna (preset) |
| `AvatarPreviewStage` | `avatarId` | getAvatar |
| `SavePublishBar` | `avatarId, onPublished` | publishAvatar |
| `AvatarCardGrid` | `items, loading` | (data passed in) |
| `TrendingAvatarRail` | — | trendingAvatars internally |
| `RecommendedAvatarRail` | — | recommendedAvatars internally |
| `MarketplaceFilterSidebar` | `marketCode, roleId, onChange*` | (controlled) |
| `CountryDropdown` | `value, onChange, label` | getMetaMarketProfiles |
| `PayoutRequestForm` | `creatorId, onSuccess` | requestPayout |
| `TemplateFitBadge` | `fitScore, label` | (display only) |
| `MarketCompatibilityBadge` | `compatible, marketCode` | (display only) |
| `LanguageLockBanner` | `marketCode` | (display only) |
