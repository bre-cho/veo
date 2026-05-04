export function HomeNavbarClean() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#050816]/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <a href="/" className="text-xl font-black tracking-tight text-white">
          AI Ads Factory
        </a>

        <nav className="hidden items-center gap-4 lg:flex">
          <a className="nav-pill" href="/signup">Đăng Ký</a>
          <a className="nav-pill" href="/optimize">Tối Ưu</a>
          <a className="nav-pill" href="/templates">Thư viện mẫu</a>
          <a className="nav-pill" href="/dashboard">Bảng điều khiển</a>
          <a className="nav-cta" href="/factory">Dùng Thử</a>
        </nav>

        <a className="nav-cta lg:hidden" href="/factory">Dùng Thử</a>
      </div>
    </header>
  );
}
