import fs from "fs";
import path from "path";

const ROOT = process.cwd();

function write(file, content) {
  const full = path.join(ROOT, file);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content.trimStart(), "utf8");
  console.log("✅", file);
}

function patchPackageJson() {
  const pkgPath = path.join(ROOT, "package.json");
  if (!fs.existsSync(pkgPath)) {
    console.error("❌ package.json not found. Run this script inside repo root.");
    process.exit(1);
  }

  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));

  pkg.dependencies = {
    ...(pkg.dependencies || {}),
    "@supabase/ssr": "latest",
    "@supabase/supabase-js": "latest",
    "stripe": "latest",
    "zod": "latest",
    "js-yaml": "latest",
    "html-to-image": "latest",
    "openai": "latest"
  };

  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2), "utf8");
  console.log("✅ package.json patched");
}

patchPackageJson();

/* =========================
   V6 CORE — PROMPT ENGINE
========================= */

write("lib/prompt-v6/types.ts", `
export type V6Goal = "sale" | "lead" | "click" | "brand" | "education" | "event";

export type SellingMechanism =
  | "product"
  | "emotion"
  | "problem"
  | "result"
  | "authority"
  | "offer"
  | "education"
  | "event";

export type V6Input = {
  text: string;
  product?: string;
  industry?: string;
  audience?: string;
  goal?: V6Goal;
  mood?: "luxury" | "bold" | "minimal" | "trust" | "viral";
  hasPackaging?: boolean;
  hasCollection?: boolean;
};

export type V6Output = {
  mechanism: SellingMechanism;
  hook: string;
  cta: string;
  layout: string;
  visual: string;
  posterPrompts: {
    trust: string;
    viral: string;
    conversion: string;
  };
  funnel: any;
  botFlow: string[];
  adsPlan: any;
  kpiRules: any;
};
`);

write("lib/prompt-v6/engine.ts", `
import { SellingMechanism, V6Input } from "./types";

export function detectSellingMechanism(input: V6Input): SellingMechanism {
  const t = [
    input.text,
    input.product,
    input.industry,
    input.audience,
    input.goal
  ].filter(Boolean).join(" ").toLowerCase();

  if (/giảm|khuyến mãi|ưu đãi|sale|deal|combo|giá/.test(t)) return "offer";
  if (/trước sau|before after|kết quả|biến đổi|thay đổi|transformation/.test(t)) return "result";
  if (/chuyên gia|bác sĩ|doctor|expert|được khuyên dùng|kiểm chứng/.test(t)) return "authority";
  if (/đau|vấn đề|lỗi|khó khăn|problem|pain|sợ/.test(t)) return "problem";
  if (/quy trình|framework|hướng dẫn|checklist|course|education|bài học/.test(t)) return "education";
  if (/event|sự kiện|workshop|hội thảo|countdown|đăng ký/.test(t)) return "event";
  if (/cảm xúc|đẹp|tự tin|quyến rũ|sang trọng|luxury|comfort/.test(t)) return "emotion";

  return "product";
}

export function generateHook(mechanism: SellingMechanism) {
  const hooks: Record<SellingMechanism, string> = {
    problem: "Bạn đang gặp vấn đề này?",
    result: "7 ngày thay đổi rõ rệt",
    emotion: "Bạn xứng đáng tốt hơn",
    offer: "Ưu đãi giới hạn hôm nay",
    authority: "Chuyên gia khuyên dùng",
    product: "Giải pháp đơn giản hơn bạn nghĩ",
    education: "Nhìn 1 lần là hiểu quy trình",
    event: "Bạn sắp bỏ lỡ sự kiện này?"
  };

  return hooks[mechanism];
}

export function generateCTA(goal: V6Input["goal"]) {
  if (goal === "sale") return "Mua ngay";
  if (goal === "lead") return "Nhận demo";
  if (goal === "click") return "Xem ngay";
  if (goal === "education") return "Tải framework";
  if (goal === "event") return "Đăng ký ngay";
  return "Khám phá";
}

export function decideLayout(input: V6Input, mechanism: SellingMechanism) {
  if (input.hasCollection) return "lookbook";
  if (mechanism === "education") return "editorial_grid";
  if (mechanism === "event") return "event_cover";
  if (mechanism === "result") return "before_after";
  if (mechanism === "authority") return "expert_trust";
  if (mechanism === "offer") return "price_badge";
  if (input.hasPackaging || mechanism === "product") return "product_dominance";
  return "realism";
}

export function decideVisual(mechanism: SellingMechanism) {
  const map: Record<SellingMechanism, string> = {
    product: "product_dominance",
    emotion: "lifestyle_emotion",
    problem: "problem_solution",
    result: "before_after",
    authority: "expert_face",
    offer: "price_badge",
    education: "infographic_grid",
    event: "fomo_countdown"
  };

  return map[mechanism];
}

export function buildPosterPrompts(input: V6Input, args: {
  mechanism: SellingMechanism;
  hook: string;
  cta: string;
  layout: string;
  visual: string;
}) {
  const product = input.product || input.text;
  const base = \`
Create a premium poster for \${product}.

Mechanism: \${args.mechanism}
Visual: \${args.visual}
Layout: \${args.layout}
Hook: "\${args.hook}"
CTA: "\${args.cta}"

Rules:
- One main focus only
- Text readable in 1 second
- Clear visual hierarchy
- Strong but controlled contrast
- 25-30% whitespace
- Vietnamese text must be readable and correctly accented
- No clutter
- No random colors outside brand palette
\`.trim();

  return {
    trust: base + "\\n\\nVersion: TRUST. Clean composition, realistic lighting, credible details, premium clarity.",
    viral: base + "\\n\\nVersion: VIRAL. Unusual angle, high contrast, exaggerated visual hook, scroll-stopping composition.",
    conversion: base + "\\n\\nVersion: CONVERSION. Product/benefit first, CTA visible, simple layout, action-driven hierarchy."
  };
}
`);

