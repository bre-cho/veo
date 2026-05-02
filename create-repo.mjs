import fs from "fs";
import path from "path";

const root = "ai-ads-factory-saas";

function write(file, content) {
  const full = path.join(root, file);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content.trimStart(), "utf8");
}

fs.rmSync(root, { recursive: true, force: true });
fs.mkdirSync(root);

write("package.json", `
{
  "name": "ai-ads-factory-saas",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@supabase/ssr": "latest",
    "@supabase/supabase-js": "latest",
    "framer-motion": "latest",
    "js-yaml": "latest",
    "next": "latest",
    "openai": "latest",
    "react": "latest",
    "react-dom": "latest",
    "stripe": "latest",
    "zod": "latest"
  },
  "devDependencies": {
    "@types/js-yaml": "latest",
    "@types/node": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "autoprefixer": "latest",
    "postcss": "latest",
    "tailwindcss": "latest",
    "typescript": "latest"
  }
}
`);

write("tsconfig.json", `
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": false,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
`);

write("next.config.mjs", `
const nextConfig = {};
export default nextConfig;
`);

write("postcss.config.mjs", `
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
};
`);

write("tailwind.config.ts", `
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {}
  },
  plugins: []
};

export default config;
`);

write(".env.example", `
NEXT_PUBLIC_APP_URL=http://localhost:3000

OPENAI_API_KEY=

NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

TIKTOK_ACCESS_TOKEN=
TIKTOK_ADVERTISER_ID=
`);

