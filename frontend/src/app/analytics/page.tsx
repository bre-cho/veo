"use client";

import { useEffect, useState } from "react";
import { getMarketplaceTrending } from "@/src/lib/api";
import { useT } from "@/src/i18n/useT";

export default function AnalyticsPage() {
  const t = useT();
  const [trending, setTrending] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMarketplaceTrending()
      .then((res) => setTrending(res.trending ?? []))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 p-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <h1 className="text-3xl font-semibold">{t("analytics_title")}</h1>
          <p className="text-neutral-400 mt-1">Marketplace performance insights.</p>
        </div>

        <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Trending Avatars (7 days)</h2>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          {loading ? (
            <p className="text-neutral-500">Loading trending data…</p>
          ) : trending.length === 0 ? (
            <p className="text-neutral-400">No trending data yet. Avatars need usage events to rank.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-800">
                    <th className="text-left py-2 pr-4 text-neutral-500 font-medium">Rank</th>
                    <th className="text-left py-2 pr-4 text-neutral-500 font-medium">Avatar</th>
                    <th className="text-right py-2 pr-4 text-neutral-500 font-medium">Uses (7d)</th>
                    <th className="text-right py-2 text-neutral-500 font-medium">Trending Score</th>
                  </tr>
                </thead>
                <tbody>
                  {trending.map((item, idx) => (
                    <tr key={item.avatar_id} className="border-b border-neutral-800/50">
                      <td className="py-3 pr-4 text-neutral-500">#{idx + 1}</td>
                      <td className="py-3 pr-4">
                        <span className="text-neutral-100">{item.name}</span>
                        <span className="text-neutral-500 ml-2 text-xs">{item.avatar_id}</span>
                      </td>
                      <td className="py-3 pr-4 text-right text-neutral-300">{item.usage_count_7d}</td>
                      <td className="py-3 text-right text-emerald-400">{Number(item.trending_score).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
