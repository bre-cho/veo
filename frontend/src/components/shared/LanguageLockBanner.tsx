"use client";

interface Props {
  marketCode: string;
}

export default function LanguageLockBanner({ marketCode }: Props) {
  if (!marketCode) return null;

  return (
    <div className="flex items-center gap-2 rounded-xl border border-yellow-700/40 bg-yellow-900/20 px-4 py-3">
      <span className="text-base">🔒</span>
      <p className="text-sm text-yellow-300">
        Content is locked to market:{" "}
        <strong className="font-semibold">{marketCode}</strong>. Change in{" "}
        <span className="underline">Settings → Language</span>.
      </p>
    </div>
  );
}
