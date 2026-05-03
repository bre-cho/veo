import { AdInput, AdVariant, VariantMode } from './types';
import { detectSellingMechanism } from './detect';
import { buildPrompt } from './prompt';
import { scoreVariant } from './scoring';

const modes: VariantMode[] = ['trust', 'viral', 'conversion'];

function copyFor(mode: VariantMode, product: string) {
  if (mode === 'trust') return {
    title: 'TRUST VERSION',
    hook: `${product} — lựa chọn đáng tin cho mỗi ngày`,
    cta: 'Tìm hiểu ngay',
    caption: `Một thiết kế ads tập trung vào niềm tin, lợi ích rõ ràng và cảm giác thương hiệu chuyên nghiệp cho ${product}.`
  };
  if (mode === 'viral') return {
    title: 'VIRAL VERSION',
    hook: `Bạn đã thấy ${product} phiên bản gây chú ý này chưa?`,
    cta: 'Xem ngay',
    caption: `Một biến thể visual mạnh, màu nổi, motion cao để kéo attention và test CTR cho ${product}.`
  };
  return {
    title: 'CONVERSION VERSION',
    hook: `Đang cần giải pháp cho ${product}?`,
    cta: 'Mua ngay / Nhận tư vấn',
    caption: `Một biến thể bán hàng trực tiếp, rõ vấn đề, rõ lợi ích, rõ hành động cho ${product}.`
  };
}

export function generateAdVariants(input: AdInput): AdVariant[] {
  const mechanism = detectSellingMechanism(input);
  return modes.map((mode) => {
    const copy = copyFor(mode, input.product);
    const score = scoreVariant(input, mechanism, mode);
    return {
      id: `${mode}_${mechanism}_${Date.now()}`,
      mode,
      mechanism,
      title: copy.title,
      hook: copy.hook,
      visualDirection: [
        `Mode: ${mode}`,
        `Mechanism: ${mechanism}`,
        `Product: ${input.product}`,
        `Audience: ${input.audience || 'mass market'}`
      ],
      imagePrompt: buildPrompt(input, mechanism, mode),
      caption: copy.caption,
      cta: copy.cta,
      funnel: {
        landingHook: copy.hook,
        offerAngle: input.offer || 'value + trust + simple action',
        trackingEvent: ['view_ad', 'click_cta', 'view_landing', 'lead_or_purchase']
      },
      score
    };
  });
}

export function selectWinner(variants: AdVariant[]) {
  return [...variants].sort((a, b) => b.score.finalScore - a.score.finalScore)[0];
}
