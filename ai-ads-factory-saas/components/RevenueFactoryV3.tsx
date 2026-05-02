"use client";

import { useEffect, useMemo, useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const design = {
  colors: {
    primary: "#0A0F2C",
    accent: "#2563EB",
    highlight: "#FACC15",
    background: "#0A0F2C",
    surface: "#111827",
    text: "#FFFFFF"
  }
};

export function RevenueFactoryV3() {
  const supabase = useMemo(() => createSupabaseBrowserClient(), []);
  const [product, setProduct] = useState("AI Design Tool");
  const [industry, setIndustry] = useState("SaaS");
  const [audience, setAudience] = useState("seller, marketer, creator");
  const [ads, setAds] = useState<any[]>([]);
  const [videoUrl, setVideoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [userId, setUserId] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data }) => {
      setUserId(data.session?.user.id || "");
      setEmail(data.session?.user.email || "");
    });

    const { data } = supabase.auth.onAuthStateChange((_, session) => {
      setUserId(session?.user.id || "");
      setEmail(session?.user.email || "");
    });

    return () => {
      data.subscription.unsubscribe();
    };
  }, [supabase]);

  async function signIn() {
    if (!supabase) {
      setError("Thiếu NEXT_PUBLIC_SUPABASE_URL hoặc NEXT_PUBLIC_SUPABASE_ANON_KEY");
      return;
    }
    setError("");
    setNotice("");
    const { error: signInError } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin + "/revenue-factory" }
    });
    if (signInError) {
      setError(signInError.message);
      return;
    }
    setNotice("Đã gửi magic link qua email.");
  }

  async function signOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    setUserId("");
  }

  async function generate() {
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/prompt/v3", {
        method: "POST",
        body: JSON.stringify({
          design,
          input: {
            product,
            industry,
            audience,
            offer: "demo miễn phí",
            goal: "Lead",
            platform: "TikTok",
            mode: "Money"
          }
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Generate failed");
      setAds(data.top3 || []);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function runWorkerUntilDone(jobId: string) {
    const maxRounds = 30;
    for (let i = 0; i < maxRounds; i += 1) {
      await fetch("/api/jobs/worker", { method: "POST" });
      const statusRes = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
      const statusData = await statusRes.json();
      if (!statusRes.ok) throw new Error(statusData.error || "Cannot get job status");

      const status = statusData.job.status;
      if (status === "completed") {
        return statusData.job.result_urls?.[0] || "";
      }
      if (status === "failed") {
        throw new Error(statusData.job.error || "Render failed");
      }

      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
    throw new Error("Render timeout");
  }

  async function renderVideo(ad: any) {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const queueRes = await fetch("/api/render/ad-video", {
        method: "POST",
        body: JSON.stringify({ ad, design, userId: userId || null, mode: "queue" })
      });
      const queueData = await queueRes.json();
      if (!queueRes.ok) throw new Error(queueData.error || "Queue failed");
      setNotice("Đã queue job render. Đang xử lý...");

      const completedUrl = await runWorkerUntilDone(queueData.jobId);
      setVideoUrl(completedUrl);
      setNotice("Render hoàn tất.");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", padding: 32 }}>
      <h1 style={{ fontSize: 44, fontWeight: 950 }}>Revenue Factory V3</h1>
      <p style={{ color: "#CBD5E1" }}>1 input → 3 ads có score → preview → render video 9:16</p>

      <section className="card" style={{ marginTop: 24 }}>
        <h3 style={{ marginTop: 0 }}>Auth UI</h3>
        <p style={{ color: "#CBD5E1" }}>Đăng nhập magic link để bind user và credit billing.</p>
        <div className="stack-on-mobile" style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 12 }}>
          <input placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="btn" onClick={signIn}>Gửi magic link</button>
          <button className="btn" style={{ background: "#334155" }} onClick={signOut}>Sign out</button>
        </div>
        <p style={{ color: "#CBD5E1", marginBottom: 0 }}>User ID: {userId || "(chưa đăng nhập)"}</p>
      </section>

      <section className="card" style={{ marginTop: 24 }}>
        <div className="stack-on-mobile" style={{ display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 12 }}>
          <input value={product} onChange={(e) => setProduct(e.target.value)} />
          <input value={industry} onChange={(e) => setIndustry(e.target.value)} />
          <input value={audience} onChange={(e) => setAudience(e.target.value)} />
        </div>
        <button className="btn" style={{ marginTop: 16 }} onClick={generate}>
          {loading ? "Đang xử lý..." : "Generate Top 3 Ads"}
        </button>
      </section>

      {notice && <p style={{ color: "#93C5FD", marginTop: 20 }}>{notice}</p>}
      {error && <p style={{ color: "#FCA5A5", marginTop: 20 }}>{error}</p>}

      <section className="stack-on-mobile" style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 20 }}>
        {ads.map((ad) => (
          <div className="card" key={ad.id}>
            <div style={{ color: "#FACC15" }}>Score {ad.score}</div>
            <h2>{ad.hook}</h2>
            <p style={{ color: "#CBD5E1" }}>{ad.headline}</p>

            <div style={{
              aspectRatio: "9/16",
              borderRadius: 24,
              background: "linear-gradient(135deg,#2563EB,#FACC15)",
              padding: 24,
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between"
            }}>
              <h3 style={{ fontSize: 28 }}>{ad.headline}</h3>
              <button className="btn" style={{ background: "white", color: "#111827" }}>{ad.cta}</button>
            </div>

            <p style={{ color: "#CBD5E1", fontSize: 14 }}>{ad.whyItConverts}</p>
            <button className="btn" style={{ width: "100%" }} onClick={() => renderVideo(ad)}>Render video</button>
          </div>
        ))}
      </section>

      {videoUrl && (
        <section className="card" style={{ marginTop: 32 }}>
          <h2>Rendered Video</h2>
          <video src={videoUrl} controls style={{ width: 320, borderRadius: 20 }} />
        </section>
      )}
    </main>
  );
}
