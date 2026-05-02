import Link from "next/link";

const plans = [
  { id: "creator", name: "Creator", price: "199K/thang", credits: "200 credits" },
  { id: "pro", name: "Pro", price: "499K/thang", credits: "1.000 credits" },
  { id: "studio", name: "Studio", price: "1.500K/thang", credits: "5.000 credits" }
];

export default function PricingPage() {
  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>Pricing</h1>
      <p style={{ color: "#CBD5E1" }}>Nạp credits theo gói để unlock render và no-watermark workflow.</p>

      <section className="stack-on-mobile" style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 20 }}>
        {plans.map((plan) => (
          <div className="card" key={plan.id}>
            <h3 style={{ fontSize: 30 }}>{plan.name}</h3>
            <h2>{plan.price}</h2>
            <p style={{ color: "#CBD5E1" }}>{plan.credits}</p>
            <button className="btn" style={{ width: "100%", marginTop: 16 }}>Chọn gói</button>
          </div>
        ))}
      </section>

      <p style={{ marginTop: 24, color: "#CBD5E1" }}>
        Checkout API: POST /api/billing/checkout. Sau khi thanh toán, webhook cập nhật plan + cộng credits.
      </p>
      <Link href="/dashboard" className="btn" style={{ display: "inline-block", marginTop: 12 }}>
        Mở Dashboard KPI
      </Link>
    </main>
  );
}
