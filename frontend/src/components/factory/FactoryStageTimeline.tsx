"use client";

import { useT } from "@/src/i18n/useT";

type Stage = {
  stage_name: string;
  stage_index: number;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  error_detail?: string | null;
};

const STATUS_COLORS: Record<string, string> = {
  done: "bg-green-500/20 text-green-300 border-green-500/30",
  running: "bg-blue-500/20 text-blue-300 border-blue-500/30 animate-pulse",
  failed: "bg-red-500/20 text-red-300 border-red-500/30",
  pending: "bg-white/5 text-white/40 border-white/10",
  skipped: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
};

export default function FactoryStageTimeline({ stages }: { stages: Stage[] }) {
  const t = useT();

  if (!stages.length) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
        {t("factory_timeline_title")}
      </h3>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {stages.map((stage) => (
          <div
            key={stage.stage_name}
            className={[
              "rounded-2xl border p-3",
              STATUS_COLORS[stage.status] ?? STATUS_COLORS.pending,
            ].join(" ")}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold">{stage.stage_index + 1}. {stage.stage_name}</span>
              <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase">
                {stage.status}
              </span>
            </div>
            {stage.duration_ms != null && (
              <p className="mt-1 text-[10px] opacity-60">{stage.duration_ms} ms</p>
            )}
            {stage.error_detail && (
              <p className="mt-1 text-[10px] text-red-300 line-clamp-2">{stage.error_detail}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
