"use client";

import { useState } from "react";
import { classifyContentGoal, recommendAvatar, recommendCTA, recommendTemplate } from "@/src/lib/api";
import { useT } from "@/src/i18n/useT";

export default function ProductionStudioPage() {
  const t = useT();
  const [avatarId, setAvatarId] = useState("");
  const [marketCode, setMarketCode] = useState("");
  const [contentGoal, setContentGoal] = useState("");
  const [productBrief, setProductBrief] = useState("");
  const [results, setResults] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const classifyRes = await classifyContentGoal({ brief: productBrief || contentGoal || t("productionstudio.defaultBrief") });
      const goal = contentGoal || classifyRes.content_goal;

      const [avatarRes, ctaRes] = await Promise.all([
        recommendAvatar({ content_goal: goal, market_code: marketCode || undefined }),
        recommendCTA({ content_goal: goal }),
      ]);

      let templateRes = null;
      if (avatarId) {
        templateRes = await recommendTemplate({ avatar_id: avatarId, content_goal: goal });
      }

      setResults({ classifiedGoal: goal, avatars: avatarRes.avatars, cta: ctaRes.cta_text, templates: templateRes?.templates });
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 p-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <div>
          <h1 className="text-3xl font-semibold">{t("productionstudio.title")}</h1>
          <p className="text-neutral-400 mt-1">{t("productionstudio.subtitle")}</p>
        </div>

        <form onSubmit={handleRun} className="rounded-2xl bg-neutral-900 border border-neutral-800 p-6 space-y-5">
          <div className="space-y-2">
            <label className="block text-sm text-neutral-400">{t("productionstudio.form.productBrief")}</label>
            <textarea
              value={productBrief}
              onChange={(e) => setProductBrief(e.target.value)}
              rows={3}
              placeholder={t("productionstudio.form.productBriefPlaceholder")}
              className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm text-neutral-400">{t("productionstudio.form.avatarId")}</label>
              <input
                value={avatarId}
                onChange={(e) => setAvatarId(e.target.value)}
                placeholder={t("productionstudio.form.avatarIdPlaceholder")}
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm text-neutral-400">{t("productionstudio.form.marketCode")}</label>
              <input
                value={marketCode}
                onChange={(e) => setMarketCode(e.target.value)}
                placeholder={t("productionstudio.form.marketCodePlaceholder")}
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
              />
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-neutral-100 text-neutral-950 font-semibold py-3 hover:bg-white disabled:opacity-50 transition-colors"
          >
            {loading ? t("productionstudio.form.submitLoading") : t("productionstudio.form.submit")}
          </button>
        </form>

        {results && (
          <div className="space-y-5">
            <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">{t("productionstudio.result.detectedGoal")}</p>
              <p className="text-emerald-400 font-semibold text-lg capitalize">{results.classifiedGoal.replace("_", " ")}</p>
            </div>

            <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-3">{t("productionstudio.result.recommendedCta")}</p>
              <p className="text-neutral-100 italic">"{results.cta}"</p>
            </div>

            {results.avatars?.length > 0 && (
              <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-3">{t("productionstudio.result.recommendedAvatars")}</p>
                <div className="space-y-2">
                  {results.avatars.map((a: any) => (
                    <div key={a.id} className="flex items-center gap-3 text-sm">
                      <span className="text-lg">🎭</span>
                      <span className="text-neutral-100">{a.name}</span>
                      {a.niche_code && <span className="text-neutral-500 text-xs">{a.niche_code}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.templates?.length > 0 && (
              <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-3">{t("productionstudio.result.recommendedTemplates")}</p>
                <div className="space-y-2">
                  {results.templates.map((t: any) => (
                    <div key={t.template_family_id} className="text-sm">
                      <span className="text-neutral-100">{t.name}</span>
                      {t.content_goal && <span className="text-neutral-500 ml-2 text-xs">{t.content_goal}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
