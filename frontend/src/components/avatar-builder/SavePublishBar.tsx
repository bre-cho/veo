"use client";

import { useState } from "react";
import { publishAvatar } from "@/src/lib/api";

interface Props {
  avatarId: string;
  onPublished?: () => void;
}

export default function SavePublishBar({ avatarId, onPublished }: Props) {
  const [publishing, setPublishing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handlePublish() {
    setPublishing(true);
    setError(null);
    setStatus(null);
    try {
      const res = await publishAvatar(avatarId);
      setStatus(res.status ?? "published");
      onPublished?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-neutral-800 bg-neutral-900 px-5 py-4">
      <button
        className="rounded-xl border border-neutral-700 bg-neutral-800 px-5 py-2 text-sm font-semibold text-neutral-300 transition hover:bg-neutral-700"
        onClick={() => setStatus("draft saved")}
      >
        Save Draft
      </button>

      <button
        onClick={handlePublish}
        disabled={publishing}
        className="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
      >
        {publishing ? "Publishing…" : "Publish"}
      </button>

      {status && <span className="text-xs text-green-400">{status} ✓</span>}
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}
