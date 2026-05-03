import { AdInput, Mechanism, Score, VariantMode } from './types';

function clamp(n: number) {
  return Math.max(0, Math.min(100, Math.round(n)));
}

export function scoreVariant(input: AdInput, mechanism: Mechanism, mode: VariantMode): Score {
  const goal = input.goal || 'sale';
  let ctr = 70;
  let attention = 70;
  let trust = 70;
  let conversion = 70;
  let brandFit = 75;
  let risk = 10;

  if (mode === 'viral') { ctr += 12; attention += 15; trust -= 8; conversion -= 4; }
  if (mode === 'trust') { trust += 15; brandFit += 10; ctr -= 3; }
  if (mode === 'conversion') { conversion += 15; trust += 5; risk += 4; }

  if (mechanism === 'problem') { conversion += 10; ctr += 6; risk += 6; }
  if (mechanism === 'ingredient') { ctr += 12; attention += 10; brandFit += 4; }
  if (mechanism === 'aspiration') { trust += 6; brandFit += 12; conversion -= 3; }
  if (mechanism === 'proof') { trust += 15; conversion += 10; }
  if (mechanism === 'offer') { conversion += 12; risk += 5; }

  if (goal === 'sale' && mode === 'conversion') conversion += 8;
  if (goal === 'awareness' && mode === 'viral') ctr += 8;
  if (goal === 'premium' && mode === 'trust') brandFit += 8;

  const finalScore = clamp(ctr * 0.25 + attention * 0.2 + trust * 0.2 + conversion * 0.25 + brandFit * 0.1 - risk * 0.15);
  return { ctr: clamp(ctr), attention: clamp(attention), trust: clamp(trust), conversion: clamp(conversion), brandFit: clamp(brandFit), risk: clamp(risk), finalScore };
}
