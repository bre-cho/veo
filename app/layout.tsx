import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "AI Ads Factory SaaS",
  description: "AI Creative Revenue Operating System"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <header className="sticky top-0 z-40 border-b border-black/10 bg-white/90 backdrop-blur">
          <nav className="mx-auto flex w-full max-w-7xl items-center gap-2 px-4 py-3 sm:px-6">
            <Link href="/" className="rounded-lg px-3 py-2 text-sm font-extrabold text-[#0A0F2C]">
              AI Ads Factory
            </Link>
            <div className="ml-auto flex flex-wrap items-center gap-2 text-sm font-semibold">
              <Link href="/factory" className="rounded-lg border border-black/10 px-3 py-2 hover:bg-black/5">
                Factory
              </Link>
              <Link href="/studio" className="rounded-lg border border-black/10 px-3 py-2 hover:bg-black/5">
                Studio
              </Link>
              <Link href="/marketplace" className="rounded-lg border border-black/10 px-3 py-2 hover:bg-black/5">
                Marketplace
              </Link>
              <Link href="/dashboard" className="rounded-lg border border-black/10 px-3 py-2 hover:bg-black/5">
                Dashboard
              </Link>
              <Link href="/v5-demo" className="rounded-lg bg-[#FACC15] px-3 py-2 text-black hover:brightness-95">
                V5 Demo
              </Link>
            </div>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
