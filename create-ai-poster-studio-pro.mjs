import fs from "fs";
import path from "path";
import { execSync } from "child_process";

const root = "ai-poster-studio-pro";

function write(file, content) {
  const full = path.join(root, file);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content.trimStart(), "utf8");
}

fs.rmSync(root, { recursive: true, force: true });
fs.rmSync(`${root}.zip`, { force: true });
fs.mkdirSync(root);

write("package.json", `
{
  "name": "ai-poster-studio-pro",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "latest",
    "react": "latest",
    "react-dom": "latest",
    "openai": "latest",
    "zod": "latest",
    "js-yaml": "latest",
    "zustand": "latest",
    "react-rnd": "latest",
    "stripe": "latest"
  },
  "devDependencies": {
    "typescript": "latest",
    "@types/node": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "@types/js-yaml": "latest"
  }
}
`);

write("tsconfig.json", `
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": false,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  },
  "include": ["**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
`);

write("next.config.mjs", `export default {};`);

write(".env.example", `
OPENAI_API_KEY=
NEXT_PUBLIC_APP_URL=http://localhost:3000
STRIPE_SECRET_KEY=
`);

write("app/layout.tsx", `
import "./globals.css";

export const metadata = {
  title: "AI Poster Studio Pro",
  description: "AI Agency Visual Engine for poster creation"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
`);

write("app/globals.css", `
body {
  margin: 0;
  background: #0A0F2C;
  color: white;
  font-family: Inter, Arial, sans-serif;
}
a { color: inherit; text-decoration: none; }
input, textarea, select, button { font-family: inherit; }
.card {
  background: #111827;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 20px;
  padding: 24px;
}
.btn {
  background: #2563EB;
  color: white;
  border: 0;
  border-radius: 14px;
  padding: 14px 18px;
  font-weight: 800;
  cursor: pointer;
}
.input {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(0,0,0,.3);
  color: white;
  box-sizing: border-box;
}
`);

write("app/page.tsx", `
import Link from "next/link";

export default function Home() {
  return (
    <main style={{ minHeight: "100vh", padding: 40 }}>
      <section style={{ maxWidth: 1080, margin: "0 auto", textAlign: "center", paddingTop: 80 }}>
        <p style={{ color: "#FACC15", fontWeight: 900 }}>AI Agency Visual Engine</p>
        <h1 style={{ fontSize: 64, lineHeight: 1.05, fontWeight: 950 }}>
          Tạo poster chuyên nghiệp bằng AI Creative Director
        </h1>
        <p style={{ color: "#CBD5E1", fontSize: 20 }}>
          Prompt Engine V5 tự quyết định mục tiêu, màu, typography, layout, visual hook, scoring và template DESIGN.md.
        </p>
        <div style={{ marginTop: 32, display: "flex", gap: 16, justifyContent: "center" }}>
          <Link className="btn" href="/studio">Mở Studio</Link>
          <Link className="btn" href="/editor">Mở Editor</Link>
          <Link className="btn" href="/marketplace">Marketplace</Link>
        </div>
      </section>
    </main>
  );
}
`);

write("lib/prompt-v5/color-engine.ts", `
export type ColorIntent = "luxury" | "energy" | "trust" | "beauty" | "tech" | "education" | "event";

export function generateColorSystem(intent: ColorIntent) {
  const map = {
    luxury: { scheme: "monochromatic + accent", primary: "#0B0B0B", accent: "#D4AF37", background: "#F8F5F2", text: "#111111", emotion: "sang trọng, cao cấp, tinh tế" },
    energy: { scheme: "complementary", primary: "#FACC15", accent: "#EF4444", background: "#050505", text: "#FFFFFF", emotion: "mạnh, trẻ, nổi bật" },
    trust: { scheme: "analogous", primary: "#2563EB", accent: "#22C55E", background: "#F8FAFC", text: "#111827", emotion: "tin cậy, rõ ràng, chuyên nghiệp" },
    beauty: { scheme: "soft analogous", primary: "#F8C8DC", accent: "#D8A7B1", background: "#FFF7F2", text: "#3B2F2F", emotion: "mềm mại, nữ tính, sạch" },
    tech: { scheme: "dark neon", primary: "#0A0F2C", accent: "#2563EB", background: "#020617", text: "#FFFFFF", emotion: "hiện đại, thông minh, tốc độ" },
    education: { scheme: "high contrast", primary: "#111827", accent: "#FACC15", background: "#FFFFFF", text: "#111827", emotion: "rõ ràng, dễ học, có cấu trúc" },
    event: { scheme: "split complementary", primary: "#7C3AED", accent: "#F97316", background: "#111827", text: "#FFFFFF", emotion: "FOMO, năng lượng, náo nhiệt" }
  };
  return map[intent] || map.trust;
}
`);

