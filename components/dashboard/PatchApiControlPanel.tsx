"use client";

import { useMemo, useState } from "react";

type ApiResultMap = Record<string, { ok: boolean; status: number; body: unknown } | null>;

async function callApi(
  url: string,
  method: "GET" | "POST",
  body?: Record<string, unknown>
) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: method === "POST" ? JSON.stringify(body || {}) : undefined,
  });

  let payload: unknown = null;
  try {
    payload = await res.json();
  } catch {
    payload = { error: "Invalid JSON response" };
  }

  return {
    ok: res.ok,
    status: res.status,
    body: payload,
  };
}

export function PatchApiControlPanel() {
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<ApiResultMap>({});

  const samplePoster = useMemo(
    () => ({
      poster_id: "poster_ui_demo_001",
      industry: "beauty",
      brand_name: "Demo Beauty",
      headline: "Moi min dep sau 7 ngay",
      slogan_or_cta: "INBOX NGAY",
      value_icons: ["Cap am", "Sang da", "Phuc hoi"],
      product_focus: "serum",
      colors: ["gold", "white"],
      text_blocks: ["Moi min dep", "7 ngay", "Inbox ngay"],
      visual_description: "close-up product and skin transformation",
      metadata: {},
    }),
    []
  );

  async function run(name: string, url: string, method: "GET" | "POST", body?: Record<string, unknown>) {
    try {
      setRunning(name);
      const result = await callApi(url, method, body);
      setResults((prev) => ({ ...prev, [name]: result }));
    } finally {
      setRunning(null);
    }
  }

  async function runAll() {
    const jobs: Array<[string, string, "GET" | "POST", Record<string, unknown> | undefined]> = [
      ["preset.health", "/api/preset-library/health", "GET", undefined],
      ["poster.qa", "/api/poster-intelligence/qa-check", "POST", samplePoster],
      ["dna.check", "/api/winner-dna-gate/check", "POST", {
        poster_id: samplePoster.poster_id,
        industry: samplePoster.industry,
        brand_name: samplePoster.brand_name,
        headline: samplePoster.headline,
        cta: samplePoster.slogan_or_cta,
        value_icons: samplePoster.value_icons,
        visual_concept: samplePoster.visual_description,
      }],
      ["scale.detect", "/api/scale-intelligence/detect-industry", "POST", {
        text: `${samplePoster.product_focus} ${samplePoster.headline}`,
      }],
      ["self.heatmap", "/api/self-learning-ai/heatmap", "POST", {
        headline: samplePoster.headline,
        cta: samplePoster.slogan_or_cta,
        visual_type: "product_closeup",
        icon_count: samplePoster.value_icons.length,
        contrast_score: 0.82,
      }],
      ["orchestration.publish", "/api/orchestration/publish-chain", "POST", {
        poster: samplePoster,
      }],
    ];

    for (const [name, url, method, body] of jobs) {
      // Keep calls sequential so results are easier to inspect in UI
      // and orchestration can depend on persistent learner state.
      // eslint-disable-next-line no-await-in-loop
      await run(name, url, method, body);
    }
  }

  return (
    <section className="mt-8 rounded-[2rem] border border-white/10 bg-white/[.045] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-black text-white">Patch API Control Panel</h3>
          <p className="text-sm text-slate-300">
            Gọi nhanh 5 cụm API mới và endpoint orchestration publish-chain trực tiếp từ dashboard.
          </p>
        </div>
        <button
          onClick={runAll}
          disabled={!!running}
          className="rounded-xl bg-emerald-500/20 px-4 py-2 text-sm font-bold text-emerald-200 hover:bg-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {running ? `Running ${running}...` : "Run All Smoke"}
        </button>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <ApiCard
          title="Preset Library"
          actionLabel="Health"
          busy={running === "preset.health"}
          onRun={() => run("preset.health", "/api/preset-library/health", "GET")}
          result={results["preset.health"]}
        />
        <ApiCard
          title="Poster Intelligence"
          actionLabel="QA Check"
          busy={running === "poster.qa"}
          onRun={() => run("poster.qa", "/api/poster-intelligence/qa-check", "POST", samplePoster)}
          result={results["poster.qa"]}
        />
        <ApiCard
          title="Winner DNA Gate"
          actionLabel="Check"
          busy={running === "dna.check"}
          onRun={() =>
            run("dna.check", "/api/winner-dna-gate/check", "POST", {
              poster_id: samplePoster.poster_id,
              industry: samplePoster.industry,
              brand_name: samplePoster.brand_name,
              headline: samplePoster.headline,
              cta: samplePoster.slogan_or_cta,
              value_icons: samplePoster.value_icons,
              visual_concept: samplePoster.visual_description,
            })
          }
          result={results["dna.check"]}
        />
        <ApiCard
          title="Scale Intelligence"
          actionLabel="Detect Industry"
          busy={running === "scale.detect"}
          onRun={() =>
            run("scale.detect", "/api/scale-intelligence/detect-industry", "POST", {
              text: `${samplePoster.product_focus} ${samplePoster.headline}`,
            })
          }
          result={results["scale.detect"]}
        />
        <ApiCard
          title="Self Learning AI"
          actionLabel="Heatmap"
          busy={running === "self.heatmap"}
          onRun={() =>
            run("self.heatmap", "/api/self-learning-ai/heatmap", "POST", {
              headline: samplePoster.headline,
              cta: samplePoster.slogan_or_cta,
              visual_type: "product_closeup",
              icon_count: samplePoster.value_icons.length,
              contrast_score: 0.82,
            })
          }
          result={results["self.heatmap"]}
        />
        <ApiCard
          title="Publish Chain Orchestration"
          actionLabel="Run Chain"
          busy={running === "orchestration.publish"}
          onRun={() =>
            run("orchestration.publish", "/api/orchestration/publish-chain", "POST", {
              poster: samplePoster,
            })
          }
          result={results["orchestration.publish"]}
        />
      </div>
    </section>
  );
}

function ApiCard({
  title,
  actionLabel,
  busy,
  onRun,
  result,
}: {
  title: string;
  actionLabel: string;
  busy: boolean;
  onRun: () => void;
  result: { ok: boolean; status: number; body: unknown } | null | undefined;
}) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-black text-white">{title}</h4>
        <button
          onClick={onRun}
          disabled={busy}
          className="rounded-lg border border-white/20 px-3 py-1 text-xs font-bold text-slate-200 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? "Running..." : actionLabel}
        </button>
      </div>

      {result ? (
        <div className="mt-3">
          <p className={`text-xs font-bold ${result.ok ? "text-emerald-300" : "text-rose-300"}`}>
            {result.ok ? "PASS" : "FAIL"} - HTTP {result.status}
          </p>
          <pre className="mt-2 max-h-44 overflow-auto rounded-lg border border-white/10 bg-black/30 p-2 text-[11px] leading-5 text-slate-300">
            {JSON.stringify(result.body, null, 2)}
          </pre>
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">Chưa chạy.</p>
      )}
    </article>
  );
}
