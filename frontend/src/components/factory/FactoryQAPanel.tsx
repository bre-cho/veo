"use client";

import { useT } from "@/src/i18n/useT";

export function FactoryQAPanel({ run }: { run: any }) {
  const t = useT();
  const qaStage = run?.stages?.find((s: any) => s.stage_name === "QA_VALIDATE");
  const qa = qaStage?.output || {};
  const details = qa.details || {};

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h2 className="text-lg font-semibold">{t("factory.qaTitle")}</h2>
      <p className="mt-2 text-sm text-white/70">qa_passed: {qa.qa_passed ? "true" : "false"}</p>
      <p className="text-sm text-white/70">scene_count: {details.scene_count ?? 0}</p>
      <p className="text-sm text-white/70">subtitle_count: {details.subtitle_count ?? 0}</p>
      <p className="text-sm text-white/70">duration: {details.total_duration_seconds ?? 0}s</p>
      {qa.issues?.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-red-300">
          {qa.issues.map((x: string) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : null}
      {qa.warnings?.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-yellow-200">
          {qa.warnings.map((x: string) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
