import { NextResponse } from "next/server";
import { z } from "zod";
import { calculateKpi, optimizeFromKpi } from "@/lib/kpi/kpi-engine";

const KpiInputSchema = z.object({
  spend: z.number().nonnegative(),
  impressions: z.number().int().nonnegative(),
  clicks: z.number().int().nonnegative(),
  leads: z.number().int().nonnegative(),
  sales: z.number().int().nonnegative(),
  revenue: z.number().nonnegative()
});

export async function POST(req: Request) {
  try {
    const payload = await req.json();
    const row = KpiInputSchema.parse(payload);
    const metrics = calculateKpi(row);

    return NextResponse.json({
      metrics,
      recommendation: optimizeFromKpi(metrics)
    });
  } catch (error: any) {
    if (error?.name === "ZodError") {
      return NextResponse.json({ error: "Invalid payload", details: error.issues }, { status: 400 });
    }

    return NextResponse.json({ error: error.message || "KPI calculation failed" }, { status: 500 });
  }
}
