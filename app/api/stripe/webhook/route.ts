import Stripe from "stripe";
import { NextResponse } from "next/server";
import { createSupabaseServiceClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

const stripeSecret = process.env.STRIPE_SECRET_KEY;
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

function getStripeClient() {
  if (!stripeSecret) {
    throw new Error("Missing STRIPE_SECRET_KEY");
  }

  return new Stripe(stripeSecret, { apiVersion: "2026-04-22.dahlia" });
}

async function handleCheckoutCompleted(session: Stripe.Checkout.Session) {
  const userId = session.metadata?.user_id;
  const packSlug = session.metadata?.pack_slug;

  if (!userId || !packSlug) {
    return;
  }

  const supabase = createSupabaseServiceClient();

  await supabase.from("profiles").upsert(
    {
      id: userId,
      email: session.customer_details?.email || session.customer_email || null,
      stripe_customer_id: typeof session.customer === "string" ? session.customer : null
    },
    { onConflict: "id" }
  );

  await supabase.from("template_pack_entitlements").upsert(
    {
      user_id: userId,
      pack_slug: packSlug,
      stripe_session_id: session.id,
      stripe_payment_intent_id:
        typeof session.payment_intent === "string" ? session.payment_intent : null,
      amount_paid: Number(session.amount_total || 0),
      currency: session.currency || "vnd"
    },
    { onConflict: "user_id,pack_slug" }
  );
}

export async function POST(req: Request) {
  if (!webhookSecret) {
    return NextResponse.json({ error: "Missing STRIPE_WEBHOOK_SECRET" }, { status: 400 });
  }

  const sig = req.headers.get("stripe-signature");
  if (!sig) {
    return NextResponse.json({ error: "Missing stripe-signature" }, { status: 400 });
  }

  const body = await req.text();

  try {
    const stripe = getStripeClient();
    const event = stripe.webhooks.constructEvent(body, sig, webhookSecret);

    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        await handleCheckoutCompleted(session);
        break;
      }
      case "payment_intent.succeeded":
      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted":
      default:
        break;
    }

    return NextResponse.json({ received: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Webhook error" }, { status: 400 });
  }
}
