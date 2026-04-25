"use client";

import React from "react";
import { useT } from "@/src/i18n/useT";

export type GovernanceOrchestrationControlPanelProps = {
  onPause: (reason: string) => Promise<void>;
  onResume: () => Promise<void>;
  onCancel: (reason: string) => Promise<void>;
};

export default function GovernanceOrchestrationControlPanel({
  onPause,
  onResume,
  onCancel,
}: GovernanceOrchestrationControlPanelProps) {
  const t = useT();
  const [reason, setReason] = React.useState("");

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900">{t("governance_orchestration_title")}</h3>
      <p className="mt-1 text-sm text-slate-500">{t("governance_orchestration_desc")}</p>

      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="mt-4 min-h-[96px] w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
        placeholder={t("governance_reason_placeholder")}
      />

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => onPause(reason || t("governance_paused_default"))}
          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
        >
          {t("governance_pause")}
        </button>

        <button
          type="button"
          onClick={() => onResume()}
          className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
        >
          {t("governance_resume")}
        </button>

        <button
          type="button"
          onClick={() => onCancel(reason || t("governance_canceled_default"))}
          className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-medium text-white"
        >
          {t("cancel")}
        </button>
      </div>
    </section>
  );
}
