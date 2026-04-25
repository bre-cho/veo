"use client";

import { useT } from "@/src/i18n/useT";

export type BudgetPolicy = "cheap" | "balanced" | "quality" | "emergency";

interface BudgetPolicySelectorProps {
  value: BudgetPolicy;
  onChange: (policy: BudgetPolicy) => void;
}

interface PolicyOption {
  key: BudgetPolicy;
  labelKey: "budget_policy_cheap" | "budget_policy_balanced" | "budget_policy_quality" | "budget_policy_emergency";
  descKey:
    | "budget_policy_description_cheap"
    | "budget_policy_description_balanced"
    | "budget_policy_description_quality"
    | "budget_policy_description_emergency";
  accent: string;
}

const POLICIES: PolicyOption[] = [
  {
    key: "cheap",
    labelKey: "budget_policy_cheap",
    descKey: "budget_policy_description_cheap",
    accent: "border-sky-500/30 bg-sky-500/5",
  },
  {
    key: "balanced",
    labelKey: "budget_policy_balanced",
    descKey: "budget_policy_description_balanced",
    accent: "border-indigo-500/30 bg-indigo-500/5",
  },
  {
    key: "quality",
    labelKey: "budget_policy_quality",
    descKey: "budget_policy_description_quality",
    accent: "border-violet-500/30 bg-violet-500/5",
  },
  {
    key: "emergency",
    labelKey: "budget_policy_emergency",
    descKey: "budget_policy_description_emergency",
    accent: "border-rose-500/30 bg-rose-500/5",
  },
];

export default function BudgetPolicySelector({ value, onChange }: BudgetPolicySelectorProps) {
  const t = useT();

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium uppercase tracking-widest text-white/40">
        {t("budget_policy_label")}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {POLICIES.map((p) => {
          const active = value === p.key;
          return (
            <button
              key={p.key}
              onClick={() => onChange(p.key)}
              className={`rounded-2xl border p-3 text-left transition ${
                active
                  ? `${p.accent} ring-1 ring-white/20`
                  : "border-white/10 bg-white/5 hover:border-white/20"
              }`}
            >
              <p className={`text-sm font-semibold ${active ? "text-white" : "text-white/70"}`}>
                {t(p.labelKey)}
              </p>
              <p className="mt-0.5 text-xs text-white/40">{t(p.descKey)}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
