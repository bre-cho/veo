export type MarketplacePack = {
  slug: string;
  name: string;
  price: number;
  goal: string;
  platform: string;
  category: string;
  score: number;
  logic: string;
  tags: string[];
  bestFor: string[];
  description: string;
  prompt: string;
  image: string;
};

export const packs: MarketplacePack[] = [
  {
    slug: "skincare-lead-gen-pack",
    name: "Beauty KOL Skincare Glow",
    price: 199000,
    goal: "Thu lead",
    platform: "TikTok",
    category: "Beauty",
    score: 96,
    logic: "HIGH TRUST - MID CTR - BRAND BUILD",
    tags: ["Trust", "Skincare", "KOL"],
    bestFor: ["beauty", "skincare", "spa", "serum", "mỹ phẩm"],
    description: "Dành cho mỹ phẩm, skincare, spa cần visual tạo niềm tin nhanh và tăng inbox hoặc đặt lịch.",
    prompt: "Luxury skincare advertising poster, close-up Asian female KOL model, glowing skin, warm golden studio lighting, serum bottle, premium beauty brand aesthetic.",
    image: "/templates/beauty-kol.jpg"
  },
  {
    slug: "fb-craving-sales-pack",
    name: "F&B Product Hunger Trigger",
    price: 149000,
    goal: "Bán hàng",
    platform: "Meta",
    category: "F&B",
    score: 92,
    logic: "MID CTR - HIGH CONVERSION - PRODUCT DESIRE",
    tags: ["F&B", "Conversion", "Product"],
    bestFor: ["food", "drink", "snack", "F&B", "thực phẩm"],
    description: "Dành cho đồ ăn, snack, nước uống cần kích thích thèm ăn và chốt đơn nhanh.",
    prompt: "Premium food product poster, appetizing close-up, golden light, product pack hero, natural ingredients, strong CTA, high conversion commercial photography.",
    image: "/templates/fnb-hito.jpg"
  },
  {
    slug: "fashion-viral-outfit-pack",
    name: "Fashion Drop Viral",
    price: 179000,
    goal: "Tăng nhấp",
    platform: "TikTok",
    category: "Fashion",
    score: 89,
    logic: "HIGH CTR - MID VALUE - VIRAL IDENTITY",
    tags: ["Fashion", "Viral", "Drop"],
    bestFor: ["fashion", "outfit", "streetwear", "collection", "clothing"],
    description: "Dành cho BST thời trang muốn nổi bật nhanh, dễ share và tăng nhận diện.",
    prompt: "High fashion campaign poster, bold outfit, confident model, cinematic city background, strong contrast, modern editorial typography.",
    image: "/templates/fashion-drop.jpg"
  },
  {
    slug: "real-estate-trust-pack",
    name: "Luxury Sleepwear Lookbook",
    price: 249000,
    goal: "Thu lead",
    platform: "TikTok",
    category: "Luxury",
    score: 94,
    logic: "LOW CTR - HIGH VALUE - ASPIRATION SELL",
    tags: ["Luxury", "Identity", "High Value"],
    bestFor: ["luxury", "lookbook", "premium", "fashion", "sleepwear"],
    description: "Dành cho thương hiệu cao cấp muốn tạo cảm giác sang, khát khao sở hữu và nhận diện mạnh.",
    prompt: "Luxury lookbook poster, black gold palette, premium product focus, cinematic background, elegant serif typography.",
    image: "/templates/luxury-sleepwear.jpg"
  },
  {
    slug: "fitness-transformation-pack",
    name: "Corporate Giftset Premium",
    price: 179000,
    goal: "Thu lead",
    platform: "Meta",
    category: "Gift",
    score: 90,
    logic: "LOW CTR - HIGH TRUST - B2B VALUE",
    tags: ["Gift", "B2B", "Premium"],
    bestFor: ["giftset", "quà tặng", "doanh nghiệp", "tri ân"],
    description: "Dành cho quà tặng doanh nghiệp, hộp quà tri ân, chiến dịch branding B2B.",
    prompt: "Luxury corporate giftset poster, premium box, ribbon, thank-you card, gold navy lighting, elegant flatlay, high trust branding.",
    image: "/templates/giftset-premium.jpg"
  },
  {
    slug: "course-authority-pack",
    name: "Authority Course Campaign",
    price: 249000,
    goal: "Thu lead",
    platform: "TikTok",
    category: "Education",
    score: 88,
    logic: "HIGH TRUST - CLARITY - LEAD CAPTURE",
    tags: ["Education", "Authority", "Lead"],
    bestFor: ["course", "coaching", "education", "đào tạo", "khóa học"],
    description: "Dành cho khóa học và coaching cần truyền uy tín, lộ trình rõ và tạo lead chất lượng.",
    prompt: "Educational authority poster, mentor portrait, curriculum highlights, trust badges, clear CTA, premium learning brand design.",
    image: "/templates/saas-demo.jpg"
  },
  {
    slug: "saas-demo-conversion-pack",
    name: "SaaS Demo Conversion",
    price: 299000,
    goal: "Đăng ký",
    platform: "Landing",
    category: "SaaS",
    score: 91,
    logic: "HIGH CLARITY - HIGH TRUST - SIGNUP INTENT",
    tags: ["SaaS", "Demo", "Signup"],
    bestFor: ["software", "AI", "SaaS", "tool", "dashboard", "app"],
    description: "Dành cho web app hoặc SaaS cần hero rõ giá trị, tăng đăng ký và demo request.",
    prompt: "Premium SaaS product hero poster, dark dashboard, glowing analytics, clear value proposition, orange CTA, Apple Stripe inspired.",
    image: "/templates/saas-demo.jpg"
  },
  {
    slug: "spa-clinic-booking-pack",
    name: "Spa Clinic Booking",
    price: 199000,
    goal: "Đặt lịch",
    platform: "Meta",
    category: "Beauty",
    score: 93,
    logic: "HIGH TRUST - HIGH ACTION - BOOKING",
    tags: ["Beauty", "Clinic", "Booking"],
    bestFor: ["spa", "clinic", "skincare", "treatment", "mụn"],
    description: "Dành cho spa, clinic, treatment ads cần tăng đặt lịch và tư vấn.",
    prompt: "Clinic booking poster, clean premium facial visual, trust icons, doctor-approved cues, strong booking CTA, soft luxury lighting.",
    image: "/templates/beauty-kol.jpg"
  },
  {
    slug: "event-fomo-pack",
    name: "Event FOMO Registration",
    price: 149000,
    goal: "Đăng ký",
    platform: "TikTok",
    category: "Event",
    score: 87,
    logic: "HIGH ATTENTION - URGENCY - REGISTRATION",
    tags: ["Event", "FOMO", "Signup"],
    bestFor: ["event", "launch", "webinar", "workshop", "đăng ký"],
    description: "Dành cho sự kiện cần tạo FOMO nhanh, tăng đăng ký và nhắc deadline.",
    prompt: "Event registration poster, countdown urgency, speaker or venue hero, bold CTA, high contrast typography, energetic commercial layout.",
    image: "/templates/fashion-drop.jpg"
  },
  {
    slug: "interior-transformation-pack",
    name: "Interior Transformation",
    price: 199000,
    goal: "Thu lead",
    platform: "Meta",
    category: "Home",
    score: 86,
    logic: "HIGH TRUST - BEFORE AFTER - LEAD",
    tags: ["Interior", "Transformation", "Lead"],
    bestFor: ["interior", "nội thất", "before after", "renovation"],
    description: "Dành cho nội thất hoặc cải tạo cần before-after rõ và lead tư vấn.",
    prompt: "Interior transformation poster, before-after room comparison, premium furniture hero, trust icons, consultation CTA, elegant natural lighting.",
    image: "/templates/giftset-premium.jpg"
  }
];
