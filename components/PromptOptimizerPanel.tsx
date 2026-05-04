"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useDesign } from "./DesignProvider";
import { generateOptimizedPrompts } from "@/lib/prompt/optimizer";

type PosterImport = {
  preset?: {
    id?: string;
    name?: string;
  };
  brief?: {
    product?: string;
    goal?: string;
    cta?: string;
    audience?: string;
    offer?: string;
  };
  concept?: {
    winner?: {
      hook?: string;
      cta?: string;
      prompt?: string;
    };
  };
};

const PRESET_THEMES: Record<string, { pageBg: string; cardBg: string; accent: string }> = {
  "flash-sale-burst": {
    pageBg: "linear-gradient(140deg, #23090E 0%, #3F1020 38%, #1B203A 100%)",
    cardBg: "#28142A",
    accent: "#FACC15"
  },
  "premium-minimal": {
    pageBg: "linear-gradient(145deg, #10162E 0%, #1B274A 45%, #0B1226 100%)",
    cardBg: "#182647",
    accent: "#93C5FD"
  },
  "launch-countdown": {
    pageBg: "linear-gradient(145deg, #090B27 0%, #151E52 42%, #123454 100%)",
    cardBg: "#121E45",
    accent: "#22D3EE"
  }
};

function normalizeGoal(value?: string): "CTR" | "Lead" | "Sale" {
  const v = (value || "").trim().toLowerCase();
  if (v === "lead") return "Lead";
  if (v === "sale") return "Sale";
  if (v === "ctr" || v === "click") return "CTR";
  return "Lead";
}

function normalizePlatform(value?: string): "TikTok" | "Facebook" | "Landing" {
  const v = (value || "").trim().toLowerCase();
  if (v === "facebook" || v === "meta") return "Facebook";
  if (v === "landing") return "Landing";
  return "TikTok";
}

export function PromptOptimizerPanel() {
  const { design, designMd, setDesignMd } = useDesign();
  const searchParams = useSearchParams();
  const [product, setProduct] = useState("AI Design Tool");
  const [results, setResults] = useState<any[]>([]);
  const [importMessage, setImportMessage] = useState("");
  const [importedConcept, setImportedConcept] = useState<PosterImport["concept"] | null>(null);
  const [theme, setTheme] = useState(PRESET_THEMES["flash-sale-burst"]);
  const [hasImportedPoster, setHasImportedPoster] = useState(false);

  function run(productOverride?: string, goalOverride?: string, platformOverride?: string) {
    const prompts = generateOptimizedPrompts({
      product: productOverride || product,
      audience: "seller, marketer, creator",
      industry: "SaaS",
      goal: normalizeGoal(goalOverride || design.conversion?.goal),
      platform: normalizePlatform(platformOverride || design.conversion?.platform),
      mode: "Money"
    }, design);

    setResults(prompts.slice(0, 6));
  }

  useEffect(() => {
    if (hasImportedPoster || searchParams.get("source") !== "poster") {
      return;
    }

    const productFromQuery = searchParams.get("product")?.trim();
    const goalFromQuery = searchParams.get("goal")?.trim();
    const platformFromQuery = searchParams.get("platform")?.trim();
    const ctaFromQuery = searchParams.get("cta")?.trim();
    const presetFromQuery = searchParams.get("preset")?.trim();

    const nextProduct = productFromQuery || product;
    if (productFromQuery) {
      setProduct(productFromQuery);
    }

    const lines: string[] = [];
    if (goalFromQuery) {
      lines.push(`goal: ${goalFromQuery}`);
    }
    if (ctaFromQuery) {
      lines.push(`cta: ${ctaFromQuery}`);
    }
    if (presetFromQuery) {
      lines.push(`preset: ${presetFromQuery}`);
    }
    if (platformFromQuery) {
      lines.push(`platform: ${platformFromQuery}`);
    }

    if (lines.length > 0) {
      const marker = "\n# Poster Input\n";
      const withoutOld = designMd.replace(/\n# Poster Input\n[\s\S]*$/m, "");
      setDesignMd(`${withoutOld}${marker}${lines.join("\n")}\n`);
    }

    let storageMessage = "";
    let importedFromStorage: PosterImport | null = null;
    try {
      const raw = sessionStorage.getItem("poster:selectedPreset");
      if (raw) {
        const parsed = JSON.parse(raw) as PosterImport;
        importedFromStorage = parsed;
        const presetName = parsed?.preset?.name || presetFromQuery || "unknown";
        storageMessage = `Đã import preset ${presetName} từ /poster.`;
      }
    } catch {
      storageMessage = "Đã nhận dữ liệu từ /poster.";
    }

    const presetId = importedFromStorage?.preset?.id || presetFromQuery || "flash-sale-burst";
    setTheme(PRESET_THEMES[presetId] || PRESET_THEMES["flash-sale-burst"]);
    setImportedConcept(importedFromStorage?.concept || null);

    setImportMessage(storageMessage || "Đã nhận dữ liệu từ /poster.");
    run(nextProduct, goalFromQuery || undefined, platformFromQuery || undefined);
    setHasImportedPoster(true);
  }, [design, designMd, hasImportedPoster, product, searchParams, setDesignMd]);

  return (
    <main className="ds-page min-h-screen p-6" style={{ background: theme.pageBg }}>
      <h1 className="text-4xl font-black">Prompt Engine V2 <span style={{ color: theme.accent }}>Tối ưu Chuyển đổi</span></h1>
      {importMessage && <p className="mt-3 text-sm text-yellow-300">{importMessage}</p>}

      {importedConcept?.winner && (
        <section className="mt-5 rounded-2xl border border-white/15 p-5" style={{ background: theme.cardBg }}>
          <p className="text-xs font-semibold uppercase tracking-[0.2em]" style={{ color: theme.accent }}>Kết quả nhập sẵn từ Poster</p>
          <h2 className="mt-2 text-2xl font-extrabold">{importedConcept.winner.hook || "AI Concept"}</h2>
          <p className="mt-2 text-sm opacity-90">CTA: {importedConcept.winner.cta || "Nhận demo miễn phí"}</p>
          {importedConcept.winner.prompt && (
            <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-black/30 p-4 text-xs text-white/85">
              {importedConcept.winner.prompt}
            </pre>
          )}
        </section>
      )}

      <div className="mt-6 grid grid-cols-2 gap-6">
        <section className="ds-card" style={{ background: theme.cardBg }}>
          <label className="font-bold">DESIGN.md</label>
          <textarea value={designMd} onChange={(e) => setDesignMd(e.target.value)} className="mt-3 h-[360px] w-full rounded-lg bg-black/30 p-4 font-mono text-sm" />
        </section>

        <section className="ds-card" style={{ background: theme.cardBg }}>
          <label className="font-bold">Sản phẩm</label>
          <input value={product} onChange={(e) => setProduct(e.target.value)} className="mt-3 w-full rounded-lg bg-black/30 p-3" />
          <button onClick={() => run()} className="ds-button mt-4">Tối ưu prompt conversion</button>

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
