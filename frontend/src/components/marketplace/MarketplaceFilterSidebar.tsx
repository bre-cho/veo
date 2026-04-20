"use client";

interface Props {
  marketCode: string;
  roleId: string;
  onMarketChange: (v: string) => void;
  onRoleChange: (v: string) => void;
}

export default function MarketplaceFilterSidebar({
  marketCode,
  roleId,
  onMarketChange,
  onRoleChange,
}: Props) {
  return (
    <aside className="flex flex-col gap-4 rounded-2xl border border-neutral-800 bg-neutral-900 p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">
        Filters
      </h3>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Market Code</span>
        <input
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={marketCode}
          onChange={(e) => onMarketChange(e.target.value)}
          placeholder="e.g. US, UK, SG"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-neutral-400">Role</span>
        <input
          className="rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-indigo-500"
          value={roleId}
          onChange={(e) => onRoleChange(e.target.value)}
          placeholder="e.g. host, presenter"
        />
      </label>

      {(marketCode || roleId) && (
        <button
          onClick={() => {
            onMarketChange("");
            onRoleChange("");
          }}
          className="rounded-lg border border-neutral-700 py-1.5 text-xs text-neutral-400 transition hover:text-neutral-200"
        >
          Clear filters
        </button>
      )}
    </aside>
  );
}
