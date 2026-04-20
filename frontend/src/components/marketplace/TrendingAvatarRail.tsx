"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { trendingAvatars } from "@/src/lib/api";

export default function TrendingAvatarRail() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    trendingAvatars(8)
      .then((res) => setItems(res.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex gap-3 overflow-x-auto pb-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-24 w-36 flex-shrink-0 animate-pulse rounded-xl bg-neutral-800"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {items.map((item, idx) => (
        <Link
          key={item.id}
          href={`/marketplace/${item.id}`}
          className="relative flex w-36 flex-shrink-0 flex-col gap-2 rounded-xl border border-neutral-800 bg-neutral-900 p-3 transition hover:border-indigo-700"
        >
          <span className="absolute right-2 top-2 rounded-full bg-yellow-500/20 px-2 py-0.5 text-[10px] font-bold text-yellow-400">
            #{idx + 1}
          </span>
          <div className="flex h-10 items-center justify-center text-2xl">🎭</div>
          <p className="truncate text-xs font-semibold text-neutral-100">{item.name}</p>
          {item.niche_code && (
            <p className="truncate text-[10px] text-neutral-500">{item.niche_code}</p>
          )}
        </Link>
      ))}
      {!items.length && (
        <p className="text-sm text-neutral-500">No trending avatars.</p>
      )}
    </div>
  );
}
