"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getCreator, getCreatorStore, getCreatorEarnings } from "@/src/lib/api";
import CreatorStoreHeader from "@/src/components/creator/CreatorStoreHeader";
import CreatorStats from "@/src/components/creator/CreatorStats";
import CreatorAvatarGrid from "@/src/components/creator/CreatorAvatarGrid";
import PayoutRequestForm from "@/src/components/creator/PayoutRequestForm";

interface Props {
  params: Promise<{ id: string }>;
}

export default function CreatorProfilePage({ params }: Props) {
  const { id } = use(params);
  const [creator, setCreator] = useState<any | null>(null);
  const [store, setStore] = useState<any | null>(null);
  const [earnings, setEarnings] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([getCreator(id), getCreatorStore(id), getCreatorEarnings(id)])
      .then(([c, s, e]) => {
        setCreator(c);
        setStore(s);
        setEarnings(e);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <Link
          href="/marketplace"
          className="mb-6 inline-flex items-center gap-1 text-sm text-neutral-400 transition hover:text-neutral-200"
        >
          ← Back to Marketplace
        </Link>

        {loading && (
          <div className="flex h-64 items-center justify-center rounded-2xl border border-neutral-800 bg-neutral-900">
            <p className="text-sm text-neutral-500">Loading…</p>
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-900/40 bg-neutral-900 p-6">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {!loading && !error && (
          <div className="flex flex-col gap-6">
            <CreatorStoreHeader creatorId={id} store={store} />

            <CreatorStats
              analytics={{
                avatar_count: store?.total_avatars,
                total_earnings_usd: store?.total_earnings_usd,
                rank_score: creator?.rank_score,
              }}
            />

            {store?.avatars?.length > 0 && (
              <div>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-400">
                  Top Avatars
                </h2>
                <CreatorAvatarGrid avatars={store.avatars} />
              </div>
            )}

            <PayoutRequestForm creatorId={id} />

            {earnings && (
              <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
                <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-neutral-400">
                  Earnings Summary
                </h2>
                <pre className="overflow-x-auto text-xs text-neutral-400">
                  {JSON.stringify(earnings, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
