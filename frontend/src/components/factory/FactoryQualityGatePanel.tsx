"use client";

import { useT } from "@/src/i18n/useT";

type Gate = {
  gate_name: string;
  stage_name: string;
  result: string;
  score?: number | null;
  threshold?: number | null;
  action_taken: string;
  detail?: string | null;
};

const RESULT_COLORS: Record<string, string> = {
  pass: "text-green-300",
  fail: "text-red-300",
  warn: "text-yellow-300",
  skip: "text-white/40",
};

export default function FactoryQualityGatePanel({ gates }: { gates: Gate[] }) {
  const t = useT();

  if (!gates.length) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
        {t("factory_gate_title")}
      </h3>
      <div className="overflow-x-auto rounded-2xl border border-white/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-xs text-white/40">
              <th className="px-4 py-2 text-left">{t("factory_gate_name")}</th>
              <th className="px-4 py-2 text-left">{t("factory_stage")}</th>
              <th className="px-4 py-2 text-left">{t("factory_gate_result")}</th>
              <th className="px-4 py-2 text-right">{t("factory_gate_score")}</th>
              <th className="px-4 py-2 text-right">{t("factory_gate_threshold")}</th>
              <th className="px-4 py-2 text-left">{t("factory_gate_action")}</th>
            </tr>
          </thead>
          <tbody>
            {gates.map((g, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                <td className="px-4 py-2 font-mono text-xs">{g.gate_name}</td>
                <td className="px-4 py-2 text-xs text-white/60">{g.stage_name}</td>
                <td className={["px-4 py-2 font-semibold", RESULT_COLORS[g.result] ?? ""].join(" ")}>
                  {g.result.toUpperCase()}
                </td>
                <td className="px-4 py-2 text-right">{g.score ?? "—"}</td>
                <td className="px-4 py-2 text-right text-white/60">{g.threshold ?? "—"}</td>
                <td className="px-4 py-2 text-xs text-white/60">{g.action_taken}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
