# Rollout Plan: AICLIP Tree Integration

## Overview

The AICLIP Tree integration was delivered in phases A–G, merged progressively into the
KOL Render Factory. This document describes the merge plan, gate checks, rollback strategy,
and production deployment checklist.

---

## Phase Plan (A–G)

### Phase A: Types and API Domain Modules
- **Files**: `src/types/avatar.ts`, `src/types/creator.ts`, `src/types/marketplace.ts`,
  `src/types/meta.ts`, `src/types/render.ts`
- **Files**: `src/lib/api/avatars.ts` through `src/lib/api/index.ts`
- **Gate**: TypeScript compiles with zero errors. No existing imports break.
- **Risk**: Low – additive only, no modification to existing `lib/api.ts`

### Phase B: React Context Stores
- **Files**: `src/store/locale-store.tsx`, `src/store/builder-store.tsx`,
  `src/store/marketplace-store.tsx`, `src/store/render-studio-store.tsx`
- **Gate**: Store providers render without runtime errors. useReducer dispatches tested manually.
- **Risk**: Low – no external deps, pure React

### Phase C: Hooks
- **Files**: `src/hooks/use-country-switch.ts`, `src/hooks/use-builder.ts`,
  `src/hooks/use-marketplace.ts`, `src/hooks/use-avatar-preview.ts`,
  `src/hooks/use-template-fit.ts`
- **Gate**: Hooks import cleanly. No circular deps.
- **Risk**: Low

### Phase D: Shared Components
- **Files**: `src/components/shared/CountryDropdown.tsx`,
  `src/components/shared/LanguageLockBanner.tsx`,
  `src/components/shared/TemplateFitBadge.tsx`,
  `src/components/shared/MarketCompatibilityBadge.tsx`
- **Gate**: Components render with mock props. No TS errors.
- **Risk**: Low

### Phase E: Feature Components (Avatar Builder + Marketplace + Creator)
- **Files**: All `components/avatar-builder/`, `components/marketplace/`, `components/creator/`
- **Gate**: `npm run build` succeeds. Visual smoke test of each component.
- **Risk**: Medium – these call API endpoints that may not exist in test env

### Phase F: New Pages
- **Files**: `app/marketplace/[id]/page.tsx`, `app/creator/[id]/page.tsx`,
  `app/wallet/page.tsx`
- **Gate**: Pages load with loading state. API errors show graceful error UI.
- **Risk**: Medium – depends on backend avatar/creator endpoints being available

### Phase G: Sidebar Update + Docs + Infra
- **Files**: `components/Sidebar.tsx` (modified), `docs/architecture.md`,
  `docs/module-wiring.md`, `docs/rollout-plan.md`,
  `infra/scripts/seed.sh`, `infra/scripts/bootstrap.sh`
- **Gate**: Sidebar renders new items. Navigation works. Docs reviewed.
- **Risk**: Low

---

## Gate Checks Per Merge

| Check | Tool | Pass Criteria |
|-------|------|--------------|
| TypeScript compile | `npm run build` | Zero type errors |
| Lint | ESLint (if configured) | Zero errors |
| Unit tests | Existing test suite | All pass |
| Backend compile | `python -m compileall app -q` | No syntax errors |
| Backend tests | `python -m pytest -q` | All pass |
| E2E smoke | Playwright | Key pages render |

---

## Rollback Strategy

### Frontend rollback
```bash
git revert <merge-commit-sha>
cd frontend && npm run build
```

The rollback is safe because:
1. `lib/api.ts` was never modified – only appended to
2. New pages are additive (new routes only)
3. `Sidebar.tsx` change only adds nav items – removing them is trivial
4. All stores/hooks/components are in new files – delete to revert

### Backend rollback
```bash
cd backend && alembic downgrade -1
```
Each migration is a single Alembic revision. Downgrade removes the AICLIP tables
without touching existing render/project tables.

---

## Production Deployment Checklist

### Pre-deployment
- [ ] All TypeScript compiles clean (`npm run build`)
- [ ] Backend tests pass (`pytest -q`)
- [ ] E2E tests pass on staging
- [ ] Backend DB migrations reviewed (`alembic upgrade head` tested on staging)
- [ ] Seed data loaded (`./infra/scripts/bootstrap.sh`)
- [ ] Environment variables set:
  - `NEXT_PUBLIC_API_BASE_URL` → production API URL
  - Database connection strings
  - Provider API keys

### Deployment Steps
1. Deploy backend: `alembic upgrade head`
2. Run seed: `./infra/scripts/bootstrap.sh`
3. Deploy frontend: `npm run build && npm start` (or Vercel/container)
4. Smoke test: navigate to `/marketplace`, `/avatar-builder`, `/wallet`
5. Verify API connectivity: check network tab for 200 responses

### Post-deployment
- [ ] Verify trending/recommended avatars load
- [ ] Verify avatar builder steps work end-to-end
- [ ] Verify creator earnings page loads
- [ ] Monitor error rates in observability dashboard

---

## Dependency Map

```
Phase A (types + api modules)
  └── required by Phase B, C, D, E, F

Phase B (stores)
  └── required by Phase E (components use stores)

Phase C (hooks)
  └── required by Phase E (components use hooks)

Phase D (shared components)
  └── required by Phase E

Phase E (feature components)
  └── required by Phase F (pages import components)

Phase F (pages)
  └── required by Phase G (sidebar links to pages)

Phase G (sidebar + docs + infra)
  └── final integration layer
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Backend avatar endpoints not available | Medium | Medium | All pages show loading/error states gracefully |
| lib/api.ts function signature mismatch | Low | High | Type-safe imports; functions verified against api.ts |
| Circular import in lib/api/index.ts | Low | Medium | Re-exports only, no new logic |
| DB migration conflict with existing tables | Low | High | Each AICLIP table uses new namespaced names |
| Performance regression from new store providers | Low | Low | Stores only wrap pages that need them |
