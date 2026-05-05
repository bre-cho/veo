import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    modules: [
      "winner_dna_learning",
      "auto_scale_kill",
      "winner_clone",
      "weight_retrain",
      "heatmap_click_predictor",
    ],
  });
}
