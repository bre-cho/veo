"use client";

interface Props {
  creatorId: string;
  store: any;
}

export default function CreatorStoreHeader({ creatorId, store }: Props) {
  const displayName = store?.name ?? creatorId;

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-900/40 text-4xl">
        🧑‍🎨
      </div>
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold text-neutral-100">{displayName}</h2>
        <p className="text-xs text-neutral-500">Creator ID: {creatorId}</p>
        {store?.total_avatars != null && (
          <p className="text-xs text-neutral-400">
            {store.total_avatars} avatar{store.total_avatars !== 1 ? "s" : ""} in store
          </p>
        )}
      </div>
    </div>
  );
}
