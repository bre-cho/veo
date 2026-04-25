"use client";

import { useT } from "@/src/i18n/useT";

type DecisionStatus = "allow" | "downgrade" | "block";

interface RebuildDecision {
  selected_strategy: string;
  decision: DecisionStatus;
  reason_summary: string;
  budget_policy: string;
  estimated_cost: { total: number; budget_limit: number };
  estimated_time: { total_sec: number; time_limit_sec: number };
  affected_scenes: string[];
  mandatory_scenes: string[];
  optional_scenes: string[];
  skipped_scenes: string[];
  warnings: string[];
  project_id?: string;
  episode_id?: string;
}

interface RebuildDecisionPanelProps {
  decision: RebuildDecision | null;
  loading?: boolean;
  onApprove?: (decision: RebuildDecision) => void;
  onCancel?: () => void;
}

function statusBadge(decision: DecisionStatus) {
  const map: Record<DecisionStatus, string> = {
    allow: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    downgrade: "border-amber-500/30 bg-amber-500/10 text-amber-200",
    block: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  };
  return map[decision] ?? "border-white/15 bg-white/5 text-white/70";
}

function SceneList({ ids, label }: { ids: string[]; label: string }) {
  if (!ids.length) return null;
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-widest text-white/40">{label}</p>
      <div className="flex flex-wrap gap-2">
        {ids.map((id) => (
          <span
            key={id}
            className="rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-xs text-white/70"
          >
            {id}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function RebuildDecisionPanel({
  decision,
  loading,
  onApprove,
  onCancel,
}: RebuildDecisionPanelProps) {
  const t = useT();

  if (loading) {
    return (
      <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
        <p className="text-sm text-white/50">{t("rebuild_decision_loading")}</p>
      </div>
    );
  }

  if (!decision) {
    return (
      <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
        <p className="text-sm text-white/50">{t("rebuild_no_decision")}</p>
      </div>
    );
  }

  const canApprove = decision.decision !== "block";

  return (
    <div className="space-y-4 rounded-3xl border border-white/10 bg-white/5 p-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold">{t("rebuild_decision_title")}</h3>
        <span className={`rounded-full border px-3 py-0.5 text-xs font-medium ${statusBadge(decision.decision)}`}>
          {decision.decision === "allow"
            ? t("rebuild_status_allow")
            : decision.decision === "downgrade"
            ? t("rebuild_status_downgrade")
            : t("rebuild_status_block")}
        </span>
      </div>

      {/* Strategy + Policy */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-white/40">{t("rebuild_strategy")}</p>
          <p className="font-mono text-white/80">{decision.selected_strategy}</p>
        </div>
        <div>
          <p className="text-xs text-white/40">{t("rebuild_budget_policy")}</p>
          <p className="font-mono text-white/80">{decision.budget_policy}</p>
        </div>
      </div>

      {/* Reason */}
      <div>
        <p className="text-xs text-white/40">{t("rebuild_reason")}</p>
        <p className="mt-0.5 text-sm text-white/70">{decision.reason_summary}</p>
      </div>

      {/* Cost + Time */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-white/40">{t("rebuild_estimated_cost")}</p>
          <p className="text-white/80">
            {decision.estimated_cost.total.toFixed(2)}{" "}
            <span className="text-white/40">/ {decision.estimated_cost.budget_limit}</span>
          </p>
        </div>
        <div>
          <p className="text-xs text-white/40">{t("rebuild_estimated_time")}</p>
          <p className="text-white/80">
            {decision.estimated_time.total_sec.toFixed(0)}s{" "}
            <span className="text-white/40">/ {decision.estimated_time.time_limit_sec}s</span>
          </p>
        </div>
      </div>

      {/* Scene lists */}
      <SceneList ids={decision.mandatory_scenes} label={t("rebuild_mandatory_scenes")} />
      <SceneList ids={decision.optional_scenes} label={t("rebuild_optional_scenes")} />
      <SceneList ids={decision.skipped_scenes} label={t("rebuild_skipped_scenes")} />

      {/* Warnings */}
      {decision.warnings.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-amber-400/70">
            {t("rebuild_warnings")}
          </p>
          <ul className="mt-1 space-y-1">
            {decision.warnings.map((w, i) => (
              <li key={i} className="text-xs text-amber-200/80">
                • {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-1">
        {canApprove && onApprove && (
          <button
            onClick={() => onApprove(decision)}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
          >
            {t("rebuild_approve_btn")}
          </button>
        )}
        {onCancel && (
          <button
            onClick={onCancel}
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-white/70 transition hover:border-white/30"
          >
            {t("rebuild_cancel_btn")}
          </button>
        )}
      </div>
    </div>
  );
}
