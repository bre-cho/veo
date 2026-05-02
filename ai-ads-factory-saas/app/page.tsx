import Link from "next/link";

const plans = [
  ["Creator", "199K/tháng", "200 credits, Prompt V3, HD export"],
  ["Pro", "499K/tháng", "1.000 credits, Auto video render, No watermark"],
  ["Studio", "1.500K/tháng", "5.000 credits, Batch render, Team workspace"]
];

export default function Home() {
  return (
    <main style={{ minHeight: "100vh", background: "#0A0F2C", color: "white" }}>
      <section style={{ padding: "96px 24px", textAlign: "center" }}>
        <p style={{ color: "#FACC15", fontWeight: 800 }}>AI Ads Factory</p>
        <h1 style={{ maxWidth: 980, margin: "16px auto", fontSize: 64, lineHeight: 1.05, fontWeight: 950 }}>
          Tạo ads bán hàng + video TikTok trong <span style={{ color: "#FACC15" }}>60 giây</span>
        </h1>
        <p style={{ maxWidth: 720, margin: "24px auto", fontSize: 20, color: "#CBD5E1" }}>
          Từ 1 ý tưởng, AI tạo hook, visual, CTA, prompt, video và funnel để kéo lead.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 32 }}>
          <Link className="btn" href="/revenue-factory">Dùng thử miễn phí</Link>
          <Link className="btn" style={{ background: "rgba(255,255,255,.1)" }} href="/factory">Mở Orchestrator</Link>
          <Link className="btn" style={{ background: "#0EA5E9" }} href="/dashboard">Xem KPI</Link>
        </div>
      </section>

      <section className="stack-on-mobile" style={{ padding: 24, maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
        {["Nhập sản phẩm", "AI tạo Top 3 Ads", "Render video 9:16"].map((t, i) => (
          <div className="card" key={t}>
            <div style={{ fontSize: 44, color: "#FACC15", fontWeight: 900 }}>{i + 1}</div>
            <h3>{t}</h3>
            <p style={{ color: "#CBD5E1" }}>Tối ưu cho TikTok, Facebook và landing page.</p>
          </div>
        ))}
      </section>

      <section id="pricing" style={{ padding: "80px 24px", maxWidth: 1120, margin: "0 auto" }}>
        <h2 style={{ textAlign: "center", fontSize: 44 }}>Pricing</h2>
        <div className="stack-on-mobile" style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20, marginTop: 32 }}>
          {plans.map(([name, price, desc]) => (
            <div className="card" key={name}>
              <h3 style={{ fontSize: 28 }}>{name}</h3>
              <h2>{price}</h2>
              <p style={{ color: "#CBD5E1" }}>{desc}</p>
              <Link className="btn" style={{ display: "block", textAlign: "center", marginTop: 16, background: "#FACC15", color: "#111827" }} href="/pricing">
                Bắt đầu
              </Link>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
