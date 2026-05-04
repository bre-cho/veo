"use client";

import Link from "next/link";
import Image from "next/image";
import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

type PosterPreset = {
  id: string;
  name: string;
  thumbnail: string;
  ratio: string;
  tone: string;
  platform: "Facebook" | "TikTok" | "Landing";
  palette: string;
  style: string;
  emotion: string;
};

type ConceptPayload = {
  winner?: {
    hook?: string;
    cta?: string;
    prompt?: string;
  };
  variants?: Array<{
    hook?: string;
    cta?: string;
    prompt?: string;
  }>;
};

const posterPresets: PosterPreset[] = [
  {
    id: "flash-sale-burst",
    name: "Flash Sale Burst",
    thumbnail: "/poster-presets/flash-sale-burst.svg",
    ratio: "4:5",
    tone: "Urgency",
    platform: "Facebook",
    palette: "#FACC15 / #FB7185 / #111827",
    style: "Bold retail",
    emotion: "High-energy"
  },
  {
    id: "premium-minimal",
    name: "Premium Minimal",
    thumbnail: "/poster-presets/premium-minimal.svg",
    ratio: "1:1",
    tone: "Luxury",
    platform: "Landing",
    palette: "#E5E7EB / #2563EB / #0A0F2C",
    style: "Clean premium",
    emotion: "Trust"
  },
  {
    id: "launch-countdown",
    name: "Launch Countdown",
    thumbnail: "/poster-presets/launch-countdown.svg",
    ratio: "9:16",
    tone: "Hype",
    platform: "TikTok",
    palette: "#22D3EE / #6366F1 / #0B1024",
    style: "Cinematic neon",
    emotion: "Excitement"
  }
];

const buildSteps = [
  "Nhập offer, giá, thời hạn và insight khách hàng.",
  "AI dựng headline, visual hook và bố cục theo tỉ lệ đã chọn.",
  "Tối ưu CTA, contrast, hierarchy và xuất poster cho ads."
];

