# 12 — Deploy Vercel

Install:

```bash
npm i -g vercel
```

Deploy:

```bash
vercel
vercel --prod
```

Add env in Vercel:

```env
NEXT_PUBLIC_APP_URL=https://yourdomain.com
OPENAI_API_KEY=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

After domain setup, redeploy.
