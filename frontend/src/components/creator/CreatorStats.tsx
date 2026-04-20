"use client";

interface Props {
  analytics: any;
}

export default function CreatorStats({ analytics }: Props) {
  const stats = [
    {
      label: "Total Avatars",
      value: analytics?.avatar_count ?? analytics?.total_avatars ?? "—",
    },
    {
      label: "Total Earnings (USD)",
      value:
        analytics?.total_earnings_usd != null
          ? `$${Number(analytics.total_earnings_usd).toFixed(2)}`
          : "—",
    },
    {
      label: "Rank Score",
      value:
        analytics?.rank_score != null
          ? Number(analytics.rank_score).toFixed(2)
          : "—",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="flex flex-col gap-1 rounded-2xl border border-neutral-800 bg-neutral-900 p-5"
        >
          <p className="text-xs text-neutral-500">{stat.label}</p>
          <p className="text-2xl font-bold text-neutral-100">{stat.value}</p>
        </div>
      ))}
    </div>
  );
}
