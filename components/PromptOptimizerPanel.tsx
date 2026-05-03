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
      <h1 className="text-4xl font-black">Prompt Engine V2 <span className="ds-highlight">Tối ưu Chuyển đổi</span></h1>

      <div className="mt-6 grid grid-cols-2 gap-6">
        <section className="ds-card">
          <label className="font-bold">DESIGN.md</label>
          <textarea value={designMd} onChange={(e) => setDesignMd(e.target.value)} className="mt-3 h-[360px] w-full rounded-lg bg-black/30 p-4 font-mono text-sm" />
        </section>

        <section className="ds-card">
          <label className="font-bold">Sản phẩm</label>
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
