import { ArrowRight, Sparkles } from "lucide-react";
import { HeroPosterStack } from "@/components/homepage/HeroPosterStack";

export function HomeHero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(37,99,235,.34),transparent_32%),radial-gradient(circle_at_82%_12%,rgba(245,158,11,.24),transparent_30%)]" />
      <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-5 py-16 lg:grid-cols-[1fr_.92fr] lg:py-24">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm font-black text-amber-200">
            <Sparkles className="h-4 w-4" /> Visual proof first · SaaS conversion homepage
          </div>
          <h1 className="text-5xl font-black leading-[1.02] tracking-tight text-white md:text-7xl">
            Tạo poster quảng cáo
            <span className="block bg-gradient-to-r from-amber-200 via-white to-blue-200 bg-clip-text text-transparent">bán được hàng</span>
            trong 30 giây
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Nhập sản phẩm → AI sinh 3 mẫu ads → chấm điểm → chọn winner → sẵn sàng chạy TikTok, Meta, Facebook, Zalo.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <a href="/factory" className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-7 py-4 font-black text-white shadow-[0_0_42px_rgba(245,158,11,.45)] transition hover:-translate-y-1">
              Dùng thử miễn phí <ArrowRight className="h-5 w-5" />
            </a>
            <a href="#demo" className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[.06] px-7 py-4 font-black text-white transition hover:bg-white/[.1]">
              Xem demo poster
            </a>
          </div>
        </div>
        <HeroPosterStack />
      </div>
    </section>
  );
}
