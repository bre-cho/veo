"use client";

import ScriptUploadPreviewFlow from "@/src/components/ScriptUploadPreviewFlow";
import { useT } from "@/src/i18n/useT";

export default function ScriptUploadPage() {
  const t = useT();
  return (
    <main className="min-h-screen bg-neutral-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="mb-8">
          <p className="text-sm uppercase tracking-[0.25em] text-white/40">
            {t("nav_script_upload")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {t("script_upload_page_title")}
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-white/55">
            {t("script_upload_page_desc")}
          </p>
        </header>

        <section className="mb-6 rounded-3xl border border-white/10 bg-white/5 p-5">
          <div className="grid gap-4 md:grid-cols-3">
            <InfoCard
              label={t("script_upload_flow_label")}
              value={t("script_upload_flow_value")}
              hint={t("script_upload_flow_hint")}
            />
            <InfoCard
              label={t("script_upload_validation_label")}
              value={t("script_upload_validation_value")}
              hint={t("script_upload_validation_hint")}
            />
            <InfoCard
              label={t("script_upload_next_label")}
              value={t("script_upload_next_value")}
              hint={t("script_upload_next_hint")}
            />
          </div>
        </section>

        <ScriptUploadPreviewFlow />
      </div>
    </main>
  );
}

function InfoCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-wide text-white/45">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-white/55">{hint}</p>
    </div>
  );
}
