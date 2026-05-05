import { NextResponse } from "next/server";
import { WinnerDNALearner } from "@/lib/self-learning-ai";

export async function POST() {
  const model = await new WinnerDNALearner().retrain();
  return NextResponse.json(model);
}
