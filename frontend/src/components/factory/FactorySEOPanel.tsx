"use client";

import { useT } from "@/src/i18n/useT";

export function FactorySEOPanel({ run }: { run: any }) {
  const t = useT();
  const stage = run?.stages?.find((s: any) => s.stage_name === "SEO_PACKAGE");
  const seo = stage?.output || {};

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h2 className="text-lg font-semibold">{t("factory.seoTitle")}</h2>
      <p className="mt-2 text-sm text-white/70">title: {seo.title || "N/A"}</p>
      <p className="text-sm text-white/70">description: {seo.description || "N/A"}</p>
      <p className="text-sm text-white/70">tags: {(seo.tags || []).join(", ") || "N/A"}</p>
      <p className="text-sm text-white/70">hashtags_video: {(seo.hashtags_video || []).join(" ") || "N/A"}</p>
      <p className="text-sm text-white/70">hashtags_channel: {(seo.hashtags_channel || []).join(" ") || "N/A"}</p>
    </section>
  );
}
