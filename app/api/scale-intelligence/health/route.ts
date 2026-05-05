import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    modules: [
      "auto_industry_detector",
      "winner_learning_engine",
      "auto_funnel_generator",
      "real_ctr_data_engine",
    ],
  });
}
