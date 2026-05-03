import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#0A0F2C] text-white flex items-center justify-center p-6">
      <section className="max-w-5xl text-center">
        <p className="text-[#FACC15] font-bold">AI Ads Factory SaaS</p>
        <h1 className="text-6xl font-black mt-4">
          Tạo ads bán hàng trong <span className="text-[#FACC15]">60 giây</span>
        </h1>
        <p className="mt-6 text-xl text-gray-300">
          Điều phối Insight, Offer, Creative, DESIGN.md, Image Ads, Video, Funnel, Bot Sales và KPI Optimization.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/factory" className="rounded-xl bg-[#2563EB] px-6 py-4 font-bold">
            Mở AI Factory
          </Link>
          <Link href="/studio" className="rounded-xl bg-white/10 px-6 py-4 font-bold">
            Mở Studio
          </Link>
          <Link href="/v5-demo" className="rounded-xl bg-[#FACC15] px-6 py-4 font-bold text-black">
            Mở V5 Demo
          </Link>
        </div>
      </section>
    </main>
  );
}
