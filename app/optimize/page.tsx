import { SaasShell } from "@/components/shared/SaasShell";
import { Wand2 } from "lucide-react";

export default function OptimizePage() {
  return (
    <SaasShell
      eyebrow="Prompt Engine V2"
      title="Tối ưu prompt chuyển đổi"
      subtitle="Biến brief thô thành prompt quảng cáo rõ chủ thể, rõ hook, rõ CTA và đúng mục tiêu bán hàng."
    >
      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-10 lg:grid-cols-[1fr_.9fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/[.045] p-6">
          <label className="text-sm font-black uppercase tracking-widest text-amber-300">Brief / DESIGN.md</label>
          <textarea
            className="mt-4 min-h-[440px] w-full rounded-2xl border border-white/10 bg-[#050816] px-5 py-4 font-mono text-sm leading-7 text-white outline-none placeholder:text-slate-500 focus:border-amber-400"
            defaultValue={`---
version: alpha
name: "Revenue Ads System"
goal: "lead"
platform: "TikTok"
conversion:
  hook: "problem"
  cta: "inbox now"
---`}
          />
        </div>

        <div className="rounded-[2rem] border border-amber-400/40 bg-gradient-to-br from-blue-950 to-[#050816] p-6 shadow-[0_0_42px_rgba(245,158,11,.20)]">
          <label className="text-sm font-black uppercase tracking-widest text-blue-300">Sản phẩm</label>
          <input
            className="mt-4 w-full rounded-2xl border border-white/10 bg-[#050816] px-5 py-4 text-white outline-none placeholder:text-slate-500 focus:border-amber-400"
            defaultValue="AI Design Tool"
          />

          <button className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-6 py-4 font-black text-white shadow-[0_0_32px_rgba(245,158,11,.35)]">
            <Wand2 className="h-5 w-5" />
            Tối ưu prompt conversion
          </button>

          <div className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-5">
            <p className="text-sm font-black uppercase tracking-widest text-amber-300">Output preview</p>
            <p className="mt-4 leading-7 text-slate-300">
              High-conversion SaaS advertising poster, clear problem-solution hook, premium dark background,
              glowing dashboard, strong CTA, TikTok-ready layout, Vietnamese Unicode typography.
            </p>
          </div>
        </div>
      </section>
    </SaasShell>
  );
}
