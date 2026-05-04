import { ArrowRight, Sparkles } from "lucide-react";

export function HomeHeroClean() {
  return (
    <section className="relative">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(37,99,235,.32),transparent_34%),radial-gradient(circle_at_84%_16%,rgba(245,158,11,.26),transparent_32%)]" />

      <div className="relative mx-auto grid min-h-[calc(100vh-86px)] max-w-7xl items-center gap-12 px-6 py-14 lg:grid-cols-[0.92fr_1.08fr]">
        <div className="max-w-2xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm font-black text-amber-200">
            <Sparkles className="h-4 w-4" />
            AI Poster Ads System
          </div>

          <h1 className="text-5xl font-black leading-[1.02] tracking-tight text-white md:text-7xl">
            Tạo poster quảng cáo
            <span className="block bg-gradient-to-r from-amber-200 via-white to-blue-200 bg-clip-text text-transparent">
              nhìn là muốn mua
            </span>
          </h1>

          <p className="mt-6 text-lg leading-8 text-slate-300">
            Nhập sản phẩm, AI tạo poster bán hàng theo ngành, theo mục tiêu, theo nền tảng TikTok, Meta, Facebook, Zalo.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <a
              href="/factory"
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-7 py-4 font-black text-white shadow-[0_0_42px_rgba(245,158,11,.45)] transition hover:-translate-y-1"
            >
              Tạo poster ngay
              <ArrowRight className="h-5 w-5" />
            </a>

            <a
              href="/templates"
              className="inline-flex rounded-2xl border border-white/10 bg-white/[.06] px-7 py-4 font-black text-white transition hover:bg-white/[.1]"
            >
              Xem mẫu đẹp
            </a>
          </div>

          <div className="mt-8 flex flex-wrap gap-3 text-sm font-bold text-slate-300">
            <span className="rounded-full border border-white/10 bg-white/[.05] px-4 py-2">Poster 4:5 / 1:1 / 9:16</span>
            <span className="rounded-full border border-white/10 bg-white/[.05] px-4 py-2">Đa ngành nghề</span>
            <span className="rounded-full border border-white/10 bg-white/[.05] px-4 py-2">Sẵn sàng chạy ads</span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[620px]">
          <div className="absolute -inset-8 rounded-[3rem] bg-gradient-to-r from-orange-500/30 via-amber-300/20 to-blue-500/25 blur-3xl" />

          <div className="relative rounded-[2rem] border border-amber-300/40 bg-white/[.06] p-3 shadow-[0_0_80px_rgba(245,158,11,.36)] backdrop-blur-xl">
            <img
              src="/hero/best-poster.png"
              alt="Poster quảng cáo đẹp nhất được tạo bởi AI Ads Factory"
              className="aspect-[4/5] w-full rounded-[1.5rem] object-cover"
            />

            <div className="absolute left-6 top-6 rounded-full bg-black/65 px-4 py-2 text-sm font-black text-amber-300 backdrop-blur">
              Best Output · Hero Poster
            </div>
          </div>

          <p className="mt-4 text-center text-sm font-bold text-slate-400">
            Đây là vị trí chèn poster đẹp nhất của hệ thống.
          </p>
        </div>
      </div>
    </section>
  );
}
