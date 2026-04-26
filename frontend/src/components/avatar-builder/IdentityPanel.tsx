"use client";

import { useState } from "react";
import { request } from "@/src/lib/api";

interface Props {
  avatarId: string;
  onSaved?: () => void;
}

export default function IdentityPanel({ avatarId, onSaved }: Props) {
  const [name, setName] = useState("");
  const [roleId, setRoleId] = useState("");
  const [nicheCode, setNicheCode] = useState("");
  const [marketCode, setMarketCode] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await request<any>("/avatar-builder/identity", {
        method: "POST",
        body: JSON.stringify({
          avatar_id: avatarId,
          name,
          role_id: roleId,
          niche_code: nicheCode,
          market_code: marketCode,
        }),
      });
      setSaved(true);
      onSaved?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-neutral-100">Identity</h3>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Name</span>
        <input
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Avatar name"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Role ID</span>
        <input
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={roleId}
          onChange={(e) => setRoleId(e.target.value)}
          placeholder="e.g. host, presenter"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Niche Code</span>
        <input
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={nicheCode}
          onChange={(e) => setNicheCode(e.target.value)}
          placeholder="e.g. beauty, tech, finance"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Market Code</span>
        <input
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={marketCode}
          onChange={(e) => setMarketCode(e.target.value)}
          placeholder="e.g. US, UK, SG"
        />
      </label>

      {error && <p className="text-xs text-red-400">{error}</p>}
      {saved && <p className="text-xs text-green-400">Identity saved ✓</p>}

      <button
        onClick={handleSave}
        disabled={saving || !name}
        className="self-start rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Luu va tiep tuc"}
      </button>
    </div>
  );
}
