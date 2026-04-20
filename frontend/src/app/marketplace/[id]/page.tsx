"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getAvatar } from "@/src/lib/api";

interface Props {
  params: Promise<{ id: string }>;
}

export default function AvatarDetailPage({ params }: Props) {
  const { id } = use(params);
  const [avatar, setAvatar] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getAvatar(id)
      .then(setAvatar)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <div className="mx-auto max-w-3xl px-6 py-12">
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

        {avatar && (
          <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center gap-6 rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-indigo-900/30 text-5xl">
                🎭
              </div>
              <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-bold text-neutral-100">{avatar.name}</h1>
                <div className="flex flex-wrap gap-2">
                  {avatar.is_featured && (
                    <span className="rounded-full bg-yellow-900/40 px-3 py-0.5 text-xs font-semibold text-yellow-400">
                      ⭐ Featured
                    </span>
                  )}
                  {avatar.is_published && (
                    <span className="rounded-full bg-green-900/40 px-3 py-0.5 text-xs font-semibold text-green-400">
                      ✓ Published
                    </span>
                  )}
                  {!avatar.is_published && (
                    <span className="rounded-full bg-neutral-700 px-3 py-0.5 text-xs font-semibold text-neutral-400">
                      Draft
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Details */}
            <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
              <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-neutral-400">
                Details
              </h2>
              <dl className="grid grid-cols-2 gap-4">
                {[
                  { label: "Role", value: avatar.role_id },
                  { label: "Niche", value: avatar.niche_code },
                  { label: "Market", value: avatar.market_code },
                  { label: "Creator", value: avatar.creator_id },
                ].map(
                  ({ label, value }) =>
                    value && (
                      <div key={label} className="flex flex-col gap-0.5">
                        <dt className="text-xs text-neutral-500">{label}</dt>
                        <dd className="text-sm font-medium text-neutral-100">{value}</dd>
                      </div>
                    )
                )}
              </dl>
            </div>

            {/* Pricing */}
            {avatar.marketplace_item && (
              <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
                <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-neutral-400">
                  Pricing
                </h2>
                <div className="flex items-center gap-4">
                  <span className="text-2xl font-bold text-neutral-100">
                    {avatar.marketplace_item.is_free
                      ? "Free"
                      : avatar.marketplace_item.price_usd != null
                      ? `$${avatar.marketplace_item.price_usd}`
                      : "—"}
                  </span>
                  {avatar.marketplace_item.license_type && (
                    <span className="rounded-full bg-neutral-700 px-3 py-0.5 text-xs text-neutral-300">
                      {avatar.marketplace_item.license_type}
                    </span>
                  )}
                </div>
                {avatar.marketplace_item.rating_avg != null && (
                  <p className="mt-2 text-xs text-neutral-400">
                    ★ {Number(avatar.marketplace_item.rating_avg).toFixed(1)} (
                    {avatar.marketplace_item.rating_count} reviews)
                  </p>
                )}
              </div>
            )}

            {/* Action */}
            <Link
              href="/production-studio"
              className="inline-flex items-center justify-center rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
            >
              Use in Production →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
