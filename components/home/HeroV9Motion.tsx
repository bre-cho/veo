import { ArrowRight, Sparkles } from "lucide-react";

export function HeroV9Motion() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#050816] text-white">
      <header className="relative z-50 border-b border-white/10 bg-[#050816]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <a href="/" className="text-xl font-black tracking-tight text-white">
            AI Ads Factory
          </a>

          <nav className="hidden items-center gap-4 lg:flex">
            <a className="v9-nav-pill" href="/signup">Đăng Ký</a>
            <a className="v9-nav-pill" href="/optimize">Tối Ưu</a>
            <a className="v9-nav-pill" href="/templates">Thư viện mẫu</a>
            <a className="v9-nav-pill" href="/dashboard">Bảng điều khiển</a>
            <a className="v9-nav-cta" href="/factory">Dùng Thử</a>
          </nav>
        </div>
      </header>

      <section className="relative min-h-[calc(100vh-82px)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_16%_0%,rgba(37,99,235,.35),transparent_34%),radial-gradient(circle_at_82%_18%,rgba(245,158,11,.28),transparent_32%),linear-gradient(135deg,#050816_0%,#0b1025_52%,#111827_100%)]" />

        <div className="relative mx-auto max-w-7xl px-6 py-16 lg:py-20">
          <div className="v9-hero-grid grid items-center gap-12 lg:grid-cols-2">
            <div className="v9-fade-up max-w-xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm font-black text-amber-200 shadow-[0_0_28px_rgba(245,158,11,.16)]">
              <Sparkles className="h-4 w-4" />
              AI Poster Ads System
            </div>

            <h1 className="text-5xl font-black leading-[1.02] tracking-tight text-white md:text-7xl">
              Tạo poster quảng cáo
              <span className="block bg-gradient-to-r from-amber-200 via-white to-blue-200 bg-clip-text text-transparent">
                nhìn là muốn mua
              </span>
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
              Thu hút khách trong 3 giây đầu, tăng nhận diện thương hiệu và tạo ra nhiều đơn hàng hơn chỉ với 1 poster đúng.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <a href="/factory" className="v9-primary-btn">
                Tạo poster ngay
                <ArrowRight className="h-5 w-5" />
              </a>
              <a href="/templates" className="v9-secondary-btn">
                Xem mẫu đẹp
              </a>
            </div>

            <div className="mt-8 flex flex-wrap gap-3 text-sm font-bold text-slate-300">
              <span className="v9-chip">4:5 / 1:1 / 9:16</span>
              <span className="v9-chip">Đa ngành</span>
              <span className="v9-chip">Sẵn sàng chạy ads</span>
            </div>
            </div>

            <div className="flex justify-end">
              <div className="v9-poster-frame">
                <img
                  src="/hero/best-poster.png"
                  alt="Poster quảng cáo Hạt Điều HITO"
                  className="v9-poster-image"
                />
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
