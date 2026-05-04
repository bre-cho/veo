import { heroPosters } from "@/lib/homepage-data";

export function HeroPosterStack() {
  return (
    <div className="relative mx-auto w-full max-w-[520px]">
      <div className="absolute -inset-8 rounded-[3rem] bg-gradient-to-r from-orange-500/25 via-amber-300/20 to-blue-500/25 blur-3xl" />
      <div className="relative aspect-[3/4] rounded-[2rem] border border-amber-300/40 bg-white/5 p-3 shadow-[0_0_70px_rgba(245,158,11,.32)] backdrop-blur-xl">
        <img src={heroPosters[0].src} alt="Best AI poster demo" className="h-full w-full rounded-[1.5rem] object-cover" />
        <div className="absolute left-6 top-6 rounded-full bg-black/65 px-4 py-2 text-sm font-black text-amber-300 backdrop-blur">
          Winner · {heroPosters[0].score}
        </div>
      </div>
      <img src={heroPosters[1].src} alt="Beauty poster demo" className="absolute -right-6 top-20 hidden w-[38%] rotate-6 rounded-2xl border border-white/20 shadow-[0_0_34px_rgba(244,114,182,.25)] lg:block" />
      <img src={heroPosters[2].src} alt="SaaS poster demo" className="absolute -left-8 bottom-20 hidden w-[40%] -rotate-6 rounded-2xl border border-white/20 shadow-[0_0_34px_rgba(37,99,235,.25)] lg:block" />
    </div>
  );
}
