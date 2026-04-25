"use client";

import { useState } from "react";
import { useT } from "@/src/i18n/useT";
import FactoryRunPanel from "@/src/components/factory/FactoryRunPanel";
import FactoryStageTimeline from "@/src/components/factory/FactoryStageTimeline";
import FactoryQualityGatePanel from "@/src/components/factory/FactoryQualityGatePanel";
import FactoryMemoryPanel from "@/src/components/factory/FactoryMemoryPanel";
import {
  getFactoryRun,
  type FactoryRunOut,
  type FactoryRunDetailOut,
} from "@/src/lib/api";

export default function FactoryPage() {
  const t = useT();
  const [runs, setRuns] = useState<FactoryRunOut[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<FactoryRunDetailOut | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  function handleRunCreated(run: FactoryRunOut) {
    setRuns((prev) => [run, ...prev]);
  }

  function handleRunUpdated(updated: FactoryRunOut) {
    setRuns((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    if (selectedDetail?.id === updated.id) {
      setSelectedDetail((d) => d ? { ...d, ...updated } : null);
    }
  }

  async function handleSelectRun(runId: string) {
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const detail = await getFactoryRun(runId);
      setSelectedDetail(detail);
    } catch (err: any) {
      setDetailError(err?.message ?? "Failed to load run detail");
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 px-6 py-10 text-white">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <header className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <p className="text-sm uppercase tracking-[0.25em] text-white/40">
            CLOSED_LOOP_VIDEO_FACTORY_OS
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{t("factory_title")}</h1>
          <p className="mt-2 max-w-3xl text-sm text-white/60">{t("factory_subtitle")}</p>
          <div className="mt-4 grid grid-cols-6 gap-1">
            {[
              "INTAKE", "CONTEXT_LOAD", "SKILL_ROUTE", "SCRIPT_PLAN",
              "SCENE_BUILD", "AVATAR_AUDIO_BUILD", "RENDER_PLAN",
              "EXECUTE_RENDER", "QA_VALIDATE", "SEO_PACKAGE", "PUBLISH", "TELEMETRY_LEARN",
            ].map((stage, i) => (
              <div key={stage} className="rounded-xl border border-white/10 bg-white/5 px-2 py-1 text-center">
                <span className="text-[9px] font-semibold text-white/40">{i + 1}</span>
                <p className="text-[8px] text-white/60 leading-tight">{stage}</p>
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left: run panel */}
          <div>
            <FactoryRunPanel
              runs={runs}
              onRunCreated={handleRunCreated}
              onRunUpdated={handleRunUpdated}
              onSelectRun={handleSelectRun}
            />
          </div>

          {/* Right: detail panel */}
          <div className="space-y-6">
            {loadingDetail && (
              <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <p className="text-sm text-white/40">{t("factory_loading_detail")}</p>
              </div>
            )}
            {detailError && (
              <div className="rounded-3xl border border-red-500/20 bg-red-500/10 p-4">
                <p className="text-sm text-red-400">{detailError}</p>
              </div>
            )}
            {selectedDetail && !loadingDetail && (
              <>
                {/* Run summary */}
                <div className="rounded-3xl border border-white/10 bg-white/5 p-6 space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold">{selectedDetail.id.slice(0, 16)}…</h2>
                    <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold">
                      {selectedDetail.status} · {selectedDetail.percent_complete}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-white/60 transition-all"
                      style={{ width: `${selectedDetail.percent_complete}%` }}
                    />
                  </div>
                  {selectedDetail.seo_title && (
                    <p className="text-xs text-white/60">{t("factory_seo_label")}: {selectedDetail.seo_title}</p>
                  )}
                  {selectedDetail.render_job_id && (
                    <p className="text-xs text-white/40">{t("factory_render_job_label")}: {selectedDetail.render_job_id}</p>
                  )}
                  {selectedDetail.blocking_reason && (
                    <p className="text-xs text-red-400">{t("factory_blocked_label")}: {selectedDetail.blocking_reason}</p>
                  )}
                </div>

                <FactoryStageTimeline stages={selectedDetail.stages ?? []} />
                <FactoryQualityGatePanel gates={selectedDetail.quality_gates ?? []} />

                {/* Incidents */}
                {(selectedDetail.incidents ?? []).length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
                      {t("factory_incidents_title")}
                    </h3>
                    <div className="space-y-2">
                      {selectedDetail.incidents.map((inc) => (
                        <div key={inc.id} className="rounded-2xl border border-red-500/20 bg-red-500/10 p-3">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-red-300">{inc.severity.toUpperCase()}</span>
                            <span className="text-xs text-white/60">{inc.incident_type}</span>
                            {inc.stage_name && <span className="text-xs text-white/40">@ {inc.stage_name}</span>}
                          </div>
                          {inc.detail && <p className="mt-1 text-xs text-red-200/70 line-clamp-3">{inc.detail}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