write("app/globals.css", `
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-primary: #0A0F2C;
  --color-accent: #2563EB;
  --color-highlight: #FACC15;
  --color-background: #0A0F2C;
  --color-surface: #111827;
  --color-text: #FFFFFF;
  --radius-md: 8px;
  --radius-lg: 16px;
}

body {
  margin: 0;
  background: var(--color-background);
  color: var(--color-text);
}

.ds-page {
  background: var(--color-background);
  color: var(--color-text);
}

.ds-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid rgba(255,255,255,.1);
}

.ds-button {
  background: var(--color-accent);
  color: white;
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-weight: 800;
}

.ds-highlight {
  color: var(--color-highlight);
}
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

write("app/page.tsx", `
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#0A0F2C] text-white flex items-center justify-center p-6">
      <section className="max-w-5xl text-center">
        <p className="text-[#FACC15] font-bold">AI Ads Factory SaaS</p>
        <h1 className="text-6xl font-black mt-4">
          Tạo ads bán hàng trong <span className="text-[#FACC15]">60 giây</span>
        </h1>
        <p className="mt-6 text-xl text-gray-300">
          Điều phối Insight, Offer, Creative, DESIGN.md, Image Ads, Video, Funnel, Bot Sales và KPI Optimization.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/factory" className="rounded-xl bg-[#2563EB] px-6 py-4 font-bold">
            Mở AI Factory
          </Link>
          <Link href="/studio" className="rounded-xl bg-white/10 px-6 py-4 font-bold">
            Mở Studio
          </Link>
        </div>
      </section>
    </main>
  );
}
`);

write("lib/agents/prompts.ts", `
export const agents = [
  {
    name: "Insight Agent",
    prompt: "Phân tích insight khách hàng: pain, desire, objection, góc bán hàng mạnh nhất."
  },
  {
    name: "Offer Agent",
    prompt: "Tạo offer chính, lý do mua, điểm khác biệt, bonus, CTA."
  },
  {
    name: "Creative Director Agent",
    prompt: "Tạo 3 concept ads: big idea, visual direction, hook, CTA, lý do chuyển đổi."
  },
  {
    name: "DESIGN.md Agent",
    prompt: "Tạo DESIGN.md gồm colors, typography, layout rules, components, do/don't, CTA style, visual mood."
  },
  {
    name: "Image Ads Agent",
    prompt: "Tạo prompt hero banner, ads 1:1, ads 4:5, thumbnail, text overlay."
  },
  {
    name: "Video Avatar Agent",
    prompt: "Tạo script video 6-8s, 15s, storyboard, voice-over, subtitle, CTA cuối video."
  },
  {
    name: "Funnel Agent",
    prompt: "Tạo hero section, demo section, offer, Q&A, lead form, thank-you message, email gửi demo."
  },
  {
    name: "Bot Sales Agent",
    prompt: "Tạo chatbot flow: opening, qualify, diagnose, offer demo, xin phone/email, follow-up 6h/24h, close."
  },
  {
    name: "Ads Launch Agent",
    prompt: "Tạo campaign objective, 3 ad angles, 3 caption, 3 CTA, budget test, KPI cần theo dõi."
  },
  {
    name: "KPI Optimization Agent",
    prompt: "Tạo logic tối ưu dựa trên CTR, CPC, CPM, Lead, Close rate."
  }
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
        controller.enqueue(
          encoder.encode("event: agent_start\\ndata: " + JSON.stringify({ agent: agent.name }) + "\\n\\n")
        );

        let output = "";

        if (!process.env.OPENAI_API_KEY) {
          output = mockOutput(agent.name, input);
        } else {
          const completion = await openai.chat.completions.create({
            model: "gpt-4.1-mini",
            messages: [
              {
                role: "system",
                content: \`
Bạn là \${agent.name}.
Nguyên tắc:
- Conversion > đẹp
- Ít chữ, rõ thông điệp
- Luôn có CTA
- Không dùng thương hiệu/bản quyền chưa được phép
- Chuẩn tiếng Việt Unicode
\`
              },
              {
                role: "user",
                content: agent.prompt + "\\n\\nContext trước đó:\\n" + context
              }
            ]
          });

          output = completion.choices[0]?.message?.content || "";
        }

        context += "\\n\\n## " + agent.name + "\\n" + output;

        controller.enqueue(
          encoder.encode("event: agent_done\\ndata: " + JSON.stringify({ agent: agent.name, output }) + "\\n\\n")
        );
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

function mockOutput(agent: string, input: any) {
  return \`## \${agent}

Sản phẩm: \${input.product || "AI Design Tool"}

- Insight: khách muốn tạo ads nhanh, đẹp, có chuyển đổi.
- Big idea: biến 1 ý tưởng thành ads bán hàng trong 60 giây.
- Hook: Bạn đang đốt tiền ads mà không có khách?
- CTA: Nhận demo miễn phí.
- Ghi chú: Đây là mock output. Thêm OPENAI_API_KEY để chạy agent thật.\`;
}
`);

write("components/AgentStreamingConsole.tsx", `
"use client";

import { useState } from "react";

type AgentBlock = {
  agent: string;
  status: "running" | "done";
  output?: string;
};

export function AgentStreamingConsole() {
  const [input, setInput] = useState({
    industry: "SaaS",
    product: "AI Design Tool",
    audience: "seller, marketer, creator",
    goal: "Lead",
    platform: "TikTok"
  });

  const [blocks, setBlocks] = useState<AgentBlock[]>([]);
  const [running, setRunning] = useState(false);

  async function run() {
    setBlocks([]);
    setRunning(true);

    const res = await fetch("/api/orchestrator/stream", {
      method: "POST",
      body: JSON.stringify(input)
    });

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

        if (event === "agent_start") {
          setBlocks((prev) => [...prev, { agent: data.agent, status: "running" }]);
        }

        if (event === "agent_done") {
          setBlocks((prev) =>
            prev.map((b) =>
              b.agent === data.agent ? { ...b, status: "done", output: data.output } : b
            )
          );
        }

        if (event === "done") setRunning(false);
      }
    }

    setRunning(false);
  }

  return (
    <main className="min-h-screen bg-[#0A0F2C] text-white p-6">
      <h1 className="text-3xl font-black">🧠 AI Ads Factory Orchestrator</h1>

      <section className="mt-6 rounded-2xl bg-[#111827] p-5">
        <div className="grid grid-cols-2 gap-3">
          <input className="rounded-lg bg-black/30 p-3" value={input.industry} onChange={(e) => setInput({ ...input, industry: e.target.value })} />
          <input className="rounded-lg bg-black/30 p-3" value={input.product} onChange={(e) => setInput({ ...input, product: e.target.value })} />
          <input className="rounded-lg bg-black/30 p-3 col-span-2" value={input.audience} onChange={(e) => setInput({ ...input, audience: e.target.value })} />
        </div>

        <button onClick={run} disabled={running} className="mt-4 rounded-xl bg-[#2563EB] px-5 py-3 font-bold disabled:opacity-50">
          {running ? "Đang chạy 10 agents..." : "Run Full Factory"}
        </button>
      </section>

      <section className="mt-6 space-y-4">
        {blocks.map((b) => (
          <div key={b.agent} className="rounded-2xl border border-white/10 bg-[#111827] p-5">
            <div className="flex items-center gap-3">
              <span className={\`h-3 w-3 rounded-full \${b.status === "running" ? "bg-yellow-400 animate-pulse" : "bg-green-400"}\`} />
              <h2 className="font-bold">{b.agent}</h2>
            </div>

            {b.status === "running" && <p className="mt-3 text-gray-400">Đang tạo output...</p>}

            {b.output && <pre className="mt-4 whitespace-pre-wrap text-sm text-gray-200">{b.output}</pre>}
          </div>
        ))}
      </section>
    </main>
  );
}
`);

write("app/factory/page.tsx", `
import { AgentStreamingConsole } from "@/components/AgentStreamingConsole";

export default function FactoryPage() {
  return <AgentStreamingConsole />;
}
`);

write("lib/design/schema.ts", `
import { z } from "zod";

export const DesignSystemSchema = z.object({
  version: z.string().optional(),
  name: z.string(),
  description: z.string().optional(),
  colors: z.object({
    primary: z.string(),
    secondary: z.string().optional(),
    accent: z.string(),
    highlight: z.string().optional(),
    background: z.string(),
    surface: z.string(),
    text: z.string()
  }),
  typography: z.record(z.any()).optional(),
  spacing: z.record(z.string()).optional(),
  rounded: z.record(z.string()).optional(),
  components: z.record(z.any()).optional(),
  conversion: z.object({
    goal: z.enum(["CTR", "Lead", "Sale"]).optional(),
    platform: z.enum(["TikTok", "Facebook", "Landing"]).optional(),
    primaryAction: z.string().optional()
  }).optional()
});

export type DesignSystem = z.infer<typeof DesignSystemSchema>;
`);

write("lib/design/parser.ts", `
import yaml from "js-yaml";
import { DesignSystem, DesignSystemSchema } from "./schema";

export function parseDesignMd(content: string): DesignSystem {
  const match = content.match(/^---\\n([\\s\\S]*?)\\n---/);
  if (!match) throw new Error("DESIGN.md thiếu YAML frontmatter.");
  const raw = yaml.load(match[1]);
  return DesignSystemSchema.parse(raw);
}
`);

write("lib/design/css-vars.ts", `
import { DesignSystem } from "./schema";

export function designToCssVars(ds: DesignSystem) {
  return {
    "--color-primary": ds.colors.primary,
    "--color-secondary": ds.colors.secondary || ds.colors.primary,
    "--color-accent": ds.colors.accent,
    "--color-highlight": ds.colors.highlight || ds.colors.accent,
    "--color-background": ds.colors.background,
    "--color-surface": ds.colors.surface,
    "--color-text": ds.colors.text,
    "--radius-md": ds.rounded?.md || "8px",
    "--radius-lg": ds.rounded?.lg || "16px"
  } as React.CSSProperties;
}
`);

write("components/DesignProvider.tsx", `
"use client";

import { createContext, useContext, useMemo, useState } from "react";
import { DesignSystem } from "@/lib/design/schema";
import { parseDesignMd } from "@/lib/design/parser";
import { designToCssVars } from "@/lib/design/css-vars";

const defaultDesignMd = \`---
version: alpha
name: "Revenue Ads System"
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
rounded:
  md: 8px
  lg: 16px
spacing:
  md: 16px
  lg: 32px
conversion:
  goal: "Lead"
  platform: "TikTok"
  primaryAction: "demo"
---
\`;

type Ctx = {
  designMd: string;
  setDesignMd: (v: string) => void;
  design: DesignSystem;
  cssVars: React.CSSProperties;
};

const DesignContext = createContext<Ctx | null>(null);

export function DesignProvider({ children }: { children: React.ReactNode }) {
  const [designMd, setDesignMd] = useState(defaultDesignMd);
  const design = useMemo(() => parseDesignMd(designMd), [designMd]);
  const cssVars = useMemo(() => designToCssVars(design), [design]);

  return (
    <DesignContext.Provider value={{ designMd, setDesignMd, design, cssVars }}>
      <div style={cssVars}>{children}</div>
    </DesignContext.Provider>
  );
}

export function useDesign() {
  const ctx = useContext(DesignContext);
  if (!ctx) throw new Error("useDesign must be used inside DesignProvider");
  return ctx;
}
`);

write("lib/prompt/optimizer.ts", `
import { DesignSystem } from "@/lib/design/schema";

type Goal = "CTR" | "Lead" | "Sale";
type Platform = "TikTok" | "Facebook" | "Landing";
type Mode = "Money" | "Viral" | "Premium";

export type PromptInput = {
  product: string;
  audience: string;
  offer?: string;
  industry: string;
  goal: Goal;
  platform: Platform;
  mode: Mode;
};

const hooks = {
  pain: [
    "Bạn đang đốt tiền ads mà không có khách?",
    "Bạn đang mất bao nhiêu khách vì điều này?",
    "Tại sao bạn chưa bán được hàng?"
  ],
  curiosity: [
    "Xem cái này trước khi bạn chạy ads",
    "Không ai nói với bạn điều này",
    "Điều này thay đổi cách bán hàng"
  ],
  result: [
    "Tăng CTR chỉ với 1 thay đổi",
    "Khách hiểu sản phẩm nhanh hơn",
    "1 visual giúp bán hàng tốt hơn"
  ],
  fomo: [
    "Đối thủ bạn đang dùng cái này",
    "Bạn đang tụt lại phía sau",
    "Bạn có đang bỏ lỡ cơ hội này?"
  ]
};

const visualMap = {
  TikTok: [
    "fast before-after transformation",
    "AI demo workflow from text to final ad",
    "human reaction with strong emotion"
  ],
  Facebook: [
    "left hook text, right product visual",
    "clean product ad with offer badge",
    "testimonial proof block with CTA"
  ],
  Landing: [
    "hero section with UI mockup",
    "problem-solution section",
    "comparison before-after section"
  ]
};

export function generateOptimizedPrompts(input: PromptInput, ds: DesignSystem) {
  const selectedHooks = selectHooks(input);
  const visuals = visualMap[input.platform];

  return selectedHooks.flatMap((hook) =>
    visuals.map((visual) => {
      const cta = getCta(input.goal);
      const score = scorePrompt(input, hook, visual);

      return {
        score,
        hook,
        visual,
        cta,
        prompt: \`
High-converting \${input.platform} ad creative.

Product: \${input.product}
Industry: \${input.industry}
Audience: \${input.audience}
Goal: \${input.goal}
Offer: \${input.offer || "clear offer"}

Hook: "\${hook}"
CTA: "\${cta}"
Visual: \${visual}

DESIGN.md brand lock:
- Primary: \${ds.colors.primary}
- Accent: \${ds.colors.accent}
- Highlight: \${ds.colors.highlight || ds.colors.accent}
- Background: \${ds.colors.background}
- Surface: \${ds.colors.surface}
- Text: \${ds.colors.text}

Rules:
- 1 message only
- maximum 3 text lines
- CTA must be visible
- product or face must be main focus
- strong contrast
- conversion-focused layout
- do not break brand system
\`.trim()
      };
    })
  ).sort((a, b) => b.score - a.score);
}

function selectHooks(input: PromptInput) {
  if (input.mode === "Viral") return [...hooks.curiosity, ...hooks.fomo];
  if (input.mode === "Premium") return [...hooks.result, ...hooks.curiosity];
  if (input.goal === "Lead") return [...hooks.pain, ...hooks.result];
  if (input.goal === "Sale") return [...hooks.result, ...hooks.fomo];
  return [...hooks.curiosity, ...hooks.result];
}

function getCta(goal: Goal) {
  if (goal === "Lead") return "Nhận demo miễn phí";
  if (goal === "Sale") return "Mua ngay";
  return "Xem video ngay";
}

function scorePrompt(input: PromptInput, hook: string, visual: string) {
  let score = 70;
  if (input.goal === "Lead" && hook.includes("đốt tiền")) score += 15;
  if (input.platform === "TikTok" && visual.includes("fast")) score += 12;
  if (input.mode === "Money") score += 8;
  return score;
}
`);

write("components/PromptOptimizerPanel.tsx", `
"use client";

import { useState } from "react";
import { useDesign } from "./DesignProvider";
import { generateOptimizedPrompts } from "@/lib/prompt/optimizer";

export function PromptOptimizerPanel() {
  const { design, designMd, setDesignMd } = useDesign();
  const [product, setProduct] = useState("AI Design Tool");
  const [results, setResults] = useState<any[]>([]);

  function run() {
    const prompts = generateOptimizedPrompts({
      product,
      audience: "seller, marketer, creator",
      industry: "SaaS",
      goal: design.conversion?.goal || "Lead",
      platform: design.conversion?.platform || "TikTok",
      mode: "Money"
    }, design);

    setResults(prompts.slice(0, 6));
  }

  return (
    <main className="ds-page min-h-screen p-6">
      <h1 className="text-4xl font-black">Prompt Engine V2 <span className="ds-highlight">Conversion Optimizer</span></h1>

      <div className="mt-6 grid grid-cols-2 gap-6">
        <section className="ds-card">
          <label className="font-bold">DESIGN.md</label>
          <textarea value={designMd} onChange={(e) => setDesignMd(e.target.value)} className="mt-3 h-[360px] w-full rounded-lg bg-black/30 p-4 font-mono text-sm" />
        </section>

        <section className="ds-card">
          <label className="font-bold">Product</label>
          <input value={product} onChange={(e) => setProduct(e.target.value)} className="mt-3 w-full rounded-lg bg-black/30 p-3" />
          <button onClick={run} className="ds-button mt-4">Tối ưu prompt conversion</button>

          <div className="mt-6 space-y-4">
            {results.map((r, i) => (
              <div key={i} className="rounded-xl bg-black/30 p-4">
                <div className="text-sm ds-highlight">Score: {r.score}</div>
                <h3 className="mt-2 font-bold">{r.hook}</h3>
                <p className="mt-1 text-sm opacity-70">CTA: {r.cta}</p>
                <pre className="mt-3 whitespace-pre-wrap text-xs opacity-70">{r.prompt}</pre>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
`);

write("app/studio/page.tsx", `
import { DesignProvider } from "@/components/DesignProvider";
import { PromptOptimizerPanel } from "@/components/PromptOptimizerPanel";

export default function StudioPage() {
  return (
    <DesignProvider>
      <PromptOptimizerPanel />
    </DesignProvider>
  );
}
`);

write("lib/marketplace/packs.ts", `
export const packs = [
  { slug: "skincare-lead-gen-pack", name: "Skincare Lead Gen Pack", price: 199000, goal: "Lead", platform: "TikTok" },
  { slug: "fb-craving-sales-pack", name: "F&B Craving Sales Pack", price: 149000, goal: "Sale", platform: "TikTok" },
  { slug: "fashion-viral-outfit-pack", name: "Fashion Viral Outfit Pack", price: 179000, goal: "CTR", platform: "TikTok" },
  { slug: "real-estate-trust-pack", name: "Real Estate Trust Pack", price: 249000, goal: "Lead", platform: "TikTok" },
  { slug: "fitness-transformation-pack", name: "Fitness Transformation Pack", price: 179000, goal: "Lead", platform: "TikTok" },
  { slug: "course-authority-pack", name: "Course / Coaching Authority Pack", price: 249000, goal: "Lead", platform: "TikTok" },
  { slug: "saas-demo-conversion-pack", name: "SaaS Demo Conversion Pack", price: 299000, goal: "Signup", platform: "TikTok" },
  { slug: "spa-clinic-booking-pack", name: "Spa / Clinic Booking Pack", price: 199000, goal: "Booking", platform: "TikTok" },
  { slug: "event-fomo-pack", name: "Event FOMO Pack", price: 149000, goal: "Registration", platform: "TikTok" },
  { slug: "interior-transformation-pack", name: "Interior Transformation Pack", price: 199000, goal: "Lead", platform: "TikTok" }
];
`);

write("app/marketplace/page.tsx", `
import { packs } from "@/lib/marketplace/packs";

export default function MarketplacePage() {
  return (
    <main className="min-h-screen bg-[#0A0F2C] text-white p-6">
      <h1 className="text-4xl font-black">Revenue Preset Marketplace</h1>
      <p className="mt-3 text-gray-300">Template không chỉ đẹp — mà có logic kéo click, lead và sale.</p>

      <div className="mt-8 grid grid-cols-3 gap-5">
        {packs.map((p) => (
          <div key={p.slug} className="rounded-2xl bg-[#111827] p-5 border border-white/10">
            <div className="h-40 rounded-xl bg-gradient-to-br from-[#2563EB] to-[#FACC15]" />
            <h2 className="mt-4 text-xl font-bold">{p.name}</h2>
            <p className="mt-2 text-sm text-gray-400">{p.platform} · {p.goal}</p>
            <div className="mt-4 flex items-center justify-between">
              <b>{p.price.toLocaleString()}đ</b>
              <button className="rounded-lg bg-[#2563EB] px-4 py-2 font-bold">Mua pack</button>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
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

create table public.design_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  name text not null,
  design_md jsonb not null default '{}',
  created_at timestamptz default now()
);

create table public.generation_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  project_id uuid references public.design_projects(id) on delete cascade,
  prompt text not null,
  status job_status default 'queued',
  result_urls text[] default '{}',
  error text,
  created_at timestamptz default now()
);

alter table profiles enable row level security;
alter table design_projects enable row level security;
alter table generation_jobs enable row level security;

create policy "profiles owner read" on profiles for select using (auth.uid() = id);
create policy "projects owner all" on design_projects for all using (auth.uid() = user_id);
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
components:
  button-primary:
    padding: 12px
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

- http://localhost:3000
- http://localhost:3000/factory
- http://localhost:3000/studio
- http://localhost:3000/marketplace

Nếu chưa có OPENAI_API_KEY, Factory dùng mock output.
`);

write("docs/01-setup.md", `
# Setup

1. Cài Node.js 20+
2. Chạy:
\`\`\`bash
cp .env.example .env.local
npm install
npm run dev
\`\`\`
`);

write("docs/02-env.md", `
# ENV

Điền vào .env.local:

- OPENAI_API_KEY
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
`);

write("docs/03-database.md", `
# Database

Chạy SQL trong \`supabase/migrations/001_init.sql\` trên Supabase SQL Editor.
`);

write("docs/04-dev-patch-guide.md", `
# Dev Patch Guide

## P0
- Thêm auth UI
- Kết nối Supabase session
- Bảo vệ API generate
- Thêm Stripe checkout thật

## P1
- Kết nối image API
- Lưu asset vào Supabase Storage
- Thêm generation job queue

## P2
- TikTok OAuth
- TikTok Direct Post
- TikTok Ads campaign create
`);

write("docs/05-launch-checklist.md", `
# Launch Checklist

- Landing rõ promise
- Factory chạy được
- Studio parse DESIGN.md
- Marketplace có 10 pack
- Stripe test payment
- Supabase RLS bật
- Không expose service role key
`);

console.log("✅ Repo created: " + root);
console.log("Next:");
console.log("cd " + root);
console.log("cp .env.example .env.local");
console.log("npm install");
console.log("npm run dev");
