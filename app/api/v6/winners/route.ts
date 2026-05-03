import { NextResponse } from "next/server";
import { listWinnerDNA } from "@/lib/v6-pro/repository";

export async function GET() {
  try {
    const winners = await listWinnerDNA();
    return NextResponse.json({ ok: true, winners });
  } catch (error: any) {
    return NextResponse.json({ ok: false, error: error.message || "Cannot load winners" }, { status: 500 });
  }
}