/* =========================
   V6 FUNNEL / BOT / ADS / KPI
========================= */

write("lib/funnel/engine.ts", `
export function generateFunnel(input: any) {
  const product = input.product || "sản phẩm";

  return {
    landing: {
      heroHeadline: \`Tạo kết quả tốt hơn với \${product}\`,
      subHeadline: "Hiểu nhanh, thấy rõ lợi ích, hành động ngay.",
      cta: input.goal === "sale" ? "Mua ngay" : "Nhận demo miễn phí"
    },
    sections: [
      "Problem",
      "Solution",
      "Demo / Visual proof",
      "Offer",
      "FAQ",
      "Lead form"
    ],
    thankYou: "Cảm ơn bạn. Chúng tôi sẽ gửi demo trong ít phút.",
    email: {
      subject: \`Demo cho \${product}\`,
      body: "Đây là demo bạn vừa yêu cầu. Nếu cần tối ưu thêm, hãy phản hồi email này."
    }
  };
}
`);

write("lib/bot/sales-flow.ts", `
export function generateBotSalesFlow(input: any) {
  return [
    "Chào bạn, bạn đang muốn tạo poster/video cho sản phẩm nào?",
    "Mục tiêu của bạn là tăng đơn, tăng lead hay tăng nhận diện?",
    "Bạn đã có ảnh sản phẩm hoặc brand màu chưa?",
    "Mình sẽ tạo thử 1 concept demo cho bạn.",
    "Bạn muốn nhận demo qua email hay Zalo?",
    "Sau 6h: Bạn đã xem demo chưa? Mình có thể chỉnh theo ngành của bạn.",
    "Sau 24h: Nếu bạn muốn, mình có thể tạo thêm 3 version để test."
  ];
}
`);

write("lib/ads/launch-engine.ts", `
export function generateAdsPlan(input: any) {
  return {
    objective: input.goal === "sale" ? "Sales / Conversions" : "Leads / Traffic",
    angles: [
      "Problem angle",
      "Result angle",
      "Offer angle"
    ],
    captions: [
      "Bạn đang mất khách vì visual chưa đủ rõ?",
      "Một poster tốt giúp khách hiểu sản phẩm nhanh hơn.",
      "Tạo bản demo cho sản phẩm của bạn ngay hôm nay."
    ],
    ctas: ["Xem ngay", "Nhận demo", "Đăng ký"],
    budgetTest: "300k/ngày trong 24h",
    kpi: ["CTR", "CPC", "CPM", "Lead", "CPL", "Close rate"]
  };
}
`);

