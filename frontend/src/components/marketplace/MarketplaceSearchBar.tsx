"use client";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export default function MarketplaceSearchBar({ value, onChange, placeholder }: Props) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-neutral-700 bg-neutral-800 px-3 py-2">
      <span className="text-base">🔍</span>
      <input
        className="flex-1 bg-transparent text-sm text-neutral-100 outline-none placeholder:text-neutral-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? "Search avatars…"}
      />
      {value && (
        <button
          onClick={() => onChange("")}
          className="text-xs text-neutral-500 transition hover:text-neutral-300"
        >
          ✕
        </button>
      )}
    </div>
  );
}
