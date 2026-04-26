"use client";

import { useT } from "@/src/i18n/useT";

export function FactoryArtifactPanel({ run }: { run: any }) {
  const t = useT();
  const executeStage = run?.stages?.find((s: any) => s.stage_name === "EXECUTE_RENDER");
  const output = executeStage?.output || {};
  const validation = output?.artifact_validation || {};

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h2 className="text-lg font-semibold">{t("factory.artifactTitle")}</h2>
      <p className="mt-2 text-sm text-white/70">render_job_id: {output.render_job_id || "N/A"}</p>
      <p className="text-sm text-white/70">trang thai: {validation.ok ? "Hop le" : "Chua hop le"}</p>
      <p className="text-sm text-white/70">scene_count: {output.manifest_scene_count ?? 0}</p>
      <p className="text-sm text-white/70">duration: {output.estimated_duration_seconds ?? 0}s</p>
      {validation.issues?.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-red-300">
          {validation.issues.map((x: string) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : null}
      {validation.warnings?.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-yellow-200">
          {validation.warnings.map((x: string) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
