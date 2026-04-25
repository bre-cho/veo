"use client";

import { useState } from "react";
import { useT } from "@/src/i18n/useT";
import { type TranslationKey } from "@/src/i18n/vi";
import FactoryRunPanel from "@/src/components/factory/FactoryRunPanel";
import FactoryStageTimeline from "@/src/components/factory/FactoryStageTimeline";
import FactoryQualityGatePanel from "@/src/components/factory/FactoryQualityGatePanel";
import FactoryMemoryPanel from "@/src/components/factory/FactoryMemoryPanel";
import {
  getFactoryRun,
  type FactoryRunOut,
  type FactoryRunDetailOut,
} from "@/src/lib/api";

// Map raw QA issue codes → i18n keys
const QA_ISSUE_KEY_PREFIX = "factory_issue_";

function QAIssueLabel({ code, t }: { code: string; t: (k: TranslationKey) => string }) {
  // Strip dynamic suffix (e.g. "manifest_scene_mismatch:expected=3,got=2")
  const base = code.split(":")[0];
  const key = `${QA_ISSUE_KEY_PREFIX}${base}` as TranslationKey;
  const label = t(key) !== key ? t(key) : code;
  return <span>{label}</span>;
}

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

  // Extract QA issues from the QA_VALIDATE stage output summary
  const qaIssues: string[] = (() => {
    if (!selectedDetail) return [];
    const qaStage = (selectedDetail.stages ?? []).find(
      (s: any) => s.stage_name === "QA_VALIDATE"
    );
    if (!qaStage?.output_summary) return [];
    try {
      const parsed = JSON.parse(qaStage.output_summary);
      return Array.isArray(parsed.issues) ? parsed.issues : [];
    } catch {
      return [];
    }
  })();

  // Extract SEO details from run or stage output
  const seoData: Record<string, any> = (() => {
    if (!selectedDetail) return {};
    const seoStage = (selectedDetail.stages ?? []).find(
      (s: any) => s.stage_name === "SEO_PACKAGE"
    );
    if (!seoStage?.output_summary) return {};
    try {
      return JSON.parse(seoStage.output_summary) ?? {};
    } catch {
      return {};
    }
  })();

  // Extract publish details from stage output
  const publishData: Record<string, any> = (() => {
    if (!selectedDetail) return {};
    const pubStage = (selectedDetail.stages ?? []).find(
      (s: any) => s.stage_name === "PUBLISH"
    );
    if (!pubStage?.output_summary) return {};
    try {
      return JSON.parse(pubStage.output_summary) ?? {};
    } catch {
      return {};
    }
  })();

  // Extract artifact details from EXECUTE_RENDER output
  const artifactData: Record<string, any> = (() => {
    if (!selectedDetail) return {};
    const exStage = (selectedDetail.stages ?? []).find(
      (s: any) => s.stage_name === "EXECUTE_RENDER"
    );
    if (!exStage?.output_summary) return {};
    try {
      return JSON.parse(exStage.output_summary) ?? {};
    } catch {
      return {};
    }
  })();

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

                {/* QA Issues */}
                {qaIssues.length > 0 && (
                  <div className="rounded-3xl border border-orange-500/20 bg-orange-500/10 p-4 space-y-2">
                    <h3 className="text-sm font-semibold text-orange-300 uppercase tracking-wider">
                      {t("factory_incidents_title")}
                    </h3>
                    <ul className="space-y-1">
                      {qaIssues.map((code) => (
                        <li key={code} className="flex items-start gap-2 text-xs text-orange-200">
                          <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-400" />
                          <QAIssueLabel code={code} t={t as any} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Artifact panel */}
                {(selectedDetail.output_video_url || artifactData.manifest_scene_count != null) && (
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4 space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
                      {t("factory_artifact_title")}
                    </h3>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                      {selectedDetail.output_video_url && (
                        <>
                          <dt className="text-white/40">{t("factory_artifact_video_url")}</dt>
                          <dd className="truncate text-white/70">
                            <a href={selectedDetail.output_video_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                              {selectedDetail.output_video_url}
                            </a>
                          </dd>
                        </>
                      )}
                      {artifactData.manifest_scene_count != null && (
                        <>
                          <dt className="text-white/40">{t("factory_artifact_scene_count")}</dt>
                          <dd className="text-white/70">{artifactData.manifest_scene_count}</dd>
                        </>
                      )}
                      {artifactData.estimated_duration_seconds != null && (
                        <>
                          <dt className="text-white/40">{t("factory_artifact_duration")}</dt>
                          <dd className="text-white/70">{artifactData.estimated_duration_seconds}s</dd>
                        </>
                      )}
                    </dl>
                  </div>
                )}

                {/* SEO package panel */}
                {(seoData.title || seoData.description) && (
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4 space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
                      {t("factory_seo_label")}
                    </h3>
                    {!seoData.title && !seoData.generated && (
                      <p className="text-xs text-white/40">{t("factory_seo_not_generated")}</p>
                    )}
                    <dl className="space-y-1 text-xs">
                      {seoData.title && (
                        <div>
                          <dt className="text-white/40">{t("factory_seo_title_label")}</dt>
                          <dd className="text-white/70">{seoData.title}</dd>
                        </div>
                      )}
                      {seoData.description && (
                        <div>
                          <dt className="text-white/40">{t("factory_seo_description_label")}</dt>
                          <dd className="text-white/60 line-clamp-3">{seoData.description}</dd>
                        </div>
                      )}
                      {Array.isArray(seoData.hashtags_video) && seoData.hashtags_video.length > 0 && (
                        <div>
                          <dt className="text-white/40">{t("factory_seo_tags_label")}</dt>
                          <dd className="text-white/60">{seoData.hashtags_video.join(" ")}</dd>
                        </div>
                      )}
                    </dl>
                  </div>
                )}

                {/* Publish panel */}
                {publishData.status && (
                  <div className="rounded-3xl border border-white/10 bg-white/5 p-4 space-y-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
                      {t("factory_publish_title")}
                    </h3>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                      <dt className="text-white/40">{t("factory_status")}</dt>
                      <dd className="text-white/70">
                        {publishData.status === "dry_run"
                          ? t("factory_publish_status_dry_run")
                          : publishData.status === "scheduled"
                          ? t("factory_publish_status_scheduled")
                          : publishData.status === "live"
                          ? t("factory_publish_status_live")
                          : publishData.status}
                      </dd>
                      <dt className="text-white/40">{t("factory_publish_dry_run_label")}</dt>
                      <dd className="text-white/70">
                        {publishData.dry_run ? "✓ Bật" : "✗ Tắt"}
                      </dd>
                    </dl>
                    {publishData.dry_run && (
                      <p className="text-xs text-yellow-300/80">{t("factory_publish_approval_required")}</p>
                    )}
                  </div>
                )}

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

