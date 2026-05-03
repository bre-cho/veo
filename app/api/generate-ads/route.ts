import { NextRequest, NextResponse } from 'next/server';
import { generateAdVariants, selectWinner } from '@/lib/visual-engine-v5/generator';

export async function POST(req: NextRequest) {
  try {
    const input = await req.json();
    if (!input?.product) {
      return NextResponse.json({ error: 'Missing product' }, { status: 400 });
    }
    const variants = generateAdVariants(input);
    const winner = selectWinner(variants);
    return NextResponse.json({ input, variants, winner });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to generate ads' }, { status: 500 });
  }
}
