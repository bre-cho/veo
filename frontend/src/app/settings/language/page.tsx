"use client";

import { useEffect, useState } from "react";
import { getMetaMarketProfiles, switchCountry } from "@/src/lib/api";

export default function LanguageSettingsPage() {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [switchResult, setSwitchResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    getMetaMarketProfiles()
      .then((res) => setProfiles(Array.isArray(res) ? res : []))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleSwitch(marketCode: string) {
    setSwitching(true);
    setError(null);
    try {
      const res = await switchCountry(marketCode);
      setSwitchResult(res);
      setSelected(marketCode);
    } catch (err) {
      setError(String(err));
    } finally {
      setSwitching(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 p-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl font-semibold">Language & Region</h1>
          <p className="text-neutral-400 mt-1">Switch your market profile to localize avatar and template recommendations.</p>
        </div>

        {switchResult && (
          <div className="rounded-2xl bg-neutral-900 border border-emerald-700 p-4 flex items-center gap-3">
            <span className="text-emerald-400">✓</span>
            <span className="text-neutral-200">
              Switched to <strong>{switchResult.country_name}</strong>
              {switchResult.language_code && ` · ${switchResult.language_code.toUpperCase()}`}
              {switchResult.currency_code && ` · ${switchResult.currency_code}`}
              {switchResult.rtl && " · RTL"}
            </span>
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}

        {loading ? (
          <p className="text-neutral-500">Loading market profiles…</p>
        ) : profiles.length === 0 ? (
          <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-8 text-center">
            <p className="text-neutral-400">No market profiles configured yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {profiles.map((p) => (
              <button
                key={p.market_code}
                onClick={() => handleSwitch(p.market_code)}
                disabled={switching}
                className={`rounded-2xl border p-4 text-left transition-colors hover:border-neutral-600 disabled:opacity-50 ${
                  selected === p.market_code
                    ? "border-emerald-600 bg-neutral-900"
                    : "border-neutral-800 bg-neutral-900"
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium text-neutral-100">{p.country_name}</p>
                  {selected === p.market_code && <span className="text-emerald-400 text-xs">Active</span>}
                </div>
                <p className="text-xs text-neutral-500 mt-1">
                  {p.market_code}
                  {p.language_code && ` · ${p.language_code.toUpperCase()}`}
                  {p.currency_code && ` · ${p.currency_code}`}
                  {p.rtl && " · RTL"}
                </p>
                {p.preferred_niches?.length > 0 && (
                  <p className="text-xs text-neutral-600 mt-1 truncate">
                    Niches: {p.preferred_niches.slice(0, 3).join(", ")}
                  </p>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
