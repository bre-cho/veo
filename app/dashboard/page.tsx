import { SaasShell } from "@/components/shared/SaasShell";
import { MetricCard } from "@/components/shared/MetricCard";

const rows = [
  { name: "Giftset doanh nghiệp", industry: "Gift", winner: "Conversion", score: 96, status: "Ready" },
  { name: "Hạt điều HITO", industry: "F&B", winner: "Viral", score: 91, status: "Draft" },
  { name: "Spa booking", industry: "Beauty", winner: "Authority", score: 94, status: "Ready" },
];

export default function DashboardPage() {
  return (
    <SaasShell
      eyebrow="Campaign Control"
      title="Bảng điều khiển chiến dịch"
      subtitle="Theo dõi campaign, winner, score và trạng thái deploy. Đây là trung tâm vận hành để chuyển từ tạo ảnh sang kiếm tiền."
    >
      <section className="mx-auto max-w-7xl px-5 py-10">
        <div className="grid gap-5 md:grid-cols-4">
          <MetricCard label="Campaign" value="12" desc="Chiến dịch đã tạo" tone="blue" />
          <MetricCard label="Winner DNA" value="8" desc="Mẫu thắng đã lưu" tone="amber" />
          <MetricCard label="Avg Score" value="92" desc="Điểm trung bình" tone="green" />
          <MetricCard label="Draft Ads" value="5" desc="Sẵn sàng deploy" tone="purple" />
        </div>

        <div className="mt-8 overflow-hidden rounded-[2rem] border border-white/10 bg-white/[.045]">
          <div className="grid grid-cols-5 bg-white/[.06] px-5 py-4 text-sm font-black text-slate-300">
            <span>Campaign</span>
            <span>Ngành</span>
            <span>Winner</span>
            <span>Score</span>
            <span>Trạng thái</span>
          </div>
          {rows.map((row) => (
            <div key={row.name} className="grid grid-cols-5 border-t border-white/10 px-5 py-4 text-sm text-slate-300">
              <span className="font-bold text-white">{row.name}</span>
              <span>{row.industry}</span>
              <span className="font-bold text-amber-300">{row.winner}</span>
              <span>{row.score}/100</span>
              <span>
                <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-black text-emerald-300">
                  {row.status}
                </span>
              </span>
            </div>
          ))}
        </div>
      </section>
    </SaasShell>
  );
}