write("lib/kpi/kpi-engine.ts", `
export function calculateKpi(row: {
  spend: number;
  impressions: number;
  clicks: number;
  leads: number;
  sales: number;
  revenue: number;
}) {
  return {
    ctr: row.impressions ? Number(((row.clicks / row.impressions) * 100).toFixed(2)) : 0,
    cpc: row.clicks ? Number((row.spend / row.clicks).toFixed(2)) : 0,
    cpl: row.leads ? Number((row.spend / row.leads).toFixed(2)) : 0,
    cpa: row.sales ? Number((row.spend / row.sales).toFixed(2)) : 0,
    roas: row.spend ? Number((row.revenue / row.spend).toFixed(2)) : 0,
    profit: row.revenue - row.spend
  };
}

export function optimizeFromKpi(metrics: any) {
  if (metrics.ctr < 1.5) return "Hook yếu → test viral version hoặc tăng contrast.";
  if (metrics.cpl > 50000) return "Offer/CTA yếu → test conversion version.";
  if (metrics.roas >= 2) return "Winner → scale ngân sách x2.";
  return "Tiếp tục test thêm visual + hook.";
}
`);

/* =========================
   ORCHESTRATOR
========================= */

write("lib/orchestrator-v6.ts", `
import {
  detectSellingMechanism,
  generateHook,
  generateCTA,
  decideLayout,
  decideVisual,
  buildPosterPrompts
} from "./prompt-v6/engine";

import { generateFunnel } from "./funnel/engine";
import { generateBotSalesFlow } from "./bot/sales-flow";
import { generateAdsPlan } from "./ads/launch-engine";

export function runV6System(input: any) {
  const mechanism = detectSellingMechanism(input);
  const hook = generateHook(mechanism);
  const cta = generateCTA(input.goal);
  const layout = decideLayout(input, mechanism);
  const visual = decideVisual(mechanism);

  const posterPrompts = buildPosterPrompts(input, {
    mechanism,
    hook,
    cta,
    layout,
    visual
  });

  return {
    strategy: \`Hệ thống phải khiến người xem \${input.goal === "sale" ? "muốn mua" : "muốn tìm hiểu"} trong 3 giây.\`,
    mechanism,
    hook,
    cta,
    layout,
    visual,
    posterPrompts,
    funnel: generateFunnel(input),
    botFlow: generateBotSalesFlow(input),
    adsPlan: generateAdsPlan(input),
    kpiRules: {
      ctrLow: "Đổi hook / visual hook",
      cplHigh: "Đổi CTA / offer",
      roasHigh: "Scale winner"
    }
  };
}
`);

/* =========================
   API ROUTES
========================= */

write("app/api/v6/run/route.ts", `
import { NextResponse } from "next/server";
import { runV6System } from "@/lib/orchestrator-v6";

export async function POST(req: Request) {
  const input = await req.json();
  return NextResponse.json(runV6System(input));
}
`);

write("app/api/v6/kpi/route.ts", `
import { NextResponse } from "next/server";
import { calculateKpi, optimizeFromKpi } from "@/lib/kpi/kpi-engine";

export async function POST(req: Request) {
  const row = await req.json();
  const metrics = calculateKpi(row);
  return NextResponse.json({
    metrics,
    recommendation: optimizeFromKpi(metrics)
  });
}
`);

/* =========================
   SUPABASE
========================= */

write("lib/supabase/server.ts", `
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createServerSupabaseClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        }
      }
    }
  );
}
`);

write("app/api/projects/save/route.ts", `
import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function POST(req: Request) {
  const body = await req.json();

  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    return NextResponse.json({
      mock: true,
      message: "Supabase env missing. Project save mocked.",
      data: body
    });
  }

  const supabase = await createServerSupabaseClient();
  const { data: userData } = await supabase.auth.getUser();

  if (!userData.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data, error } = await supabase
    .from("poster_projects")
    .insert({
      user_id: userData.user.id,
      name: body.name || "Untitled Project",
      document: body.document || {},
      prompt_result: body.promptResult || {}
    })
    .select()
    .single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data);
}
`);

