"use client";

import { useEffect, useState } from "react";
import { listAvatars } from "@/src/lib/api";

export default function MarketplacePage() {
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [marketCode, setMarketCode] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listAvatars({ market_code: marketCode || undefined, role_id: roleFilter || undefined })
      .then((res) => setItems(res.items ?? []))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [marketCode, roleFilter]);

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <h1 className="text-3xl font-semibold">Avatar Marketplace</h1>
          <p className="text-neutral-400 mt-1">Browse and discover AI avatars for your content.</p>
        </div>

        <div className="flex gap-3 flex-wrap">
          <input
            value={marketCode}
            onChange={(e) => setMarketCode(e.target.value)}
            placeholder="Filter by market (e.g. US)"
            className="rounded-xl bg-neutral-900 border border-neutral-800 px-4 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-600"
          />
          <input
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            placeholder="Filter by role ID"
            className="rounded-xl bg-neutral-900 border border-neutral-800 px-4 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-600"
          />
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        {loading ? (
          <p className="text-neutral-500">Loading avatars…</p>
        ) : items.length === 0 ? (
          <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-8 text-center">
            <p className="text-neutral-400">No avatars found. Adjust filters or add avatars via the Builder.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {items.map((avatar) => (
              <div
                key={avatar.id}
                className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5 space-y-3 hover:border-neutral-600 transition-colors"
              >
                <div className="h-16 w-16 rounded-full bg-neutral-800 flex items-center justify-center text-2xl">
                  🎭
                </div>
                <div>
                  <p className="font-semibold text-neutral-100 truncate">{avatar.name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {avatar.role_id || "No role"} · {avatar.niche_code || "General"}
                  </p>
                  {avatar.market_code && (
                    <span className="inline-block mt-1 text-xs bg-neutral-800 text-neutral-400 px-2 py-0.5 rounded-full">
                      {avatar.market_code}
                    </span>
                  )}
                </div>
                {avatar.marketplace_item && (
                  <p className="text-sm text-emerald-400">
                    {avatar.marketplace_item.is_free ? "Free" : `$${avatar.marketplace_item.price_usd ?? "—"}`}
                    {avatar.marketplace_item.download_count > 0 && (
                      <span className="text-neutral-500 ml-2">{avatar.marketplace_item.download_count} downloads</span>
                    )}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