export default function PosterPage() {
  const router = useRouter();
  const [selectedPresetId, setSelectedPresetId] = useState(posterPresets[0].id);
  const [brief, setBrief] = useState({
    product: "AI Design Tool",
    goal: "lead",
    audience: "Seller online",
    offer: "Dùng thử 7 ngày miễn phí",
    ratio: posterPresets[0].ratio,
    cta: "Nhận demo miễn phí"
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [concept, setConcept] = useState<ConceptPayload | null>(null);

  const selectedPreset = useMemo(
    () => posterPresets.find((preset) => preset.id === selectedPresetId) || posterPresets[0],
    [selectedPresetId]
  );

  async function generateConcept(nextBrief?: typeof brief, nextPreset?: PosterPreset) {
    const briefData = nextBrief || brief;
    const presetData = nextPreset || selectedPreset;

    if (!briefData.product.trim()) {
      setMessage("Vui lòng nhập sản phẩm trước khi sinh concept.");
      return null;
    }

    try {
      setIsGenerating(true);
      setMessage("Đang sinh concept tự động...");

      const res = await fetch("/api/generate-ads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product: briefData.product,
          goal: briefData.goal,
          audience: briefData.audience,
          offer: briefData.offer,
          ratio: briefData.ratio,
          cta: briefData.cta,
          style: presetData.style,
          platform: presetData.platform,
          emotion: presetData.emotion,
          preset: presetData.id
        })
      });

      const payload = (await res.json()) as ConceptPayload & { error?: string };

      if (!res.ok) {
        setMessage(payload.error || "Không thể sinh concept.");
        return null;
      }

      setConcept(payload);
      setMessage("Đã sinh concept. Bạn có thể gửi sang editor ngay.");
      return payload;
    } catch {
      setMessage("Lỗi kết nối API. Vui lòng thử lại.");
      return null;
    } finally {
      setIsGenerating(false);
    }
  }

  function pushToEditor(preset: PosterPreset, briefOverride?: typeof brief, conceptOverride?: ConceptPayload | null) {
    const briefData = briefOverride || brief;
    const conceptData = conceptOverride === undefined ? concept : conceptOverride;

    const params = new URLSearchParams({
      source: "poster",
      preset: preset.id,
      ratio: briefData.ratio,
      tone: preset.tone,
      style: preset.style,
      platform: preset.platform,
      product: briefData.product,
      goal: briefData.goal,
      cta: briefData.cta
    });

    if (typeof window !== "undefined") {
      sessionStorage.setItem(
        "poster:selectedPreset",
        JSON.stringify({ preset, brief: briefData, concept: conceptData, ts: new Date().toISOString() })
      );
    }

    router.push(`/studio?${params.toString()}`);
  }

  async function onChoosePreset(preset: PosterPreset) {
    const nextBrief = { ...brief, ratio: preset.ratio };
    setSelectedPresetId(preset.id);
    setBrief(nextBrief);
    const nextConcept = await generateConcept(nextBrief, preset);
    pushToEditor(preset, nextBrief, nextConcept);
  }

  function onSubmitBrief(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void generateConcept();
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#060B21] text-white">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_15%,rgba(250,204,21,0.24),transparent_32%),radial-gradient(circle_at_80%_0%,rgba(37,99,235,0.35),transparent_35%),linear-gradient(140deg,#060B21_0%,#0A1030_46%,#0A0F2C_100%)]" />

      <section className="mx-auto max-w-6xl px-6 pb-10 pt-14 md:pt-20">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.55, ease: "easeOut" }}
          className="rounded-3xl border border-white/15 bg-white/[0.03] p-8 backdrop-blur-sm md:p-12"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#FACC15]">Xưởng Poster</p>
          <h1
            className="mt-4 text-4xl font-black leading-tight md:text-6xl"
            style={{ fontFamily: "Space Grotesk, Sora, system-ui, sans-serif" }}
          >
            Tạo Poster Ads Có Tỉ Lệ Chuyển Đổi Cao Trong 60 Giây
          </h1>
          <p className="mt-5 max-w-3xl text-base text-slate-200 md:text-lg">
            Một màn hình duy nhất để đi từ brief đến thiết kế có thể chạy ads ngay: hook rõ, layout sạch,
            thông điệp bán hàng sắc nét, đúng chuẩn feed và story.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/studio"
              className="rounded-xl bg-[#2563EB] px-6 py-3 text-sm font-bold uppercase tracking-wide transition hover:bg-[#1D4ED8]"
            >
              Mở Studio Poster
            </Link>
            <Link
              href="/factory"
              className="rounded-xl border border-white/20 bg-white/5 px-6 py-3 text-sm font-bold uppercase tracking-wide transition hover:bg-white/10"
            >
              Mở Xưởng AI
            </Link>
            <Link
              href="/marketplace"
              className="rounded-xl border border-[#FACC15]/50 bg-[#FACC15]/10 px-6 py-3 text-sm font-bold uppercase tracking-wide text-[#FACC15] transition hover:bg-[#FACC15]/20"
            >
              Chợ Preset
            </Link>
          </div>
        </motion.div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="rounded-3xl border border-white/15 bg-[#0A122E] p-7 md:p-10"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#FACC15]">Brief Sang Concept</p>
              <h3 className="mt-2 text-2xl font-black md:text-3xl">Nhập brief và sinh concept tự động</h3>
            </div>
            <button
              onClick={() => pushToEditor(selectedPreset)}
              className="rounded-xl border border-[#FACC15]/45 bg-[#FACC15]/10 px-4 py-2 text-sm font-bold text-[#FACC15] hover:bg-[#FACC15]/20"
            >
              Mở editor với preset đang chọn
            </button>
          </div>

          <form onSubmit={onSubmitBrief} className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-semibold text-slate-200">
              Sản phẩm
              <input
                value={brief.product}
                onChange={(e) => setBrief({ ...brief, product: e.target.value })}
                className="mt-2 w-full rounded-xl border border-white/15 bg-[#0B1432] px-4 py-3 text-sm outline-none transition focus:border-[#2563EB]"
                placeholder="Ví dụ: Khóa học chạy ads AI"
              />
            </label>

            <label className="text-sm font-semibold text-slate-200">
              Mục tiêu
              <select
                value={brief.goal}
                onChange={(e) => setBrief({ ...brief, goal: e.target.value })}
                className="mt-2 w-full rounded-xl border border-white/15 bg-[#0B1432] px-4 py-3 text-sm outline-none transition focus:border-[#2563EB]"
              >
                <option value="lead">Thu lead</option>
                <option value="sale">Bán hàng</option>
                <option value="click">Tăng nhấp</option>
              </select>
            </label>

            <label className="text-sm font-semibold text-slate-200">
              Tệp khách hàng
              <input
                value={brief.audience}
                onChange={(e) => setBrief({ ...brief, audience: e.target.value })}
                className="mt-2 w-full rounded-xl border border-white/15 bg-[#0B1432] px-4 py-3 text-sm outline-none transition focus:border-[#2563EB]"
              />
            </label>

            <label className="text-sm font-semibold text-slate-200">
              Kêu gọi hành động
              <input
                value={brief.cta}
                onChange={(e) => setBrief({ ...brief, cta: e.target.value })}
                className="mt-2 w-full rounded-xl border border-white/15 bg-[#0B1432] px-4 py-3 text-sm outline-none transition focus:border-[#2563EB]"
              />
            </label>

            <label className="md:col-span-2 text-sm font-semibold text-slate-200">
              Offer
              <input
                value={brief.offer}
                onChange={(e) => setBrief({ ...brief, offer: e.target.value })}
                className="mt-2 w-full rounded-xl border border-white/15 bg-[#0B1432] px-4 py-3 text-sm outline-none transition focus:border-[#2563EB]"
              />
            </label>

            <div className="md:col-span-2 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={isGenerating}
                className="rounded-xl bg-[#2563EB] px-5 py-3 text-sm font-bold uppercase tracking-wide transition hover:bg-[#1D4ED8] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isGenerating ? "Đang sinh..." : "Sinh concept tự động"}
              </button>
              {message && <p className="text-sm text-slate-200">{message}</p>}
            </div>
          </form>

          {concept && (
            <div className="mt-6 rounded-2xl border border-white/15 bg-white/5 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#FACC15]">Concept preview</p>
              <h4 className="mt-2 text-xl font-extrabold">{concept.winner?.hook || "AI Concept"}</h4>
              <p className="mt-2 text-sm text-slate-200">CTA: {concept.winner?.cta || brief.cta}</p>
              {concept.winner?.prompt && (
                <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-black/25 p-4 text-xs text-slate-200">
                  {concept.winner.prompt}
                </pre>
              )}
            </div>
          )}
        </motion.div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12">
        <div className="grid gap-4 md:grid-cols-3">
          {posterPresets.map((preset, index) => {
            const isActive = selectedPresetId === preset.id;

            return (
              <motion.article
                key={preset.id}
                initial={{ opacity: 0, y: 26 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.45, ease: "easeOut", delay: index * 0.08 }}
                className={`group relative overflow-hidden rounded-2xl border bg-[#0F1636]/80 p-6 transition duration-300 hover:-translate-y-1 ${
                  isActive ? "border-[#FACC15]/75" : "border-white/15 hover:border-[#FACC15]/60"
                }`}
              >
                <div className="absolute inset-0 bg-[linear-gradient(160deg,rgba(250,204,21,0.13),transparent_40%,rgba(37,99,235,0.2))] opacity-90" />
                <div className="relative">
                  <div className="relative h-40 overflow-hidden rounded-xl border border-white/10">
                    <Image
                      src={preset.thumbnail}
                      alt={preset.name}
                      fill
                      sizes="(max-width: 768px) 100vw, 33vw"
                      className="object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                    />
                  </div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">Preset {index + 1}</p>
                  <h2 className="mt-2 text-2xl font-extrabold">{preset.name}</h2>
                  <div className="mt-5 space-y-2 text-sm text-slate-200">
                    <p>Tỉ lệ: {preset.ratio}</p>
                    <p>Phong cách: {preset.tone}</p>
                    <p>Palette: {preset.palette}</p>
                  </div>
                  <button
                    onClick={() => void onChoosePreset(preset)}
                    className="mt-6 rounded-lg bg-white/10 px-4 py-2 text-sm font-bold transition group-hover:bg-[#FACC15] group-hover:text-[#0A0F2C]"
                  >
                    Chọn preset và mở editor
                  </button>
                </div>
              </motion.article>
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
          className="rounded-3xl border border-white/15 bg-[#0A122E] p-7 md:p-10"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#FACC15]">Workflow</p>
          <h3 className="mt-3 text-3xl font-black md:text-4xl">Từ Brief Sang Poster Live Trong 3 Bước</h3>
          <div className="mt-7 grid gap-4 md:grid-cols-3">
            {buildSteps.map((step, i) => (
              <div key={step} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <p className="text-sm font-bold text-[#FACC15]">Bước 0{i + 1}</p>
                <p className="mt-2 text-sm leading-relaxed text-slate-100">{step}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </section>
    </main>
  );
}
