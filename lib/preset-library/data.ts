import { PresetTemplate } from "./types";

export const BEAUTY_ENGINE_V4_TEMPLATES: PresetTemplate[] = [
  {
    template_id: "beauty_lipstick_split_luxury_v1",
    name: "Luxury Lipstick Split Before/After",
    engine: "beauty_engine_v4",
    industry: "beauty",
    category: "lipstick",
    format: "4:5",
    qa_hardlock: {
      brand_required: true,
      min_value_icons: 3,
      cta_required: true,
      single_focus: true,
      winner_dna_required_before_publish: true,
    },
    recommended_text: {
      headline: "",
      cta: "INBOX CHỌN MÀU THEO CÁ TÍNH",
      icons: [
        "⚡ Lên màu tức thì",
        "💧 Không khô môi",
        "🔥 Cực kỳ nổi bật",
      ],
    },
    prompt: `Ultra high converting luxury lipstick ad poster

MAIN VISUAL:
Extreme close-up lips with split effect:
left side: natural lips, slightly pale, low saturation, subtle dryness
right side: rich deep red lipstick, vibrant, high micro contrast

LIPSTICK:
gold luxury lipstick placed at the center between both sides
tip lightly touching lower lip (apply moment)
strong golden glow aura around lipstick
metallic reflection sharp and premium
subtle cinematic light streak

LIGHTING:
focused highlight on lipstick and lips only
soft beauty light on face
dark luxury background (black / deep navy)

TEXT:
bottom CTA button: "INBOX CHỌN MÀU THEO CÁ TÍNH"

ICONS:
3 small glowing icons near lips:
⚡ Lên màu tức thì
💧 Không khô môi
🔥 Cực kỳ nổi bật

STYLE:
ultra realistic, no plastic skin
visible lip texture
cinematic luxury beauty campaign

FORMAT:
vertical 4:5`,
    negative_prompt:
      "plastic skin, over-smoothed lips, flat lighting, missing CTA, missing value icons, unreadable Vietnamese, cluttered layout, distorted lipstick, watermark",
    ctr_notes: {
      strength: "Before/after split + apply moment + gold lipstick aura",
      predicted_ctr: "3.5%–4.8%",
      best_for: [
        "cold traffic",
        "beauty product launch",
        "TikTok/Facebook vertical ads",
      ],
    },
  },
  {
    template_id: "fashion_sleepwear_realistic_editorial_v1",
    name: "Luxury Sleepwear Realistic Editorial",
    engine: "fashion_engine_v4",
    industry: "fashion",
    category: "sleepwear_loungewear",
    format: "3:4",
    qa_hardlock: {
      brand_required: true,
      min_value_icons: 3,
      cta_required: true,
      single_focus: true,
      editorial_safe_styling: true,
      winner_dna_required_before_publish: true,
    },
    recommended_text: {
      headline: "Tinh tế & Quyến rũ",
      cta: "INBOX TƯ VẤN SIZE & MẪU",
      icons: [
        "✨ Ren cao cấp",
        "🖤 Thiết kế tối giản",
        "🌙 Mặc nhà sang trọng",
      ],
    },
    prompt: `Create a 3:4 vertical high-end fashion poster for a luxury sleepwear / loungewear collection in black and blush pink tones.

REALISM PRIORITY:
Ultra photorealistic, must look like a real camera photo, NOT AI-generated.
Preserve natural imperfections and avoid over-perfection.

DO NOT:
- overly smooth skin
- plastic skin texture
- perfect symmetry
- unrealistic body proportions
- exaggerated curves
- artificial lighting glow
- beauty filter look

MODEL:
A young Asian female model with realistic natural beauty:
visible skin texture, slight uneven tone, tiny imperfections
natural face asymmetry
normal eye size, natural lips, subtle under-eye texture
real skin shading, not airbrushed

Hair:
Long black hair, slightly messy, a few loose strands, natural flyaways, NOT perfectly styled.

Body:
Natural proportions, realistic gravity, no exaggerated shaping.

POSE:
Minimalist fashion pose, standing relaxed, slight body angle.
Micro-adjusted posture like real photoshoot.
Hands relaxed, fingers naturally imperfect.
Expression: neutral, calm, slightly distant editorial gaze.

LIGHTING:
Professional studio lighting but natural:
one soft key light from side
subtle shadow falloff
no over-glow
slight shadow imperfections on skin
realistic highlight roll-off

CAMERA:
50mm or 85mm lens
shallow depth of field, natural
subtle grain/noise
realistic dynamic range, no HDR look

BACKGROUND:
Soft pink gradient studio wall, slightly uneven tone.
No perfectly flat digital gradient.

OUTFIT:
Editorial-safe luxury sleepwear inspired by lace/mesh design.
Elegant coverage with refined black lace and mesh layers.
Fabric reacts to gravity naturally, slight wrinkles and folds.
Lace details slightly imperfect and realistic.

LAYOUT:
Center: full-body model dominant
Right: 2–3 real close-up crops (fabric, lace, straps)
Bottom: product + packaging shot with realistic shadows

TEXT:
"Tinh tế & Quyến rũ"
"Chất liệu ren cao cấp"
"Thiết kế tối giản – Đẳng cấp"

FINAL LOOK:
Luxury fashion campaign photographed in real life.
Magazine shoot feel, not rendered image.
Subtle imperfections make it believable.`,
    negative_prompt:
      "explicit nudity, overly transparent sensitive areas, unrealistic body, plastic skin, perfect symmetry, HDR look, AI render look, distorted anatomy, unreadable Vietnamese, watermark",
    ctr_notes: {
      strength:
        "Realistic editorial trust + material close-ups + premium styling",
      predicted_ctr: "2.4%–3.5%",
      best_for: ["fashion lookbook", "landing page", "premium retargeting"],
    },
  },
  {
    template_id: "fnb_watermelon_juice_low_angle_product_dominance_v1",
    name: "Watermelon Juice Product Dominance",
    engine: "fnb_engine_v4",
    industry: "fnb",
    category: "beverage",
    format: "4:5_or_9:16",
    qa_hardlock: {
      brand_required: true,
      min_value_icons: 3,
      cta_required: true,
      single_focus: true,
      product_dominates_foreground: true,
      winner_dna_required_before_publish: true,
    },
    recommended_text: {
      headline: "DƯA HẤU TƯƠI MÁT",
      cta: "ĐẶT NGAY – GIẢI NHIỆT HÔM NAY",
      icons: ["🍉 Tươi mát", "⚡ Bổ sung năng lượng", "💧 Giải nhiệt tức thì"],
    },
    prompt: `Low-angle fashion campaign photograph of a confident model holding a large watermelon juice very close to the camera.

COMPOSITION:
exaggerated perspective with the hand and product dominating the foreground
full-body pose visible in the background
wide stance, dynamic posture
product is the largest visual object and sharpest focus

BACKGROUND:
clean pure white studio background
ultra-clean commercial composition

LIGHTING:
high-key lighting
crisp shadows
sharp focus on product
slight depth of field on the model

MODEL:
confident modern model
bold colorful outfit with strong contrast tones
commercial lifestyle energy

PRODUCT:
large watermelon juice packaging/cup
glossy packaging detail visible
condensation droplets, fresh cold feeling
watermelon color cues, fresh splash accent

TEXT:
headline: "DƯA HẤU TƯƠI MÁT"
3 value icons:
🍉 Tươi mát
⚡ Bổ sung năng lượng
💧 Giải nhiệt tức thì
CTA: "ĐẶT NGAY – GIẢI NHIỆT HÔM NAY"

STYLE:
modern F&B advertising aesthetic
scroll-stopping product dominance
ultra realistic studio photography
clean layout with typography space`,
    negative_prompt:
      "product too small, cluttered background, flat lighting, unreadable label, missing CTA, missing value icons, distorted hands, floating product, watermark",
    ctr_notes: {
      strength:
        "Low-angle exaggerated product dominance + clean white studio + fresh thirst trigger",
      predicted_ctr: "2.8%–4.0%",
      best_for: [
        "F&B launch",
        "beverage promo",
        "TikTok/Reels vertical ads",
      ],
    },
  },
];

export const PRESET_TEMPLATES_MAP = new Map(
  BEAUTY_ENGINE_V4_TEMPLATES.map((t) => [t.template_id, t])
);
