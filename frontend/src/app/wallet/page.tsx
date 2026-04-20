"use client";

import { useState } from "react";
import { getCreatorEarnings, requestPayout } from "@/src/lib/api";

export default function WalletPage() {
  const [creatorId, setCreatorId] = useState("");
  const [earnings, setEarnings] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payoutAmount, setPayoutAmount] = useState("");
  const [payoutLoading, setPayoutLoading] = useState(false);
  const [payoutMsg, setPayoutMsg] = useState<string | null>(null);

  async function loadEarnings() {
    if (!creatorId.trim()) return;
    setLoading(true);
    setError(null);
    setEarnings(null);
    try {
      const res = await getCreatorEarnings(creatorId.trim());
      setEarnings(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handlePayout() {
    const amt = parseFloat(payoutAmount);
    if (isNaN(amt) || amt <= 0) {
      setPayoutMsg("Enter a valid amount.");
      return;
    }
    setPayoutLoading(true);
    setPayoutMsg(null);
    try {
      await requestPayout(creatorId, amt);
      setPayoutMsg("Payout requested ✓");
      setPayoutAmount("");
    } catch (e) {
      setPayoutMsg(String(e));
    } finally {
      setPayoutLoading(false);
    }
  }

  const earningsList: any[] = earnings?.earnings ?? earnings?.items ?? [];

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <div className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="mb-2 text-3xl font-bold">Wallet</h1>
        <p className="mb-8 text-sm text-neutral-400">
          View earnings and request payouts.
        </p>

        {/* Creator ID input */}
        <div className="mb-6 flex gap-3">
          <input
            className="flex-1 rounded-xl border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
            value={creatorId}
            onChange={(e) => setCreatorId(e.target.value)}
            placeholder="Enter creator ID"
            onKeyDown={(e) => e.key === "Enter" && loadEarnings()}
          />
          <button
            onClick={loadEarnings}
            disabled={loading || !creatorId.trim()}
            className="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Loading…" : "Load"}
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-900/40 bg-neutral-900 p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Earnings table */}
        {earningsList.length > 0 && (
          <div className="mb-6 overflow-x-auto rounded-2xl border border-neutral-800 bg-neutral-900">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-neutral-500">
                    Amount (USD)
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-neutral-500">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-neutral-500">
                    Payout Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-neutral-500">
                    Period
                  </th>
                </tr>
              </thead>
              <tbody>
                {earningsList.map((e: any) => (
                  <tr
                    key={e.id}
                    className="border-b border-neutral-800/50 last:border-0"
                  >
                    <td className="px-4 py-3 text-neutral-100">
                      ${Number(e.amount_usd).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-neutral-400">
                      {e.earning_type ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={[
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          e.payout_status === "paid"
                            ? "bg-green-900/40 text-green-400"
                            : e.payout_status === "pending"
                            ? "bg-yellow-900/40 text-yellow-400"
                            : "bg-neutral-700 text-neutral-400",
                        ].join(" ")}
                      >
                        {e.payout_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-500">
                      {e.period_start
                        ? `${e.period_start}${e.period_end ? ` → ${e.period_end}` : ""}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {earnings && earningsList.length === 0 && (
          <div className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900 p-6 text-center">
            <p className="text-sm text-neutral-500">No earnings records found.</p>
          </div>
        )}

        {/* Payout request */}
        {creatorId && (
          <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-5">
            <h2 className="mb-4 text-sm font-semibold text-neutral-100">Request Payout</h2>
            <div className="flex gap-3">
              <input
                type="number"
                min="0"
                step="0.01"
                className="w-40 rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                placeholder="0.00"
              />
              <button
                onClick={handlePayout}
                disabled={payoutLoading || !payoutAmount}
                className="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
              >
                {payoutLoading ? "Requesting…" : "Request"}
              </button>
            </div>
            {payoutMsg && (
              <p className="mt-2 text-xs text-neutral-300">{payoutMsg}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
