import { NextResponse } from "next/server";
import { WinnerDNALearner } from "@/lib/self-learning-ai";

export async function GET() {
  const winners = await new WinnerDNALearner().listWinners();
  return NextResponse.json({ winners });
}
