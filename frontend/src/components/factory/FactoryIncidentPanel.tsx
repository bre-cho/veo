"use client";

import { useT } from "@/src/i18n/useT";

export function FactoryIncidentPanel({ run }: { run: any }) {
  const t = useT();
  const timeline = run?.timeline || [];
  const incidents = timeline.filter((item: any) => item.status === "failed" || item.status === "blocked");

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h2 className="text-lg font-semibold">{t("factory.incidentTitle")}</h2>
      {!incidents.length ? <p className="mt-2 text-sm text-white/60">Khong co su co dang mo.</p> : null}
      <div className="mt-3 space-y-2">
        {incidents.map((item: any) => (
          <div key={item.id} className="rounded-xl border border-red-400/20 bg-red-500/5 p-3 text-sm">
            <p className="font-semibold text-red-200">{item.stage}</p>
            <p className="text-red-100/80">{item.message || item.event_type}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