write("lib/prompt-v5/typography-engine.ts", `
export type TypographyMood = "luxury" | "modern" | "bold" | "editorial" | "friendly";

export function generateTypographySystem(mood: TypographyMood) {
  const map = {
    luxury: { headlineFont: "Playfair Display / Cormorant Garamond", bodyFont: "Inter", headlineStyle: "serif, elegant, refined", rule: "headline lớn, ít chữ, nhiều khoảng thở" },
    modern: { headlineFont: "Inter / Satoshi", bodyFont: "Inter", headlineStyle: "clean sans-serif, geometric", rule: "rõ ràng, dễ đọc, không trang trí thừa" },
    bold: { headlineFont: "Bebas Neue / Anton", bodyFont: "Inter", headlineStyle: "condensed, uppercase, high-impact", rule: "title cực mạnh, không quá 8 từ" },
    editorial: { headlineFont: "Serif Display", bodyFont: "Grotesk Sans", headlineStyle: "magazine-style, high-end", rule: "phân cấp title/sub rõ như tạp chí" },
    friendly: { headlineFont: "Nunito / Poppins", bodyFont: "Inter", headlineStyle: "rounded, approachable", rule: "thân thiện, dễ gần, không quá nghiêm" }
  };

  return {
    ...map[mood],
    maxFonts: 2,
    maxWords: 10,
    hierarchy: {
      headline: "largest, read in 1 second",
      subline: "secondary, support message",
      cta: "short, visible, action-driven"
    }
  };
}
`);

write("lib/prompt-v5/composition-engine.ts", `
export type CompositionLayout = "dominance" | "lookbook" | "realism" | "editorial_grid" | "event_cover";

export function generateComposition(layout: CompositionLayout) {
  const common = {
    focusRule: "one main focus only",
    depth: "foreground / midground / background",
    alignment: "rule of thirds or strong grid",
    whitespace: "at least 25-30% breathing space",
    mobileTest: "must remain readable at thumbnail size"
  };

  const map = {
    dominance: { ...common, hero: "product or subject occupies 70-80%", textZone: "small, clear, placed in negative space", bestFor: "product hero, FMCG, beauty, sales poster" },
    lookbook: { ...common, hero: "1 main large image", supporting: "5-7 smaller frames", textZone: "minimal serif typography", bestFor: "fashion collection, interior, editorial" },
    realism: { ...common, hero: "realistic model/product centered", supporting: "fabric/product detail crops", textZone: "premium minimal text", bestFor: "fashion, beauty, lifestyle" },
    editorial_grid: { ...common, hero: "headline + numbered structure", supporting: "grid blocks and examples", textZone: "clear hierarchy", bestFor: "education, framework, infographic poster" },
    event_cover: { ...common, hero: "event title + date/time", supporting: "speaker/logo/sponsor zone", textZone: "CTA and schedule area", bestFor: "event, workshop, launch" }
  };

  return map[layout];
}
`);

write("lib/prompt-v5/visual-scoring-engine.ts", `
export function scorePosterV5(input: {
  hasSingleFocus: boolean;
  textWordCount: number;
  contrastLevel: "low" | "medium" | "high";
  layout: string;
  hasCTA?: boolean;
  hasWhitespace?: boolean;
  typographyReadable?: boolean;
}) {
  let impact = 50, clarity = 50, trust = 50, conversion = 50;

  if (input.hasSingleFocus) { impact += 15; clarity += 15; }
  if (input.textWordCount <= 10) clarity += 20; else clarity -= 15;
  if (input.contrastLevel === "high") { impact += 20; clarity += 10; }
  if (input.hasWhitespace) { trust += 12; clarity += 10; }
  if (input.typographyReadable) clarity += 15;
  if (input.hasCTA) conversion += 20;
  if (input.layout === "dominance") { impact += 10; conversion += 10; }
  if (input.layout === "lookbook" || input.layout === "realism") trust += 15;

  return {
    impact: clamp(impact),
    clarity: clamp(clarity),
    trust: clamp(trust),
    conversion: clamp(conversion),
    total: clamp(Math.round((impact + clarity + trust + conversion) / 4))
  };
}

function clamp(n: number) {
  return Math.max(0, Math.min(100, n));
}
`);

