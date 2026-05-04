import { SaasShell } from "@/components/shared/SaasShell";

const packs = [
  ["Gói thu lead ngành skincare", "TikTok · Thu lead", "199.000đ"],
  ["Gói bán hàng F&B kích thích thèm ăn", "TikTok · Bán hàng", "149.000đ"],
  ["Gói outfit thời trang viral", "TikTok · Tăng nhập", "179.000đ"],
  ["Gói bất động sản tạo niềm tin", "TikTok · Thu lead", "249.000đ"],
  ["Gói fitness lột xác", "TikTok · Thu lead", "179.000đ"],
  ["Gói khóa học / coaching tạo uy tín", "TikTok · Thu lead", "249.000đ"],
  ["Gói SaaS demo chuyển đổi", "TikTok · Đăng ký", "299.000đ"],
  ["Gói spa / clinic đặt lịch", "TikTok · Đặt lịch", "499.000đ"],
  ["Gói sự kiện hiệu ứng FOMO", "TikTok · Đăng ký", "149.000đ"],
];

export default function TemplatesPage() {
  return (
    <SaasShell
      eyebrow="Template Library"
      title="Thư viện mẫu poster đa ngành nghề"
      subtitle="Mỗi gói được thiết kế theo ngành, mục tiêu, hành vi khách hàng và logic chuyển đổi khác nhau."
    >
      <section className="mx-auto max-w-7xl px-5 py-10">
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {packs.map(([title, meta, price]) => (
            <article key={title} className="rounded-[2rem] border border-white/10 bg-white/[.045] p-6 transition hover:-translate-y-1 hover:border-amber-400/50 hover:shadow-[0_0_36px_rgba(245,158,11,.22)]">
              <p className="text-sm font-black uppercase tracking-widest text-blue-300">{meta}</p>
              <h2 className="mt-4 min-h-[76px] text-3xl font-black leading-tight text-amber-400">{title}</h2>
              <div className="mt-6 flex items-center justify-between">
                <span className="text-2xl font-black text-white">{price}</span>
                <button className="rounded-2xl bg-gradient-to-r from-orange-600 to-amber-400 px-5 py-3 font-black text-white shadow-[0_0_28px_rgba(245,158,11,.30)]">
                  Mua gói
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </SaasShell>
  );
}
