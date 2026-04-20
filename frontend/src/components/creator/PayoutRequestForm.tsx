"use client";

import { useState } from "react";
import { requestPayout } from "@/src/lib/api";

interface Props {
  creatorId: string;
  onSuccess?: (result: any) => void;
}

export default function PayoutRequestForm({ creatorId, onSuccess }: Props) {
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = parseFloat(amount);
    if (isNaN(parsed) || parsed <= 0) {
      setError("Enter a valid amount greater than 0.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await requestPayout(creatorId, parsed);
      setSuccess(true);
      setAmount("");
      onSuccess?.(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 rounded-2xl border border-neutral-800 bg-neutral-900 p-5"
    >
      <h3 className="text-sm font-semibold text-neutral-100">Request Payout</h3>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Amount (USD)</span>
        <input
          type="number"
          min="0"
          step="0.01"
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.00"
        />
      </label>

      {error && <p className="text-xs text-red-400">{error}</p>}
      {success && <p className="text-xs text-green-400">Payout requested successfully ✓</p>}

      <button
        type="submit"
        disabled={loading || !amount}
        className="self-start rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
      >
        {loading ? "Requesting…" : "Request Payout"}
      </button>
    </form>
  );
}
