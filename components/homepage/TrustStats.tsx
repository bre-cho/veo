import { trustStats } from "@/lib/homepage-data";

export function TrustStats() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-8">
      <div className="grid gap-4 md:grid-cols-4">
        {trustStats.map((item) => (
          <div key={item.label} className="rounded-[1.5rem] border border-white/10 bg-white/[.045] p-5">
            <p className="text-sm font-black uppercase tracking-widest text-blue-300">{item.label}</p>
            <h3 className="mt-3 text-4xl font-black text-white">{item.value}</h3>
            <p className="mt-2 text-slate-400">{item.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
