"use client";

import { useState } from "react";
import { useT } from "@/src/i18n/useT";
import {
  startFactoryRun,
  approveFactoryRun,
  retryFactoryRun,
  cancelFactoryRun,
  type FactoryRunOut,
  type FactoryRunRequest,
} from "@/src/lib/api";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-white/10 text-white/60",
  running: "bg-blue-500/20 text-blue-300 animate-pulse",
  completed: "bg-green-500/20 text-green-300",
  failed: "bg-red-500/20 text-red-300",
  cancelled: "bg-white/10 text-white/40 line-through",
  awaiting_approval: "bg-yellow-500/20 text-yellow-300",
};

type Props = {
  runs: FactoryRunOut[];
  onRunCreated: (run: FactoryRunOut) => void;
  onRunUpdated: (run: FactoryRunOut) => void;
  onSelectRun: (runId: string) => void;
};

export default function FactoryRunPanel({ runs, onRunCreated, onRunUpdated, onSelectRun }: Props) {
  const t = useT();
  const [form, setForm] = useState<FactoryRunRequest>({ input_type: "topic" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const run = await startFactoryRun(form);
      onRunCreated(run);
    } catch (err: any) {
      setError(err?.message ?? "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(runId: string) {
    try {
      const run = await approveFactoryRun(runId);
      onRunUpdated(run);
    } catch (err: any) {
      alert(err?.message);
    }
  }

  async function handleRetry(runId: string) {
    try {
      const run = await retryFactoryRun(runId);
      onRunUpdated(run);
    } catch (err: any) {
      alert(err?.message);
    }
  }

  async function handleCancel(runId: string) {
    try {
      const run = await cancelFactoryRun(runId);
      onRunUpdated(run);
    } catch (err: any) {
      alert(err?.message);
    }
  }

  return (
    <div className="space-y-6">
      {/* New Run Form */}
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <h2 className="mb-4 text-lg font-semibold">{t("factory_new_run")}</h2>
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-white/50">{t("factory_input_type")}</label>
            <select
              value={form.input_type}
              onChange={(e) => setForm((f) => ({ ...f, input_type: e.target.value as any }))}
              className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
            >
              <option value="topic">topic</option>
              <option value="script">script</option>
              <option value="avatar">avatar</option>
              <option value="series">series</option>
            </select>
          </div>

          {(form.input_type === "topic") && (
            <div>
              <label className="mb-1 block text-xs text-white/50">{t("factory_input_topic")}</label>
              <input
                type="text"
                value={form.input_topic ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, input_topic: e.target.value }))}
                placeholder="AI trends 2026..."
                className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-white/30"
              />
            </div>
          )}

          {(form.input_type === "script") && (
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs text-white/50">{t("factory_input_script")}</label>
              <textarea
                rows={4}
                value={form.input_script ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, input_script: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
              />
            </div>
          )}

          {form.input_type === "avatar" && (
            <div>
              <label className="mb-1 block text-xs text-white/50">{t("factory_input_avatar")}</label>
              <input
                type="text"
                value={form.input_avatar_id ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, input_avatar_id: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
              />
            </div>
          )}

          {form.input_type === "series" && (
            <div>
              <label className="mb-1 block text-xs text-white/50">{t("factory_input_series")}</label>
              <input
                type="text"
                value={form.input_series_id ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, input_series_id: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs text-white/50">{t("factory_project_id")}</label>
            <input
              type="text"
              value={form.project_id ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value || undefined }))}
              className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-white/50">{t("factory_budget")}</label>
            <input
              type="number"
              value={form.budget_cents ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, budget_cents: e.target.value ? Number(e.target.value) : undefined }))}
              className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
            />
          </div>

          <div className="sm:col-span-2">
            {error && <p className="mb-2 text-sm text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-white px-5 py-2 text-sm font-semibold text-black transition hover:bg-white/90 disabled:opacity-50"
            >
              {submitting ? t("factory_submitting") : t("factory_submit")}
            </button>
          </div>
        </form>
      </div>

      {/* Run List */}
      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
        <h2 className="mb-4 text-lg font-semibold">{t("factory_runs_title")}</h2>
        {runs.length === 0 ? (
          <p className="text-sm text-white/40">{t("factory_no_runs")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs text-white/40">
                  <th className="px-3 py-2 text-left">{t("factory_run_id")}</th>
                  <th className="px-3 py-2 text-left">{t("factory_status")}</th>
                  <th className="px-3 py-2 text-left">{t("factory_stage")}</th>
                  <th className="px-3 py-2 text-right">{t("factory_progress")}</th>
                  <th className="px-3 py-2 text-left">{t("factory_actions")}</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-3 py-2 font-mono text-xs text-white/70">
                      <button
                        onClick={() => onSelectRun(run.id)}
                        className="hover:underline"
                      >
                        {run.id.slice(0, 8)}…
                      </button>
                    </td>
                    <td className="px-3 py-2">
                      <span className={["rounded-full px-2 py-0.5 text-xs font-semibold", STATUS_BADGE[run.status] ?? ""].join(" ")}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-white/60">{run.current_stage}</td>
                    <td className="px-3 py-2 text-right text-xs">{run.percent_complete}%</td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button onClick={() => onSelectRun(run.id)} className="text-xs text-white/60 hover:text-white">
                          {t("factory_view_detail")}
                        </button>
                        {run.status === "awaiting_approval" && (
                          <button onClick={() => handleApprove(run.id)} className="text-xs text-yellow-300 hover:text-yellow-200">
                            {t("factory_approve")}
                          </button>
                        )}
                        {(run.status === "failed" || run.status === "cancelled") && (
                          <button onClick={() => handleRetry(run.id)} className="text-xs text-blue-300 hover:text-blue-200">
                            {t("factory_retry")}
                          </button>
                        )}
                        {(run.status === "pending" || run.status === "running") && (
                          <button onClick={() => handleCancel(run.id)} className="text-xs text-red-300 hover:text-red-200">
                            {t("factory_cancel")}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
