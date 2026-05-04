import { Wand2 } from "lucide-react";

export function LiveGenerationMock() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-14">
      <div className="grid gap-8 lg:grid-cols-[.9fr_1.1fr]">
        <div>
          <p className="text-sm font-black uppercase tracking-widest text-blue-300">Live generation preview</p>
          <h2 className="mt-3 text-4xl font-black text-white md:text-5xl">Cho người dùng cảm giác AI đang chạy thật</h2>
          <p className="mt-4 text-lg leading-8 text-slate-300">Nhập sản phẩm, thấy kết quả poster mock ngay, rồi bấm dùng thử.</p>
        </div>
        <div className="rounded-[2rem] border border-white/10 bg-white/[.05] p-5">
          <div className="flex flex-col gap-4 sm:flex-row">
            <input className="min-h-14 flex-1 rounded-2xl border border-white/10 bg-[#050816] px-5 text-white outline-none placeholder:text-slate-500 focus:border-amber-400" defaultValue="hạt điều rang muối premium" />
            <a href="/factory" className="inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-6 font-black text-white shadow-[0_0_34px_rgba(245,158,11,.35)]">
              <Wand2 className="h-5 w-5" /> Tạo poster
            </a>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {["Hook", "Visual", "CTA"].map((step, index) => (
              <div key={step} className="rounded-2xl border border-white/10 bg-[#050816] p-4">
                <p className="text-xs font-black uppercase tracking-widest text-amber-300">Step {index + 1}</p>
                <h3 className="mt-2 text-xl font-black text-white">{step}</h3>
                <p className="mt-2 text-sm text-slate-400">{index === 0 ? "Ăn vặt sạch, giòn, không phụ gia." : index === 1 ? "Ingredient splash + product focus." : "Đặt hàng hôm nay nhận ưu đãi."}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
