"use client";

import { useState } from "react";
import { startAvatarBuilder } from "@/src/lib/api";

export default function AvatarBuilderPage() {
  const [name, setName] = useState("");
  const [roleId, setRoleId] = useState("");
  const [nicheCode, setNicheCode] = useState("");
  const [marketCode, setMarketCode] = useState("");
  const [result, setResult] = useState<{ avatar_id: string; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await startAvatarBuilder({
        name,
        role_id: roleId || undefined,
        niche_code: nicheCode || undefined,
        market_code: marketCode || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 p-8">
      <div className="mx-auto max-w-2xl space-y-8">
        <div>
          <h1 className="text-3xl font-semibold">Avatar Builder</h1>
          <p className="text-neutral-400 mt-1">Create a new avatar identity for your content.</p>
        </div>

        {result ? (
          <div className="rounded-2xl bg-neutral-900 border border-emerald-700 p-6 space-y-3">
            <p className="text-emerald-400 font-semibold text-lg">✓ Avatar Created</p>
            <p className="text-neutral-300">Name: <span className="text-white font-medium">{result.name}</span></p>
            <p className="text-neutral-400 text-sm">ID: {result.avatar_id}</p>
            <button
              onClick={() => { setResult(null); setName(""); }}
              className="mt-2 rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-700"
            >
              Build Another
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="rounded-2xl bg-neutral-900 border border-neutral-800 p-6 space-y-5">
            <div className="space-y-2">
              <label className="block text-sm text-neutral-400">Avatar Name *</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Sophia – Tech Educator"
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm text-neutral-400">Role ID</label>
              <input
                value={roleId}
                onChange={(e) => setRoleId(e.target.value)}
                placeholder="e.g. educator, presenter"
                className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="block text-sm text-neutral-400">Niche Code</label>
                <input
                  value={nicheCode}
                  onChange={(e) => setNicheCode(e.target.value)}
                  placeholder="e.g. edtech, saas"
                  className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm text-neutral-400">Market Code</label>
                <input
                  value={marketCode}
                  onChange={(e) => setMarketCode(e.target.value)}
                  placeholder="e.g. US, GB, AE"
                  className="w-full rounded-xl bg-neutral-800 border border-neutral-700 px-4 py-3 text-neutral-100 placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
                />
              </div>
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="w-full rounded-xl bg-neutral-100 text-neutral-950 font-semibold py-3 hover:bg-white disabled:opacity-50 transition-colors"
            >
              {loading ? "Creating…" : "Create Avatar"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
