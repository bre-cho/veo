import { templatePreview } from "@/lib/homepage-data";

export function TemplatePreview() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-14">
      <div className="mb-8 flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-black uppercase tracking-widest text-amber-300">Template marketplace</p>
          <h2 className="mt-3 text-4xl font-black text-white md:text-5xl">Thư viện mẫu có thể bán ngay</h2>
          <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-300">Không chỉ tạo ảnh — bạn có thể bán template pack theo ngành.</p>
        </div>
        <a href="/templates" className="rounded-2xl border border-white/10 bg-white/[.06] px-6 py-4 font-black text-white hover:bg-white/[.1]">Xem thư viện</a>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        {templatePreview.map((item) => (
          <article key={item.title} className="overflow-hidden rounded-[2rem] border border-white/10 bg-white/[.045] transition hover:-translate-y-1 hover:shadow-[0_0_36px_rgba(245,158,11,.22)]">
            <img src={item.img} alt={item.title} className="h-[320px] w-full object-cover" />
            <div className="p-5">
              <p className="text-sm font-black uppercase tracking-widest text-blue-300">{item.meta}</p>
              <h3 className="mt-3 text-2xl font-black text-white">{item.title}</h3>
              <div className="mt-5 flex items-center justify-between">
                <span className="text-xl font-black text-amber-300">{item.price}</span>
                <button className="rounded-xl bg-gradient-to-r from-orange-600 to-amber-400 px-4 py-3 font-black text-white">Mua gói</button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
