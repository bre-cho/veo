# 14 — Debug Playbook

## Build failed
Run:

```bash
npm run build
```

Check TypeScript import paths.

## Supabase Unauthorized
Check:

- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- user login session
- RLS policy

## Stripe webhook error
Check:

- STRIPE_WEBHOOK_SECRET
- endpoint URL
- raw body usage
- webhook event type

## Image render failed
Check:

- OPENAI_API_KEY
- prompt length
- route maxDuration
