import Stripe from "stripe";
import { headers } from "next/headers";
import { NextResponse } from "next/server";
import { addCredits, ensureProfile } from "@/lib/billing/credits";
import { createSupabaseServiceClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "missing");

const planCreditMap: Record<string, number> = {
  creator: 200,
  pro: 1000,
  studio: 5000
};

async function upsertPlan(userId: string, plan: string, stripeCustomerId?: string | null) {
  const supabase = createSupabaseServiceClient();
  await supabase
    .from("profiles")
    .update({ plan, stripe_customer_id: stripeCustomerId || null })
    .eq("id", userId);
}

export async function POST(req: Request) {
  if (!process.env.STRIPE_WEBHOOK_SECRET || !process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Stripe webhook env missing" }, { status: 400 });
  }

  const signature = (await headers()).get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ error: "Missing stripe-signature" }, { status: 400 });
  }

  const rawBody = await req.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (error) {
    return NextResponse.json({ error: "Webhook signature invalid", detail: String(error) }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const userId = session.metadata?.userId;
    const email = session.customer_details?.email || session.customer_email;
    const plan = session.metadata?.plan || "free";

    if (userId) {
      await ensureProfile(userId, email);
      await upsertPlan(userId, plan, typeof session.customer === "string" ? session.customer : null);

      const credits = planCreditMap[plan] || 0;
      if (credits > 0) {
        await addCredits(userId, credits, `Stripe subscription ${plan}`);
      }
    }
  }

  return NextResponse.json({ received: true });
}
