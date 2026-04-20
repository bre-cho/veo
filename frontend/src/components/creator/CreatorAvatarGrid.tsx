"use client";

import Link from "next/link";

interface Props {
  avatars: any[];
}

export default function CreatorAvatarGrid({ avatars }: Props) {
  if (!avatars?.length) {
    return (
      <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-6 text-center">
        <p className="text-sm text-neutral-500">No avatars in this portfolio yet.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
      {avatars.map((item) => (
        <Link
          key={item.id}
          href={`/marketplace/${item.id}`}
          className="flex flex-col gap-2 rounded-xl border border-neutral-800 bg-neutral-900 p-4 transition hover:border-indigo-700"
        >
          <div className="flex h-12 items-center justify-center text-2xl">🎭</div>
          <p className="truncate text-sm font-semibold text-neutral-100">{item.name}</p>
          <div className="flex flex-wrap gap-1">
            {item.role_id && (
              <span className="rounded-full bg-indigo-900/40 px-2 py-0.5 text-[10px] text-indigo-300">
                {item.role_id}
              </span>
            )}
            {item.is_published && (
              <span className="rounded-full bg-green-900/40 px-2 py-0.5 text-[10px] text-green-400">
                Published
              </span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