write("lib/prompt-v5/poster-engine-v5.ts", `
import { generateColorSystem } from "./color-engine";
import { generateTypographySystem } from "./typography-engine";
import { generateComposition } from "./composition-engine";
import { scorePosterV5 } from "./visual-scoring-engine";

export type PosterV5Input = {
  text: string;
  productName?: string;
  industry?: string;
  goal?: "sale" | "brand" | "viral" | "education" | "event" | "lookbook";
  audience?: string;
  mood?: "luxury" | "modern" | "bold" | "editorial" | "friendly";
  hasPackaging?: boolean;
  hasCollection?: boolean;
  hasCTA?: boolean;
  headline?: string;
  subline1?: string;
  subline2?: string;
  cta?: string;
};

export function generatePosterV5(input: PosterV5Input) {
  const intent = detectIntent(input);
  const layout = decideLayoutV5(input);
  const color = generateColorSystem(intent.colorIntent);
  const typography = generateTypographySystem(intent.typeMood);
  const composition = generateComposition(layout);

  const strategy = \`Poster này phải khiến người xem \${intent.desiredAction} trong 3 giây.\`;

  const versions = [
    buildVersion("trust", input, color, typography, composition, layout),
    buildVersion("viral", input, color, typography, composition, layout),
    buildVersion("conversion", input, color, typography, composition, layout)
  ];

  return {
    strategy,
    intent,
    layout,
    color,
    typography,
    composition,
    versions,
    scoring: versions.map((v) => ({ version: v.version, scores: v.scores })),
    checklist: buildChecklist()
  };
}

function detectIntent(input: PosterV5Input) {
  const text = [input.text, input.industry, input.goal, input.audience].filter(Boolean).join(" ").toLowerCase();

  if (input.goal === "education" || /quy trình|framework|hướng dẫn|course|bài học/.test(text)) {
    return { colorIntent: "education" as const, typeMood: "bold" as const, desiredAction: "hiểu ý chính thật nhanh" };
  }
  if (input.goal === "event" || /event|sự kiện|workshop|hội thảo/.test(text)) {
    return { colorIntent: "event" as const, typeMood: "bold" as const, desiredAction: "chú ý tới sự kiện" };
  }
  if (/luxury|cao cấp|sang trọng|lookbook|fashion|sleepwear/.test(text)) {
    return { colorIntent: "luxury" as const, typeMood: "luxury" as const, desiredAction: "nhớ cảm giác thương hiệu" };
  }
  if (/skincare|beauty|spa|clinic|mỹ phẩm/.test(text)) {
    return { colorIntent: "beauty" as const, typeMood: "editorial" as const, desiredAction: "tin vào chất lượng sản phẩm" };
  }
  if (/saas|app|tech|ai|dashboard/.test(text)) {
    return { colorIntent: "tech" as const, typeMood: "modern" as const, desiredAction: "hiểu lợi ích sản phẩm" };
  }
  if (/năng lượng|viral|trẻ|bold|tết|vui/.test(text)) {
    return { colorIntent: "energy" as const, typeMood: "bold" as const, desiredAction: "dừng lại vì thị giác mạnh" };
  }
  return { colorIntent: "trust" as const, typeMood: "modern" as const, desiredAction: "hiểu thông điệp chính" };
}

function decideLayoutV5(input: PosterV5Input) {
  if (input.hasCollection || input.goal === "lookbook") return "lookbook" as const;
  if (input.goal === "education") return "editorial_grid" as const;
  if (input.goal === "event") return "event_cover" as const;
  if (input.hasPackaging || input.goal === "sale") return "dominance" as const;
  return "realism" as const;
}

function buildVersion(version: "trust" | "viral" | "conversion", input: PosterV5Input, color: any, typography: any, composition: any, layout: string) {
  const headline = input.headline || input.productName || "Poster Campaign";
  const subline1 = input.subline1 || "Thiết kế chuyên nghiệp";
  const subline2 = input.subline2 || "Ấn tượng, rõ thông điệp";
  const cta = input.cta || "Khám phá ngay";

  const versionInstruction = {
    trust: "Ưu tiên cảm giác đáng tin: bố cục sạch, ánh sáng thật, chi tiết rõ, không lòe loẹt.",
    viral: "Ưu tiên dừng lướt: tương phản mạnh, góc nhìn lạ, scale contrast, visual hook rõ.",
    conversion: "Ưu tiên hành động: sản phẩm/benefit rõ, CTA dễ thấy, text cực ngắn."
  }[version];

  const prompt = \`
Create a premium \${layout} poster for \${input.productName || input.text}.

=== STRATEGY ===
\${versionInstruction}

=== COMPOSITION ===
- Hero: \${composition.hero}
- Text zone: \${composition.textZone || "clear typography area"}
- Focus rule: \${composition.focusRule}
- Depth: \${composition.depth}
- Alignment: \${composition.alignment}
- Whitespace: \${composition.whitespace}

=== COLOR SYSTEM ===
- Scheme: \${color.scheme}
- Primary: \${color.primary}
- Accent: \${color.accent}
- Background: \${color.background}
- Text: \${color.text}
- Emotional tone: \${color.emotion}

=== TYPOGRAPHY ===
- Headline font style: \${typography.headlineFont}
- Body font style: \${typography.bodyFont}
- Rule: \${typography.rule}
- Max fonts: \${typography.maxFonts}
- Max words: \${typography.maxWords}
- Headline must be readable in 1 second

=== TEXT ===
“\${headline}”
“\${subline1}”
“\${subline2}”
CTA: “\${cta}”

=== EXECUTION ===
- Realistic lighting direction
- Strong but controlled contrast
- Premium poster composition
- No clutter
- No unreadable Vietnamese text
- No random colors outside palette
\`.trim();

  const scores = scorePosterV5({
    hasSingleFocus: true,
    textWordCount: countWords([headline, subline1, subline2, cta].join(" ")),
    contrastLevel: version === "viral" ? "high" : "medium",
    layout,
    hasCTA: version === "conversion" || Boolean(input.hasCTA),
    hasWhitespace: true,
    typographyReadable: true
  });

  return { version, prompt, scores };
}

function countWords(text: string) {
  return text.trim().split(/\\s+/).filter(Boolean).length;
}

function buildChecklist() {
  return [
    "Có 1 focus chính",
    "Headline đọc được trong 1 giây",
    "Không quá 2 font",
    "Không nhồi chữ",
    "Có khoảng trống",
    "Có phân cấp headline / subline / CTA",
    "Màu bám đúng cảm xúc thương hiệu",
    "Bố cục có hero / supporting / text zone",
    "Thu nhỏ vẫn nhìn ra chủ thể",
    "Không có chi tiết thừa làm loãng thông điệp"
  ];
}
`);

