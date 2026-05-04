import { pricingPreview } from "@/lib/homepage-data";

export function PricingPreview() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-14">
      <div className="mb-8 max-w-3xl">
        <p className="text-sm font-black uppercase tracking-widest text-blue-300">SaaS money mode</p>
        <h2 className="mt-3 text-4xl font-black text-white md:text-5xl">Biến tool thành sản phẩm thuê bao</h2>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        {pricingPreview.map((plan) => (
          <article key={plan.name} className={plan.popular ? "rounded-[2rem] border border-amber-400/50 bg-gradient-to-br from-blue-950 to-[#050816] p-6 shadow-[0_0_44px_rgba(245,158,11,.34)]" : "rounded-[2rem] border border-white/10 bg-white/[.045] p-6"}>
            <h3 className="text-2xl font-black text-white">{plan.name}</h3>
            <p className="mt-4 text-5xl font-black text-white">{plan.price}</p>
            <p className="mt-3 text-slate-400">{plan.desc}</p>
            <a href="/pricing" className={plan.popular ? "mt-7 inline-flex w-full justify-center rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-6 py-4 font-black text-white" : "mt-7 inline-flex w-full justify-center rounded-2xl border border-white/10 bg-white/[.06] px-6 py-4 font-black text-white"}>{plan.cta}</a>
          </article>
        ))}
      </div>
    </section>
  );
}
