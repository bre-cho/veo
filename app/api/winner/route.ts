import { NextRequest, NextResponse } from 'next/server';
import { selectWinner } from '@/lib/visual-engine-v5/generator';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    if (!Array.isArray(body.variants)) {
      return NextResponse.json({ error: 'Missing variants[]' }, { status: 400 });
    }
    return NextResponse.json({ winner: selectWinner(body.variants) });
  } catch {
    return NextResponse.json({ error: 'Failed to select winner' }, { status: 500 });
  }
}