write("lib/prompt-v5/template-pack-v5.ts", `
import { generatePosterV5, PosterV5Input } from "./poster-engine-v5";

export function buildTemplatePackV5(input: PosterV5Input) {
  const generated = generatePosterV5(input);
  const slug = slugify(input.productName || input.industry || "poster-template");

  return {
    slug,
    files: {
      "DESIGN.md": buildDesignMd(input, generated),
      "config.json": JSON.stringify(buildConfig(input, generated), null, 2),
      "prompts.json": JSON.stringify(Object.fromEntries(generated.versions.map((v) => [v.version, v.prompt])), null, 2),
      "checklist.md": generated.checklist.map((x) => \`- [ ] \${x}\`).join("\\n"),
      "usage.md": buildUsage(input, generated)
    },
    generated
  };
}

function buildDesignMd(input: PosterV5Input, generated: any) {
  return \`---
version: 1.0
name: "\${input.productName || "Poster Template V5"}"
description: "Auto-generated DESIGN.md poster template"

colors:
  primary: "\${generated.color.primary}"
  accent: "\${generated.color.accent}"
  background: "\${generated.color.background}"
  surface: "#FFFFFF"
  text: "\${generated.color.text}"

typography:
  headline:
    fontFamily: "\${generated.typography.headlineFont}"
    style: "\${generated.typography.headlineStyle}"
  body:
    fontFamily: "\${generated.typography.bodyFont}"

layout:
  default: "\${generated.layout}"
  focusRule: "\${generated.composition.focusRule}"
  whitespace: "\${generated.composition.whitespace}"
  alignment: "\${generated.composition.alignment}"

visual:
  colorEmotion: "\${generated.color.emotion}"
  strategy: "\${generated.strategy}"

rules:
  do:
    - "Use one main focus"
    - "Keep typography readable"
    - "Use strong hierarchy"
    - "Maintain whitespace"
  dont:
    - "Do not clutter"
    - "Do not use more than 2 fonts"
    - "Do not add random colors"
    - "Do not make Vietnamese text unreadable"
---
# \${input.productName || "Poster Template V5"}

\${generated.strategy}
\`;
}

function buildConfig(input: PosterV5Input, generated: any) {
  return {
    id: slugify(input.productName || "poster-template"),
    layout: generated.layout,
    color: generated.color,
    typography: generated.typography,
    versions: generated.scoring
  };
}

function buildUsage(input: PosterV5Input, generated: any) {
  return \`# Usage

Best for:
- \${input.industry || "multi-industry poster"}
- Goal: \${input.goal || "brand"}

Main strategy:
\${generated.strategy}

Use versions:
- Trust: premium / brand / clarity
- Viral: attention / scroll-stop
- Conversion: CTA / sales / action
\`;
}

function slugify(text: string) {
  return text.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}
`);

