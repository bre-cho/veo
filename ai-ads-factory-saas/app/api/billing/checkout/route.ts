import Stripe from "stripe";
import { NextResponse } from "next/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "missing");

const priceMap: Record<string, string | undefined> = {
  creator: process.env.STRIPE_PRICE_CREATOR,
  pro: process.env.STRIPE_PRICE_PRO,
  studio: process.env.STRIPE_PRICE_STUDIO
};

export async function POST(req: Request) {
  const { plan, userId, email } = await req.json();
  const price = priceMap[plan];

  if (!process.env.STRIPE_SECRET_KEY || !price || !userId || !email) {
    return NextResponse.json({ error: "Stripe env missing or invalid plan" }, { status: 400 });
  }

  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    allow_promotion_codes: true,
    customer_email: email,
    line_items: [{ price, quantity: 1 }],
    metadata: { plan, userId },
    success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?success=1`,
    cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/pricing?cancel=1`
  });

  return NextResponse.json({ url: session.url });
}
