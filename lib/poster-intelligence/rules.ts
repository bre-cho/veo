export const INDUSTRY_COLOR_HINTS: Record<string, string[]> = {
  beauty: ["gold", "beige", "white", "champagne", "pink"],
  fnb: ["red", "green", "yellow", "orange", "fresh"],
  fashion: ["black", "white", "beige", "gold", "minimal"],
  fmcg: ["green", "gold", "yellow", "natural"],
  saas: ["dark", "blue", "neon", "glow"],
  education: ["blue", "white", "green", "clean"],
};

export const ICON_SUGGESTIONS: Record<string, string[]> = {
  beauty: ["Dưỡng trắng", "Cấp ẩm sâu", "Phục hồi & bảo vệ"],
  fnb: ["Tươi mát", "Giàu vitamin", "Bổ sung năng lượng"],
  fashion: ["Form tôn dáng", "Chất liệu cao cấp", "Dễ phối đồ"],
  fmcg: ["Tự nhiên", "Giòn ngon", "An toàn"],
  saas: ["Tăng CTR", "Tạo nhanh", "Tự động tối ưu"],
  education: ["Chẩn đoán điểm yếu", "Lộ trình rõ", "Tăng điểm"],
  custom: ["Giá trị nổi bật 1", "Giá trị nổi bật 2", "Giá trị nổi bật 3"],
};

export const CTA_PATTERNS: Record<string, string[]> = {
  beauty: ["Test da miễn phí", "Nhận ưu đãi hôm nay", "Inbox để được tư vấn"],
  fnb: ["Đặt ngay", "Nhận deal hôm nay", "Giao tận nơi"],
  fashion: ["Xem bộ sưu tập", "Inbox tư vấn size", "Mua ngay"],
  fmcg: ["Đặt hàng ngay", "Nhận tư vấn", "Mua ngay hôm nay"],
  saas: ["Nhận demo miễn phí", "Tạo ads ngay", "Bắt đầu tối ưu"],
  education: ["Test đầu vào miễn phí", "Nhận lộ trình học", "Đăng ký tư vấn"],
  custom: ["Inbox ngay", "Nhận ưu đãi", "Mua ngay"],
};

export const HARDLOCK_RULES = [
  {
    rule_id: "brand_required",
    severity: "blocker",
    check: (poster: any) => !!poster.brand_name,
    message: "Brand/Logo không được để trống",
    fix: "Thêm tên thương hiệu rõ ràng vào visual hoặc headline",
  },
  {
    rule_id: "headline_required",
    severity: "blocker",
    check: (poster: any) => !!poster.headline,
    message: "Hook/Headline không được để trống",
    fix: "Viết headline mạnh mẽ giải quyết pain point",
  },
  {
    rule_id: "product_visual_required",
    severity: "blocker",
    check: (poster: any) => !!poster.product_focus && !!poster.visual_description,
    message: "Product visual không rõ",
    fix: "Đảm bảo product là focus chính trong hình ảnh",
  },
  {
    rule_id: "min_icons",
    severity: "blocker",
    check: (poster: any) => (poster.value_icons?.length || 0) >= 3,
    message: "Số lượng value icons < 3",
    fix: "Thêm ít nhất 3 icon giá trị hợp lệ cho ngành",
  },
  {
    rule_id: "cta_required",
    severity: "blocker",
    check: (poster: any) => !!poster.slogan_or_cta,
    message: "CTA/Slogan không được để trống",
    fix: "Thêm CTA giải quyết pain point ngay tức thì",
  },
  {
    rule_id: "single_focus",
    severity: "major",
    check: (poster: any) => (poster.text_blocks?.length || 0) <= 3,
    message: "Quá nhiều text blocks (lỗi UX layout)",
    fix: "Giảm số lượng text, tập trung vào 1 message chính",
  },
];

export const getIndustryRules = (industry: string = "custom") => {
  const normalizedIndustry = industry.toLowerCase();
  return {
    colors: INDUSTRY_COLOR_HINTS[normalizedIndustry] || INDUSTRY_COLOR_HINTS.custom,
    icons: ICON_SUGGESTIONS[normalizedIndustry] || ICON_SUGGESTIONS.custom,
    ctas: CTA_PATTERNS[normalizedIndustry] || CTA_PATTERNS.custom,
  };
};