write("supabase/migrations/003_v6_production.sql", `
create table if not exists public.poster_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  name text not null,
  document jsonb not null default '{}',
  prompt_result jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.ad_metrics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  campaign_name text,
  spend numeric default 0,
  impressions int default 0,
  clicks int default 0,
  leads int default 0,
  sales int default 0,
  revenue numeric default 0,
  created_at timestamptz default now()
);

alter table public.poster_projects enable row level security;
alter table public.ad_metrics enable row level security;

drop policy if exists "poster_projects owner all" on public.poster_projects;
create policy "poster_projects owner all"
on public.poster_projects
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "ad_metrics owner all" on public.ad_metrics;
create policy "ad_metrics owner all"
on public.ad_metrics
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
`);

/* =========================
   STRIPE
========================= */

write("app/api/stripe/webhook/route.ts", `
import Stripe from "stripe";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "missing");

export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get("stripe-signature");

  if (!process.env.STRIPE_WEBHOOK_SECRET || !sig) {
    return NextResponse.json({ error: "Missing webhook secret or signature" }, { status: 400 });
  }

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );

    if (event.type === "checkout.session.completed") {
      const session = event.data.object as any;
      console.log("Payment completed:", session.id);
      // TODO: update user plan / unlock template pack in Supabase.
    }

    return NextResponse.json({ received: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 400 });
  }
}
`);

/* =========================
   DOCS — V6 PRODUCTION SYSTEM
========================= */

write("docs/v6-production-system/00-overview.md", `
# 00 — Overview

V6 biến AI Poster Studio thành AI Ads Factory SaaS.

Flow:

User input
→ Prompt Engine V6
→ Poster prompts
→ Funnel
→ Bot sales flow
→ Ads launch plan
→ KPI optimization

Core modules:

- DESIGN.md / brand system
- Prompt Engine V6
- Image render
- Editor
- Marketplace
- Supabase auth/project save
- Stripe payment
- KPI tracking
`);

write("docs/v6-production-system/01-setup-local.md", `
# 01 — Setup Local

\`\`\`bash
npm install
npm run dev
\`\`\`

Open:

\`\`\`txt
http://localhost:3000
http://localhost:3000/studio
http://localhost:3000/editor
http://localhost:3000/marketplace
\`\`\`

Test V6:

\`\`\`bash
curl -X POST http://localhost:3000/api/v6/run \\
  -H "Content-Type: application/json" \\
  -d '{"text":"Tôi bán serum trị mụn","product":"Serum trị mụn","goal":"sale","industry":"Beauty"}'
\`\`\`
`);

write("docs/v6-production-system/02-env-config.md", `
# 02 — ENV Config

Local:

\`\`\`env
NEXT_PUBLIC_APP_URL=http://localhost:3000

OPENAI_API_KEY=

NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
\`\`\`

Production:

\`\`\`env
NEXT_PUBLIC_APP_URL=https://yourdomain.com
\`\`\`

Không commit .env.local.
`);

write("docs/v6-production-system/03-supabase-setup.md", `
# 03 — Supabase Setup

1. Create Supabase project.
2. Copy env:

\`\`\`env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
\`\`\`

3. Run SQL:

\`\`\`sql
-- use file:
supabase/migrations/003_v6_production.sql
\`\`\`

Tables:

- poster_projects
- ad_metrics

RLS enabled.
`);

write("docs/v6-production-system/04-stripe-setup.md", `
# 04 — Stripe Setup

Create products:

- Pro Poster Studio — $19/mo
- Agency System — $49/mo
- Empire Automation — $99/mo

Webhook endpoint:

\`\`\`txt
https://yourdomain.com/api/stripe/webhook
\`\`\`

Events:

\`\`\`txt
checkout.session.completed
payment_intent.succeeded
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
\`\`\`

ENV:

\`\`\`env
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
\`\`\`
`);

write("docs/v6-production-system/05-patch-v6.md", `
# 05 — Patch V6

Run:

\`\`\`bash
node patch-v6-production.mjs
npm install
npm run dev
\`\`\`

Added:

- lib/prompt-v6/*
- lib/orchestrator-v6.ts
- lib/funnel/engine.ts
- lib/bot/sales-flow.ts
- lib/ads/launch-engine.ts
- lib/kpi/kpi-engine.ts
- app/api/v6/run
- app/api/v6/kpi
- app/api/stripe/webhook
- app/api/projects/save
- supabase migration
`);

