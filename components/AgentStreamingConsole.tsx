"use client";

import { useEffect, useState } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

type SessionInfo = {
  access_token: string;
};

type AgentBlock = {
  agent: string;
  status: "running" | "done";
  output?: string;
};

export function AgentStreamingConsole() {
  const supabase = getSupabaseBrowserClient();
  const [input, setInput] = useState({
    industry: "SaaS",
    product: "AI Design Tool",
    audience: "seller, marketer, creator",
    goal: "Lead",
    platform: "TikTok"
  });

  const [blocks, setBlocks] = useState<AgentBlock[]>([]);
  const [running, setRunning] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMessage, setAuthMessage] = useState("");
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [jobPrompt, setJobPrompt] = useState("Banner 1:1 bán phần mềm AI cho chủ shop online");
  const [jobId, setJobId] = useState("");
  const [jobState, setJobState] = useState("");
  const [jobAssets, setJobAssets] = useState<string[]>([]);

  useEffect(() => {
    if (!supabase) return;

    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (mounted) {
        setSession(data.session ? { access_token: data.session.access_token } : null);
      }
    });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession ? { access_token: nextSession.access_token } : null);
    });

    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, [supabase]);

  async function signUp() {
    if (!supabase) {
      setAuthMessage("Thiếu biến Supabase trong .env.local");
      return;
    }

    setAuthMessage("");
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setAuthMessage(error.message);
      return;
    }
    setAuthMessage("Đăng ký thành công. Kiểm tra email để xác thực nếu Supabase bật confirm.");
  }

  async function signIn() {
    if (!supabase) {
      setAuthMessage("Thiếu biến Supabase trong .env.local");
      return;
    }

    setAuthMessage("");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setAuthMessage(error.message);
      return;
    }
    setAuthMessage("Đăng nhập thành công.");
  }

  async function signOut() {
    if (!supabase) {
      setAuthMessage("Thiếu biến Supabase trong .env.local");
      return;
    }

    await supabase.auth.signOut();
    setAuthMessage("Đã đăng xuất.");
  }

  async function run() {
    if (!session?.access_token) {
      setAuthMessage("Bạn cần đăng nhập để chạy factory.");
      return;
    }

    setBlocks([]);
    setRunning(true);

    const res = await fetch("/api/orchestrator/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`
      },
      body: JSON.stringify(input)
    });

    if (!res.ok) {
      setRunning(false);
      const data = await res.json().catch(() => ({ error: "Run factory failed" }));
      setAuthMessage(data.error || "Run factory failed");
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        const eventLine = chunk.split("\n").find((l) => l.startsWith("event:"));
        const dataLine = chunk.split("\n").find((l) => l.startsWith("data:"));
        if (!eventLine || !dataLine) continue;

        const event = eventLine.replace("event:", "").trim();
        const data = JSON.parse(dataLine.replace("data:", "").trim());

        if (event === "agent_start") {
          setBlocks((prev) => [...prev, { agent: data.agent, status: "running" }]);
        }

        if (event === "agent_done") {
          setBlocks((prev) =>
            prev.map((b) =>
              b.agent === data.agent ? { ...b, status: "done", output: data.output } : b
            )
          );
        }

        if (event === "done") setRunning(false);
      }
    }

    setRunning(false);
  }

  async function createJob() {
    if (!session?.access_token) {
      setAuthMessage("Bạn cần đăng nhập để tạo job.");
      return;
    }

    setJobAssets([]);
    setJobState("queued");

    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`
      },
      body: JSON.stringify({ prompt: jobPrompt })
    });

    const payload = await res.json();
    if (!res.ok) {
      setJobState("failed");
      setAuthMessage(payload.error || "Create job failed");
      return;
    }

    setJobId(payload.jobId);
  }

  useEffect(() => {
    if (!jobId || !session?.access_token) return;

    const timer = setInterval(async () => {
      const res = await fetch(`/api/jobs/${jobId}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`
        }
      });

      const payload = await res.json();
      if (!res.ok) {
        setJobState("failed");
        setAuthMessage(payload.error || "Get job failed");
        clearInterval(timer);
        return;
      }

      const job = payload.job;
      setJobState(job.status);
      setJobAssets(job.result_urls || []);

      if (job.status === "completed" || job.status === "failed") {
        clearInterval(timer);
      }
    }, 1800);

    return () => clearInterval(timer);
  }, [jobId, session?.access_token]);

  return (
    <main className="min-h-screen bg-[#0A0F2C] text-white p-6">
      <h1 className="text-3xl font-black">Poster Design Đa Ngành Nghề</h1>
      <p className="mt-2 text-gray-300">Mẫu không chỉ đẹp mà còn có logic kéo tăng nhấp, thu khách hàng tiềm năng và bán hàng.</p>

      <section className="mt-6 rounded-2xl bg-[#111827] p-5 space-y-3">
        <h2 className="text-xl font-bold">Xác thực</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            className="rounded-lg bg-black/30 p-3"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="rounded-lg bg-black/30 p-3"
            placeholder="Mật khẩu"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={signUp} className="rounded-lg bg-white/10 px-4 py-2 font-bold">Đăng ký</button>
          <button onClick={signIn} className="rounded-lg bg-[#2563EB] px-4 py-2 font-bold">Đăng nhập</button>
          <button onClick={signOut} className="rounded-lg bg-red-500/80 px-4 py-2 font-bold">Đăng xuất</button>
        </div>
        <p className="text-sm text-gray-300">
          Trạng thái: {session ? "Đã đăng nhập" : "Chưa đăng nhập"}
        </p>
        {authMessage && <p className="text-sm text-yellow-300">{authMessage}</p>}
        {!supabase && (
          <p className="text-sm text-red-300">
            Thiếu NEXT_PUBLIC_SUPABASE_URL hoặc NEXT_PUBLIC_SUPABASE_ANON_KEY trong .env.local.
          </p>
        )}
      </section>

      <section className="mt-6 rounded-2xl bg-[#111827] p-5">
        <div className="grid grid-cols-2 gap-3">
          <input className="rounded-lg bg-black/30 p-3" value={input.industry} onChange={(e) => setInput({ ...input, industry: e.target.value })} />
          <input className="rounded-lg bg-black/30 p-3" value={input.product} onChange={(e) => setInput({ ...input, product: e.target.value })} />
          <input className="rounded-lg bg-black/30 p-3 col-span-2" value={input.audience} onChange={(e) => setInput({ ...input, audience: e.target.value })} />
        </div>

        <button onClick={run} disabled={running} className="mt-4 rounded-xl bg-[#2563EB] px-5 py-3 font-bold disabled:opacity-50">
          {running ? "Đang chạy 10 agents..." : "Chạy Full Factory"}
        </button>
      </section>

      <section className="mt-6 rounded-2xl bg-[#111827] p-5">
        <h2 className="text-xl font-bold">Hàng đợi tạo ảnh AI</h2>
        <div className="mt-3 flex flex-col gap-3">
          <textarea
            className="rounded-lg bg-black/30 p-3 min-h-24"
            value={jobPrompt}
            onChange={(e) => setJobPrompt(e.target.value)}
          />
          <button onClick={createJob} className="w-fit rounded-lg bg-[#FACC15] text-black px-4 py-2 font-bold">
            Tạo job
          </button>
          <p className="text-sm text-gray-300">Mã công việc: {jobId || "-"}</p>
          <p className="text-sm text-gray-300">Trạng thái: {jobState || "-"}</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {jobAssets.map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer" className="rounded-lg overflow-hidden border border-white/10 block">
                <img src={url} alt="Generated asset" className="w-full h-40 object-cover" />
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-6 space-y-4">
        {blocks.map((b) => (
          <div key={b.agent} className="rounded-2xl border border-white/10 bg-[#111827] p-5">
            <div className="flex items-center gap-3">
              <span className={`h-3 w-3 rounded-full ${b.status === "running" ? "bg-yellow-400 animate-pulse" : "bg-green-400"}`} />
              <h2 className="font-bold">{b.agent}</h2>
            </div>

            {b.status === "running" && <p className="mt-3 text-gray-400">Đang tạo output...</p>}

            {b.output && <pre className="mt-4 whitespace-pre-wrap text-sm text-gray-200">{b.output}</pre>}
          </div>
        ))}
      </section>
    </main>
  );
}
