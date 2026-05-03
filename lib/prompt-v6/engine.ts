import { SellingMechanism, V6Input } from "./types";

export function detectSellingMechanism(input: V6Input): SellingMechanism {
  const t = [
    input.text,
    input.product,
    input.industry,
    input.audience,
    input.goal
  ].filter(Boolean).join(" ").toLowerCase();

  if (/giảm|khuyến mãi|ưu đãi|sale|deal|combo|giá/.test(t)) return "offer";
  if (/trước sau|before after|kết quả|biến đổi|thay đổi|transformation/.test(t)) return "result";
  if (/chuyên gia|bác sĩ|doctor|expert|được khuyên dùng|kiểm chứng/.test(t)) return "authority";
  if (/đau|vấn đề|lỗi|khó khăn|problem|pain|sợ/.test(t)) return "problem";
  if (/quy trình|framework|hướng dẫn|checklist|course|education|bài học/.test(t)) return "education";
  if (/event|sự kiện|workshop|hội thảo|countdown|đăng ký/.test(t)) return "event";
  if (/cảm xúc|đẹp|tự tin|quyến rũ|sang trọng|luxury|comfort/.test(t)) return "emotion";

  return "product";
}

export function generateHook(mechanism: SellingMechanism) {
  const hooks: Record<SellingMechanism, string> = {
    problem: "Bạn đang gặp vấn đề này?",
    result: "7 ngày thay đổi rõ rệt",
    emotion: "Bạn xứng đáng tốt hơn",
    offer: "Ưu đãi giới hạn hôm nay",
    authority: "Chuyên gia khuyên dùng",
    product: "Giải pháp đơn giản hơn bạn nghĩ",
    education: "Nhìn 1 lần là hiểu quy trình",
    event: "Bạn sắp bỏ lỡ sự kiện này?"
  };

  return hooks[mechanism];
}

export function generateCTA(goal: V6Input["goal"]) {
  if (goal === "sale") return "Mua ngay";
  if (goal === "lead") return "Nhận demo";
  if (goal === "click") return "Xem ngay";
  if (goal === "education") return "Tải framework";
  if (goal === "event") return "Đăng ký ngay";
  return "Khám phá";
}

export function decideLayout(input: V6Input, mechanism: SellingMechanism) {
  if (input.hasCollection) return "lookbook";
  if (mechanism === "education") return "editorial_grid";
  if (mechanism === "event") return "event_cover";
  if (mechanism === "result") return "before_after";
  if (mechanism === "authority") return "expert_trust";
  if (mechanism === "offer") return "price_badge";
  if (input.hasPackaging || mechanism === "product") return "product_dominance";
  return "realism";
}

export function decideVisual(mechanism: SellingMechanism) {
  const map: Record<SellingMechanism, string> = {
    product: "product_dominance",
    emotion: "lifestyle_emotion",
    problem: "problem_solution",
    result: "before_after",
    authority: "expert_face",
    offer: "price_badge",
    education: "infographic_grid",
    event: "fomo_countdown"
  };

  return map[mechanism];
}

export function buildPosterPrompts(input: V6Input, args: {
  mechanism: SellingMechanism;
  hook: string;
  cta: string;
  layout: string;
  visual: string;
}) {
  const product = input.product || input.text;
  const base = `
Create a premium poster for ${product}.

Mechanism: ${args.mechanism}
Visual: ${args.visual}
Layout: ${args.layout}
Hook: "${args.hook}"
CTA: "${args.cta}"

Rules:
- One main focus only
- Text readable in 1 second
- Clear visual hierarchy
- Strong but controlled contrast
- 25-30% whitespace
- Vietnamese text must be readable and correctly accented
- No clutter
- No random colors outside brand palette
`.trim();

  return {
    trust: base + "\n\nVersion: TRUST. Clean composition, realistic lighting, credible details, premium clarity.",
    viral: base + "\n\nVersion: VIRAL. Unusual angle, high contrast, exaggerated visual hook, scroll-stopping composition.",
    conversion: base + "\n\nVersion: CONVERSION. Product/benefit first, CTA visible, simple layout, action-driven hierarchy."
  };
}
