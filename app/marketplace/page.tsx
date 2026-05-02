"use client";

import { useEffect, useState } from "react";
import { packs } from "@/lib/marketplace/packs";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

export default function MarketplacePage() {
  const supabase = getSupabaseBrowserClient();
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data }) => {
      setToken(data.session?.access_token || "");
    });

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setToken(session?.access_token || "");
    });

    return () => data.subscription.unsubscribe();
  }, [supabase]);

  async function checkout(pack: (typeof packs)[number]) {
    if (!token) {
      setMessage("Bạn cần đăng nhập ở trang Factory trước khi checkout.");
      return;
    }

    setMessage("Đang tạo Stripe checkout...");
    const res = await fetch("/api/stripe/checkout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(pack)
    });

    const payload = await res.json();
    if (!res.ok || !payload.url) {
      setMessage(payload.error || "Không thể tạo checkout session.");
      return;
    }

    window.location.href = payload.url;
  }

  return (
    <main className="min-h-screen bg-[#0A0F2C] text-white p-6">
      <h1 className="text-4xl font-black">Revenue Preset Marketplace</h1>
      <p className="mt-3 text-gray-300">Template không chỉ đẹp — mà có logic kéo click, lead và sale.</p>
      {message && <p className="mt-3 text-sm text-yellow-300">{message}</p>}
      {!supabase && (
        <p className="mt-3 text-sm text-red-300">
          Thiếu NEXT_PUBLIC_SUPABASE_URL hoặc NEXT_PUBLIC_SUPABASE_ANON_KEY trong .env.local.
        </p>
      )}

      <div className="mt-8 grid grid-cols-3 gap-5">
        {packs.map((p) => (
          <div key={p.slug} className="rounded-2xl bg-[#111827] p-5 border border-white/10">
            <div className="h-40 rounded-xl bg-gradient-to-br from-[#2563EB] to-[#FACC15]" />
            <h2 className="mt-4 text-xl font-bold">{p.name}</h2>
            <p className="mt-2 text-sm text-gray-400">{p.platform} · {p.goal}</p>
            <div className="mt-4 flex items-center justify-between">
              <b>{p.price.toLocaleString()}đ</b>
              <button
                onClick={() => checkout(p)}
                className="rounded-lg bg-[#2563EB] px-4 py-2 font-bold"
              >
                Mua pack
              </button>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