write("app/api/poster/v5/route.ts", `
import { NextResponse } from "next/server";
import { generatePosterV5 } from "@/lib/prompt-v5/poster-engine-v5";

export async function POST(req: Request) {
  const input = await req.json();
  return NextResponse.json(generatePosterV5(input));
}
`);

write("app/api/template-pack/v5/route.ts", `
import { NextResponse } from "next/server";
import { buildTemplatePackV5 } from "@/lib/prompt-v5/template-pack-v5";

export async function POST(req: Request) {
  const input = await req.json();
  return NextResponse.json(buildTemplatePackV5(input));
}
`);

write("app/api/image/generate-poster/route.ts", `
import OpenAI from "openai";
import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: Request) {
  const { prompt, size = "1024x1536" } = await req.json();

  if (!prompt) return NextResponse.json({ error: "Missing prompt" }, { status: 400 });
  if (!process.env.OPENAI_API_KEY) return NextResponse.json({ error: "Missing OPENAI_API_KEY" }, { status: 400 });

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  const result = await openai.images.generate({
    model: "gpt-image-1",
    prompt,
    size,
    quality: "high",
    output_format: "png"
  });

  const b64 = result.data?.[0]?.b64_json;
  if (!b64) return NextResponse.json({ error: "No image returned" }, { status: 500 });

  const dir = path.join(process.cwd(), "public", "generated");
  fs.mkdirSync(dir, { recursive: true });

  const filename = \`\${Date.now()}-poster.png\`;
  fs.writeFileSync(path.join(dir, filename), Buffer.from(b64, "base64"));

  return NextResponse.json({ url: \`/generated/\${filename}\` });
}
`);

