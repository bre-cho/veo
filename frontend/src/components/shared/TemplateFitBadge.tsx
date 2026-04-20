"use client";

interface Props {
  fitScore: number | null;
  label?: string;
}

export default function TemplateFitBadge({ fitScore, label }: Props) {
  if (fitScore === null || fitScore === undefined) {
    return (
      <span className="inline-flex rounded-full bg-neutral-700 px-2 py-0.5 text-xs text-neutral-400">
        {label ?? "Fit: —"}
      </span>
    );
  }

  const colorClass =
    fitScore >= 0.8
      ? "bg-green-900/50 text-green-400"
      : fitScore >= 0.5
      ? "bg-yellow-900/50 text-yellow-400"
      : "bg-red-900/50 text-red-400";

  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}>
      {label ?? `Fit: ${fitScore.toFixed(2)}`}
    </span>
  );
}
