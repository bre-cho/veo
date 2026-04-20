"use client";

import { useEffect, useState } from "react";
import { getAvatar } from "@/src/lib/api";

interface Props {
  avatarId: string;
}

export default function AvatarPreviewStage({ avatarId }: Props) {
  const [avatar, setAvatar] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!avatarId) return;
    setLoading(true);
    getAvatar(avatarId)
      .then(setAvatar)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [avatarId]);

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center rounded-2xl border border-neutral-800 bg-neutral-900">
        <span className="text-sm text-neutral-500">Loading preview…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-900/40 bg-neutral-900 p-4">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-neutral-800 bg-neutral-900 p-8">
      <div className="flex h-24 w-24 items-center justify-center rounded-full bg-indigo-900/40 text-4xl">
        🎭
      </div>

      {avatar ? (
        <>
          <h3 className="text-lg font-semibold text-neutral-100">{avatar.name}</h3>
          <div className="flex flex-wrap justify-center gap-2">
            {avatar.role_id && (
              <span className="rounded-full bg-indigo-900/50 px-3 py-1 text-xs text-indigo-300">
                {avatar.role_id}
              </span>
            )}
            {avatar.niche_code && (
              <span className="rounded-full bg-purple-900/50 px-3 py-1 text-xs text-purple-300">
                {avatar.niche_code}
              </span>
            )}
            {avatar.market_code && (
              <span className="rounded-full bg-neutral-700 px-3 py-1 text-xs text-neutral-300">
                {avatar.market_code}
              </span>
            )}
          </div>
          <p className="text-xs text-neutral-500">
            {avatar.is_published ? "✓ Published" : "Draft – not yet published"}
          </p>
        </>
      ) : (
        <p className="text-sm text-neutral-500">No avatar data yet.</p>
      )}
    </div>
  );
}
