"use client";

import { useT } from "@/src/i18n/useT";

type MemoryEvent = {
  id: string;
  memory_type: string;
  payload_json?: string | null;
  recorded_at: string;
};

export default function FactoryMemoryPanel({ events }: { events: MemoryEvent[] }) {
  const t = useT();

  if (!events.length) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-white/50">
        {t("factory_memory_title")}
      </h3>
      <div className="space-y-2">
        {events.map((ev) => (
          <div key={ev.id} className="rounded-2xl border border-white/10 bg-white/5 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-white/80">{ev.memory_type}</span>
              <span className="text-[10px] text-white/40">{new Date(ev.recorded_at).toLocaleString()}</span>
            </div>
            {ev.payload_json && (
              <pre className="mt-2 overflow-x-auto rounded bg-black/30 p-2 text-[10px] text-white/60">
                {JSON.stringify(JSON.parse(ev.payload_json), null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
