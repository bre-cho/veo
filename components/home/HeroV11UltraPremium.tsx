"use client";

import { useEffect, useRef } from "react";

export function HeroV11UltraPremium() {
  const rootRef = useRef<HTMLElement | null>(null);
  const posterRef = useRef<HTMLDivElement | null>(null);
  const titleRef = useRef<HTMLHeadingElement | null>(null);

  useEffect(() => {
    const root = rootRef.current;
    const poster = posterRef.current;
    const title = titleRef.current;
    if (!root || !poster || !title) return;

    const onPointerMove = (event: PointerEvent) => {
      const rect = root.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;

      root.style.setProperty("--cursor-x", `${x * 100}%`);
      root.style.setProperty("--cursor-y", `${y * 100}%`);

      poster.style.setProperty("--rotate-y", `${(x - 0.5) * 10}deg`);
      poster.style.setProperty("--rotate-x", `${-(y - 0.5) * 8}deg`);
      poster.style.setProperty("--poster-x", `${(x - 0.5) * 18}px`);
      poster.style.setProperty("--poster-y", `${(y - 0.5) * 14}px`);
    };

    const onScroll = () => {
      const offset = Math.min(window.scrollY, 240);
      root.style.setProperty("--scroll-y", `${offset}px`);
      poster.style.setProperty("--scroll-scale", `${1 - offset / 2400}`);
      poster.style.setProperty("--scroll-lift", `${offset * -0.18}px`);
    };

    root.addEventListener("pointermove", onPointerMove);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    return () => {
      root.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <main ref={rootRef} className="v11-page">
      <header className="v11-navbar">
        <a href="/" className="v11-logo">Không phải poster đẹp — mà là poster bán được hàng</a>

        <nav className="v11-nav">
          <a href="/signup">Đăng Ký</a>
          <a href="/optimize">Tối Ưu</a>
          <a href="/templates">Thư viện mẫu</a>
          <a href="/dashboard">Bảng điều khiển</a>
          <a href="/factory" className="v11-nav-primary">Dùng Thử</a>
        </nav>
      </header>

      <section className="v11-hero">
        <div className="v11-aurora v11-aurora-one" />
        <div className="v11-aurora v11-aurora-two" />
        <div className="v11-cursor-light" />
        <div className="v11-grid-bg" />

        <div className="v11-shell">
          <div className="v11-left">
            <div className="v11-badge">AI Poster Ads System</div>

            <h1 ref={titleRef} className="v11-title">
              Tạo poster quảng cáo
              <span>nhìn là muốn mua</span>
            </h1>

            <p className="v11-subtitle">
              Thu hút khách trong 3 giây đầu, tăng nhận diện thương hiệu và tạo ra nhiều đơn hàng hơn chỉ với 1 poster đúng.
            </p>

            <div className="v11-actions">
              <a href="/factory" className="v11-cta">Tạo poster ngay →</a>
              <a href="/templates" className="v11-ghost">Xem mẫu đẹp</a>
            </div>

            <div className="v11-proof">
              <span>4:5 / 1:1 / 9:16</span>
              <span>Đa ngành</span>
              <span>Sẵn sàng chạy ads</span>
            </div>
          </div>

          <div className="v11-right">
            <div className="v11-poster-glow" />

            <div ref={posterRef} className="v11-poster-card">
              <img src="/hero/best-poster.png" alt="Poster quảng cáo Hạt Điều HITO" />
              <div className="v11-shine" />
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
