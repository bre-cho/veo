import { SaasShell } from "@/components/shared/SaasShell";
import { CheckCircle2 } from "lucide-react";

export default function SignupPage() {
  return (
    <SaasShell
      eyebrow="Account"
      title="Đăng ký để lưu campaign và mở khóa Winner DNA"
      subtitle="Tạo tài khoản để lưu lịch sử quảng cáo, sử dụng credits và chuẩn bị deploy TikTok/Meta ở bước tiếp theo."
    >
      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-12 lg:grid-cols-[.9fr_1.1fr]">
        <div className="rounded-[2rem] border border-white/10 bg-white/[.05] p-7">
          <h2 className="text-3xl font-black text-white">Tạo tài khoản</h2>
          <p className="mt-3 text-slate-400">Bắt đầu miễn phí, nâng cấp khi cần scale.</p>

          <div className="mt-7 space-y-4">
            <input className="w-full rounded-2xl border border-white/10 bg-[#050816] px-5 py-4 text-white outline-none placeholder:text-slate-500 focus:border-amber-400" placeholder="Email" />
            <input className="w-full rounded-2xl border border-white/10 bg-[#050816] px-5 py-4 text-white outline-none placeholder:text-slate-500 focus:border-amber-400" placeholder="Mật khẩu" type="password" />
            <button className="w-full rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-6 py-4 font-black text-white shadow-[0_0_32px_rgba(245,158,11,.35)]">
              Đăng ký ngay
            </button>
          </div>

          <p className="mt-5 text-sm text-slate-400">
            Đã có tài khoản? <a href="/signin" className="font-bold text-amber-300">Đăng nhập</a>
          </p>
        </div>

        <div className="rounded-[2rem] border border-amber-400/40 bg-gradient-to-br from-blue-950 to-[#050816] p-7 shadow-[0_0_42px_rgba(245,158,11,.20)]">
          <h2 className="text-3xl font-black text-white">Bạn nhận được gì?</h2>
          <ul className="mt-7 space-y-4">
            {[
              "Lưu toàn bộ campaign đã tạo",
              "So sánh 3 biến thể: Conversion / Lead / Awareness",
              "Lưu Winner DNA để tái sử dụng",
              "Chuẩn bị kết nối TikTok Ads draft deploy",
            ].map((item) => (
              <li key={item} className="flex gap-3 text-slate-300">
                <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-300" />
                <span className="font-semibold">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </SaasShell>
  );
}
