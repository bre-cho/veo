import { NextResponse } from "next/server";
import { blurScore, thumbnailScore } from "@/lib/scoring/advanced";

export async function POST() {
  return NextResponse.json({
    blur: blurScore(),
    thumbnail: thumbnailScore()
  });
}
