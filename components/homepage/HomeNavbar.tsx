export function HomeNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#050816]/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 px-5 py-4">
        <a href="/" className="text-xl font-black tracking-tight text-white">AI Ads Factory</a>
        <nav className="hidden items-center gap-3 lg:flex">
          {[
            ["Đăng Ký", "/signup"],
            ["Tối Ưu", "/optimize"],
            ["Thư viện mẫu", "/templates"],
            ["Bảng điều khiển", "/dashboard"],
          ].map(([label, href]) => (
            <a key={label} href={href} className="inline-flex min-h-11 items-center justify-center whitespace-nowrap rounded-full bg-gradient-to-r from-orange-700 to-amber-500 px-5 text-sm font-black text-white shadow-[0_0_24px_rgba(245,158,11,.22)] transition hover:-translate-y-0.5">
              {label}
            </a>
          ))}
          <a href="/factory" className="inline-flex min-h-12 items-center justify-center whitespace-nowrap rounded-full bg-gradient-to-r from-orange-600 to-amber-400 px-6 text-sm font-black text-white shadow-[0_0_38px_rgba(255,106,0,.48)] transition hover:-translate-y-0.5 hover:scale-[1.03]">Dùng Thử</a>
        </nav>
      </div>
    </header>
  );
}
