export function BeforeAfterBlock() {
  return (
    <section id="demo" className="mx-auto max-w-7xl px-5 py-14">
      <div className="mb-8 max-w-3xl">
        <p className="text-sm font-black uppercase tracking-widest text-amber-300">Before / After</p>
        <h2 className="mt-3 text-4xl font-black text-white md:text-5xl">Từ brief thô thành poster quảng cáo có khả năng chuyển đổi</h2>
        <p className="mt-4 text-lg leading-8 text-slate-300">Người xem cần thấy kết quả ngay. Đây là vùng “wow moment”.</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-[2rem] border border-white/10 bg-white/[.04] p-6">
          <span className="rounded-full bg-slate-700 px-3 py-1 text-sm font-black text-slate-200">Before</span>
          <div className="mt-5 rounded-2xl border border-white/10 bg-[#050816] p-5 font-mono text-sm leading-7 text-slate-300">
            Tôi bán serum trị mụn, muốn làm poster TikTok để thu khách inbox.
          </div>
        </div>
        <div className="rounded-[2rem] border border-amber-400/40 bg-gradient-to-br from-blue-950 to-[#050816] p-6 shadow-[0_0_42px_rgba(245,158,11,.24)]">
          <span className="rounded-full bg-amber-400 px-3 py-1 text-sm font-black text-slate-950">After</span>
          <div className="mt-5 grid gap-4 sm:grid-cols-[.65fr_1fr]">
            <img src="/demo-posters/hero-poster-2.svg" alt="After poster" className="rounded-2xl border border-white/10" />
            <div>
              <h3 className="text-2xl font-black text-white">Skincare lead poster</h3>
              <p className="mt-3 text-slate-300">Hook rõ vấn đề, visual beauty trust, CTA đặt lịch/inbox, tỷ lệ 4:5 phù hợp TikTok và Meta.</p>
              <p className="mt-5 text-4xl font-black text-amber-300">94/100</p>
              <p className="text-sm font-bold text-slate-400">Authority + Lead Winner</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
