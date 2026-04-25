"use client";

import Link from "next/link";
import { useT } from "@/src/i18n/useT";

export default function HomePage() {
  const t = useT();
  return (
    <main className="min-h-screen bg-neutral-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-white/40">{t("home_eyebrow")}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{t("home_title")}</h1>
          <p className="mt-2 max-w-3xl text-sm text-white/60">{t("home_description")}</p>
        </header>
        <section className="grid gap-4 md:grid-cols-3">
          <Card title={t("home_card_dashboard")} href="/render-jobs" desc={t("home_card_dashboard_desc")} />
          <Card title={t("home_card_script_upload")} href="/script-upload" desc={t("home_card_script_upload_desc")} />
          <Card title={t("home_card_audio_studio")} href="/audio" desc={t("home_card_audio_studio_desc")} />
          <Card title={t("home_card_autopilot")} href="/autopilot" desc={t("home_card_autopilot_desc")} />
          <Card title={t("home_card_strategy")} href="/strategy" desc={t("home_card_strategy_desc")} />
          <Card title={t("home_card_templates")} href="/templates" desc={t("home_card_templates_desc")} />
          <Card title={t("home_card_projects")} href="/projects" desc={t("home_card_projects_desc")} />
          <Card title={t("home_card_governance")} href="/templates/governance/scheduling" desc={t("home_card_governance_desc")} />
          <Card title={t("home_card_settings")} href="/settings" desc={t("home_card_settings_desc")} />
          <Card
            title={t("home_card_api_docs")}
            href={`${(process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/api\/v1$/, "")}/docs`}
            desc={t("home_card_api_docs_desc")}
            external
          />
        </section>
      </div>
    </main>
  );
}

function Card({ title, href, desc, external }: { title: string; href: string; desc: string; external?: boolean }) {
  const className = "rounded-3xl border border-white/10 bg-white/5 p-5 transition hover:border-white/25";
  return external ? (
    <a href={href} target="_blank" rel="noreferrer" className={className}>
      <p className="text-lg font-semibold">{title}</p>
      <p className="mt-2 text-sm text-white/60">{desc}</p>
    </a>
  ) : (
    <Link href={href} className={className}>
      <p className="text-lg font-semibold">{title}</p>
      <p className="mt-2 text-sm text-white/60">{desc}</p>
    </Link>
  );
}

