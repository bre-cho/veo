"use client";

import Link from "next/link";

interface Props {
  items: any[];
  loading?: boolean;
}

export default function AvatarCardGrid({ items, loading }: Props) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="h-40 animate-pulse rounded-2xl border border-neutral-800 bg-neutral-900"
          />
        ))}
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-8 text-center">
        <p className="text-sm text-neutral-500">No avatars found.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
      {items.map((item) => (
        <Link
          key={item.id}
          href={`/marketplace/${item.id}`}
          className="group flex flex-col gap-3 rounded-2xl border border-neutral-800 bg-neutral-900 p-4 transition hover:border-indigo-700 hover:bg-neutral-800"
        >
          <div className="flex h-16 w-full items-center justify-center rounded-xl bg-indigo-900/20 text-3xl">
            🎭
          </div>

          <div className="flex flex-col gap-1">
            <p className="truncate text-sm font-semibold text-neutral-100 group-hover:text-indigo-300">
              {item.name}
            </p>

            <div className="flex flex-wrap gap-1">
              {item.role_id && (
                <span className="rounded-full bg-indigo-900/50 px-2 py-0.5 text-[10px] text-indigo-300">
                  {item.role_id}
                </span>
              )}
              {item.niche_code && (
                <span className="rounded-full bg-purple-900/50 px-2 py-0.5 text-[10px] text-purple-300">
                  {item.niche_code}
                </span>
              )}
              {item.market_code && (
                <span className="rounded-full bg-neutral-700 px-2 py-0.5 text-[10px] text-neutral-400">
                  {item.market_code}
                </span>
              )}
            </div>

            {item.marketplace_item && (
              <p className="text-xs text-green-400">
                {item.marketplace_item.is_free
                  ? "Free"
                  : item.marketplace_item.price_usd != null
                  ? `$${item.marketplace_item.price_usd}`
                  : ""}
              </p>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
