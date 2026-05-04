import Link from "next/link";

export function FactoryNavbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link href="/" className="logo">
          AI Ads Factory
        </Link>
        <nav className="nav-actions">
          <Link href="/factory">Factory</Link>
          <Link href="/studio">Studio</Link>
          <Link href="/templates">Templates</Link>
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/v5-demo">V5 Demo</Link>
        </nav>
      </div>
    </header>
  );
}