write("docs/v6-production-system/06-api-system.md", `
# 06 — API System

## Run full V6

\`\`\`txt
POST /api/v6/run
\`\`\`

Input:

\`\`\`json
{
  "text": "Tôi bán serum trị mụn",
  "product": "Serum trị mụn",
  "goal": "sale",
  "industry": "Beauty"
}
\`\`\`

Output:

- mechanism
- hook
- CTA
- layout
- visual
- posterPrompts
- funnel
- botFlow
- adsPlan
- kpiRules

## KPI

\`\`\`txt
POST /api/v6/kpi
\`\`\`
`);

write("docs/v6-production-system/07-render-engine.md", `
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
`);

write("docs/v6-production-system/08-editor-upgrade.md", `
# 08 — Editor Upgrade

Current editor:

- Drag/drop with react-rnd
- Export PNG with html-to-image
- Upload image layer

Next patches:

- Layer panel
- Inline text edit
- Font selector
- DESIGN.md color lock
- Template apply button
- Save project to Supabase
`);

write("docs/v6-production-system/09-marketplace-production.md", `
# 09 — Marketplace Production

Marketplace must support:

- Template list
- Pack detail page
- Stripe checkout
- Unlock download after payment
- DESIGN.md preview
- Prompt preview
- Usage guide

Production rule:

Do not return template files unless payment or user entitlement is verified.
`);

write("docs/v6-production-system/10-auth-project-save.md", `
# 10 — Auth + Project Save

Supabase auth flow:

- Login
- User session
- Save poster project
- Load project
- Export image

API:

\`\`\`txt
POST /api/projects/save
\`\`\`

DB:

\`\`\`txt
poster_projects
\`\`\`

Patch next:

- /dashboard/projects
- /project/[id]
- project autosave
`);

write("docs/v6-production-system/11-kpi-tracking.md", `
# 11 — KPI Tracking

Metrics:

- spend
- impressions
- clicks
- leads
- sales
- revenue

Calculated:

- CTR
- CPC
- CPL
- CPA
- ROAS
- profit

API:

\`\`\`txt
POST /api/v6/kpi
\`\`\`

Optimization rules:

- CTR low → change hook / visual
- CPL high → change offer / CTA
- ROAS high → scale winner
`);

write("docs/v6-production-system/12-deploy-vercel.md", `
# 12 — Deploy Vercel

Install:

\`\`\`bash
npm i -g vercel
\`\`\`

Deploy:

\`\`\`bash
vercel
vercel --prod
\`\`\`

Add env in Vercel:

\`\`\`env
NEXT_PUBLIC_APP_URL=https://yourdomain.com
OPENAI_API_KEY=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
\`\`\`

After domain setup, redeploy.
`);

write("docs/v6-production-system/13-go-live-checklist.md", `
# 13 — Go Live Checklist

Before launch:

- [ ] npm run build pass
- [ ] /api/v6/run works
- [ ] /api/v6/kpi works
- [ ] /studio generates prompt
- [ ] image render works
- [ ] editor export works
- [ ] Supabase save works
- [ ] Stripe checkout works
- [ ] Stripe webhook receives event
- [ ] production env correct
- [ ] domain connected
`);

write("docs/v6-production-system/14-debug-playbook.md", `
# 14 — Debug Playbook

## Build failed
Run:

\`\`\`bash
npm run build
\`\`\`

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
`);

write("docs/v6-production-system/15-scale-system.md", `
# 15 — Scale System

Phase 1:
- Launch template marketplace
- Sell 10 DESIGN.md packs
- Free demo studio

Phase 2:
- Add subscription
- Add user dashboard
- Add project save
- Add batch generation

Phase 3:
- Add KPI feedback loop
- Add ads import
- Add winner recommendation
- Add team workspace

Phase 4:
- AI Agency automation
- Funnel generator
- Bot sales integration
- TikTok launch system
`);

console.log("\\n🚀 V6 PRODUCTION PATCH DONE");
console.log("Next:");
console.log("1. npm install");
console.log("2. npm run dev");
console.log("3. Read docs/v6-production-system/00-overview.md");
