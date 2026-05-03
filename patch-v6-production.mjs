import fs from "fs";
import path from "path";

const ROOT = process.cwd();

function write(file, content) {
  const full = path.join(ROOT, file);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content.trimStart(), "utf8");
  console.log("✅", file);
}

function updatePkg() {
  const file = "package.json";
  const pkg = JSON.parse(fs.readFileSync(file, "utf8"));

  pkg.dependencies = {
    ...(pkg.dependencies || {}),
    "@supabase/ssr": "latest",
    "@supabase/supabase-js": "latest",
    "stripe": "latest",
    "zod": "latest",
    "html-to-image": "latest",
    "js-yaml": "latest"
  };

  fs.writeFileSync(file, JSON.stringify(pkg, null, 2));
}

updatePkg();


// =======================
// PROMPT ENGINE V6
// =======================

write("lib/prompt-v6/engine.ts", `
export function detectMechanism(text: string) {
  const t = text.toLowerCase();

  if (/giảm|deal|sale/.test(t)) return "offer";
  if (/before|after|trước/.test(t)) return "result";
  if (/chuyên gia|doctor/.test(t)) return "authority";
  if (/đau|lỗi|problem/.test(t)) return "problem";
  if (/đẹp|tự tin/.test(t)) return "emotion";

  return "product";
}

export function hook(mech: string) {
  const map = {
    problem: "Bạn đang gặp vấn đề này?",
    result: "7 ngày thay đổi rõ rệt",
    emotion: "Bạn xứng đáng tốt hơn",
    offer: "Giảm 50% hôm nay",
    authority: "Chuyên gia khuyên dùng",
    product: "Giải pháp đơn giản"
  };
  return map[mech] || map.product;
}

export function cta(goal: string) {
  if (goal === "sale") return "Mua ngay";
  if (goal === "lead") return "Nhận demo";
  return "Xem ngay";
}
`);


// =======================
// ORCHESTRATOR
// =======================

write("lib/orchestrator.ts", `
import { detectMechanism, hook, cta } from "./prompt-v6/engine";

export function runSystem(input: any) {
  const mechanism = detectMechanism(input.text);

  return {
    mechanism,
    hook: hook(mechanism),
    cta: cta(input.goal),
    visual: decideVisual(mechanism),
    funnel: {
      landing: "Landing cơ bản",
      followup: ["Bạn cần demo không?", "Mình hỗ trợ bạn"]
    }
  };
}

function decideVisual(mech: string) {
  if (mech === "result") return "before_after";
  if (mech === "authority") return "expert_face";
  if (mech === "emotion") return "lifestyle";
  if (mech === "offer") return "price_badge";
  return "product";
}
`);


// =======================
// FULL API
// =======================

write("app/api/v6/run/route.ts", `
import { runSystem } from "@/lib/orchestrator";

export async function POST(req: Request) {
  const input = await req.json();
  return Response.json(runSystem(input));
}
`);


// =======================
// STRIPE WEBHOOK
// =======================

write("app/api/stripe/webhook/route.ts", `
import Stripe from "stripe";
import { NextResponse } from "next/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get("stripe-signature")!;

  try {
    const event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    );

    if (event.type === "checkout.session.completed") {
      console.log("💰 Payment success");
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json({ error: "Webhook error" }, { status: 400 });
  }
}
`);


// =======================
// DOCS FOLDER
// =======================

write("docs/v6-production-system/00-overview.md", `
# V6 Production System

AI Ads Factory SaaS:

Input text
→ AI generate poster
→ landing
→ bot
→ ads
→ KPI tracking
`);

write("docs/v6-production-system/01-setup-local.md", `
# Setup Local

npm install
npm run dev
`);

write("docs/v6-production-system/02-env-config.md", `
# ENV

OPENAI_API_KEY=
STRIPE_SECRET_KEY=
NEXT_PUBLIC_APP_URL=

SUPABASE_URL=
SUPABASE_ANON_KEY=
`);

write("docs/v6-production-system/03-supabase-setup.md", `
# Supabase

create table poster_projects (...)
`);

write("docs/v6-production-system/04-stripe-setup.md", `
# Stripe

create product
setup webhook
`);

write("docs/v6-production-system/12-deploy-vercel.md", `
# Deploy

vercel
add env
deploy
`);

write("docs/v6-production-system/13-go-live-checklist.md", `
# Go Live

- test payment
- test generate
- test save
`);

console.log("🚀 V6 PATCH DONE");
