import Stripe from "stripe";
import { getUserFromBearer } from "@/lib/supabase/server";

const stripeKey = process.env.STRIPE_SECRET_KEY;

export async function POST(req: Request) {
  try {
    const auth = await getUserFromBearer(req);
    if (!auth.user) {
      return Response.json({ error: auth.error }, { status: 401 });
    }

    if (!stripeKey) {
      return Response.json({ error: "Missing STRIPE_SECRET_KEY" }, { status: 500 });
    }

    const body = await req.json();
    const name = String(body.name || "Ads Pack");
    const slug = String(body.slug || "pack");
    const amount = Number(body.price || 0);

    if (!Number.isFinite(amount) || amount <= 0) {
      return Response.json({ error: "Invalid pack price" }, { status: 400 });
    }

    const stripe = new Stripe(stripeKey, { apiVersion: "2026-04-22.dahlia" });
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [
        {
          quantity: 1,
          price_data: {
            currency: "vnd",
            unit_amount: Math.round(amount),
            product_data: {
              name,
              metadata: { slug }
            }
          }
        }
      ],
      success_url: `${appUrl}/marketplace?checkout=success`,
      cancel_url: `${appUrl}/marketplace?checkout=cancel`,
      customer_email: auth.user.email || undefined,
      metadata: {
        user_id: auth.user.id,
        pack_slug: slug
      }
    });

    return Response.json({ url: session.url });
  } catch (error: any) {
    return Response.json({ error: error.message || "Checkout create failed" }, { status: 500 });
  }
}
