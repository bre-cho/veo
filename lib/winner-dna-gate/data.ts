/**
 * Mock Winner DNA database - would load from Supabase in production
 * Structure: industry -> winners array
 */
export const MOCK_WINNER_DNA_DB: Record<string, any[]> = {
  beauty: [
    {
      dna_id: "beauty_winner_01",
      industry: "beauty",
      hook: "Ultra high converting luxury lipstick ad poster",
      visual_concept: "Extreme close-up lips with split effect",
      cta: "INBOX CHỌN MÀU THEO CÁ TÍNH",
      icons: ["⚡ Lên màu tức thì", "💧 Không khô môi", "🔥 Cực kỳ nổi bật"],
      predicted_ctr: "3.5%–4.8%",
      metadata: {
        template: "beauty_lipstick_split_luxury_v1",
        tested_variants: 3,
        winner_rate: "87%",
      },
    },
  ],
  fnb: [
    {
      dna_id: "fnb_winner_01",
      industry: "fnb",
      hook: "Low-angle fashion campaign photograph of a confident model holding a large watermelon juice",
      visual_concept:
        "Product dominance with low-angle perspective and exaggerated foreground",
      cta: "ĐẶT NGAY – GIẢI NHIỆT HÔM NAY",
      icons: ["🍉 Tươi mát", "⚡ Bổ sung năng lượng", "💧 Giải nhiệt tức thì"],
      predicted_ctr: "2.8%–4.0%",
      metadata: {
        template: "fnb_watermelon_juice_low_angle_product_dominance_v1",
        tested_variants: 3,
        winner_rate: "82%",
      },
    },
  ],
  fashion: [
    {
      dna_id: "fashion_winner_01",
      industry: "fashion",
      hook: "Luxury sleepwear realistic editorial with natural imperfections",
      visual_concept:
        "Ultra photorealistic model in professional studio lighting with natural beauty",
      cta: "INBOX TƯ VẤN SIZE & MẪU",
      icons: ["✨ Ren cao cấp", "🖤 Thiết kế tối giản", "🌙 Mặc nhà sang trọng"],
      predicted_ctr: "2.4%–3.5%",
      metadata: {
        template: "fashion_sleepwear_realistic_editorial_v1",
        tested_variants: 3,
        winner_rate: "79%",
      },
    },
  ],
};

export class WinnerDNALoader {
  byIndustry(industry: string): any[] {
    const normalized = industry.toLowerCase();
    return MOCK_WINNER_DNA_DB[normalized] || [];
  }

  byId(id: string): any | null {
    for (const winners of Object.values(MOCK_WINNER_DNA_DB)) {
      const found = winners.find((w) => w.dna_id === id);
      if (found) return found;
    }
    return null;
  }
}
