import { AdInput, Mechanism, VariantMode } from './types';

export function buildPrompt(input: AdInput, mechanism: Mechanism, mode: VariantMode) {
  const product = input.product;
  const audience = input.audience || 'target customer';

  const base = `Vertical 9:16 high-conversion advertising poster for ${product}, targeted to ${audience}. Ultra realistic commercial photography, sharp product focus, premium layout, clear Vietnamese typography space, no watermark, no fake brand logo unless provided.`;

  const map: Record<VariantMode, string> = {
    trust: `Trust version: clean premium composition, confident model, product close-up, soft luxury lighting, benefit icons, credible claims, minimal elegant typography, strong brand trust.`,
    viral: `Viral version: explosive visual hook, dynamic splash or motion freeze, bright color contrast, oversized product/ingredient foreground, high attention layout, bold headline area.`,
    conversion: `Conversion version: problem-solution layout, visible proof blocks, before-after style composition when appropriate, checklist benefits, strong CTA zone, direct response ad design.`
  };

  const mechanismText: Record<Mechanism, string> = {
    problem: `Selling mechanism: pain-point transformation, show the customer problem clearly and present ${product} as the simple solution, avoid medical overclaim.`,
    ingredient: `Selling mechanism: ingredient freshness, show natural ingredients, ice, splash, freshness, sensory appeal, appetite and refreshment cues.`,
    aspiration: `Selling mechanism: aspiration and identity, luxury mood, confidence, status, lifestyle upgrade, cinematic background.`,
    proof: `Selling mechanism: evidence and feedback, show review cards, product texture, usage proof, detail close-ups.`,
    offer: `Selling mechanism: irresistible offer, highlight bundle/value/limited-time deal while keeping design premium.`,
    lifestyle: `Selling mechanism: lifestyle fit, show the product naturally integrated into a desirable daily moment.`
  };

  return `${base} ${map[mode]} ${mechanismText[mechanism]}`;
}
