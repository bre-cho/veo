export type Goal = 'sale' | 'awareness' | 'premium' | 'lead';
export type Mechanism = 'problem' | 'ingredient' | 'aspiration' | 'proof' | 'offer' | 'lifestyle';
export type VariantMode = 'trust' | 'viral' | 'conversion';

export interface AdInput {
  product: string;
  industry?: string;
  goal?: Goal;
  audience?: string;
  priceTier?: 'low' | 'mid' | 'premium';
  brandTone?: string;
  offer?: string;
}

export interface Score {
  ctr: number;
  attention: number;
  trust: number;
  conversion: number;
  brandFit: number;
  risk: number;
  finalScore: number;
}

export interface AdVariant {
  id: string;
  mode: VariantMode;
  mechanism: Mechanism;
  title: string;
  hook: string;
  visualDirection: string[];
  imagePrompt: string;
  caption: string;
  cta: string;
  funnel: {
    landingHook: string;
    offerAngle: string;
    trackingEvent: string[];
  };
  score: Score;
}
