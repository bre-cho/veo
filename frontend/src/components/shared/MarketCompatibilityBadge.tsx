"use client";

interface Props {
  compatible: boolean;
  marketCode: string;
}

export default function MarketCompatibilityBadge({ compatible, marketCode }: Props) {
  return compatible ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-green-900/50 px-3 py-0.5 text-xs font-medium text-green-400">
      ✓ Compatible with {marketCode}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-900/50 px-3 py-0.5 text-xs font-medium text-red-400">
      ⚠ Market mismatch
    </span>
  );
}