write("app/studio/page.tsx", `
"use client";

import { useState } from "react";

export default function StudioPage() {
  const [input, setInput] = useState({
    text: "Quy trình thiết kế poster quảng cáo ấn tượng thị giác mạnh, đen vàng, infographic, 11 bước",
    productName: "Poster Blueprint System",
    industry: "Education",
    goal: "education",
    audience: "marketer, designer, freelancer",
    mood: "bold",
    hasCTA: true,
    headline: "Quy trình thiết kế poster quảng cáo",
    subline1: "Ấn tượng thị giác mạnh",
    subline2: "11 bước từ ý tưởng đến xuất file",
    cta: "Tải template"
  });

  const [result, setResult] = useState<any>(null);
  const [imageUrl, setImageUrl] = useState("");

  async function generate() {
    const res = await fetch("/api/poster/v5", { method: "POST", body: JSON.stringify(input) });
    setResult(await res.json());
  }

  async function renderImage(prompt: string) {
    const res = await fetch("/api/image/generate-poster", {
      method: "POST",
      body: JSON.stringify({ prompt })
    });
    const data = await res.json();
    setImageUrl(data.url);
  }

  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>Poster Studio V5</h1>
      <p style={{ color: "#CBD5E1" }}>AI Agency tự quyết định visual, layout, màu, typography và scoring.</p>

      <section className="card" style={{ marginTop: 24 }}>
        <textarea className="input" style={{ minHeight: 120 }} value={input.text} onChange={(e) => setInput({ ...input, text: e.target.value })} />
        <button className="btn" style={{ marginTop: 16 }} onClick={generate}>Generate V5</button>
      </section>

      {result && (
        <section style={{ marginTop: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div className="card">
            <h2>Decision</h2>
            <pre style={{ whiteSpace: "pre-wrap", color: "#CBD5E1" }}>
              {JSON.stringify({
                strategy: result.strategy,
                intent: result.intent,
                layout: result.layout,
                color: result.color,
                typography: result.typography,
                composition: result.composition,
                scoring: result.scoring
              }, null, 2)}
            </pre>
          </div>

          <div className="card">
            <h2>Versions</h2>
            {result.versions.map((v: any) => (
              <div key={v.version} style={{ marginBottom: 24 }}>
                <h3>{v.version.toUpperCase()} — Score {v.scores.total}</h3>
                <button className="btn" onClick={() => renderImage(v.prompt)}>Render preview</button>
                <pre style={{ whiteSpace: "pre-wrap", color: "#CBD5E1", fontSize: 12 }}>{v.prompt}</pre>
              </div>
            ))}
          </div>
        </section>
      )}

      {imageUrl && (
        <section className="card" style={{ marginTop: 24 }}>
          <h2>Generated Preview</h2>
          <img src={imageUrl} style={{ width: 360, borderRadius: 20 }} />
        </section>
      )}
    </main>
  );
}
`);

write("lib/editor/editor-store.ts", `
import { create } from "zustand";

export type PosterElement = {
  id: string;
  type: "text" | "image" | "shape" | "badge";
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  content?: string;
  src?: string;
  style?: Record<string, any>;
};

export type PosterDocument = {
  id: string;
  name: string;
  width: number;
  height: number;
  layout: string;
  elements: PosterElement[];
};

type EditorState = {
  doc: PosterDocument;
  selectedId?: string;
  select: (id?: string) => void;
  updateElement: (id: string, patch: Partial<PosterElement>) => void;
};

export const useEditorStore = create<EditorState>((set) => ({
  doc: {
    id: "poster-1",
    name: "Untitled Poster",
    width: 900,
    height: 1200,
    layout: "dominance",
    elements: [
      { id: "hero", type: "image", x: 60, y: 80, w: 520, h: 780, z: 1, style: { background: "linear-gradient(135deg,#2563EB,#FACC15)" } },
      { id: "title", type: "text", x: 600, y: 120, w: 250, h: 120, z: 2, content: "Poster Studio", style: { fontSize: 42, fontWeight: 800, color: "#111827" } },
      { id: "cta", type: "badge", x: 600, y: 960, w: 220, h: 64, z: 3, content: "Khám phá ngay", style: { background: "#FACC15", color: "#111827" } }
    ]
  },
  select: (id) => set({ selectedId: id }),
  updateElement: (id, patch) => set((s) => ({
    doc: { ...s.doc, elements: s.doc.elements.map((el) => el.id === id ? { ...el, ...patch } : el) }
  }))
}));
`);

