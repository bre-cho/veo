import { NextRequest, NextResponse } from 'next/server';
import { scoreVariant } from '@/lib/visual-engine-v5/scoring';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const score = scoreVariant(body.input, body.mechanism, body.mode);
    return NextResponse.json({ score });
  } catch {
    return NextResponse.json({ error: 'Failed to score ad' }, { status: 500 });
  }
}
