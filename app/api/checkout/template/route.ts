import Stripe from "stripe";
import { NextResponse } from "next/server";
import { packs as templatePacks } from "@/lib/marketplace/packs";

export async function POST(req: Request) {
  const { slug } = await req.json();

  if (!process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Missing Stripe key" });
  }

  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
  const pack = templatePacks.find(p => p.slug === slug);

  if (!pack) return NextResponse.json({ error: "Not found" });

  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{
      price_data: {
        currency: "usd",
        unit_amount: pack.price * 100,
        product_data: { name: pack.name }
      },
      quantity: 1
    }],
    success_url: process.env.NEXT_PUBLIC_APP_URL,
    cancel_url: process.env.NEXT_PUBLIC_APP_URL
  });

  return NextResponse.json({ url: session.url });
}