write("components/editor/PosterCanvas.tsx", `
"use client";

import { Rnd } from "react-rnd";
import { useEditorStore } from "@/lib/editor/editor-store";

export function PosterCanvas() {
  const { doc, selectedId, select, updateElement } = useEditorStore();

  return (
    <div
      style={{
        width: doc.width,
        height: doc.height,
        background: "#F8F5F2",
        position: "relative",
        overflow: "hidden",
        borderRadius: 24,
        boxShadow: "0 40px 120px rgba(0,0,0,.35)"
      }}
      onMouseDown={() => select(undefined)}
    >
      {doc.elements.sort((a, b) => a.z - b.z).map((el) => (
        <Rnd
          key={el.id}
          size={{ width: el.w, height: el.h }}
          position={{ x: el.x, y: el.y }}
          bounds="parent"
          onMouseDown={(e) => { e.stopPropagation(); select(el.id); }}
          onDragStop={(_, d) => updateElement(el.id, { x: d.x, y: d.y })}
          onResizeStop={(_, __, ref, ___, pos) =>
            updateElement(el.id, {
              w: Number(ref.style.width.replace("px", "")),
              h: Number(ref.style.height.replace("px", "")),
              x: pos.x,
              y: pos.y
            })
          }
          style={{ border: selectedId === el.id ? "2px solid #2563EB" : "1px solid transparent", zIndex: el.z }}
        >
          {el.type === "text" && <div style={{ ...el.style, width: "100%", height: "100%" }}>{el.content}</div>}
          {el.type === "badge" && <div style={{ ...el.style, width: "100%", height: "100%", borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900 }}>{el.content}</div>}
          {el.type === "image" && <div style={{ ...el.style, width: "100%", height: "100%", borderRadius: 24, backgroundSize: "cover", backgroundPosition: "center", backgroundImage: el.src ? \`url(\${el.src})\` : el.style?.background }} />}
        </Rnd>
      ))}
    </div>
  );
}
`);

write("app/editor/page.tsx", `
import { PosterCanvas } from "@/components/editor/PosterCanvas";

export default function EditorPage() {
  return (
    <main style={{ minHeight: "100vh", background: "#0A0F2C", color: "white", padding: 32 }}>
      <h1>Canva-like Poster Editor</h1>
      <p style={{ color: "#CBD5E1" }}>Drag/drop MVP editor. P1: thêm export PNG và layer panel.</p>
      <div style={{ marginTop: 24, display: "flex", justifyContent: "center" }}>
        <PosterCanvas />
      </div>
    </main>
  );
}
`);

write("lib/marketplace/packs.ts", `
export const templatePacks = [
  { slug: "impact-yellow-black", name: "Impact Yellow Black Blueprint", price: 19, category: "Education", description: "Poster quy trình / infographic mạnh thị giác.", tags: ["education", "black-yellow", "grid"] },
  { slug: "fashion-realism-luxury", name: "Fashion Realism Luxury", price: 29, category: "Fashion", description: "Poster thời trang chân thật cao cấp.", tags: ["fashion", "realism", "luxury"] },
  { slug: "lookbook-collage-premium", name: "Lookbook Collage Premium", price: 29, category: "Fashion", description: "Collage lookbook 1 ảnh lớn + 5–7 frame.", tags: ["lookbook", "editorial"] },
  { slug: "product-dominance-studio", name: "Product Dominance Studio", price: 19, category: "Product", description: "Sản phẩm lớn tiền cảnh, góc máy phóng đại.", tags: ["dominance", "fmcg"] },
  { slug: "beauty-clean-minimal", name: "Beauty Clean Minimal", price: 19, category: "Beauty", description: "Poster mỹ phẩm sạch, high-key, trust.", tags: ["beauty", "clean"] },
  { slug: "event-fomo-neon", name: "Event FOMO Neon", price: 15, category: "Event", description: "Poster sự kiện năng lượng, countdown.", tags: ["event", "fomo"] },
  { slug: "saas-clean-ui", name: "SaaS Clean UI", price: 19, category: "SaaS", description: "Poster SaaS sạch, dashboard-first.", tags: ["saas", "tech"] },
  { slug: "real-estate-luxury", name: "Real Estate Luxury", price: 29, category: "Real Estate", description: "Poster bất động sản cao cấp.", tags: ["realestate", "luxury"] },
  { slug: "fitness-transformation", name: "Fitness Transformation", price: 15, category: "Fitness", description: "Poster thể hình before/after.", tags: ["fitness", "transformation"] },
  { slug: "corporate-trust-system", name: "Corporate Trust System", price: 15, category: "Corporate", description: "Poster doanh nghiệp chuyên nghiệp.", tags: ["corporate", "trust"] }
];
`);

