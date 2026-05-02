import fs from "fs";
import path from "path";
import { execSync } from "child_process";

const root = "ai-ads-factory-saas";

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
  "name": "ai-ads-factory-saas",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "remotion:preview": "remotion preview remotion/index.ts",
    "remotion:render": "remotion render remotion/index.ts AdVideo public/renders/demo.mp4"
  },
  "dependencies": {
    "@remotion/bundler": "latest",
    "@remotion/cli": "latest",
    "@remotion/renderer": "latest",
    "@supabase/ssr": "latest",
    "@supabase/supabase-js": "latest",
    "framer-motion": "latest",
    "js-yaml": "latest",
    "next": "latest",
    "openai": "latest",
    "react": "latest",
    "react-dom": "latest",
    "remotion": "latest",
    "stripe": "latest",
    "zod": "latest"
  },
  "devDependencies": {
    "@types/js-yaml": "latest",
    "@types/node": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "typescript": "latest"
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
NEXT_PUBLIC_APP_URL=http://localhost:3000
OPENAI_API_KEY=

NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_CREATOR=
STRIPE_PRICE_PRO=
STRIPE_PRICE_STUDIO=
`);

write("app/layout.tsx", `
import "./globals.css";

export const metadata = {
  title: "AI Ads Factory SaaS",
  description: "AI Creative Revenue Operating System"
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
input, textarea, button { font-family: inherit; }
a { color: inherit; text-decoration: none; }
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
`);

write("app/page.tsx", `
import Link from "next/link";

const plans = [
  ["Creator", "199K/tháng", "200 credits, Prompt V3, HD export"],
  ["Pro", "499K/tháng", "1.000 credits, Auto video render, No watermark"],
  ["Studio", "1.500K/tháng", "5.000 credits, Batch render, Team workspace"]
];

export default function Home() {
  return (
    <main style={{ minHeight: "100vh", background: "#0A0F2C", color: "white" }}>
      <section style={{ padding: "96px 24px", textAlign: "center" }}>
        <p style={{ color: "#FACC15", fontWeight: 800 }}>AI Ads Factory</p>
        <h1 style={{ maxWidth: 980, margin: "16px auto", fontSize: 64, lineHeight: 1.05, fontWeight: 950 }}>
          Tạo ads bán hàng + video TikTok trong <span style={{ color: "#FACC15" }}>60 giây</span>
        </h1>
        <p style={{ maxWidth: 720, margin: "24px auto", fontSize: 20, color: "#CBD5E1" }}>
          Từ 1 ý tưởng, AI tạo hook, visual, CTA, prompt, video và funnel để kéo lead.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 32 }}>
          <Link className="btn" href="/revenue-factory">Dùng thử miễn phí</Link>
          <Link className="btn" style={{ background: "rgba(255,255,255,.1)" }} href="/factory">Mở Orchestrator</Link>
        </div>
      </section>

      <section style={{ padding: 24, maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
        {["Nhập sản phẩm", "AI tạo Top 3 Ads", "Render video 9:16"].map((t, i) => (
          <div className="card" key={t}>
            <div style={{ fontSize: 44, color: "#FACC15", fontWeight: 900 }}>{i + 1}</div>
            <h3>{t}</h3>
            <p style={{ color: "#CBD5E1" }}>Tối ưu cho TikTok, Facebook và landing page.</p>
          </div>
        ))}
      </section>

      <section id="pricing" style={{ padding: "80px 24px", maxWidth: 1120, margin: "0 auto" }}>
        <h2 style={{ textAlign: "center", fontSize: 44 }}>Pricing</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20, marginTop: 32 }}>
          {plans.map(([name, price, desc]) => (
            <div className="card" key={name}>
              <h3 style={{ fontSize: 28 }}>{name}</h3>
              <h2>{price}</h2>
              <p style={{ color: "#CBD5E1" }}>{desc}</p>
              <button className="btn" style={{ width: "100%", marginTop: 16, background: "#FACC15", color: "#111827" }}>
                Bắt đầu
              </button>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
`);

write("lib/prompt/prompt-engine-v3.ts", `
export type Goal = "CTR" | "Lead" | "Sale";
export type Platform = "TikTok" | "Facebook" | "Landing";
export type Mode = "Money" | "Viral" | "Premium";

export type DesignLock = {
  colors: {
    primary: string;
    accent: string;
    highlight?: string;
    background: string;
    surface: string;
    text: string;
  };
};

export type PromptV3Input = {
  product: string;
  industry: string;
  audience: string;
  offer?: string;
  goal: Goal;
  platform: Platform;
  mode: Mode;
};

export type AdOutputV3 = {
  id: string;
  score: number;
  concept: string;
  angle: string;
  hook: string;
  headline: string;
  cta: string;
  layout: {
    type: "left-text-right-visual" | "split-before-after" | "center-focus";
    textPosition: "left" | "top" | "center";
    ctaPosition: "bottom" | "bottom-right" | "center";
    visualFocus: "product" | "person" | "ui" | "result";
  };
  visual: {
    scene: string;
    lighting: string;
    colorMood: string;
    motionHint: string;
  };
  prompt2D: string;
  promptVideo: string;
  whyItConverts: string;
};

const hookBank = {
  pain: [
    "Bạn đang đốt tiền ads mà không có khách?",
    "Bạn đang mất khách vì visual quá yếu?",
    "Ads đẹp nhưng không ai click?"
  ],
  curiosity: [
    "Xem cái này trước khi bạn chạy ads",
    "Không ai nói với bạn điều này",
    "Một thay đổi nhỏ làm khách hiểu nhanh hơn"
  ],
  result: [
    "Tăng CTR chỉ với 1 thay đổi",
    "Tạo ads bán hàng trong 60 giây",
    "1 visual giúp khách hiểu sản phẩm nhanh hơn"
  ],
  fomo: [
    "Đối thủ bạn đang dùng kiểu ads này",
    "Bạn có đang bỏ lỡ khách mỗi ngày?",
    "Đừng để ads của bạn tụt lại"
  ]
};

const layouts: AdOutputV3["layout"][] = [
  { type: "left-text-right-visual", textPosition: "left", ctaPosition: "bottom-right", visualFocus: "product" },
  { type: "split-before-after", textPosition: "top", ctaPosition: "bottom", visualFocus: "result" },
  { type: "center-focus", textPosition: "center", ctaPosition: "bottom", visualFocus: "person" }
];

export function generatePromptV3(input: PromptV3Input, design: DesignLock) {
  const angles = selectAngles(input);
  const hooks = angles.flatMap((a) => hookBank[a as keyof typeof hookBank]);

  return hooks.flatMap((hook, hookIndex) =>
    layouts.map((layout, layoutIndex) => {
      const headline = makeHeadline(input);
      const cta = makeCTA(input.goal);
      const visual = makeVisual(input, layout);
      const score = scoreAd(input, hook, layout);

      return {
        id: \`\${input.platform}-\${input.goal}-\${hookIndex}-\${layoutIndex}\`,
        score,
        concept: makeConcept(layout),
        angle: getAngleFromHook(hook),
        hook,
        headline,
        cta,
        layout,
        visual,
        prompt2D: build2DPrompt(input, design, hook, headline, cta, layout, visual),
        promptVideo: buildVideoPrompt(input, design, hook, headline, cta, layout, visual),
        whyItConverts: \`Hook tạo \${getAngleFromHook(hook)}, layout \${layout.type}, CTA bám mục tiêu \${input.goal}.\`
      };
    })
  ).sort((a, b) => b.score - a.score);
}

function selectAngles(input: PromptV3Input) {
  if (input.mode === "Money") return ["pain", "result", "fomo"];
  if (input.mode === "Viral") return ["curiosity", "fomo", "pain"];
  return ["result", "curiosity"];
}

function makeHeadline(input: PromptV3Input) {
  if (input.goal === "Lead") return \`Nhận demo cho \${input.product}\`;
  if (input.goal === "Sale") return \`Ưu đãi cho \${input.product}\`;
  return \`\${input.product} trong 60 giây\`;
}

function makeCTA(goal: Goal) {
  if (goal === "Lead") return "Nhận demo miễn phí";
  if (goal === "Sale") return "Mua ngay";
  return "Xem video ngay";
}

function makeConcept(layout: AdOutputV3["layout"]) {
  if (layout.type === "split-before-after") return "Before/After transformation";
  if (layout.type === "left-text-right-visual") return "Direct response ad layout";
  return "Hero focus conversion layout";
}

function makeVisual(input: PromptV3Input, layout: AdOutputV3["layout"]) {
  return {
    scene: layout.type === "split-before-after" ? "before state versus after result" : \`\${input.product} commercial showcase\`,
    lighting: input.mode === "Premium" ? "soft premium studio lighting" : "high contrast cinematic lighting",
    colorMood: input.mode === "Viral" ? "bold energetic scroll-stopping" : "clean high contrast conversion-focused",
    motionHint: input.platform === "TikTok" ? "fast cut, motion blur, beat synced" : "static clear composition"
  };
}

function build2DPrompt(input: PromptV3Input, design: DesignLock, hook: string, headline: string, cta: string, layout: AdOutputV3["layout"], visual: AdOutputV3["visual"]) {
  return \`
High-converting advertising creative for \${input.product}.
Industry: \${input.industry}.
Audience: \${input.audience}.
Goal: \${input.goal}.
Platform: \${input.platform}.
Mode: \${input.mode}.
Offer: \${input.offer || "clear commercial offer"}.

Hook: "\${hook}"
Headline: "\${headline}"
CTA: "\${cta}"

Layout: \${layout.type}
Text position: \${layout.textPosition}
CTA position: \${layout.ctaPosition}
Visual focus: \${layout.visualFocus}

Visual scene: \${visual.scene}
Lighting: \${visual.lighting}
Color mood: \${visual.colorMood}

Brand lock:
Primary: \${design.colors.primary}
Accent: \${design.colors.accent}
Highlight: \${design.colors.highlight || design.colors.accent}
Background: \${design.colors.background}
Text: \${design.colors.text}

Rules:
One message only, maximum 3 lines of text, visible CTA, high contrast, do not break brand.
\`.trim();
}

function buildVideoPrompt(input: PromptV3Input, design: DesignLock, hook: string, headline: string, cta: string, layout: AdOutputV3["layout"], visual: AdOutputV3["visual"]) {
  return \`
Create a 9:16 short video ad for \${input.product}.
0-2s: Hook — "\${hook}"
2-4s: Show problem / before state
4-5s: Smooth transition with \${visual.motionHint}
5-8s: Show after/result
8-12s: CTA — "\${cta}"

Brand colors: \${design.colors.primary}, \${design.colors.accent}, \${design.colors.highlight || design.colors.accent}
Layout: \${layout.type}
Text readable on mobile, fast pacing, clear transformation.
\`.trim();
}

function scoreAd(input: PromptV3Input, hook: string, layout: AdOutputV3["layout"]) {
  let score = 70;
  if (input.goal === "Lead" && hook.includes("đốt tiền")) score += 15;
  if (input.platform === "TikTok" && layout.type === "split-before-after") score += 15;
  if (input.mode === "Money") score += 10;
  if (layout.visualFocus === "result") score += 8;
  return score;
}

function getAngleFromHook(hook: string) {
  if (hook.includes("đốt tiền") || hook.includes("mất khách")) return "pain";
  if (hook.includes("Không ai") || hook.includes("Xem cái này")) return "curiosity";
  if (hook.includes("Tăng") || hook.includes("60 giây")) return "result";
  return "fomo";
}
`);

write("app/api/prompt/v3/route.ts", `
import { NextResponse } from "next/server";
import { generatePromptV3 } from "@/lib/prompt/prompt-engine-v3";

export async function POST(req: Request) {
  const { input, design } = await req.json();
  const variants = generatePromptV3(input, design);
  return NextResponse.json({ top3: variants.slice(0, 3), all: variants });
}
`);

write("remotion/AdVideo.tsx", `
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export type AdVideoProps = {
  hook: string;
  headline: string;
  cta: string;
  primary: string;
  accent: string;
  highlight: string;
};

export function AdVideo(props: AdVideoProps) {
  const frame = useCurrentFrame();
  const isAfter = frame > 150;
  const blur = frame > 120 && frame < 165 ? "blur(16px)" : "none";
  const scale = interpolate(frame, [0, 150, 360], [1, 1.05, 1]);

  return (
    <AbsoluteFill style={{ background: props.primary, color: "white", padding: 70 }}>
      <h1 style={{ fontSize: 74, fontWeight: 900, lineHeight: 1.05 }}>
        {isAfter ? props.headline : props.hook}
      </h1>

      <div
        style={{
          marginTop: 80,
          height: 1120,
          borderRadius: 42,
          transform: \`scale(\${scale})\`,
          filter: blur,
          background: isAfter
            ? \`linear-gradient(135deg, \${props.accent}, \${props.highlight})\`
            : "linear-gradient(135deg,#64748B,#1E293B)",
          boxShadow: \`0 40px 120px \${props.accent}66\`
        }}
      />

      <div style={{
        position: "absolute",
        bottom: 90,
        left: 70,
        right: 70,
        background: props.accent,
        borderRadius: 24,
        padding: 32,
        textAlign: "center",
        fontSize: 42,
        fontWeight: 900
      }}>
        {props.cta}
      </div>
    </AbsoluteFill>
  );
}
`);

write("remotion/Root.tsx", `
import { Composition } from "remotion";
import { AdVideo } from "./AdVideo";

export function RemotionRoot() {
  return (
    <Composition
      id="AdVideo"
      component={AdVideo}
      durationInFrames={360}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        hook: "Bạn đang đốt tiền ads?",
        headline: "Tạo ads trong 60 giây",
        cta: "Nhận demo miễn phí",
        primary: "#0A0F2C",
        accent: "#2563EB",
        highlight: "#FACC15"
      }}
    />
  );
}
`);

write("remotion/index.ts", `
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";
registerRoot(RemotionRoot);
`);

write("lib/render/remotion-render.ts", `
import fs from "fs";
import path from "path";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

export async function renderAdVideo(inputProps: any) {
  const renderDir = path.join(process.cwd(), "public", "renders");
  fs.mkdirSync(renderDir, { recursive: true });

  const entry = path.join(process.cwd(), "remotion", "index.ts");
  const serveUrl = await bundle(entry);

  const composition = await selectComposition({
    serveUrl,
    id: "AdVideo",
    inputProps
  });

  const filename = \`\${Date.now()}-ad.mp4\`;
  const outputLocation = path.join(renderDir, filename);

  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    outputLocation,
    inputProps
  });

  return \`/renders/\${filename}\`;
}
`);

write("app/api/render/ad-video/route.ts", `
import { NextResponse } from "next/server";
import { renderAdVideo } from "@/lib/render/remotion-render";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: Request) {
  const { ad, design } = await req.json();

  const url = await renderAdVideo({
    hook: ad.hook,
    headline: ad.headline,
    cta: ad.cta,
    primary: design.colors.primary,
    accent: design.colors.accent,
    highlight: design.colors.highlight || design.colors.accent
  });

  return NextResponse.json({ url });
}
`);

write("components/RevenueFactoryV3.tsx", `
"use client";

import { useState } from "react";

const design = {
  colors: {
    primary: "#0A0F2C",
    accent: "#2563EB",
    highlight: "#FACC15",
    background: "#0A0F2C",
    surface: "#111827",
    text: "#FFFFFF"
  }
};

export function RevenueFactoryV3() {
  const [product, setProduct] = useState("AI Design Tool");
  const [industry, setIndustry] = useState("SaaS");
  const [audience, setAudience] = useState("seller, marketer, creator");
  const [ads, setAds] = useState<any[]>([]);
  const [videoUrl, setVideoUrl] = useState("");
  const [loading, setLoading] = useState(false);

  async function generate() {
    setLoading(true);
    const res = await fetch("/api/prompt/v3", {
      method: "POST",
      body: JSON.stringify({
        design,
        input: {
          product,
          industry,
          audience,
          offer: "demo miễn phí",
          goal: "Lead",
          platform: "TikTok",
          mode: "Money"
        }
      })
    });
    const data = await res.json();
    setAds(data.top3 || []);
    setLoading(false);
  }

  async function renderVideo(ad: any) {
    setLoading(true);
    const res = await fetch("/api/render/ad-video", {
      method: "POST",
      body: JSON.stringify({ ad, design })
    });
    const data = await res.json();
    setVideoUrl(data.url);
    setLoading(false);
  }

  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>Revenue Factory V3</h1>
      <p style={{ color: "#CBD5E1" }}>1 input → 3 ads có score → preview → render video 9:16</p>

      <section className="card" style={{ marginTop: 24 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
          <input value={product} onChange={(e) => setProduct(e.target.value)} />
          <input value={industry} onChange={(e) => setIndustry(e.target.value)} />
          <input value={audience} onChange={(e) => setAudience(e.target.value)} />
        </div>
        <button className="btn" style={{ marginTop: 16 }} onClick={generate}>
          {loading ? "Đang xử lý..." : "Generate Top 3 Ads"}
        </button>
      </section>

      <section style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
        {ads.map((ad) => (
          <div className="card" key={ad.id}>
            <div style={{ color: "#FACC15" }}>Score {ad.score}</div>
            <h2>{ad.hook}</h2>
            <p style={{ color: "#CBD5E1" }}>{ad.headline}</p>

            <div style={{
              aspectRatio: "9/16",
              borderRadius: 24,
              background: "linear-gradient(135deg,#2563EB,#FACC15)",
              padding: 24,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between"
            }}>
              <h3 style={{ fontSize: 28 }}>{ad.headline}</h3>
              <button className="btn" style={{ background: "white", color: "#111827" }}>{ad.cta}</button>
            </div>

            <p style={{ color: "#CBD5E1", fontSize: 14 }}>{ad.whyItConverts}</p>
            <button className="btn" style={{ width: "100%" }} onClick={() => renderVideo(ad)}>Render video</button>
          </div>
        ))}
      </section>

      {videoUrl && (
        <section className="card" style={{ marginTop: 32 }}>
          <h2>Rendered Video</h2>
          <video src={videoUrl} controls style={{ width: 320, borderRadius: 20 }} />
        </section>
      )}
    </main>
  );
}
`);

write("app/revenue-factory/page.tsx", `
import { RevenueFactoryV3 } from "@/components/RevenueFactoryV3";
export default function Page() {
  return <RevenueFactoryV3 />;
}
`);

write("lib/agents/prompts.ts", `
export const agents = [
  { name: "Insight Agent", prompt: "Phân tích insight khách hàng: pain, desire, objection, góc bán hàng mạnh nhất." },
  { name: "Offer Agent", prompt: "Tạo offer chính, lý do mua, điểm khác biệt, bonus, CTA." },
  { name: "Creative Director Agent", prompt: "Tạo 3 concept ads: big idea, visual direction, hook, CTA, lý do chuyển đổi." },
  { name: "DESIGN.md Agent", prompt: "Tạo DESIGN.md gồm colors, typography, layout, components, do/don't, CTA style." },
  { name: "Image Ads Agent", prompt: "Tạo prompt hero banner, ads 1:1, ads 4:5, thumbnail, text overlay." },
  { name: "Video Avatar Agent", prompt: "Tạo script video 6-8s, 15s, storyboard, voice-over, subtitle, CTA." },
  { name: "Funnel Agent", prompt: "Tạo hero section, demo section, offer, Q&A, lead form, thank-you, email demo." },
  { name: "Bot Sales Agent", prompt: "Tạo chatbot flow: opening, qualify, diagnose, demo, phone/email, follow-up, close." },
  { name: "Ads Launch Agent", prompt: "Tạo objective, 3 ad angles, 3 caption, 3 CTA, budget test, KPI." },
  { name: "KPI Optimization Agent", prompt: "Tạo logic tối ưu dựa trên CTR, CPC, CPM, Lead, Close rate." }
];
`);

write("app/api/orchestrator/stream/route.ts", `
import OpenAI from "openai";
import { agents } from "@/lib/agents/prompts";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "missing" });

export async function POST(req: Request) {
  const input = await req.json();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let context = "INPUT:\\n" + JSON.stringify(input, null, 2);

      for (const agent of agents) {
        controller.enqueue(encoder.encode("event: agent_start\\ndata: " + JSON.stringify({ agent: agent.name }) + "\\n\\n"));

        let output = "";
        if (!process.env.OPENAI_API_KEY) {
          output = \`## \${agent.name}\\nMock output cho \${input.product}. Thêm OPENAI_API_KEY để chạy agent thật.\\nCTA: Nhận demo miễn phí.\`;
        } else {
          const completion = await openai.chat.completions.create({
            model: "gpt-4.1-mini",
            messages: [
              { role: "system", content: \`Bạn là \${agent.name}. Conversion > đẹp. Ít chữ. Luôn có CTA. Chuẩn Unicode tiếng Việt.\` },
              { role: "user", content: agent.prompt + "\\n\\nContext:\\n" + context }
            ]
          });
          output = completion.choices[0]?.message?.content || "";
        }

        context += "\\n\\n## " + agent.name + "\\n" + output;
        controller.enqueue(encoder.encode("event: agent_done\\ndata: " + JSON.stringify({ agent: agent.name, output }) + "\\n\\n"));
      }

      controller.enqueue(encoder.encode("event: done\\ndata: {}\\n\\n"));
      controller.close();
    }
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive"
    }
  });
}
`);

write("components/AgentStreamingConsole.tsx", `
"use client";

import { useState } from "react";

export function AgentStreamingConsole() {
  const [input, setInput] = useState({
    industry: "SaaS",
    product: "AI Design Tool",
    audience: "seller, marketer, creator",
    goal: "Lead",
    platform: "TikTok"
  });
  const [blocks, setBlocks] = useState<any[]>([]);
  const [running, setRunning] = useState(false);

  async function run() {
    setBlocks([]);
    setRunning(true);
    const res = await fetch("/api/orchestrator/stream", { method: "POST", body: JSON.stringify(input) });
    const reader = res.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const chunks = buffer.split("\\n\\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        const eventLine = chunk.split("\\n").find((l) => l.startsWith("event:"));
        const dataLine = chunk.split("\\n").find((l) => l.startsWith("data:"));
        if (!eventLine || !dataLine) continue;

        const event = eventLine.replace("event:", "").trim();
        const data = JSON.parse(dataLine.replace("data:", "").trim());

        if (event === "agent_start") setBlocks((p) => [...p, { agent: data.agent, status: "running" }]);
        if (event === "agent_done") setBlocks((p) => p.map((b) => b.agent === data.agent ? { ...b, status: "done", output: data.output } : b));
        if (event === "done") setRunning(false);
      }
    }
    setRunning(false);
  }

  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>AI Ads Factory Orchestrator</h1>
      <section className="card" style={{ marginTop: 24 }}>
        <input value={input.product} onChange={(e) => setInput({ ...input, product: e.target.value })} />
        <button className="btn" style={{ marginLeft: 12 }} onClick={run}>{running ? "Đang chạy..." : "Run Full Factory"}</button>
      </section>

      <section style={{ marginTop: 24, display: "grid", gap: 16 }}>
        {blocks.map((b) => (
          <div className="card" key={b.agent}>
            <h2>{b.status === "running" ? "🟡" : "🟢"} {b.agent}</h2>
            <pre style={{ whiteSpace: "pre-wrap", color: "#CBD5E1" }}>{b.output || "Đang tạo output..."}</pre>
          </div>
        ))}
      </section>
    </main>
  );
}
`);

write("app/factory/page.tsx", `
import { AgentStreamingConsole } from "@/components/AgentStreamingConsole";
export default function Page() {
  return <AgentStreamingConsole />;
}
`);

write("app/api/billing/checkout/route.ts", `
import Stripe from "stripe";
import { NextResponse } from "next/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "missing");

const priceMap: Record<string, string | undefined> = {
  creator: process.env.STRIPE_PRICE_CREATOR,
  pro: process.env.STRIPE_PRICE_PRO,
  studio: process.env.STRIPE_PRICE_STUDIO
};

export async function POST(req: Request) {
  const { plan, userId, email } = await req.json();
  const price = priceMap[plan];

  if (!process.env.STRIPE_SECRET_KEY || !price) {
    return NextResponse.json({ error: "Stripe env missing or invalid plan" }, { status: 400 });
  }

  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer_email: email,
    line_items: [{ price, quantity: 1 }],
    metadata: { plan, userId },
    success_url: \`\${process.env.NEXT_PUBLIC_APP_URL}/dashboard?success=1\`,
    cancel_url: \`\${process.env.NEXT_PUBLIC_APP_URL}/pricing?cancel=1\`
  });

  return NextResponse.json({ url: session.url });
}
`);

write("supabase/migrations/001_init.sql", `
create type plan_type as enum ('free','creator','pro','studio');
create type job_status as enum ('queued','processing','completed','failed');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  plan plan_type default 'free',
  credits int default 10,
  stripe_customer_id text,
  created_at timestamptz default now()
);

create table public.generation_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  prompt text not null,
  status job_status default 'queued',
  result_urls text[] default '{}',
  error text,
  created_at timestamptz default now()
);

alter table profiles enable row level security;
alter table generation_jobs enable row level security;

create policy "profiles owner read" on profiles for select using (auth.uid() = id);
create policy "jobs owner all" on generation_jobs for all using (auth.uid() = user_id);
`);

write("DESIGN.md", `
---
version: 2.1
name: "Revenue Ads System"
description: "Hệ thống tạo ads có CTR cao + chuyển đổi mạnh"
conversion:
  goal: "Lead"
  primaryAction: "demo"
  platform: "TikTok"
colors:
  primary: "#0A0F2C"
  accent: "#2563EB"
  highlight: "#FACC15"
  background: "#0A0F2C"
  surface: "#111827"
  text: "#FFFFFF"
typography:
  headline-lg:
    fontFamily: "Inter"
    fontSize: 48px
    fontWeight: 700
spacing:
  md: 16px
  lg: 32px
rounded:
  md: 8px
  lg: 16px
---
# Revenue Ads System DESIGN.md

Conversion > đẹp. Ít chữ. CTA rõ. Không phá brand.
`);

write("README.md", `
# AI Ads Factory SaaS

## Quick start

\`\`\`bash
cp .env.example .env.local
npm install
npm run dev
\`\`\`

Open:

- /
- /revenue-factory
- /factory

Nếu chưa có OPENAI_API_KEY, Orchestrator dùng mock output.
`);

write("docs/01-setup.md", `
# Setup

\`\`\`bash
cp .env.example .env.local
npm install
npm run dev
\`\`\`

Pages:

- /
- /revenue-factory
- /factory
`);

write("docs/02-env.md", `
# ENV

Điền vào .env.local:

- OPENAI_API_KEY
- STRIPE_SECRET_KEY
- STRIPE_PRICE_CREATOR
- STRIPE_PRICE_PRO
- STRIPE_PRICE_STUDIO
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY
`);

write("docs/03-database.md", `
# Database

Chạy SQL trong:

\`\`\`txt
supabase/migrations/001_init.sql
\`\`\`

trên Supabase SQL Editor.
`);

write("docs/04-prompt-engine-v3.md", `
# Prompt Engine V3

File chính:

\`\`\`txt
lib/prompt/prompt-engine-v3.ts
\`\`\`

Output:

- score
- concept
- hook
- headline
- CTA
- layout
- prompt2D
- promptVideo
- whyItConverts
`);

write("docs/05-remotion-render.md", `
# Remotion Render

Preview:

\`\`\`bash
npm run remotion:preview
\`\`\`

Render demo:

\`\`\`bash
npm run remotion:render
\`\`\`

API:

\`\`\`txt
POST /api/render/ad-video
\`\`\`

Production nên chuyển render sang queue/worker.
`);

write("docs/06-stripe-pricing.md", `
# Stripe Pricing

Route:

\`\`\`txt
app/api/billing/checkout/route.ts
\`\`\`

Env:

\`\`\`env
STRIPE_SECRET_KEY=
STRIPE_PRICE_CREATOR=
STRIPE_PRICE_PRO=
STRIPE_PRICE_STUDIO=
\`\`\`
`);

write("docs/07-funnel.md", `
# Funnel

TikTok video
→ Landing page
→ Try free
→ Generate top 3 ads
→ Render video watermark
→ Upgrade Pro
`);

write("docs/08-dev-patch-checklist.md", `
# Dev Patch Checklist

## P0
- Test /revenue-factory
- Test /factory mock mode
- Add OPENAI_API_KEY
- Test Prompt Engine V3

## P1
- Test Remotion local render
- Move render to queue/worker
- Upload video to Supabase Storage/S3

## P2
- Add Auth UI
- Add Stripe webhook
- Add credit deduction
- Add dashboard KPI
`);

write("docs/09-launch-checklist.md", `
# Launch Checklist

- Landing promise rõ
- Free trial giới hạn
- Pro plan có video render/no watermark
- Prompt V3 tạo top 3 ads
- Render video chạy được
- Stripe checkout test xong
- Không expose service role key ở client
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
