"use client";

import { useMemo, useState } from "react";
import {
  getMarketplaceTemplates,
  marketplaceCategories,
  recommendTemplates,
  type MarketplaceTemplate
} from "@/lib/marketplace/templates";

const templates = getMarketplaceTemplates();

function goalLabel(goal: string) {
  if (goal.toLowerCase().includes("đăng ký")) return "signup";
  if (goal.toLowerCase().includes("lead") || goal.toLowerCase().includes("đặt lịch")) return "lead";
  if (goal.toLowerCase().includes("bán") || goal.toLowerCase().includes("chuyển đổi")) return "conversion";
  return "awareness";
}

export function MarketplaceV3() {
  const [category, setCategory] = useState("All");
  const [selected, setSelected] = useState<MarketplaceTemplate | null>(templates[0] || null);
  const [product, setProduct] = useState("mỹ phẩm serum dưỡng da");
  const [goal, setGoal] = useState("lead");

  const filtered = useMemo(() => {
    if (category === "All") return templates;
    return templates.filter((item) => item.category === category);
  }, [category]);

  const recommended = useMemo(() => recommendTemplates(product, goal), [product, goal]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#1e293b_0%,#020617_45%,#020617_100%)] text-white">
      <section className="mx-auto max-w-7xl px-5 py-12 md:py-16">
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[32px] border border-white/10 bg-white/[0.05] p-8 shadow-[0_24px_80px_rgba(2,6,23,0.45)]">
            <div className="inline-flex rounded-full border border-[#F59E0B]/30 bg-[#F59E0B]/10 px-4 py-2 text-xs font-black uppercase tracking-[0.24em] text-[#FCD34D]">
              Template Marketplace V3
            </div>
            <h1 className="mt-5 max-w-4xl text-4xl font-black leading-tight text-white md:text-6xl">
              Chọn template đúng ngành để poster bán nhanh hơn ngay từ vòng test đầu.
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-8 text-slate-300 md:text-lg">
              Không chỉ là thư viện mẫu. Đây là lớp chọn chiến lược visual theo ngành, mục tiêu và hành vi khách hàng, có preview lớn và AI recommend ngay trên trang.
            </p>
          </div>

          <div className="rounded-[32px] border border-[#38BDF8]/20 bg-[#07111F]/85 p-7 shadow-[0_24px_70px_rgba(14,165,233,0.15)] backdrop-blur">
            <p className="text-xs font-black uppercase tracking-[0.24em] text-[#7DD3FC]">AI Recommend</p>
            <div className="mt-5 grid gap-3">
              <input
                value={product}
                onChange={(event) => setProduct(event.target.value)}
                placeholder="Nhập sản phẩm hoặc ngành..."
                className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#38BDF8]/60"
              />
              <select
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                className="rounded-2xl border border-white/10 bg-[#07111F] px-4 py-3 text-sm text-white outline-none focus:border-[#38BDF8]/60"
              >
                <option value="conversion">Conversion</option>
                <option value="lead">Lead</option>
                <option value="trust">Trust</option>
                <option value="awareness">Awareness</option>
                <option value="signup">Signup</option>
              </select>
            </div>

            <div className="mt-5 space-y-3">
              {recommended.map((item, index) => (
                <button
                  key={item.id}
                  onClick={() => setSelected(item)}
                  className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-4 text-left transition hover:border-[#38BDF8]/40 hover:bg-white/[0.07]"
                >
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-[#7DD3FC]">Top {index + 1}</p>
                    <p className="mt-1 font-bold text-white">{item.name}</p>
                  </div>
                  <div className="rounded-full bg-[#38BDF8]/10 px-3 py-1 text-sm font-black text-[#7DD3FC]">
                    {item.recommendScore}/100
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <section className="mt-8 flex flex-wrap gap-3">
          {marketplaceCategories.map((item) => (
            <button
              key={item}
              onClick={() => setCategory(item)}
              className={`rounded-full px-4 py-2 text-sm font-bold transition ${
                item === category
                  ? "bg-[#F59E0B] text-slate-950"
                  : "border border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/[0.08]"
              }`}
            >
              {item}
            </button>
          ))}
        </section>

        <section className="mt-8 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="grid gap-5 md:grid-cols-2">
            {filtered.map((item) => (
              <article
                key={item.id}
                onClick={() => setSelected(item)}
                className="group cursor-pointer overflow-hidden rounded-[28px] border border-white/10 bg-white/[0.04] transition hover:-translate-y-1 hover:border-[#F59E0B]/50 hover:shadow-[0_20px_60px_rgba(245,158,11,0.18)]"
              >
                <div className="relative h-[240px] overflow-hidden bg-slate-900">
                  <img src={item.image} alt={item.name} className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
                  <div className="absolute left-4 top-4 rounded-full bg-black/55 px-3 py-1 text-xs font-black uppercase tracking-[0.18em] text-[#FCD34D]">
                    {item.platform}
                  </div>
                  <div className="absolute bottom-4 right-4 rounded-full bg-[#38BDF8]/90 px-3 py-1 text-sm font-black text-slate-950">
                    {item.score}/100
                  </div>
                </div>
                <div className="p-5">
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{item.logic}</p>
                  <h2 className="mt-3 text-2xl font-black leading-tight text-white">{item.name}</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{item.description}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {item.tags.map((tag) => (
                      <span key={tag} className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs font-bold text-slate-200">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="mt-5 flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Mục tiêu</p>
                      <p className="mt-1 text-sm font-semibold text-slate-200">{item.goal}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Giá</p>
                      <p className="mt-1 text-xl font-black text-[#FCD34D]">{item.priceLabel}</p>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <aside className="sticky top-6 h-fit rounded-[30px] border border-white/10 bg-[#050B16]/90 p-6 shadow-[0_24px_80px_rgba(2,6,23,0.55)]">
            {selected ? (
              <>
                <div className="overflow-hidden rounded-[24px] border border-white/10 bg-slate-950">
                  <img src={selected.image} alt={selected.name} className="h-[320px] w-full object-cover" />
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-slate-400">
                  <span>{selected.category}</span>
                  <span className="text-slate-600">/</span>
                  <span>{selected.platform}</span>
                  <span className="text-slate-600">/</span>
                  <span>{goalLabel(selected.goal)}</span>
                </div>
                <h2 className="mt-3 text-3xl font-black leading-tight text-white">{selected.name}</h2>
                <p className="mt-3 text-sm leading-7 text-slate-300">{selected.description}</p>

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-[#38BDF8]/20 bg-[#38BDF8]/10 p-4">
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-[#7DD3FC]">Winner Fit</p>
                    <p className="mt-2 text-3xl font-black text-white">{selected.score}/100</p>
                  </div>
                  <div className="rounded-2xl border border-[#F59E0B]/20 bg-[#F59E0B]/10 p-4">
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-[#FCD34D]">Logic</p>
                    <p className="mt-2 text-sm font-semibold leading-6 text-white">{selected.logic}</p>
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  {selected.tags.map((tag) => (
                    <span key={tag} className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs font-bold text-slate-200">
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Prompt direction</p>
                  <p className="mt-3 text-sm leading-7 text-slate-200">{selected.prompt}</p>
                </div>

                <div className="mt-6 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Giá gói</p>
                    <p className="mt-1 text-2xl font-black text-[#FCD34D]">{selected.priceLabel}</p>
                  </div>
                  <a
                    href={`/marketplace?template=${selected.slug}`}
                    className="rounded-2xl bg-gradient-to-r from-[#F97316] to-[#F59E0B] px-5 py-3 text-sm font-black text-white shadow-[0_0_30px_rgba(249,115,22,0.28)] transition hover:brightness-110"
                  >
                    Xem gói
                  </a>
                </div>
              </>
            ) : null}
          </aside>
        </section>
      </section>
    </main>
  );
}