write("app/marketplace/page.tsx", `
import { templatePacks } from "@/lib/marketplace/packs";

export default function MarketplacePage() {
  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 52, fontWeight: 950 }}>DESIGN.md Template Marketplace</h1>
      <p style={{ color: "#CBD5E1" }}>Bán preset không chỉ là prompt — là hệ thống poster có màu, font, layout và logic.</p>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20, marginTop: 32 }}>
        {templatePacks.map((p) => (
          <div key={p.slug} className="card">
            <div style={{ aspectRatio: "4/5", borderRadius: 20, background: p.slug === "impact-yellow-black" ? "linear-gradient(135deg,#050505,#FACC15)" : "linear-gradient(135deg,#2563EB,#FACC15)" }} />
            <h2>{p.name}</h2>
            <p style={{ color: "#CBD5E1" }}>{p.description}</p>
            <div style={{ color: "#FACC15", fontWeight: 900 }}>${p.price}</div>
            <button className="btn" style={{ marginTop: 12 }}>Use Template</button>
          </div>
        ))}
      </section>
    </main>
  );
}
`);

write("DESIGN.md", `
---
version: 1.0
name: "AI Poster Studio Pro"
description: "AI Agency Visual Engine for premium posters"

colors:
  primary: "#0A0F2C"
  accent: "#2563EB"
  highlight: "#FACC15"
  background: "#0A0F2C"
  surface: "#111827"
  text: "#FFFFFF"

typography:
  headline:
    fontFamily: "Inter"
    fontSize: 48px
    fontWeight: 900
  body:
    fontFamily: "Inter"
    fontSize: 16px
    fontWeight: 400

layout:
  focusRule: "one main focus"
  whitespace: "25-30%"
  alignment: "rule of thirds or grid"
---
# AI Poster Studio Pro DESIGN.md

Conversion hỗ trợ bởi clarity, hierarchy, contrast và realism.
`);

write("README.md", `
# AI Poster Studio Pro

## Quick start

\`\`\`bash
cp .env.example .env.local
npm install
npm run dev
\`\`\`

Open:

- /
- /studio
- /editor
- /marketplace

## Core

- Prompt Engine V5
- Color Engine
- Typography Engine
- Composition Engine
- Visual Scoring
- Image Preview API
- Canva-like Drag/Drop Editor
- DESIGN.md Template Marketplace
`);

write("docs/01-setup.md", `
# Setup

\`\`\`bash
cp .env.example .env.local
npm install
npm run dev
\`\`\`
`);

write("docs/02-architecture.md", `
# Architecture

Core flow:

User input
→ Poster Engine V5
→ Color Engine
→ Typography Engine
→ Composition Engine
→ Scoring
→ Prompt versions
→ Render preview
→ Editor
→ Template marketplace
`);

write("docs/03-prompt-engine-v5.md", `
# Prompt Engine V5

Files:

- lib/prompt-v5/color-engine.ts
- lib/prompt-v5/typography-engine.ts
- lib/prompt-v5/composition-engine.ts
- lib/prompt-v5/visual-scoring-engine.ts
- lib/prompt-v5/poster-engine-v5.ts
`);

write("docs/04-design-md.md", `
# DESIGN.md

DESIGN.md là nguồn sự thật thiết kế:

- colors
- typography
- layout
- rules
`);

write("docs/05-editor.md", `
# Editor

MVP editor dùng:

- zustand
- react-rnd

P1:
- layer panel
- export PNG
- text edit
- upload image
`);

write("docs/06-marketplace.md", `
# Marketplace

Marketplace bán DESIGN.md template pack.

P1:
- Stripe checkout
- unlock download
- pack detail page
`);

write("docs/07-image-render.md", `
# Image Render

API:

POST /api/image/generate-poster

Env:

OPENAI_API_KEY=
`);

write("docs/08-dev-patch-checklist.md", `
# Dev Patch Checklist

## P0
- npm install
- npm run dev
- test /studio
- test /editor
- test /marketplace

## P1
- Add Stripe checkout
- Add export PNG
- Add pack detail page
- Add DESIGN.md parser

## P2
- Add auth
- Add project save
- Add template download
- Add admin marketplace
`);

try {
  execSync(\`zip -r \${root}.zip \${root}\`, { stdio: "inherit" });
  console.log("✅ Created:", root);
  console.log("✅ Created zip:", root + ".zip");
} catch {
  console.log("✅ Created:", root);
  console.log("⚠️ zip command not found. Run manually:");
  console.log(\`zip -r \${root}.zip \${root}\`);
}
