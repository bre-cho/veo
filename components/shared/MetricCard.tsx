export function MetricCard({
  label,
  value,
  desc,
  tone = "amber",
}: {
  label: string;
  value: string;
  desc: string;
  tone?: "amber" | "blue" | "green" | "purple";
}) {
  const toneClass = {
    amber: "from-orange-600 to-amber-400 text-amber-200",
    blue: "from-blue-600 to-cyan-400 text-blue-200",
    green: "from-emerald-600 to-green-400 text-emerald-200",
    purple: "from-fuchsia-600 to-violet-400 text-purple-200",
  }[tone];

  return (
    <article className="rounded-[1.5rem] border border-white/10 bg-[#050816] p-5 transition hover:-translate-y-1 hover:shadow-[0_0_36px_rgba(245,158,11,.20)]">
      <span className={`inline-flex rounded-full bg-gradient-to-r ${toneClass} px-3 py-1 text-xs font-black text-white`}>
        {label}
      </span>
      <h3 className="mt-5 text-4xl font-black text-white">{value}</h3>
      <p className="mt-3 leading-7 text-slate-400">{desc}</p>
    </article>
  );
}
