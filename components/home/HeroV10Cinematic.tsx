"use client";

import { useEffect, useRef } from "react";
import { ArrowRight, Sparkles } from "lucide-react";

export function HeroV10Cinematic() {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const posterRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const stage = stageRef.current;
    const poster = posterRef.current;
    if (!stage || !poster) return;

    const onMove = (event: MouseEvent) => {
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;

      poster.style.setProperty("--rx", `${-y * 7}deg`);
      poster.style.setProperty("--ry", `${x * 9}deg`);
      poster.style.setProperty("--tx", `${x * 16}px`);
      poster.style.setProperty("--ty", `${y * 12}px`);
    };

    const onLeave = () => {
      poster.style.setProperty("--rx", "0deg");
      poster.style.setProperty("--ry", "0deg");
      poster.style.setProperty("--tx", "0px");
      poster.style.setProperty("--ty", "0px");
    };

    stage.addEventListener("mousemove", onMove);
    stage.addEventListener("mouseleave", onLeave);

    return () => {
      stage.removeEventListener("mousemove", onMove);
      stage.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-[#050816] text-white">
      <header className="relative z-50 border-b border-white/10 bg-[#050816]/88 backdrop-blur-2xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <a href="/" className="text-xl font-black tracking-tight text-white">
            AI Ads Factory
          </a>

          <nav className="hidden items-center gap-4 lg:flex">
            <a className="v10-nav-pill" href="/signup">Đăng Ký</a>
            <a className="v10-nav-pill" href="/optimize">Tối Ưu</a>
            <a className="v10-nav-pill" href="/templates">Thư viện mẫu</a>
            <a className="v10-nav-pill" href="/dashboard">Bảng điều khiển</a>
            <a className="v10-nav-cta" href="/factory">Dùng Thử</a>
          </nav>

          <a className="v10-nav-cta lg:hidden" href="/factory">Dùng Thử</a>
        </div>
      </header>

      <section ref={stageRef} className="v10-hero-section">
        <div className="v10-bg-orb v10-bg-orb-a" />
        <div className="v10-bg-orb v10-bg-orb-b" />
        <div className="v10-bg-grid" />

        <div className="relative mx-auto grid min-h-[calc(100vh-82px)] max-w-7xl items-center gap-12 px-6 py-14 lg:grid-cols-2 lg:py-20">
          <div className="v10-reveal max-w-2xl">
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
              <a href="/factory" className="v10-primary-btn">
                Tạo poster ngay
                <ArrowRight className="h-5 w-5" />
              </a>
              <a href="/templates" className="v10-secondary-btn">
                Xem mẫu đẹp
              </a>
            </div>

            <div className="mt-8 flex flex-wrap gap-3 text-sm font-bold text-slate-300">
              <span className="v10-chip">4:5 / 1:1 / 9:16</span>
              <span className="v10-chip">Đa ngành</span>
              <span className="v10-chip">Sẵn sàng chạy ads</span>
            </div>
          </div>

          <div className="v10-poster-col">
            <div className="v10-light-beam" />
            <div className="v10-floating-dot v10-dot-1" />
            <div className="v10-floating-dot v10-dot-2" />
            <div className="v10-floating-dot v10-dot-3" />
            <div className="v10-floating-dot v10-dot-4" />

            <div ref={posterRef} className="v10-poster-frame">
              <img
                src="/hero/best-poster.png"
                alt="Poster quảng cáo Hạt Điều HITO"
                className="v10-poster-image"
              />

              <div className="v10-poster-shine" />
              <div className="v10-winner-badge">Best Output · Hero Poster</div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}